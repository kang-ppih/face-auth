"""
Face-Auth IdP System - Face Login Lambda Handler

This Lambda function handles face-based authentication:
1. Face liveness detection using Amazon Rekognition
2. 1:N face matching against enrolled employees
3. Authentication session creation via AWS Cognito
4. Failed attempt logging to S3

Requirements: 2.1, 2.2, 2.3, 2.4
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
from shared.face_recognition_service import FaceRecognitionService
from shared.thumbnail_processor import ThumbnailProcessor
from shared.cognito_service import CognitoService
from shared.error_handler import ErrorHandler
from shared.timeout_manager import TimeoutManager
from shared.dynamodb_service import DynamoDBService
from shared.liveness_service import LivenessService, SessionNotFoundError, SessionExpiredError
from shared.models import ErrorCodes

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_face_login(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle face-based login request
    
    Flow:
    1. Perform liveness detection on face image
    2. Search faces in Rekognition collection (1:N matching)
    3. If match found, create Cognito authentication session
    4. Update last_login timestamp in DynamoDB
    5. If no match, store failed attempt image in S3 logins/ folder
    
    Args:
        event: API Gateway event containing face login request
        context: Lambda context object
        
    Returns:
        API Gateway response with authentication result
    """
    # Initialize timeout manager
    timeout_manager = TimeoutManager()
    request_id = context.aws_request_id
    
    try:
        # Get environment variables
        bucket_name = os.environ.get('FACE_AUTH_BUCKET')
        employee_faces_table = os.environ.get('EMPLOYEE_FACES_TABLE')
        auth_sessions_table = os.environ.get('AUTH_SESSIONS_TABLE', 'AuthSessions')
        card_templates_table = os.environ.get('CARD_TEMPLATES_TABLE')
        user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        collection_id = os.environ.get('REKOGNITION_COLLECTION_ID', 'face-auth-employees')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Validate environment variables
        if not all([bucket_name, employee_faces_table, user_pool_id, client_id]):
            logger.error("Missing required environment variables")
            return _error_response(500, ErrorCodes.GENERIC_ERROR,
                                 "サーバー設定エラー", "Missing environment variables", request_id)
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Extract and validate request data
        face_image_b64 = body.get('face_image')
        liveness_session_id = body.get('liveness_session_id')  # New: Liveness session ID
        
        if not face_image_b64:
            logger.warning("Missing face image in request")
            return _error_response(400, ErrorCodes.INVALID_REQUEST,
                                 "顔画像が必要です",
                                 "Missing face_image", request_id)
        
        if not liveness_session_id:
            logger.warning("Missing liveness_session_id in request")
            return _error_response(400, ErrorCodes.INVALID_REQUEST,
                                 "Liveness検証が必要です",
                                 "Missing liveness_session_id", request_id)
        
        # Decode base64 image
        try:
            face_image = base64.b64decode(face_image_b64)
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {str(e)}")
            return _error_response(400, ErrorCodes.INVALID_REQUEST,
                                 "画像形式が正しくありません",
                                 f"Base64 decode error: {str(e)}", request_id)
        
        # Extract client info for session
        ip_address = event.get('requestContext', {}).get('identity', {}).get('sourceIp')
        user_agent = event.get('headers', {}).get('User-Agent')
        
        # Initialize services
        logger.info("Initializing services for face login")
        face_service = FaceRecognitionService(collection_id=collection_id, region_name=region)
        thumbnail_processor = ThumbnailProcessor()
        cognito_service = CognitoService(user_pool_id, client_id, region)
        error_handler = ErrorHandler()
        db_service = DynamoDBService(region_name=region)
        db_service.initialize_tables(card_templates_table, employee_faces_table, auth_sessions_table)
        
        # Step 1: Verify Liveness session (NEW - First step)
        logger.info(f"Step 1: Verifying Liveness session {liveness_session_id}")
        if not timeout_manager.should_continue(buffer_seconds=2.0):
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
        
        # Step 2: Perform 1:N face matching (removed old liveness detection)
        logger.info("Step 2: Performing 1:N face matching")
        if not timeout_manager.should_continue(buffer_seconds=3.0):
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "処理時間が超過しました",
                                 "Timeout before face matching", request_id)
        
        # Generate thumbnail for search
        thumbnail_bytes = thumbnail_processor.create_thumbnail(face_image)
        
        # Search for matching face
        matches = face_service.search_faces(thumbnail_bytes)
        
        if not matches or len(matches) == 0:
            logger.info("No face match found, storing failed attempt")
            
            # Step 3: Store failed attempt in S3 logins/ folder
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            date_folder = datetime.now().strftime('%Y-%m-%d')
            s3_key = f"logins/{date_folder}/{timestamp}_unknown.jpg"
            
            s3_client = boto3.client('s3', region_name=region)
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=thumbnail_bytes,
                ContentType='image/jpeg',
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Failed attempt stored at s3://{bucket_name}/{s3_key}")
            
            error_response = error_handler.handle_error(
                ErrorCodes.FACE_NOT_FOUND,
                {'request_id': request_id}
            )
            return _error_response(401, error_response.error_code,
                                 error_response.user_message,
                                 error_response.system_reason, request_id)
        
        # Get best match
        best_match = matches[0]
        employee_id = best_match['external_image_id']
        similarity = best_match['similarity']
        
        logger.info(f"Face match found: employee_id={employee_id}, similarity={similarity}")
        
        # Verify employee record exists and is active
        employee_record = db_service.get_employee_face_record(employee_id)
        if not employee_record or not employee_record.is_active:
            logger.warning(f"Employee {employee_id} not found or inactive")
            error_response = error_handler.handle_error(
                ErrorCodes.ACCOUNT_DISABLED,
                {'request_id': request_id, 'employee_id': employee_id}
            )
            return _error_response(401, error_response.error_code,
                                 error_response.user_message,
                                 error_response.system_reason, request_id)
        
        # Step 3: Create Cognito authentication session
        logger.info(f"Step 3: Creating authentication session for {employee_id}")
        if not timeout_manager.should_continue(buffer_seconds=2.0):
            return _error_response(408, ErrorCodes.TIMEOUT_ERROR,
                                 "処理時間が超過しました",
                                 "Timeout before session creation", request_id)
        
        session, error = cognito_service.create_authentication_session(
            employee_id=employee_id,
            auth_method='face',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if error or not session:
            logger.error(f"Failed to create authentication session: {error}")
            return _error_response(500, ErrorCodes.GENERIC_ERROR,
                                 "인증 세션 생성에 실패했습니다",
                                 f"Session creation error: {error}", request_id)
        
        # Store session in DynamoDB
        db_service.create_auth_session(session)
        
        # Step 4: Update last_login timestamp
        logger.info(f"Step 4: Updating last_login for {employee_id}")
        db_service.update_last_login(employee_id, datetime.now())
        
        logger.info(f"Face login completed successfully for employee {employee_id}")
        
        # Return success response with tokens
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'message': '로그인 성공',
                'employee_id': employee_id,
                'session_id': session.session_id,
                'access_token': session.cognito_token,
                'expires_at': session.expires_at.isoformat(),
                'similarity': similarity,
                'request_id': request_id,
                'processing_time': timeout_manager.get_elapsed_time()
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in face login handler: {str(e)}", exc_info=True)
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
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
        },
        'body': json.dumps({
            'error': error_code,
            'message': user_message,
            'request_id': request_id,
            'timestamp': datetime.now().isoformat()
        })
    }