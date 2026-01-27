"""
Face-Auth IdP System - Error Handler

This module provides comprehensive error handling with specific and generic error messages.
It separates system_reason (for logging) from user_message (for display).

Requirements: 1.6, 1.7, 1.8, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

from datetime import datetime
from typing import Dict, Any, Optional
from shared.models import ErrorResponse, ErrorCodes


class ErrorHandler:
    """
    Centralized error handling for the Face-Auth system
    
    Provides:
    - Specific error messages for system judgment errors
    - Generic error messages for technical issues
    - Separation of system_reason and user_message
    - Retry policy management
    """
    
    def __init__(self):
        """Initialize error handler with error mappings"""
        self.error_mappings = self._build_error_mappings()
    
    def _build_error_mappings(self) -> Dict[str, Dict[str, Any]]:
        """
        Build comprehensive error code to message mappings
        
        Returns:
            Dictionary mapping error codes to error details
        """
        return {
            # Specific error messages - System judgment errors
            ErrorCodes.ID_CARD_FORMAT_MISMATCH: {
                "user_message": "사원증 규격 불일치",
                "system_reason": "ID card format does not match any registered Card_Template pattern",
                "retry_allowed": True,
                "log_level": "WARNING"
            },
            ErrorCodes.REGISTRATION_INFO_MISMATCH: {
                "user_message": "등록 정보 불일치",
                "system_reason": "Employee information extracted from ID card does not match Active Directory records",
                "retry_allowed": True,
                "log_level": "WARNING"
            },
            ErrorCodes.ACCOUNT_DISABLED: {
                "user_message": "계정 비활성화",
                "system_reason": "Active Directory account is disabled (userAccountControl indicates disabled state)",
                "retry_allowed": False,
                "log_level": "WARNING"
            },
            
            # Generic error messages - Technical issues
            ErrorCodes.LIVENESS_FAILED: {
                "user_message": "밝은 곳에서 다시 시도해주세요",
                "system_reason": "Amazon Rekognition Liveness detection failed (confidence < 90%)",
                "retry_allowed": True,
                "log_level": "INFO"
            },
            ErrorCodes.FACE_NOT_FOUND: {
                "user_message": "밝은 곳에서 다시 시도해주세요",
                "system_reason": "Face not found in 1:N matching against enrolled faces",
                "retry_allowed": True,
                "log_level": "INFO"
            },
            ErrorCodes.AD_CONNECTION_ERROR: {
                "user_message": "밝은 곳에서 다시 시도해주세요",
                "system_reason": "Active Directory connection failed or timed out (10 second limit)",
                "retry_allowed": True,
                "log_level": "ERROR"
            },
            ErrorCodes.TIMEOUT_ERROR: {
                "user_message": "밝은 곳에서 다시 시도해주세요",
                "system_reason": "Lambda function timeout approaching (15 second limit)",
                "retry_allowed": True,
                "log_level": "ERROR"
            },
            ErrorCodes.GENERIC_ERROR: {
                "user_message": "밝은 곳에서 다시 시도해주세요",
                "system_reason": "Unspecified technical error occurred during processing",
                "retry_allowed": True,
                "log_level": "ERROR"
            },
            
            # Additional error codes
            ErrorCodes.INVALID_REQUEST: {
                "user_message": "잘못된 요청입니다",
                "system_reason": "Request validation failed - missing or invalid parameters",
                "retry_allowed": False,
                "log_level": "WARNING"
            },
            ErrorCodes.UNAUTHORIZED: {
                "user_message": "인증이 필요합니다",
                "system_reason": "Authentication required or session expired",
                "retry_allowed": False,
                "log_level": "WARNING"
            }
        }
    
    def handle_error(
        self,
        error_code: str,
        request_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorResponse:
        """
        Handle an error and create standardized error response
        
        Args:
            error_code: Error code from ErrorCodes class
            request_id: Request identifier for tracing
            context: Additional context information for logging
            
        Returns:
            ErrorResponse with user_message and system_reason separated
        """
        # Get error mapping or use default
        mapping = self.error_mappings.get(
            error_code,
            self._get_default_error_mapping()
        )
        
        # Build detailed system reason with context
        system_reason = self._build_system_reason(
            mapping["system_reason"],
            context
        )
        
        # Create error response
        return ErrorResponse(
            error_code=error_code,
            user_message=mapping["user_message"],
            system_reason=system_reason,
            timestamp=datetime.now(),
            request_id=request_id
        )
    
    def _get_default_error_mapping(self) -> Dict[str, Any]:
        """
        Get default error mapping for unknown error codes
        
        Returns:
            Default error mapping dictionary
        """
        return {
            "user_message": "밝은 곳에서 다시 시도해주세요",
            "system_reason": "Unknown error code - defaulting to generic error",
            "retry_allowed": True,
            "log_level": "ERROR"
        }
    
    def _build_system_reason(
        self,
        base_reason: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """
        Build detailed system reason with context information
        
        Args:
            base_reason: Base system reason message
            context: Additional context for troubleshooting
            
        Returns:
            Detailed system reason string
        """
        if not context:
            return base_reason
        
        # Filter out sensitive information
        safe_context = self._sanitize_context(context)
        
        # Build detailed reason
        context_str = " | ".join(
            f"{key}={value}" for key, value in safe_context.items()
        )
        
        return f"{base_reason} | Context: {context_str}"
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive information from context before logging
        
        Args:
            context: Raw context dictionary
            
        Returns:
            Sanitized context dictionary
        """
        # List of sensitive keys to exclude
        sensitive_keys = {
            'password',
            'token',
            'cognito_token',
            'secret',
            'api_key',
            'face_image',
            'image_bytes'
        }
        
        # Filter out sensitive keys
        return {
            key: value for key, value in context.items()
            if key.lower() not in sensitive_keys
        }
    
    def is_retry_allowed(self, error_code: str) -> bool:
        """
        Check if retry is allowed for the given error code
        
        Args:
            error_code: Error code to check
            
        Returns:
            True if retry is allowed, False otherwise
        """
        mapping = self.error_mappings.get(error_code)
        if not mapping:
            return True  # Default to allowing retry
        
        return mapping.get("retry_allowed", True)
    
    def get_log_level(self, error_code: str) -> str:
        """
        Get appropriate log level for the error code
        
        Args:
            error_code: Error code to check
            
        Returns:
            Log level string (INFO, WARNING, ERROR)
        """
        mapping = self.error_mappings.get(error_code)
        if not mapping:
            return "ERROR"
        
        return mapping.get("log_level", "ERROR")
    
    def create_error_response_dict(
        self,
        error_code: str,
        request_id: str,
        context: Optional[Dict[str, Any]] = None,
        include_system_reason: bool = False
    ) -> Dict[str, Any]:
        """
        Create error response as dictionary for API responses
        
        Args:
            error_code: Error code from ErrorCodes class
            request_id: Request identifier
            context: Additional context information
            include_system_reason: Whether to include system_reason in response
                                   (should be False for production, True for debugging)
            
        Returns:
            Dictionary suitable for JSON API response
        """
        error_response = self.handle_error(error_code, request_id, context)
        response_dict = error_response.to_dict()
        
        # Optionally include system reason for debugging
        if include_system_reason:
            response_dict['system_reason'] = error_response.system_reason
        
        # Add retry information
        response_dict['retry_allowed'] = self.is_retry_allowed(error_code)
        
        return response_dict


# Singleton instance for easy import
error_handler = ErrorHandler()
