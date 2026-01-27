"""
Face-Auth IdP System - Employee Enrollment Lambda Handler

This Lambda function handles the employee enrollment process:
1. OCR processing of employee ID cards using Amazon Textract
2. Active Directory verification via Direct Connect
3. Face capture and liveness detection using Amazon Rekognition
4. Thumbnail generation and S3 storage

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
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
from shared.models import EmployeeFaceRecord, FaceData, EmployeeInfo, ErrorCodes

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_enrollment(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle employee enrollment request
    
    Flow:
    1. Process ID card with OCR (Textract)
    2. Verify employee info with Active Directory
    3. Capture face image and perform liveness detection
    4. Generate 200x200 thumbnail
    5. Store thumbnail in S3 enroll/ folder
    6. Index face in Rekognition collection
    7. Create EmployeeFaceRecord in DynamoDB
    
    Args:
        event: API Gateway event containing enrollment request
        context: Lambda context object
        
    Returns:
        API Gateway response with enrollment result
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
        
        if not id_card_image_b64 or not face_image_b64:
            logger.warning("Missing required images in request")
            return _error_response(400, ErrorCodes.INVALID_REQUEST,
                                 "社員証と顔画像が必要です", 
                                 "Missing id_card_image or face_image", request_id)
        
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
        logger.info("Initializing services for enrollment")
        ocr_service = OCRService(region_name=region)
        
        # Initialize AD Connector (Mock or Real based on environment)
        ad_server_url = os.environ.get('AD_SERVER_URL', 'ldaps://ad.company.com')
        ad_base_dn = os.environ.get('AD_BASE_DN', 'DC=company,DC=com')
        ad_timeout = int(os.environ.get('AD_TIMEOUT', '10'))
        use_mock_ad = os.environ.get('USE_MOCK_AD', 'true').lower() == 'true'
        
        ad_connector = create_ad_connector(
            use_mock=use_mock_ad,
            server_url=ad_server_url,
            base_dn=ad_base_dn,
            timeout=ad_timeout
        )
        
        face_service = FaceRecognitionService(collection_id=collection_id, region_name=region)
        thumbnail_processor = ThumbnailProcessor(bucket_name=bucket_name, region_name=region)
        error_handler = ErrorHandler()
        db_service = DynamoDBService(region_name=region)
        db_service.initialize_tables(card_templates_table, employee_faces_table, auth_sessions_table)
        
        # Step 1: Process ID card with OCR
        logger.info("Step 1: Processing ID card with OCR")
        if not timeout_manager.should_continue(buffer_seconds=2.0):
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "処理時間が超過しました",
                                 "Timeout before OCR processing", request_id)
        
        employee_info, ocr_error = ocr_service.extract_employee_info(id_card_image, db_service)
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
        
        # Step 2: Verify with Active Directory (or Mock)
        logger.info(f"Step 2: Verifying employee {employee_info.employee_id} with AD")
        if not timeout_manager.check_ad_timeout():
            logger.warning("AD timeout limit reached before verification")
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "認証サーバー接続タイムアウト",
                                 "AD timeout before verification", request_id)
        
        ad_result = ad_connector.verify_employee(employee_info.employee_id, employee_info)
        
        if not ad_result.success:
            logger.warning(f"AD verification failed: {ad_result.reason}")
            
            # Map AD errors to appropriate error codes
            if ad_result.reason == ErrorCodes.ACCOUNT_DISABLED:
                error_response = error_handler.handle_error(
                    ErrorCodes.ACCOUNT_DISABLED,
                    {'request_id': request_id, 'employee_id': employee_info.employee_id}
                )
            elif ad_result.reason == ErrorCodes.REGISTRATION_INFO_MISMATCH:
                error_response = error_handler.handle_error(
                    ErrorCodes.REGISTRATION_INFO_MISMATCH,
                    {'request_id': request_id, 'employee_id': employee_info.employee_id}
                )
            else:
                error_response = error_handler.handle_error(
                    ErrorCodes.AD_CONNECTION_ERROR,
                    {'request_id': request_id, 'detail': ad_result.error}
                )
            
            return _error_response(400, error_response.error_code,
                                 error_response.user_message,
                                 error_response.system_reason, request_id)
        
        logger.info(f"AD verification successful for {employee_info.employee_id}")
        
        # Step 3: Process face image with liveness detection
        logger.info("Step 3: Processing face image with liveness detection")
        if not timeout_manager.should_continue(buffer_seconds=3.0):
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "処理時間が超過しました",
                                 "Timeout before face processing", request_id)
        
        liveness_result = face_service.detect_liveness(face_image)
        if not liveness_result['is_live']:
            logger.warning(f"Liveness detection failed: confidence {liveness_result.get('confidence', 0)}")
            error_response = error_handler.handle_error(
                ErrorCodes.LIVENESS_FAILED,
                {'request_id': request_id, 'confidence': liveness_result.get('confidence')}
            )
            return _error_response(400, error_response.error_code,
                                 error_response.user_message,
                                 error_response.system_reason, request_id)
        
        logger.info(f"Liveness detection passed with confidence {liveness_result['confidence']}")
        
        # Step 4: Generate 200x200 thumbnail
        logger.info("Step 4: Generating thumbnail")
        thumbnail_bytes = thumbnail_processor.create_thumbnail(face_image)
        
        # Step 5: Store thumbnail in S3 enroll/ folder
        logger.info(f"Step 5: Storing thumbnail in S3 for employee {employee_info.employee_id}")
        s3_key = f"enroll/{employee_info.employee_id}/face_thumbnail.jpg"
        
        s3_client = boto3.client('s3', region_name=region)
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=thumbnail_bytes,
            ContentType='image/jpeg',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f"Thumbnail stored at s3://{bucket_name}/{s3_key}")
        
        # Step 6: Index face in Rekognition collection
        logger.info("Step 6: Indexing face in Rekognition collection")
        if not timeout_manager.should_continue(buffer_seconds=2.0):
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "処理時間が超過しました",
                                 "Timeout before face indexing", request_id)
        
        face_id = face_service.index_face(thumbnail_bytes, employee_info.employee_id)
        if not face_id:
            logger.error("Failed to index face in Rekognition")
            return _error_response(500, ErrorCodes.GENERIC_ERROR,
                                 "얼굴 등록에 실패했습니다",
                                 "Rekognition face indexing failed", request_id)
        
        logger.info(f"Face indexed with face_id: {face_id}")
        
        # Step 7: Create EmployeeFaceRecord in DynamoDB
        logger.info("Step 7: Creating EmployeeFaceRecord in DynamoDB")
        
        # Create FaceData object
        face_data = FaceData(
            face_id=face_id,
            employee_id=employee_info.employee_id,
            bounding_box=liveness_result.get('bounding_box', {}),
            confidence=liveness_result['confidence'],
            landmarks=liveness_result.get('landmarks', []),
            thumbnail_s3_key=s3_key
        )
        
        # Create EmployeeFaceRecord
        employee_record = EmployeeFaceRecord(
            employee_id=employee_info.employee_id,
            face_id=face_id,
            enrollment_date=datetime.now(),
            last_login=None,
            thumbnail_s3_key=s3_key,
            is_active=True,
            re_enrollment_count=0,
            face_data=face_data
        )
        
        # Store in DynamoDB
        success = db_service.create_employee_face_record(employee_record)
        if not success:
            logger.warning(f"Employee {employee_info.employee_id} already exists, updating record")
            # If employee already exists, update the record (re-enrollment)
            employee_record.re_enrollment_count = 1
            db_service.update_employee_face_record(employee_record)
        
        logger.info(f"Enrollment completed successfully for employee {employee_info.employee_id}")
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': '등록이 완료되었습니다',
                'employee_id': employee_info.employee_id,
                'employee_name': employee_info.name,
                'face_id': face_id,
                'request_id': request_id,
                'processing_time': timeout_manager.get_elapsed_time()
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in enrollment handler: {str(e)}", exc_info=True)
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