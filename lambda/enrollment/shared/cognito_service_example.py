"""
Example usage of CognitoService in Lambda functions

This module demonstrates how to integrate CognitoService into
the Face-Auth Lambda handlers for user authentication and session management.

Requirements: 2.3, 3.5
"""

import os
import logging
from typing import Dict, Any, Optional

from cognito_service import CognitoService, create_cognito_service_from_env
from dynamodb_service import DynamoDBService
from models import AuthenticationSession

logger = logging.getLogger(__name__)


def example_face_login_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example: Face login Lambda handler with Cognito integration
    
    This shows how to:
    1. Perform face recognition (assumed successful)
    2. Create Cognito user and generate tokens
    3. Store session in DynamoDB
    4. Return authentication response
    """
    try:
        # Initialize services
        cognito_service = create_cognito_service_from_env()
        db_service = DynamoDBService()
        db_service.initialize_tables(
            card_templates_table_name=os.getenv('CARD_TEMPLATES_TABLE'),
            employee_faces_table_name=os.getenv('EMPLOYEE_FACES_TABLE'),
            auth_sessions_table_name=os.getenv('AUTH_SESSIONS_TABLE')
        )
        
        # Extract request data
        employee_id = event.get('employee_id')  # From face recognition result
        ip_address = event.get('requestContext', {}).get('identity', {}).get('sourceIp')
        user_agent = event.get('headers', {}).get('User-Agent')
        
        # Create authentication session with Cognito
        session, error = cognito_service.create_authentication_session(
            employee_id=employee_id,
            auth_method='face',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if error or not session:
            logger.error(f"Failed to create authentication session: {error}")
            return {
                'statusCode': 500,
                'body': {
                    'error': 'AUTHENTICATION_FAILED',
                    'message': '인증에 실패했습니다'
                }
            }
        
        # Store session in DynamoDB
        db_service.create_auth_session(session)
        
        # Update last login timestamp
        from datetime import datetime
        db_service.update_last_login(employee_id, datetime.now())
        
        # Return success response with tokens
        return {
            'statusCode': 200,
            'body': {
                'success': True,
                'session_id': session.session_id,
                'access_token': session.cognito_token,
                'expires_at': session.expires_at.isoformat(),
                'employee_id': employee_id
            }
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in face login: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'INTERNAL_ERROR',
                'message': '밝은 곳에서 다시 시도해주세요'
            }
        }


def example_emergency_auth_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example: Emergency authentication Lambda handler with Cognito integration
    
    This shows how to:
    1. Verify ID card OCR and AD password (assumed successful)
    2. Create Cognito user and generate tokens
    3. Store session in DynamoDB
    4. Return authentication response
    """
    try:
        # Initialize services
        cognito_service = create_cognito_service_from_env()
        db_service = DynamoDBService()
        db_service.initialize_tables(
            card_templates_table_name=os.getenv('CARD_TEMPLATES_TABLE'),
            employee_faces_table_name=os.getenv('EMPLOYEE_FACES_TABLE'),
            auth_sessions_table_name=os.getenv('AUTH_SESSIONS_TABLE')
        )
        
        # Extract request data
        employee_id = event.get('employee_id')  # From OCR result
        employee_name = event.get('employee_name')  # From OCR result
        ip_address = event.get('requestContext', {}).get('identity', {}).get('sourceIp')
        user_agent = event.get('headers', {}).get('User-Agent')
        
        # Create authentication session with Cognito
        session, error = cognito_service.create_authentication_session(
            employee_id=employee_id,
            auth_method='emergency',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if error or not session:
            logger.error(f"Failed to create authentication session: {error}")
            return {
                'statusCode': 500,
                'body': {
                    'error': 'AUTHENTICATION_FAILED',
                    'message': '인증에 실패했습니다'
                }
            }
        
        # Store session in DynamoDB
        db_service.create_auth_session(session)
        
        # Return success response with tokens
        return {
            'statusCode': 200,
            'body': {
                'success': True,
                'session_id': session.session_id,
                'access_token': session.cognito_token,
                'expires_at': session.expires_at.isoformat(),
                'employee_id': employee_id
            }
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in emergency auth: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'INTERNAL_ERROR',
                'message': '밝은 곳에서 다시 시도해주세요'
            }
        }


