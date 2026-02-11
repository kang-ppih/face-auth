"""
GetLivenessResult Lambda Handler

Retrieves and evaluates Rekognition Liveness session results.

Requirements: FR-1.4, FR-3
"""

import json
import logging
import os
from typing import Dict, Any

# Import shared modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))

from liveness_service import (
    LivenessService,
    LivenessServiceError,
    SessionNotFoundError,
    SessionExpiredError
)
from error_handler import ErrorHandler
from models import ErrorResponse
from timeout_manager import TimeoutManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Livenessセッション結果取得ハンドラー
    
    Request:
        GET /liveness/session/{sessionId}/result
    
    Response (200):
        {
            "session_id": "uuid-v4",
            "is_live": true,
            "confidence": 95.5,
            "status": "SUCCESS"
        }
    
    Response (404):
        {
            "error": "NOT_FOUND",
            "message": "Session not found or expired"
        }
    
    Response (401):
        {
            "error": "UNAUTHORIZED",
            "message": "Liveness verification failed",
            "details": {
                "confidence": 75.2,
                "threshold": 90.0
            }
        }
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response
        
    Requirements: FR-1.4, FR-3
    """
    timeout_manager = TimeoutManager(context)
    
    logger.info(
        "GetLivenessResult invoked",
        extra={
            'request_id': context.aws_request_id,
            'function_name': context.function_name
        }
    )
    
    # Get session_id from path parameters
    path_parameters = event.get('pathParameters', {})
    session_id = path_parameters.get('sessionId')
    
    if not session_id:
        logger.warning("Missing sessionId in path parameters")
        return ErrorResponse.bad_request("sessionId is required")
    
    # Get Liveness session result
    try:
        liveness_service = LivenessService()
        
        # Get result
        result = liveness_service.get_session_result(session_id)
        
        # If liveness verification failed, return 401
        if not result.is_live:
            logger.warning(
                "Liveness verification failed",
                extra={
                    'session_id': session_id,
                    'confidence': result.confidence,
                    'threshold': liveness_service.confidence_threshold
                }
            )
            return ErrorResponse.unauthorized(
                "Liveness verification failed",
                details={
                    'confidence': result.confidence,
                    'threshold': liveness_service.confidence_threshold,
                    'reason': result.error_message
                }
            )
        
        logger.info(
            "Liveness verification successful",
            extra={
                'session_id': session_id,
                'confidence': result.confidence,
                'request_id': context.aws_request_id
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',  # CORS
                'Access-Control-Allow-Credentials': 'true'
            },
            'body': json.dumps({
                'session_id': result.session_id,
                'is_live': result.is_live,
                'confidence': result.confidence,
                'status': result.status
            })
        }
        
    except SessionNotFoundError as e:
        logger.warning(f"Session not found: {session_id}")
        return ErrorResponse.not_found(
            "Session not found or expired",
            details={'session_id': session_id}
        )
    
    except SessionExpiredError as e:
        logger.warning(f"Session expired: {session_id}")
        return ErrorResponse.gone(
            "Session has expired",
            details={'session_id': session_id}
        )
    
    except LivenessServiceError as e:
        logger.error(
            f"Liveness service error: {str(e)}",
            extra={'session_id': session_id}
        )
        return ErrorResponse.internal_server_error(
            "Failed to get liveness session result",
            details={'error': str(e)}
        )
    
    except Exception as e:
        logger.error(
            f"Unexpected error: {str(e)}",
            exc_info=True,
            extra={'session_id': session_id}
        )
        return ErrorResponse.internal_server_error(
            "An unexpected error occurred"
        )
