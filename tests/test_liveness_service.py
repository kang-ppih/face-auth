"""
Unit tests for LivenessService

Tests the AWS Rekognition Liveness API integration service.

Requirements: FR-1, FR-3
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Import the service
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))

from liveness_service import (
    LivenessService,
    LivenessSessionResult,
    LivenessServiceError,
    SessionNotFoundError,
    SessionExpiredError,
    ConfidenceThresholdError
)


class TestLivenessService:
    """LivenessService単体テスト"""
    
    @pytest.fixture
    def mock_clients(self):
        """Create mock AWS clients"""
        return {
            'rekognition': Mock(),
            'dynamodb': Mock(),
            's3': Mock()
        }
    
    @pytest.fixture
    def liveness_service(self, mock_clients):
        """Create LivenessService instance with mocked clients"""
        return LivenessService(
            rekognition_client=mock_clients['rekognition'],
            dynamodb_client=mock_clients['dynamodb'],
            s3_client=mock_clients['s3'],
            confidence_threshold=90.0,
            session_timeout_minutes=10,
            liveness_sessions_table='test-liveness-sessions',
            face_auth_bucket='test-bucket'
        )
    
    def test_create_session_success(self, liveness_service, mock_clients):
        """
        Test: セッション作成成功
        
        Requirements: FR-1.1, FR-1.2, FR-1.3
        """
        # Arrange
        employee_id = 'EMP001'
        session_id = 'test-session-123'
        
        mock_clients['rekognition'].create_face_liveness_session.return_value = {
            'SessionId': session_id
        }
        
        mock_clients['dynamodb'].put_item.return_value = {}
        
        # Act
        result = liveness_service.create_session(employee_id)
        
        # Assert
        assert result['session_id'] == session_id
        assert 'expires_at' in result
        
        # Verify Rekognition API was called
        mock_clients['rekognition'].create_face_liveness_session.assert_called_once()
        call_args = mock_clients['rekognition'].create_face_liveness_session.call_args
        assert 'Settings' in call_args[1]
        assert 'OutputConfig' in call_args[1]['Settings']
        
        # Verify DynamoDB was called
        mock_clients['dynamodb'].put_item.assert_called_once()
        put_args = mock_clients['dynamodb'].put_item.call_args[1]
        assert put_args['Item']['session_id']['S'] == session_id
        assert put_args['Item']['employee_id']['S'] == employee_id
        assert put_args['Item']['status']['S'] == 'PENDING'

    
    def test_create_session_failure(self, liveness_service, mock_clients):
        """
        Test: セッション作成失敗
        
        Requirements: FR-1, FR-5.4
        """
        # Arrange
        employee_id = 'EMP001'
        mock_clients['rekognition'].create_face_liveness_session.side_effect = Exception("API Error")
        
        # Act & Assert
        with pytest.raises(LivenessServiceError) as exc_info:
            liveness_service.create_session(employee_id)
        
        assert "Failed to create liveness session" in str(exc_info.value)
    
    def test_get_session_result_live(self, liveness_service, mock_clients):
        """
        Test: Liveness検証成功（生体検出）
        
        信頼度が閾値（90%）以上の場合、is_live=Trueを返す
        
        Requirements: FR-3.2, FR-3.3
        """
        # Arrange
        session_id = 'test-session-123'
        confidence = 95.5
        
        # Mock DynamoDB response
        expires_at = int((datetime.utcnow() + timedelta(minutes=5)).timestamp())
        mock_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'session_id': {'S': session_id},
                'employee_id': {'S': 'EMP001'},
                'status': {'S': 'PENDING'},
                'expires_at': {'N': str(expires_at)}
            }
        }
        
        # Mock Rekognition response
        mock_clients['rekognition'].get_face_liveness_session_results.return_value = {
            'SessionId': session_id,
            'Status': 'SUCCEEDED',
            'Confidence': confidence,
            'ReferenceImage': {
                'S3Object': {
                    'Bucket': 'test-bucket',
                    'Name': 'liveness-audit/test-session-123/reference.jpg'
                }
            },
            'AuditImages': [{
                'S3Object': {
                    'Bucket': 'test-bucket',
                    'Name': 'liveness-audit/test-session-123/audit-1.jpg'
                }
            }]
        }
        
        mock_clients['dynamodb'].update_item.return_value = {}
        
        # Act
        result = liveness_service.get_session_result(session_id)
        
        # Assert
        assert result.is_live is True
        assert result.confidence == confidence
        assert result.status == 'SUCCESS'
        assert result.session_id == session_id
        assert result.reference_image_s3_key is not None
        assert result.error_message is None
    
    def test_get_session_result_not_live(self, liveness_service, mock_clients):
        """
        Test: Liveness検証失敗（信頼度不足）
        
        信頼度が閾値（90%）未満の場合、is_live=Falseを返す
        
        Requirements: FR-3.2, FR-3.3
        """
        # Arrange
        session_id = 'test-session-123'
        confidence = 75.0  # Below threshold
        
        # Mock DynamoDB response
        expires_at = int((datetime.utcnow() + timedelta(minutes=5)).timestamp())
        mock_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'session_id': {'S': session_id},
                'employee_id': {'S': 'EMP001'},
                'status': {'S': 'PENDING'},
                'expires_at': {'N': str(expires_at)}
            }
        }
        
        # Mock Rekognition response
        mock_clients['rekognition'].get_face_liveness_session_results.return_value = {
            'SessionId': session_id,
            'Status': 'SUCCEEDED',
            'Confidence': confidence
        }
        
        mock_clients['dynamodb'].update_item.return_value = {}
        
        # Act
        result = liveness_service.get_session_result(session_id)
        
        # Assert
        assert result.is_live is False
        assert result.confidence == confidence
        assert result.status == 'FAILED'
        assert result.error_message is not None
        assert "below threshold" in result.error_message

    
    def test_get_session_result_not_found(self, liveness_service, mock_clients):
        """
        Test: セッションが存在しない
        
        Requirements: FR-5.1
        """
        # Arrange
        session_id = 'non-existent-session'
        mock_clients['dynamodb'].get_item.return_value = {}  # No Item
        
        # Act & Assert
        with pytest.raises(SessionNotFoundError) as exc_info:
            liveness_service.get_session_result(session_id)
        
        assert "Session not found" in str(exc_info.value)
    
    def test_get_session_result_expired(self, liveness_service, mock_clients):
        """
        Test: セッションが期限切れ
        
        Requirements: FR-1.3, FR-5.1
        """
        # Arrange
        session_id = 'expired-session'
        
        # Mock DynamoDB response with expired timestamp
        expires_at = int((datetime.utcnow() - timedelta(minutes=1)).timestamp())  # Expired 1 minute ago
        mock_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'session_id': {'S': session_id},
                'employee_id': {'S': 'EMP001'},
                'status': {'S': 'PENDING'},
                'expires_at': {'N': str(expires_at)}
            }
        }
        
        # Act & Assert
        with pytest.raises(SessionExpiredError) as exc_info:
            liveness_service.get_session_result(session_id)
        
        assert "Session expired" in str(exc_info.value)
    
    def test_store_audit_log_success(self, liveness_service, mock_clients):
        """
        Test: 監査ログ保存成功
        
        Requirements: FR-3.4, US-5
        """
        # Arrange
        session_id = 'test-session-123'
        employee_id = 'EMP001'
        result = LivenessSessionResult(
            session_id=session_id,
            is_live=True,
            confidence=95.5,
            status='SUCCESS'
        )
        client_info = {
            'user_agent': 'Mozilla/5.0',
            'ip_address': '192.168.1.1'
        }
        
        mock_clients['s3'].put_object.return_value = {}
        
        # Act
        liveness_service.store_audit_log(session_id, result, employee_id, client_info)
        
        # Assert
        mock_clients['s3'].put_object.assert_called_once()
        call_args = mock_clients['s3'].put_object.call_args[1]
        
        assert call_args['Bucket'] == 'test-bucket'
        assert 'liveness-audit' in call_args['Key']
        assert call_args['ContentType'] == 'application/json'
        assert call_args['ServerSideEncryption'] == 'AES256'
        
        # Verify audit log content
        body = json.loads(call_args['Body'])
        assert body['session_id'] == session_id
        assert body['employee_id'] == employee_id
        assert body['result']['is_live'] is True
        assert body['client_info'] == client_info
    
    def test_confidence_threshold_configurable(self):
        """
        Test: 信頼度閾値が設定可能
        
        Requirements: FR-3.2, NFR-4.2
        """
        # Arrange
        custom_threshold = 85.0
        service = LivenessService(
            rekognition_client=Mock(),
            dynamodb_client=Mock(),
            s3_client=Mock(),
            confidence_threshold=custom_threshold
        )
        
        # Assert
        assert service.confidence_threshold == custom_threshold
        
        # Test validation with custom threshold
        assert service._validate_confidence(86.0) is True
        assert service._validate_confidence(84.0) is False
    
    def test_validate_confidence(self, liveness_service):
        """
        Test: 信頼度検証ロジック
        
        Requirements: FR-3.2
        """
        # Test cases
        assert liveness_service._validate_confidence(100.0) is True
        assert liveness_service._validate_confidence(90.0) is True
        assert liveness_service._validate_confidence(89.9) is False
        assert liveness_service._validate_confidence(0.0) is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
