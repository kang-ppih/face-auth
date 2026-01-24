"""
Unit tests for ErrorHandler class

Tests cover:
- Specific error message handling (사원증 규격 불일치, 등록 정보 불일치, 계정 비활성화)
- Generic error message handling ("밝은 곳에서 다시 시도해주세요")
- System reason and user message separation
- Context sanitization
- Retry policy management
- Log level determination

Requirements: 1.6, 1.7, 1.8, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

import pytest
from datetime import datetime
import sys
import os

# Add lambda directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from shared.error_handler import ErrorHandler, error_handler
from shared.models import ErrorCodes, ErrorResponse


class TestErrorHandler:
    """Test suite for ErrorHandler class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = ErrorHandler()
        self.test_request_id = "test-request-123"
    
    # Test specific error messages (Requirements 1.6, 1.7, 1.8, 8.2, 8.3, 8.4)
    
    def test_id_card_format_mismatch_error(self):
        """Test ID card format mismatch returns specific Korean message"""
        error_response = self.handler.handle_error(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            self.test_request_id
        )
        
        assert error_response.error_code == ErrorCodes.ID_CARD_FORMAT_MISMATCH
        assert error_response.user_message == "사원증 규격 불일치"
        assert "Card_Template" in error_response.system_reason
        assert error_response.request_id == self.test_request_id
        assert isinstance(error_response.timestamp, datetime)
    
    def test_registration_info_mismatch_error(self):
        """Test registration info mismatch returns specific Korean message"""
        error_response = self.handler.handle_error(
            ErrorCodes.REGISTRATION_INFO_MISMATCH,
            self.test_request_id
        )
        
        assert error_response.error_code == ErrorCodes.REGISTRATION_INFO_MISMATCH
        assert error_response.user_message == "등록 정보 불일치"
        assert "Active Directory" in error_response.system_reason
        assert error_response.request_id == self.test_request_id
    
    def test_account_disabled_error(self):
        """Test account disabled returns specific Korean message"""
        error_response = self.handler.handle_error(
            ErrorCodes.ACCOUNT_DISABLED,
            self.test_request_id
        )
        
        assert error_response.error_code == ErrorCodes.ACCOUNT_DISABLED
        assert error_response.user_message == "계정 비활성화"
        assert "disabled" in error_response.system_reason.lower()
        assert error_response.request_id == self.test_request_id
    
    # Test generic error messages (Requirements 2.7, 3.7, 8.5)
    
    def test_liveness_failed_generic_message(self):
        """Test liveness failure returns generic retry message"""
        error_response = self.handler.handle_error(
            ErrorCodes.LIVENESS_FAILED,
            self.test_request_id
        )
        
        assert error_response.error_code == ErrorCodes.LIVENESS_FAILED
        assert error_response.user_message == "밝은 곳에서 다시 시도해주세요"
        assert "Liveness" in error_response.system_reason
        assert "90%" in error_response.system_reason
    
    def test_face_not_found_generic_message(self):
        """Test face not found returns generic retry message"""
        error_response = self.handler.handle_error(
            ErrorCodes.FACE_NOT_FOUND,
            self.test_request_id
        )
        
        assert error_response.error_code == ErrorCodes.FACE_NOT_FOUND
        assert error_response.user_message == "밝은 곳에서 다시 시도해주세요"
        assert "1:N matching" in error_response.system_reason
    
    def test_ad_connection_error_generic_message(self):
        """Test AD connection error returns generic retry message"""
        error_response = self.handler.handle_error(
            ErrorCodes.AD_CONNECTION_ERROR,
            self.test_request_id
        )
        
        assert error_response.error_code == ErrorCodes.AD_CONNECTION_ERROR
        assert error_response.user_message == "밝은 곳에서 다시 시도해주세요"
        assert "Active Directory" in error_response.system_reason
        assert "10 second" in error_response.system_reason
    
    def test_timeout_error_generic_message(self):
        """Test timeout error returns generic retry message"""
        error_response = self.handler.handle_error(
            ErrorCodes.TIMEOUT_ERROR,
            self.test_request_id
        )
        
        assert error_response.error_code == ErrorCodes.TIMEOUT_ERROR
        assert error_response.user_message == "밝은 곳에서 다시 시도해주세요"
        assert "timeout" in error_response.system_reason.lower()
    
    def test_generic_error_message(self):
        """Test generic error returns generic retry message"""
        error_response = self.handler.handle_error(
            ErrorCodes.GENERIC_ERROR,
            self.test_request_id
        )
        
        assert error_response.error_code == ErrorCodes.GENERIC_ERROR
        assert error_response.user_message == "밝은 곳에서 다시 시도해주세요"
        assert "technical error" in error_response.system_reason.lower()
    
    # Test system_reason and user_message separation (Requirement 8.6)
    
    def test_system_reason_user_message_separation(self):
        """Test that system_reason and user_message are properly separated"""
        error_response = self.handler.handle_error(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            self.test_request_id
        )
        
        # User message should be simple Korean text
        assert error_response.user_message == "사원증 규격 불일치"
        assert len(error_response.user_message) < 50
        
        # System reason should be detailed English technical description
        assert len(error_response.system_reason) > len(error_response.user_message)
        assert "Card_Template" in error_response.system_reason
        
        # They should be different
        assert error_response.user_message != error_response.system_reason
    
    def test_system_reason_includes_context(self):
        """Test that system_reason includes context information"""
        context = {
            "employee_id": "123456",
            "card_type": "standard",
            "attempt_number": 2
        }
        
        error_response = self.handler.handle_error(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            self.test_request_id,
            context
        )
        
        # System reason should include context
        assert "employee_id=123456" in error_response.system_reason
        assert "card_type=standard" in error_response.system_reason
        assert "attempt_number=2" in error_response.system_reason
        assert "Context:" in error_response.system_reason
    
    def test_context_sanitization(self):
        """Test that sensitive information is removed from context"""
        context = {
            "employee_id": "123456",
            "password": "secret123",
            "token": "jwt-token-here",
            "cognito_token": "cognito-token",
            "face_image": b"binary-data",
            "department": "Engineering"
        }
        
        error_response = self.handler.handle_error(
            ErrorCodes.REGISTRATION_INFO_MISMATCH,
            self.test_request_id,
            context
        )
        
        # Sensitive fields should not appear in system reason
        assert "secret123" not in error_response.system_reason
        assert "jwt-token" not in error_response.system_reason
        assert "cognito-token" not in error_response.system_reason
        assert "binary-data" not in error_response.system_reason
        
        # Non-sensitive fields should appear
        assert "employee_id=123456" in error_response.system_reason
        assert "department=Engineering" in error_response.system_reason
    
    # Test retry policy management
    
    def test_retry_allowed_for_technical_errors(self):
        """Test that retry is allowed for technical errors"""
        technical_errors = [
            ErrorCodes.LIVENESS_FAILED,
            ErrorCodes.FACE_NOT_FOUND,
            ErrorCodes.AD_CONNECTION_ERROR,
            ErrorCodes.TIMEOUT_ERROR,
            ErrorCodes.GENERIC_ERROR
        ]
        
        for error_code in technical_errors:
            assert self.handler.is_retry_allowed(error_code) is True
    
    def test_retry_allowed_for_system_judgment_errors(self):
        """Test that retry is allowed for system judgment errors"""
        judgment_errors = [
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            ErrorCodes.REGISTRATION_INFO_MISMATCH
        ]
        
        for error_code in judgment_errors:
            assert self.handler.is_retry_allowed(error_code) is True
    
    def test_retry_not_allowed_for_account_disabled(self):
        """Test that retry is not allowed for disabled accounts"""
        assert self.handler.is_retry_allowed(ErrorCodes.ACCOUNT_DISABLED) is False
    
    def test_retry_not_allowed_for_invalid_request(self):
        """Test that retry is not allowed for invalid requests"""
        assert self.handler.is_retry_allowed(ErrorCodes.INVALID_REQUEST) is False
    
    # Test log level determination
    
    def test_log_level_for_system_judgment_errors(self):
        """Test log levels for system judgment errors"""
        assert self.handler.get_log_level(ErrorCodes.ID_CARD_FORMAT_MISMATCH) == "WARNING"
        assert self.handler.get_log_level(ErrorCodes.REGISTRATION_INFO_MISMATCH) == "WARNING"
        assert self.handler.get_log_level(ErrorCodes.ACCOUNT_DISABLED) == "WARNING"
    
    def test_log_level_for_technical_errors(self):
        """Test log levels for technical errors"""
        assert self.handler.get_log_level(ErrorCodes.LIVENESS_FAILED) == "INFO"
        assert self.handler.get_log_level(ErrorCodes.AD_CONNECTION_ERROR) == "ERROR"
        assert self.handler.get_log_level(ErrorCodes.TIMEOUT_ERROR) == "ERROR"
    
    # Test error response dictionary creation
    
    def test_create_error_response_dict(self):
        """Test creating error response as dictionary"""
        response_dict = self.handler.create_error_response_dict(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            self.test_request_id
        )
        
        assert response_dict['error'] == ErrorCodes.ID_CARD_FORMAT_MISMATCH
        assert response_dict['message'] == "사원증 규격 불일치"
        assert response_dict['request_id'] == self.test_request_id
        assert 'timestamp' in response_dict
        assert response_dict['retry_allowed'] is True
        
        # System reason should not be included by default
        assert 'system_reason' not in response_dict
    
    def test_create_error_response_dict_with_system_reason(self):
        """Test creating error response dict with system reason for debugging"""
        response_dict = self.handler.create_error_response_dict(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            self.test_request_id,
            include_system_reason=True
        )
        
        # System reason should be included when requested
        assert 'system_reason' in response_dict
        assert "Card_Template" in response_dict['system_reason']
    
    def test_create_error_response_dict_with_context(self):
        """Test creating error response dict with context"""
        context = {"employee_id": "123456"}
        
        response_dict = self.handler.create_error_response_dict(
            ErrorCodes.REGISTRATION_INFO_MISMATCH,
            self.test_request_id,
            context=context,
            include_system_reason=True
        )
        
        assert "employee_id=123456" in response_dict['system_reason']
    
    # Test unknown error code handling
    
    def test_unknown_error_code_defaults_to_generic(self):
        """Test that unknown error codes default to generic error"""
        error_response = self.handler.handle_error(
            "UNKNOWN_ERROR_CODE",
            self.test_request_id
        )
        
        assert error_response.user_message == "밝은 곳에서 다시 시도해주세요"
        assert "Unknown error code" in error_response.system_reason
        assert self.handler.is_retry_allowed("UNKNOWN_ERROR_CODE") is True
    
    # Test ErrorResponse to_dict method
    
    def test_error_response_to_dict(self):
        """Test ErrorResponse to_dict conversion"""
        error_response = self.handler.handle_error(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            self.test_request_id
        )
        
        response_dict = error_response.to_dict()
        
        assert response_dict['error'] == ErrorCodes.ID_CARD_FORMAT_MISMATCH
        assert response_dict['message'] == "사원증 규격 불일치"
        assert response_dict['request_id'] == self.test_request_id
        assert 'timestamp' in response_dict
        
        # Verify timestamp is ISO format string
        assert isinstance(response_dict['timestamp'], str)
        datetime.fromisoformat(response_dict['timestamp'])  # Should not raise
    
    # Test singleton instance
    
    def test_singleton_error_handler_instance(self):
        """Test that singleton error_handler instance works correctly"""
        error_response = error_handler.handle_error(
            ErrorCodes.LIVENESS_FAILED,
            self.test_request_id
        )
        
        assert error_response.user_message == "밝은 곳에서 다시 시도해주세요"
        assert error_handler.is_retry_allowed(ErrorCodes.LIVENESS_FAILED) is True
    
    # Edge cases
    
    def test_empty_context(self):
        """Test handling with empty context"""
        error_response = self.handler.handle_error(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            self.test_request_id,
            context={}
        )
        
        # Should not include "Context:" when context is empty
        assert error_response.system_reason
        assert error_response.user_message == "사원증 규격 불일치"
    
    def test_none_context(self):
        """Test handling with None context"""
        error_response = self.handler.handle_error(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            self.test_request_id,
            context=None
        )
        
        # Should work without context
        assert error_response.system_reason
        assert error_response.user_message == "사원증 규격 불일치"
    
    def test_all_error_codes_have_mappings(self):
        """Test that all defined error codes have proper mappings"""
        error_codes = [
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            ErrorCodes.REGISTRATION_INFO_MISMATCH,
            ErrorCodes.ACCOUNT_DISABLED,
            ErrorCodes.LIVENESS_FAILED,
            ErrorCodes.FACE_NOT_FOUND,
            ErrorCodes.AD_CONNECTION_ERROR,
            ErrorCodes.TIMEOUT_ERROR,
            ErrorCodes.GENERIC_ERROR,
            ErrorCodes.INVALID_REQUEST,
            ErrorCodes.UNAUTHORIZED
        ]
        
        for error_code in error_codes:
            error_response = self.handler.handle_error(error_code, self.test_request_id)
            
            # All should have valid responses
            assert error_response.user_message
            assert error_response.system_reason
            assert error_response.error_code == error_code
            assert isinstance(error_response.timestamp, datetime)
    
    def test_specific_errors_have_korean_messages(self):
        """Test that specific system judgment errors have Korean messages"""
        specific_errors = {
            ErrorCodes.ID_CARD_FORMAT_MISMATCH: "사원증 규격 불일치",
            ErrorCodes.REGISTRATION_INFO_MISMATCH: "등록 정보 불일치",
            ErrorCodes.ACCOUNT_DISABLED: "계정 비활성화"
        }
        
        for error_code, expected_message in specific_errors.items():
            error_response = self.handler.handle_error(error_code, self.test_request_id)
            assert error_response.user_message == expected_message
    
    def test_technical_errors_have_generic_korean_message(self):
        """Test that technical errors have generic Korean retry message"""
        technical_errors = [
            ErrorCodes.LIVENESS_FAILED,
            ErrorCodes.FACE_NOT_FOUND,
            ErrorCodes.AD_CONNECTION_ERROR,
            ErrorCodes.TIMEOUT_ERROR,
            ErrorCodes.GENERIC_ERROR
        ]
        
        generic_message = "밝은 곳에서 다시 시도해주세요"
        
        for error_code in technical_errors:
            error_response = self.handler.handle_error(error_code, self.test_request_id)
            assert error_response.user_message == generic_message


