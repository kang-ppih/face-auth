"""
ErrorHandler Usage Examples

This file demonstrates how to use the ErrorHandler class in various scenarios
within the Face-Auth IdP system.
"""

from typing import Dict, Any
from shared.error_handler import error_handler
from shared.models import ErrorCodes


def example_enrollment_failure() -> Dict[str, Any]:
    """Example: Handle enrollment failure due to ID card format mismatch"""
    
    # Simulate enrollment processing
    request_id = "req-enroll-123"
    context = {
        "employee_id": "123456",
        "card_type": "unknown",
        "ocr_confidence": 0.45
    }
    
    # Create error response
    error_response = error_handler.handle_error(
        ErrorCodes.ID_CARD_FORMAT_MISMATCH,
        request_id,
        context
    )
    
    # User sees: "사원증 규격 불일치"
    print(f"User Message: {error_response.user_message}")
    
    # System logs: Detailed technical information
    print(f"System Reason: {error_response.system_reason}")
    
    # Check if retry is allowed
    if error_handler.is_retry_allowed(error_response.error_code):
        print("User can retry this operation")
    
    return error_response


def example_face_recognition_failure():
    """Example: Handle face recognition failure (generic message)"""
    
    request_id = "req-login-456"
    context = {
        "employee_id": "unknown",
        "confidence_score": 0.65,
        "enrolled_faces_count": 150
    }
    
    # Create error response for face not found
    error_response = error_handler.handle_error(
        ErrorCodes.FACE_NOT_FOUND,
        request_id,
        context
    )
    
    # User sees generic retry message: "밝은 곳에서 다시 시도해주세요"
    print(f"User Message: {error_response.user_message}")
    
    # System logs detailed matching information
    print(f"System Reason: {error_response.system_reason}")
    
    return error_response


def example_ad_connection_failure():
    """Example: Handle Active Directory connection failure"""
    
    request_id = "req-ad-789"
    context = {
        "ad_server": "ldaps://ad.company.com",
        "timeout_seconds": 10,
        "connection_attempt": 2
    }
    
    # Create error response
    error_response = error_handler.handle_error(
        ErrorCodes.AD_CONNECTION_ERROR,
        request_id,
        context
    )
    
    # User sees generic message (technical issue)
    print(f"User Message: {error_response.user_message}")
    
    # System logs connection details
    print(f"System Reason: {error_response.system_reason}")
    
    # Get appropriate log level
    log_level = error_handler.get_log_level(error_response.error_code)
    print(f"Log Level: {log_level}")
    
    return error_response


def example_api_response():
    """Example: Create API response dictionary"""
    
    request_id = "req-api-999"
    
    # Create error response as dictionary for API
    response_dict = error_handler.create_error_response_dict(
        ErrorCodes.ACCOUNT_DISABLED,
        request_id,
        context={"employee_id": "123456"},
        include_system_reason=False  # Don't expose internal details to client
    )
    
    # Response suitable for JSON API
    print("API Response:")
    print(response_dict)
    # {
    #     'error': 'ACCOUNT_DISABLED',
    #     'message': '계정 비활성화',
    #     'timestamp': '2024-01-15T10:30:00.123456',
    #     'request_id': 'req-api-999',
    #     'retry_allowed': False
    # }
    
    return response_dict


def example_lambda_handler_integration():
    """Example: Integration with Lambda handler"""
    
    def lambda_handler(event, context):
        """Simulated Lambda handler with error handling"""
        request_id = context.get('requestId', 'unknown')
        
        try:
            # Simulate enrollment processing
            employee_id = event.get('employee_id')
            if not employee_id:
                # Invalid request
                error_dict = error_handler.create_error_response_dict(
                    ErrorCodes.INVALID_REQUEST,
                    request_id,
                    context={"missing_field": "employee_id"}
                )
                return {
                    'statusCode': 400,
                    'body': error_dict
                }
            
            # Simulate OCR processing failure
            # ... OCR processing code ...
            
            # If card format doesn't match
            error_dict = error_handler.create_error_response_dict(
                ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                request_id,
                context={"employee_id": employee_id}
            )
            
            return {
                'statusCode': 400,
                'body': error_dict
            }
            
        except Exception as e:
            # Unexpected error - use generic error
            error_dict = error_handler.create_error_response_dict(
                ErrorCodes.GENERIC_ERROR,
                request_id,
                context={"exception": str(e)}
            )
            
            return {
                'statusCode': 500,
                'body': error_dict
            }
    
    # Test the handler
    test_event = {'employee_id': '123456'}
    test_context = {'requestId': 'test-req-123'}
    
    result = lambda_handler(test_event, test_context)
    print(f"Lambda Response: {result}")
    
    return result


def example_with_sensitive_data():
    """Example: Context sanitization with sensitive data"""
    
    request_id = "req-secure-111"
    
    # Context with sensitive information
    context = {
        "employee_id": "123456",
        "password": "secret123",  # Will be filtered out
        "token": "jwt-token-here",  # Will be filtered out
        "department": "Engineering",  # Will be included
        "face_image": b"binary-data"  # Will be filtered out
    }
    
    error_response = error_handler.handle_error(
        ErrorCodes.REGISTRATION_INFO_MISMATCH,
        request_id,
        context
    )
    
    # System reason will NOT contain password, token, or face_image
    print(f"System Reason: {error_response.system_reason}")
    # Will include: employee_id and department
    # Will NOT include: password, token, face_image
    
    return error_response


if __name__ == "__main__":
    print("=" * 60)
    print("ErrorHandler Usage Examples")
    print("=" * 60)
    
    print("\n1. Enrollment Failure (Specific Message)")
    print("-" * 60)
    example_enrollment_failure()
    
    print("\n2. Face Recognition Failure (Generic Message)")
    print("-" * 60)
    example_face_recognition_failure()
    
    print("\n3. AD Connection Failure")
    print("-" * 60)
    example_ad_connection_failure()
    
    print("\n4. API Response Format")
    print("-" * 60)
    example_api_response()
    
    print("\n5. Lambda Handler Integration")
    print("-" * 60)
    example_lambda_handler_integration()
    
    print("\n6. Sensitive Data Sanitization")
    print("-" * 60)
    example_with_sensitive_data()
