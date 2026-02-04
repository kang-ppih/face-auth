"""
End-to-End tests for Liveness integration with authentication flows

Tests complete authentication workflows with Liveness verification.
These tests use mocked AWS services.

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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'enrollment'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'face_login'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'emergency_auth'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 're_enrollment'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))


@pytest.fixture
def mock_liveness_service():
    """Mock LivenessService for E2E tests."""
    with patch('liveness_service.LivenessService') as mock_service_class:
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        
        # Mock successful liveness verification
        from liveness_service import LivenessSessionResult
        mock_service.get_session_result.return_value = LivenessSessionResult(
            session_id='test-liveness-session',
            is_live=True,
            confidence=95.0,
            status='SUCCEEDED'
        )
        
        yield mock_service


@pytest.fixture
def sample_images():
    """Sample base64 encoded images for testing."""
    # Create minimal valid base64 strings
    id_card_image = base64.b64encode(b'fake_id_card_image_data').decode('utf-8')
    face_image = base64.b64encode(b'fake_face_image_data').decode('utf-8')
    
    return {
        'id_card': id_card_image,
        'face': face_image
    }


class TestEnrollmentWithLiveness:
    """E2E tests for Enrollment with Liveness integration."""
    
    @patch('handler.OCRService')
    @patch('handler.ADConnector')
    @patch('handler.FaceRecognitionService')
    @patch('handler.DynamoDBService')
    @patch('handler.LivenessService')
    def test_enrollment_with_liveness_success(
        self,
        mock_liveness_service_class,
        mock_dynamodb_class,
        mock_face_service_class,
        mock_ad_class,
        mock_ocr_class,
        sample_images
    ):
        """
        Test successful enrollment with Liveness verification
        
        Flow: ID Card OCR → AD Verify → Liveness → Face Register → DynamoDB
        
        Requirements: US-1, FR-4.1
        """
        from handler import handler
        from liveness_service import LivenessSessionResult
        from models import EmployeeInfo, ADVerificationResult, FaceData
        
        # Mock services
        mock_ocr = mock_ocr_class.return_value
        mock_ad = mock_ad_class.return_value
        mock_face = mock_face_service_class.return_value
        mock_db = mock_dynamodb_class.return_value
        mock_liveness = mock_liveness_service_class.return_value
        
        # Mock OCR extraction
        mock_ocr.extract_employee_info.return_value = EmployeeInfo(
            employee_id='EMP001',
            name='山田太郎',
            department='開発部'
        )
        
        # Mock AD verification
        mock_ad.verify_employee.return_value = ADVerificationResult(
            success=True,
            employee_data={'cn': '山田太郎'}
        )
        
        # Mock Liveness verification
        mock_liveness.get_session_result.return_value = LivenessSessionResult(
            session_id='liveness-session-123',
            is_live=True,
            confidence=95.5,
            status='SUCCEEDED'
        )
        
        # Mock face registration
        mock_face.index_face.return_value = 'face-id-123'
        
        # Mock DynamoDB save
        mock_db.save_employee_face.return_value = True
        
        # Create event
        event = {
            'body': json.dumps({
                'id_card_image': sample_images['id_card'],
                'face_image': sample_images['face'],
                'liveness_session_id': 'liveness-session-123'
            })
        }
        
        # Execute handler
        response = handler(event, {})
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['employee_info']['employee_id'] == 'EMP001'
        
        # Verify Liveness was checked
        mock_liveness.get_session_result.assert_called_once_with('liveness-session-123')
        
    @patch('handler.LivenessService')
    def test_enrollment_liveness_failure(self, mock_liveness_service_class, sample_images):
        """
        Test enrollment failure when Liveness verification fails
        
        Requirements: US-1, FR-4.1, NFR-2.1
        """
        from handler import handler
        from liveness_service import LivenessSessionResult
        
        mock_liveness = mock_liveness_service_class.return_value
        
        # Mock failed Liveness verification (low confidence)
        mock_liveness.get_session_result.return_value = LivenessSessionResult(
            session_id='liveness-session-456',
            is_live=False,
            confidence=75.0,
            status='SUCCEEDED',
            reason='Confidence below threshold'
        )
        
        event = {
            'body': json.dumps({
                'id_card_image': sample_images['id_card'],
                'face_image': sample_images['face'],
                'liveness_session_id': 'liveness-session-456'
            })
        }
        
        response = handler(event, {})
        
        # Verify failure response
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'liveness' in body['error']['message'].lower()


class TestLoginWithLiveness:
    """E2E tests for Face Login with Liveness integration."""
    
    @patch('handler.FaceRecognitionService')
    @patch('handler.DynamoDBService')
    @patch('handler.CognitoService')
    @patch('handler.LivenessService')
    def test_login_with_liveness_success(
        self,
        mock_liveness_service_class,
        mock_cognito_class,
        mock_dynamodb_class,
        mock_face_service_class,
        sample_images
    ):
        """
        Test successful login with Liveness verification
        
        Flow: Liveness → Face Search → Cognito Session
        
        Requirements: US-2, FR-4.2
        """
        from handler import handler
        from liveness_service import LivenessSessionResult
        from models import FaceSearchResult
        
        # Mock services
        mock_liveness = mock_liveness_service_class.return_value
        mock_face = mock_face_service_class.return_value
        mock_db = mock_dynamodb_class.return_value
        mock_cognito = mock_cognito_class.return_value
        
        # Mock Liveness verification (Step 1)
        mock_liveness.get_session_result.return_value = LivenessSessionResult(
            session_id='login-liveness-session',
            is_live=True,
            confidence=96.0,
            status='SUCCEEDED'
        )
        
        # Mock face search (Step 2)
        mock_face.search_faces.return_value = FaceSearchResult(
            success=True,
            face_id='face-id-123',
            similarity=98.5
        )
        
        # Mock employee lookup
        mock_db.get_employee_by_face_id.return_value = {
            'employee_id': 'EMP001',
            'name': '山田太郎'
        }
        
        # Mock Cognito session
        mock_cognito.create_session.return_value = {
            'token': 'jwt-token-123',
            'session_id': 'session-123'
        }
        
        # Create event
        event = {
            'body': json.dumps({
                'face_image': sample_images['face'],
                'liveness_session_id': 'login-liveness-session'
            })
        }
        
        # Execute handler
        response = handler(event, {})
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['token'] == 'jwt-token-123'
        
        # Verify Liveness was checked first
        mock_liveness.get_session_result.assert_called_once_with('login-liveness-session')


class TestEmergencyAuthWithLiveness:
    """E2E tests for Emergency Auth with Liveness integration."""
    
    @patch('handler.OCRService')
    @patch('handler.ADConnector')
    @patch('handler.CognitoService')
    @patch('handler.DynamoDBService')
    @patch('handler.LivenessService')
    def test_emergency_auth_with_liveness_success(
        self,
        mock_liveness_service_class,
        mock_dynamodb_class,
        mock_cognito_class,
        mock_ad_class,
        mock_ocr_class,
        sample_images
    ):
        """
        Test successful emergency auth with Liveness verification
        
        Flow: ID Card OCR → AD Password → Liveness → Cognito Session
        
        Requirements: US-3, FR-4.3
        """
        from handler import handler
        from liveness_service import LivenessSessionResult
        from models import EmployeeInfo, ADVerificationResult
        
        # Mock services
        mock_ocr = mock_ocr_class.return_value
        mock_ad = mock_ad_class.return_value
        mock_cognito = mock_cognito_class.return_value
        mock_db = mock_dynamodb_class.return_value
        mock_liveness = mock_liveness_service_class.return_value
        
        # Mock OCR extraction
        mock_ocr.extract_employee_info.return_value = EmployeeInfo(
            employee_id='EMP002',
            name='佐藤花子'
        )
        
        # Mock AD password verification
        mock_ad.verify_password.return_value = ADVerificationResult(
            success=True
        )
        
        # Mock Liveness verification (after AD auth)
        mock_liveness.get_session_result.return_value = LivenessSessionResult(
            session_id='emergency-liveness-session',
            is_live=True,
            confidence=94.0,
            status='SUCCEEDED'
        )
        
        # Mock rate limit check
        mock_db.check_rate_limit.return_value = True
        
        # Mock Cognito session
        mock_cognito.create_session.return_value = {
            'token': 'emergency-token-123',
            'session_id': 'emergency-session-123'
        }
        
        # Create event
        event = {
            'body': json.dumps({
                'id_card_image': sample_images['id_card'],
                'password': 'test_password',
                'liveness_session_id': 'emergency-liveness-session'
            })
        }
        
        # Execute handler
        response = handler(event, {})
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        
        # Verify Liveness was checked after AD auth
        mock_liveness.get_session_result.assert_called_once_with('emergency-liveness-session')


class TestReEnrollmentWithLiveness:
    """E2E tests for Re-enrollment with Liveness integration."""
    
    @patch('handler.OCRService')
    @patch('handler.ADConnector')
    @patch('handler.FaceRecognitionService')
    @patch('handler.DynamoDBService')
    @patch('handler.LivenessService')
    def test_re_enrollment_with_liveness_success(
        self,
        mock_liveness_service_class,
        mock_dynamodb_class,
        mock_face_service_class,
        mock_ad_class,
        mock_ocr_class,
        sample_images
    ):
        """
        Test successful re-enrollment with Liveness verification
        
        Flow: ID Card OCR → AD Verify → Liveness → Delete Old Face → Register New Face
        
        Requirements: US-4, FR-4.4
        """
        from handler import handler
        from liveness_service import LivenessSessionResult
        from models import EmployeeInfo, ADVerificationResult
        
        # Mock services
        mock_ocr = mock_ocr_class.return_value
        mock_ad = mock_ad_class.return_value
        mock_face = mock_face_service_class.return_value
        mock_db = mock_dynamodb_class.return_value
        mock_liveness = mock_liveness_service_class.return_value
        
        # Mock OCR extraction
        mock_ocr.extract_employee_info.return_value = EmployeeInfo(
            employee_id='EMP003',
            name='鈴木一郎'
        )
        
        # Mock AD verification
        mock_ad.verify_employee.return_value = ADVerificationResult(
            success=True
        )
        
        # Mock Liveness verification (after identity verification)
        mock_liveness.get_session_result.return_value = LivenessSessionResult(
            session_id='re-enroll-liveness-session',
            is_live=True,
            confidence=97.0,
            status='SUCCEEDED'
        )
        
        # Mock existing face lookup
        mock_db.get_employee_face.return_value = {
            'face_id': 'old-face-id-123'
        }
        
        # Mock face deletion
        mock_face.delete_face.return_value = True
        
        # Mock new face registration
        mock_face.index_face.return_value = 'new-face-id-456'
        
        # Mock DynamoDB update
        mock_db.update_employee_face.return_value = True
        
        # Create event
        event = {
            'body': json.dumps({
                'id_card_image': sample_images['id_card'],
                'face_image': sample_images['face'],
                'liveness_session_id': 're-enroll-liveness-session'
            })
        }
        
        # Execute handler
        response = handler(event, {})
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        
        # Verify Liveness was checked
        mock_liveness.get_session_result.assert_called_once_with('re-enroll-liveness-session')
        
        # Verify old face was deleted
        mock_face.delete_face.assert_called_once_with('old-face-id-123')


class TestLivenessFailureScenarios:
    """Test various Liveness failure scenarios across all flows."""
    
    @patch('handler.LivenessService')
    def test_missing_liveness_session_id(self, mock_liveness_service_class, sample_images):
        """
        Test handling of missing liveness_session_id parameter
        
        Requirements: FR-5.4
        """
        from handler import handler
        
        event = {
            'body': json.dumps({
                'face_image': sample_images['face']
                # Missing liveness_session_id
            })
        }
        
        response = handler(event, {})
        
        # Verify error response
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'liveness_session_id' in body['error']['message'].lower()
        
    @patch('handler.LivenessService')
    def test_expired_liveness_session(self, mock_liveness_service_class, sample_images):
        """
        Test handling of expired Liveness session
        
        Requirements: FR-5.1
        """
        from handler import handler
        from liveness_service import SessionExpiredError
        
        mock_liveness = mock_liveness_service_class.return_value
        mock_liveness.get_session_result.side_effect = SessionExpiredError(
            'Session expired: expired-session'
        )
        
        event = {
            'body': json.dumps({
                'face_image': sample_images['face'],
                'liveness_session_id': 'expired-session'
            })
        }
        
        response = handler(event, {})
        
        # Verify error response
        assert response['statusCode'] == 410
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'expired' in body['error']['message'].lower()
        
    @patch('handler.LivenessService')
    def test_liveness_session_not_found(self, mock_liveness_service_class, sample_images):
        """
        Test handling of non-existent Liveness session
        
        Requirements: FR-5.2
        """
        from handler import handler
        from liveness_service import SessionNotFoundError
        
        mock_liveness = mock_liveness_service_class.return_value
        mock_liveness.get_session_result.side_effect = SessionNotFoundError(
            'Session not found: invalid-session'
        )
        
        event = {
            'body': json.dumps({
                'face_image': sample_images['face'],
                'liveness_session_id': 'invalid-session'
            })
        }
        
        response = handler(event, {})
        
        # Verify error response
        assert response['statusCode'] == 404
        body = json.loads(response['body'])
        assert body['success'] is False
        assert 'not found' in body['error']['message'].lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
