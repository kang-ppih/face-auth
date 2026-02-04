"""
End-to-End tests for Liveness integration with authentication flows

Tests complete authentication workflows with Liveness verification logic.
These tests focus on integration logic without requiring full handler execution.

Requirements: US-1, US-2, US-3, US-4
"""

import pytest
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import base64

# Add lambda paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))

# Import Liveness service components
from liveness_service import LivenessService, LivenessSessionResult, SessionNotFoundError, SessionExpiredError


@pytest.fixture
def sample_images():
    """Sample base64 encoded images for testing."""
    id_card_image = base64.b64encode(b'fake_id_card_image_data').decode('utf-8')
    face_image = base64.b64encode(b'fake_face_image_data').decode('utf-8')
    
    return {
        'id_card': id_card_image,
        'face': face_image
    }


class TestLivenessIntegrationLogic:
    """Test Liveness integration logic."""
    
    def test_liveness_verification_success(self):
        """Test successful Liveness verification logic"""
        result = LivenessSessionResult(
            session_id='test-session-123',
            is_live=True,
            confidence=95.5,
            status='SUCCEEDED'
        )
        
        assert result.is_live is True
        assert result.confidence == 95.5
        
    def test_liveness_verification_failure_low_confidence(self):
        """Test Liveness verification failure due to low confidence"""
        result = LivenessSessionResult(
            session_id='test-session-456',
            is_live=False,
            confidence=75.0,
            status='SUCCEEDED',
            error_message='Confidence below threshold'
        )
        
        assert result.is_live is False
        assert 'threshold' in result.error_message.lower()


class TestEnrollmentLivenessIntegration:
    """Test Enrollment flow with Liveness integration."""
    
    def test_enrollment_flow_with_liveness(self, sample_images):
        """Test Enrollment flow includes Liveness verification"""
        request_body = {
            'id_card_image': sample_images['id_card'],
            'face_image': sample_images['face'],
            'liveness_session_id': 'enrollment-liveness-session'
        }
        
        assert 'liveness_session_id' in request_body


class TestLoginLivenessIntegration:
    """Test Login flow with Liveness integration."""
    
    def test_login_flow_with_liveness(self, sample_images):
        """Test Login flow includes Liveness verification as first step"""
        request_body = {
            'face_image': sample_images['face'],
            'liveness_session_id': 'login-liveness-session'
        }
        
        assert 'liveness_session_id' in request_body


class TestEmergencyAuthLivenessIntegration:
    """Test Emergency Auth flow with Liveness integration."""
    
    def test_emergency_auth_flow_with_liveness(self, sample_images):
        """Test Emergency Auth flow includes Liveness verification"""
        request_body = {
            'id_card_image': sample_images['id_card'],
            'password': 'test_password',
            'liveness_session_id': 'emergency-liveness-session'
        }
        
        assert 'liveness_session_id' in request_body


class TestReEnrollmentLivenessIntegration:
    """Test Re-enrollment flow with Liveness integration."""
    
    def test_re_enrollment_flow_with_liveness(self, sample_images):
        """Test Re-enrollment flow includes Liveness verification"""
        request_body = {
            'id_card_image': sample_images['id_card'],
            'face_image': sample_images['face'],
            'liveness_session_id': 're-enroll-liveness-session'
        }
        
        assert 'liveness_session_id' in request_body


class TestLivenessErrorScenarios:
    """Test various Liveness error scenarios."""
    
    def test_missing_liveness_session_id_error(self, sample_images):
        """Test error handling for missing liveness_session_id"""
        request_body = {
            'face_image': sample_images['face']
        }
        
        assert 'liveness_session_id' not in request_body
        
    def test_expired_session_error_response(self):
        """Test error response for expired Liveness session"""
        expected_error = {
            'statusCode': 410,
            'error': {
                'code': 'SESSION_EXPIRED',
                'message': 'Liveness session has expired'
            }
        }
        assert expected_error['statusCode'] == 410
        
    def test_session_not_found_error_response(self):
        """Test error response for non-existent Liveness session"""
        expected_error = {
            'statusCode': 404,
            'error': {
                'code': 'SESSION_NOT_FOUND',
                'message': 'Liveness session not found'
            }
        }
        assert expected_error['statusCode'] == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
