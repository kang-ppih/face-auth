"""
Face-Auth IdP System - Status Check Lambda Handler

This Lambda function handles authentication status checks:
1. Session validity verification
2. Cognito token validation
3. User authentication state
4. System health information

Requirements: 2.5, 10.7
"""

import json
import boto3
import os
import sys
import logging
from typing import Dict, Any
from datetime import datetime

# Add shared directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from cognito_service import CognitoService
from dynamodb_service import DynamoDBService
from error_handler import ErrorHandler
from models import ErrorCodes, AuthenticationSession

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handle_status(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle authentication status check request
    
    This endpoint can be used to:
    - Check if a session is still valid
    - Validate a Cognito access token
    - Get current authentication state
    - Verify user account status
    
    Query Parameters:
    - session_id: Session identifier to check (optional)
    - access_token: Cognito access token to validate (optional)
    - employee_id: Employee ID to check status (optional)
    
    Args:
        event: API Gateway event containing status request
        context: Lambda context object
        
    Returns:
        API Gateway response with status information
    """
    request_id = context.aws_request_id
    
    try:
        # Get environment variables
        auth_sessions_table = os.environ.get('AUTH_SESSIONS_TABLE', 'AuthSessions')
        employee_faces_table = os.environ.get('EMPLOYEE_FACES_TABLE')
        card_templates_table = os.environ.get('CARD_TEMPLATES_TABLE')
        user_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        client_id = os.environ.get('COGNITO_CLIENT_ID')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Validate environment variables
        if not all([user_pool_id, client_id, employee_faces_table]):
            logger.error("Missing required environment variables")
            return _error_response(500, ErrorCodes.GENERIC_ERROR,
                                 "서버 설정 오류", "Missing environment variables", request_id)
        
        # Parse query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        session_id = query_params.get('session_id')
        access_token = query_params.get('access_token')
        employee_id = query_params.get('employee_id')
        
        # Also check Authorization header for Bearer token
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # At least one parameter must be provided
        if not any([session_id, access_token, employee_id]):
            logger.warning("No status check parameters provided")
            return _error_response(400, ErrorCodes.INVALID_REQUEST,
                                 "세션 ID, 액세스 토큰 또는 직원 ID가 필요합니다",
                                 "Missing session_id, access_token, or employee_id", request_id)
        
        # Initialize services
        logger.info("Initializing services for status check")
        cognito_service = CognitoService(user_pool_id, client_id, region)
        db_service = DynamoDBService(region_name=region)
        db_service.initialize_tables(card_templates_table, employee_faces_table, auth_sessions_table)
        error_handler = ErrorHandler()
        
        status_info = {
            'authenticated': False,
            'session_valid': False,
            'token_valid': False,
            'account_active': False,
            'employee_id': None,
            'session_expires_at': None,
            'last_login': None
        }
        
        # Check 1: Validate session if session_id provided
        if session_id:
            logger.info(f"Checking session validity for session_id: {session_id}")
            session = db_service.get_auth_session(session_id)
            
            if session:
                status_info['session_valid'] = session.is_valid()
                status_info['employee_id'] = session.employee_id
                status_info['session_expires_at'] = session.expires_at.isoformat()
                status_info['auth_method'] = session.auth_method
                
                if status_info['session_valid']:
                    logger.info(f"Session {session_id} is valid")
                    status_info['authenticated'] = True
                    employee_id = session.employee_id  # Use for further checks
                else:
                    logger.info(f"Session {session_id} has expired")
            else:
                logger.warning(f"Session {session_id} not found")
        
        # Check 2: Validate Cognito token if access_token provided
        if access_token:
            logger.info("Validating Cognito access token")
            is_valid, claims = cognito_service.validate_token(access_token)
            
            status_info['token_valid'] = is_valid
            
            if is_valid and claims:
                logger.info(f"Token is valid for user: {claims.get('username')}")
                status_info['authenticated'] = True
                status_info['employee_id'] = claims.get('username')
                status_info['token_expires_at'] = datetime.fromtimestamp(claims.get('exp', 0)).isoformat()
                employee_id = claims.get('username')  # Use for further checks
            else:
                logger.warning("Token validation failed")
        
        # Check 3: Get employee account status if employee_id available
        if employee_id:
            logger.info(f"Checking account status for employee {employee_id}")
            employee_record = db_service.get_employee_face_record(employee_id)
            
            if employee_record:
                status_info['account_active'] = employee_record.is_active
                status_info['employee_id'] = employee_id
                status_info['enrollment_date'] = employee_record.enrollment_date.isoformat()
                status_info['re_enrollment_count'] = employee_record.re_enrollment_count
                
                if employee_record.last_login:
                    status_info['last_login'] = employee_record.last_login.isoformat()
                
                if not employee_record.is_active:
                    logger.warning(f"Employee {employee_id} account is inactive")
                    status_info['authenticated'] = False
            else:
                logger.warning(f"Employee {employee_id} not found in database")
                status_info['account_active'] = False
        
        # Determine overall authentication status
        is_authenticated = (
            status_info['authenticated'] and
            (status_info['session_valid'] or status_info['token_valid']) and
            status_info['account_active']
        )
        
        status_info['authenticated'] = is_authenticated
        
        # Log the status check result
        logger.info(f"Status check completed: authenticated={is_authenticated}, employee_id={status_info.get('employee_id')}")
        
        # Return status response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': status_info,
                'request_id': request_id,
                'timestamp': datetime.now().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in status handler: {str(e)}", exc_info=True)
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