def example_token_validation_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example: Token validation handler
    
    This shows how to validate JWT tokens from client requests
    """
    try:
        # Initialize Cognito service
        cognito_service = create_cognito_service_from_env()
        
        # Extract token from Authorization header
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'body': {
                    'error': 'UNAUTHORIZED',
                    'message': '인증이 필요합니다'
                }
            }
        
        access_token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Validate token
        is_valid, claims = cognito_service.validate_token(access_token)
        
        if not is_valid:
            return {
                'statusCode': 401,
                'body': {
                    'error': 'INVALID_TOKEN',
                    'message': '유효하지 않은 토큰입니다'
                }
            }
        
        # Token is valid, return user info
        return {
            'statusCode': 200,
            'body': {
                'valid': True,
                'employee_id': claims.get('username'),
                'expires_at': claims.get('exp')
            }
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in token validation: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'INTERNAL_ERROR',
                'message': '토큰 검증에 실패했습니다'
            }
        }


def example_logout_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example: Logout handler
    
    This shows how to revoke user sessions and delete from DynamoDB
    """
    try:
        # Initialize services
        cognito_service = create_cognito_service_from_env()
        db_service = DynamoDBService()
        db_service.initialize_tables(
            card_templates_table_name=os.getenv('CARD_TEMPLATES_TABLE'),
            employee_faces_table_name=os.getenv('EMPLOYEE_FACES_TABLE'),
            auth_sessions_table_name=os.getenv('AUTH_SESSIONS_TABLE')
        )
        
        # Extract data
        employee_id = event.get('employee_id')
        session_id = event.get('session_id')
        
        # Revoke all Cognito sessions for the user
        success, error = cognito_service.revoke_user_sessions(employee_id)
        
        if not success:
            logger.warning(f"Failed to revoke Cognito sessions: {error}")
        
        # Delete session from DynamoDB
        if session_id:
            db_service.delete_auth_session(session_id)
        
        return {
            'statusCode': 200,
            'body': {
                'success': True,
                'message': '로그아웃되었습니다'
            }
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in logout: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'INTERNAL_ERROR',
                'message': '로그아웃에 실패했습니다'
            }
        }


def example_enrollment_with_cognito(employee_id: str, employee_name: str) -> bool:
    """
    Example: Create Cognito user during enrollment
    
    This shows how to create a Cognito user when enrolling a new employee
    """
    try:
        cognito_service = create_cognito_service_from_env()
        
        # Create or get Cognito user
        success, error = cognito_service.create_or_get_user(employee_id, employee_name)
        
        if not success:
            logger.error(f"Failed to create Cognito user: {error}")
            return False
        
        logger.info(f"Successfully created/verified Cognito user for {employee_id}")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error creating Cognito user: {str(e)}")
        return False


# Usage notes:
"""
1. Face Login Flow:
   - Perform face recognition to identify employee
   - Call cognito_service.create_authentication_session()
   - Store session in DynamoDB
   - Return access token to client

2. Emergency Auth Flow:
   - Verify ID card OCR and AD password
   - Call cognito_service.create_authentication_session()
   - Store session in DynamoDB
   - Return access token to client

3. Token Validation:
   - Extract token from Authorization header
   - Call cognito_service.validate_token()
   - Use claims to authorize request

4. Enrollment:
   - After successful ID card verification and face capture
   - Call cognito_service.create_or_get_user()
   - User is ready for future authentication

5. Session Management:
   - Sessions are stored in both Cognito and DynamoDB
   - Cognito handles JWT token lifecycle
   - DynamoDB provides additional session metadata
   - Use TTL on DynamoDB sessions for automatic cleanup
"""
