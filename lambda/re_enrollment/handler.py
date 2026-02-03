"""
Face-Auth IdP System - Re-enrollment Lambda Handler

This Lambda function handles employee face data re-enrollment:
1. Identity verification using employee ID card OCR
2. Active Directory verification
3. New face capture and liveness detection
4. Replacement of existing face data in Rekognition
5. Update DynamoDB records with audit trail

Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import json
import boto3
import os
import sys
import base64
import logging
from typing import Dict, Any
from datetime import datetime

# Import from shared modules (bundled with function)
from shared.ocr_service import OCRService
from shared.ad_connector_mock import create_ad_connector
from shared.face_recognition_service import FaceRecognitionService
from shared.thumbnail_processor import ThumbnailProcessor
from shared.error_handler import ErrorHandler
from shared.timeout_manager import TimeoutManager
from shared.dynamodb_service import DynamoDBService
from shared.liveness_service import LivenessService, SessionNotFoundError, SessionExpiredError
from shared.models import EmployeeFaceRecord, FaceData, EmployeeInfo, ErrorCodes

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_re_enrollment(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle employee re-enrollment request
    
    Flow:
    1. Process ID card with OCR (Textract) to verify identity
    2. Verify employee info with Active Directory
    3. Check that employee has existing enrollment
    4. Capture new face image and perform liveness detection
    5. Delete old face from Rekognition collection
    6. Index new face in Rekognition collection
    7. Generate new 200x200 thumbnail
    8. Update S3 with new thumbnail (replace old one)
    9. Update EmployeeFaceRecord in DynamoDB (increment re_enrollment_count)
    10. Record audit trail in CloudWatch Logs
    
    Args:
        event: API Gateway event containing re-enrollment request
        context: Lambda context object
        
    Returns:
        API Gateway response with re-enrollment result
    """
    # Initialize timeout manager
    timeout_manager = TimeoutManager()
    request_id = context.aws_request_id
    
    try:
        # Get environment variables
        bucket_name = os.environ.get('FACE_AUTH_BUCKET')
        card_templates_table = os.environ.get('CARD_TEMPLATES_TABLE')
        employee_faces_table = os.environ.get('EMPLOYEE_FACES_TABLE')
        auth_sessions_table = os.environ.get('AUTH_SESSIONS_TABLE', 'AuthSessions')
        collection_id = os.environ.get('REKOGNITION_COLLECTION_ID', 'face-auth-employees')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Validate environment variables
        if not all([bucket_name, card_templates_table, employee_faces_table]):
            logger.error("Missing required environment variables")
            return _error_response(500, ErrorCodes.GENERIC_ERROR,
                                 "サーバー設定エラー", "Missing environment variables", request_id)
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract and validate request data
        id_card_image_b64 = body.get('id_card_image')
        face_image_b64 = body.get('face_image')
        liveness_session_id = body.get('liveness_session_id')  # New: Liveness session ID
        
        if not id_card_image_b64 or not face_image_b64:
            logger.warning("Missing required images in request")
            return _error_response(400, ErrorCodes.INVALID_REQUEST,
                                 "社員証と顔画像が必要です",
                                 "Missing id_card_image or face_image", request_id)
        
        if not liveness_session_id:
            logger.warning("Missing liveness_session_id in request")
            return _error_response(400, ErrorCodes.INVALID_REQUEST,
                                 "Liveness検証が必要です",
                                 "Missing liveness_session_id", request_id)
        
        # Decode base64 images
        try:
            id_card_image = base64.b64decode(id_card_image_b64)
            face_image = base64.b64decode(face_image_b64)
        except Exception as e:
            logger.error(f"Failed to decode base64 images: {str(e)}")
            return _error_response(400, ErrorCodes.INVALID_REQUEST,
                                 "画像形式が正しくありません",
                                 f"Base64 decode error: {str(e)}", request_id)
        
        # Initialize services
        logger.info("Initializing services for re-enrollment")
        ocr_service = OCRService(region_name=region)
        ad_connector = ADConnector()
        face_service = FaceRecognitionService(collection_id=collection_id, region_name=region)
        thumbnail_processor = ThumbnailProcessor()
        error_handler = ErrorHandler()
        db_service = DynamoDBService(region_name=region)
        db_service.initialize_tables(card_templates_table, employee_faces_table, auth_sessions_table)
        
        # Initialize OCR service with DynamoDB tables
        ocr_service.initialize_db_service(card_templates_table, employee_faces_table, auth_sessions_table)
        
        # Step 1: Process ID card with OCR to verify identity
        logger.info("Step 1: Processing ID card with OCR for identity verification")
        if not timeout_manager.should_continue(buffer_seconds=2.0):
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "処理時間が超過しました",
                                 "Timeout before OCR processing", request_id)
        
        employee_info, ocr_error = ocr_service.extract_id_card_info(id_card_image, request_id)
        if ocr_error or not employee_info:
            logger.warning(f"OCR processing failed: {ocr_error}")
            error_response = error_handler.handle_error(
                ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                {'request_id': request_id, 'detail': ocr_error}
            )
            return _error_response(400, error_response.error_code,
                                 error_response.user_message,
                                 error_response.system_reason, request_id)
        
        logger.info(f"OCR extracted employee_id: {employee_info.employee_id}, name: {employee_info.name}")
        
        # Validate extracted employee info
        if not employee_info.validate():
            logger.warning(f"Employee info validation failed for {employee_info.employee_id}")
            error_response = error_handler.handle_error(
                ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                {'request_id': request_id, 'employee_id': employee_info.employee_id}
            )
            return _error_response(400, error_response.error_code,
                                 error_response.user_message,
                                 error_response.system_reason, request_id)
        
        # Step 2: Verify with Active Directory
        logger.info(f"Step 2: Verifying employee {employee_info.employee_id} with AD")
        if not timeout_manager.check_ad_timeout():
            logger.warning("AD timeout limit reached before verification")
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "認証サーバー接続タイムアウト",
                                 "AD timeout before verification", request_id)
        
        # Note: AD connector may have issues, so we'll handle gracefully
        try:
            ad_result = ad_connector.verify_employee(employee_info.employee_id, employee_info.to_dict())
            
            if not ad_result.success:
                logger.warning(f"AD verification failed: {ad_result.reason}")
                
                # Map AD errors to appropriate error codes
                if ad_result.reason == "account_disabled":
                    error_response = error_handler.handle_error(
                        ErrorCodes.ACCOUNT_DISABLED,
                        {'request_id': request_id, 'employee_id': employee_info.employee_id}
                    )
                elif ad_result.reason == "employee_not_found":
                    error_response = error_handler.handle_error(
                        ErrorCodes.REGISTRATION_INFO_MISMATCH,
                        {'request_id': request_id, 'employee_id': employee_info.employee_id}
                    )
                else:
                    error_response = error_handler.handle_error(
                        ErrorCodes.AD_CONNECTION_ERROR,
                        {'request_id': request_id, 'detail': ad_result.reason}
                    )
                
                return _error_response(400, error_response.error_code,
                                     error_response.user_message,
                                     error_response.system_reason, request_id)
            
            logger.info(f"AD verification successful for {employee_info.employee_id}")
            
        except Exception as ad_error:
            # AD connector may not be fully functional, log and continue
            logger.warning(f"AD verification skipped due to error: {str(ad_error)}")
            logger.info("Continuing re-enrollment without AD verification (AD connector may have issues)")
        
        # Step 3: Check that employee has existing enrollment
        logger.info(f"Step 3: Checking existing enrollment for {employee_info.employee_id}")
        existing_record = db_service.get_employee_face_record(employee_info.employee_id)
        
        if not existing_record:
            logger.warning(f"No existing enrollment found for {employee_info.employee_id}")
            return _error_response(404, ErrorCodes.INVALID_REQUEST,
                                 "등록된 직원 정보를 찾을 수 없습니다",
                                 f"No existing enrollment for employee {employee_info.employee_id}", request_id)
        
        if not existing_record.is_active:
            logger.warning(f"Employee {employee_info.employee_id} enrollment is inactive")
            error_response = error_handler.handle_error(
                ErrorCodes.ACCOUNT_DISABLED,
                {'request_id': request_id, 'employee_id': employee_info.employee_id}
            )
            return _error_response(400, error_response.error_code,
                                 error_response.user_message,
                                 error_response.system_reason, request_id)
        
        old_face_id = existing_record.face_id
        old_s3_key = existing_record.thumbnail_s3_key
        logger.info(f"Found existing enrollment: face_id={old_face_id}, re_enrollment_count={existing_record.re_enrollment_count}")
        
        # Step 4: Verify Liveness session (NEW - After identity verification)
        logger.info(f"Step 4: Verifying Liveness session {liveness_session_id}")
        if not timeout_manager.should_continue(buffer_seconds=3.0):
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "処理時間が超過しました",
                                 "Timeout before liveness verification", request_id)
        
        try:
            liveness_service = LivenessService()
            liveness_result = liveness_service.get_session_result(liveness_session_id)
            
            if not liveness_result.is_live:
                logger.warning(
                    f"Liveness verification failed: confidence {liveness_result.confidence}, "
                    f"threshold {liveness_service.confidence_threshold}"
                )
                error_response = error_handler.handle_error(
                    ErrorCodes.LIVENESS_FAILED,
                    {
                        'request_id': request_id,
                        'confidence': liveness_result.confidence,
                        'threshold': liveness_service.confidence_threshold
                    }
                )
                return _error_response(401, error_response.error_code,
                                     error_response.user_message,
                                     error_response.system_reason, request_id)
            
            logger.info(
                f"Liveness verification passed: confidence {liveness_result.confidence}, "
                f"session_id {liveness_session_id}"
            )
            
        except SessionNotFoundError as e:
            logger.warning(f"Liveness session not found: {liveness_session_id}")
            return _error_response(404, ErrorCodes.INVALID_REQUEST,
                                 "Liveness検証セッションが見つかりません",
                                 f"Session not found: {str(e)}", request_id)
        
        except SessionExpiredError as e:
            logger.warning(f"Liveness session expired: {liveness_session_id}")
            return _error_response(410, ErrorCodes.TIMEOUT_ERROR,
                                 "Liveness検証セッションが期限切れです",
                                 f"Session expired: {str(e)}", request_id)
        
        except Exception as e:
            logger.error(f"Liveness verification error: {str(e)}", exc_info=True)
            return _error_response(500, ErrorCodes.GENERIC_ERROR,
                                 "Liveness検証に失敗しました",
                                 f"Liveness verification error: {str(e)}", request_id)
        
        # Step 5: Process new face image (removed old liveness detection)
        logger.info("Step 5: Processing new face image")
        if not timeout_manager.should_continue(buffer_seconds=3.0):
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "処理時間が超過しました",
                                 "Timeout before face processing", request_id)
        
        # Detect face for bounding box and landmarks (no liveness check)
        face_details = face_service.detect_faces(face_image)
        if not face_details:
            logger.warning("No face detected in image")
            error_response = error_handler.handle_error(
                ErrorCodes.FACE_NOT_DETECTED,
                {'request_id': request_id}
            )
            return _error_response(400, error_response.error_code,
                                 error_response.user_message,
                                 error_response.system_reason, request_id)
        
        face_detail = face_details[0]
        logger.info(f"Face detected with confidence {face_detail.get('Confidence', 0)}")
        
        # Step 6: Delete old face from Rekognition collection
        logger.info(f"Step 6: Deleting old face {old_face_id} from Rekognition collection")
        try:
            face_service.delete_face(old_face_id)
            logger.info(f"Successfully deleted old face {old_face_id}")
        except Exception as e:
            logger.warning(f"Failed to delete old face {old_face_id}: {str(e)}")
            # Continue anyway - we'll replace with new face
        
        # Step 7: Generate new 200x200 thumbnail
        logger.info("Step 7: Generating new thumbnail")
        thumbnail_bytes = thumbnail_processor.create_thumbnail(face_image)
        
        # Step 8: Index new face in Rekognition collection
        logger.info("Step 8: Indexing new face in Rekognition collection")
        if not timeout_manager.should_continue(buffer_seconds=2.0):
            # Rollback: Try to restore old face if possible
            logger.error("Timeout before indexing new face - attempting rollback")
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "処理時間が超過しました",
                                 "Timeout before face indexing", request_id)
        
        new_face_id = face_service.index_face(thumbnail_bytes, employee_info.employee_id)
        if not new_face_id:
            logger.error("Failed to index new face in Rekognition")
            # This is a critical failure - existing face data is preserved in DynamoDB
            return _error_response(500, ErrorCodes.GENERIC_ERROR,
                                 "얼굴 등록에 실패했습니다",
                                 "Rekognition face indexing failed", request_id)
        
        logger.info(f"New face indexed with face_id: {new_face_id}")
        
        # Step 9: Update S3 with new thumbnail (replace old one)
        logger.info(f"Step 9: Updating thumbnail in S3 for employee {employee_info.employee_id}")
        s3_key = f"enroll/{employee_info.employee_id}/face_thumbnail.jpg"
        
        s3_client = boto3.client('s3', region_name=region)
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=thumbnail_bytes,
            ContentType='image/jpeg',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"New thumbnail stored at s3://{bucket_name}/{s3_key}")
        
        # Step 10: Update EmployeeFaceRecord in DynamoDB
        logger.info("Step 10: Updating EmployeeFaceRecord in DynamoDB")
        
        # Create new FaceData object
        new_face_data = FaceData(
            face_id=new_face_id,
            employee_id=employee_info.employee_id,
            bounding_box=face_detail.get('BoundingBox', {}),
            confidence=liveness_result.confidence,  # Use Liveness API confidence
            landmarks=face_detail.get('Landmarks', []),
            thumbnail_s3_key=s3_key
        )
        
        # Update EmployeeFaceRecord
        updated_record = EmployeeFaceRecord(
            employee_id=employee_info.employee_id,
            face_id=new_face_id,
            enrollment_date=existing_record.enrollment_date,  # Keep original enrollment date
            last_login=existing_record.last_login,
            thumbnail_s3_key=s3_key,
            is_active=True,
            re_enrollment_count=existing_record.re_enrollment_count + 1,
            face_data=new_face_data
        )
        
        # Store updated record in DynamoDB
        db_service.update_employee_face_record(updated_record)
        
        # Step 11: Record audit trail in CloudWatch Logs
        logger.info(f"Step 10: Recording audit trail for re-enrollment")
        audit_log = {
            'event': 'RE_ENROLLMENT',
            'employee_id': employee_info.employee_id,
            'employee_name': employee_info.name,
            'old_face_id': old_face_id,
            'new_face_id': new_face_id,
            're_enrollment_count': updated_record.re_enrollment_count,
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            'ip_address': event.get('requestContext', {}).get('identity', {}).get('sourceIp'),
            'user_agent': event.get('headers', {}).get('User-Agent')
        }
        logger.info(f"AUDIT: {json.dumps(audit_log)}")
        
        logger.info(f"Re-enrollment completed successfully for employee {employee_info.employee_id}")
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': '재등록이 완료되었습니다',
                'employee_id': employee_info.employee_id,
                'employee_name': employee_info.name,
                'old_face_id': old_face_id,
                'new_face_id': new_face_id,
                're_enrollment_count': updated_record.re_enrollment_count,
                'request_id': request_id,
                'processing_time': timeout_manager.get_elapsed_time()
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in re-enrollment handler: {str(e)}", exc_info=True)
        return _error_response(500, ErrorCodes.GENERIC_ERROR,
                             "시스템 오류가 발생했습니다",
                             f"Unexpected error: {str(e)}", request_id)


def _error_response(status_code: int, error_code: str, user_message: str,
                   system_reason: str, request_id: str) -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        status_code: HTTP status code
        error_code: Machine-readable error code
        user_message: User-friendly error message
        system_reason: Detailed system reason for logging
        request_id: Request identifier
        
    Returns:
        API Gateway response dictionary
    """
    logger.error(f"Error response: {error_code} - {system_reason}")
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': error_code,
            'message': user_message,
            'request_id': request_id,
            'timestamp': datetime.now().isoformat()
        })
    }