class TestErrorHandlerIntegration:
    """Integration tests for ErrorHandler with other components"""
    
    def test_error_handler_with_real_context(self):
        """Test error handler with realistic context data"""
        handler = ErrorHandler()
        
        # Simulate real enrollment failure context
        context = {
            "employee_id": "123456",
            "card_type": "standard_employee",
            "ocr_confidence": 0.85,
            "template_match_score": 0.45,
            "attempt_number": 1,
            "timestamp": "2024-01-15T10:30:00Z"
        }
        
        error_response = handler.handle_error(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            "req-abc-123",
            context
        )
        
        # Verify all context is included
        assert "employee_id=123456" in error_response.system_reason
        assert "card_type=standard_employee" in error_response.system_reason
        assert "ocr_confidence=0.85" in error_response.system_reason
        
        # User message should still be simple
        assert error_response.user_message == "사원증 규격 불일치"
    
    def test_error_handler_with_ad_failure_context(self):
        """Test error handler with AD connection failure context"""
        handler = ErrorHandler()
        
        context = {
            "ad_server": "ldaps://ad.company.com",
            "timeout_seconds": 10,
            "connection_attempt": 3,
            "error_type": "timeout"
        }
        
        error_response = handler.handle_error(
            ErrorCodes.AD_CONNECTION_ERROR,
            "req-def-456",
            context
        )
        
        # Verify context is included
        assert "ad_server" in error_response.system_reason
        assert "timeout_seconds=10" in error_response.system_reason
        
        # User message should be generic
        assert error_response.user_message == "밝은 곳에서 다시 시도해주세요"
