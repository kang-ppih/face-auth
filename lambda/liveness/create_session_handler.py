"""
CreateLivenessSession Lambda Handler

Creates a new Rekognition Liveness session for face verification.

Requirements: FR-1.1, FR-1.2, FR-1.3
"""

import json
import logging
import os
from typing import Dict, Any

# Import shared modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from liveness_service import LivenessService, LivenessServiceError
from error_handler import ErrorHandler
from models import ErrorResponse
from timeout_manager import TimeoutManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Livenessセッション作成ハンドラー
    
    Request:
        POST /liveness/session/create
        {
            "employee_id": "EMP001"
        }
    
    Response (200):
        {
            "session_id": "uuid-v4",
            "expires_at": "2026-02-02T10:10:00Z"
        }
    
    Response (400):
        {
            "error": "BAD_REQUEST",
            "message": "employee_id is required"
        }
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
        
    Requirements: FR-1.1, FR-1.2, FR-1.3
    """
    timeout_manager = TimeoutManager(context)
    
    logger.info(
        "CreateLivenessSession invoked",
        extra={
            'request_id': context.aws_request_id,
            'function_name': context.function_name
        }
    )
    
    # Parse request body
    try:
        body_str = event.get('body', '{}')
        if body_str is None:
            body_str = '{}'
        body = json.loads(body_str)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {e}")
        return ErrorResponse.bad_request("Invalid JSON in request body")
    
    # Validate required fields
    employee_id = body.get('employee_id')
    if not employee_id:
        logger.warning("Missing employee_id in request")
        return ErrorResponse.bad_request("employee_id is required")
    
    # Validate employee_id format (alphanumeric, max 50 chars)
    if not employee_id.isalnum() or len(employee_id) > 50:
        logger.warning(f"Invalid employee_id format: {employee_id}")
        return ErrorResponse.bad_request(
            "employee_id must be alphanumeric and max 50 characters"
        )
    
    # Create Liveness session
    try:
        # Get configuration from environment
        confidence_threshold = float(
            os.environ.get('LIVENESS_CONFIDENCE_THRESHOLD', '90.0')
        )
        
        liveness_service = LivenessService(
            confidence_threshold=confidence_threshold
        )
        
        # Create session
        result = liveness_service.create_session(employee_id)
        
        logger.info(
            "Liveness session created successfully",
            extra={
                'employee_id': employee_id,
                'session_id': result['session_id'],
                'request_id': context.aws_request_id
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',  # CORS
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps(result)
        }
        
    except LivenessServiceError as e:
        logger.error(
            f"Liveness service error: {str(e)}",
            extra={'employee_id': employee_id}
        )
        return ErrorResponse.internal_server_error(
            "Failed to create liveness session",
            details={'error': str(e)}
        )
    
    except Exception as e:
        logger.error(
            f"Unexpected error: {str(e)}",
            exc_info=True,
            extra={'employee_id': employee_id}
        )
        return ErrorResponse.internal_server_error(
            "An unexpected error occurred"
        )
