"""
Unit tests for CreateLivenessSession Lambda Handler

Tests the Lambda handler for creating Rekognition Liveness sessions.

Requirements: FR-1
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone

# Import the handler
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'liveness'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))

from create_session_handler import handler
from liveness_service import LivenessServiceError


class TestCreateLivenessSessionHandler:
    """CreateLivenessSession Lambda Handler単体テスト"""
    
    @pytest.fixture
    def lambda_context(self):
        """Create mock Lambda context"""
        context = Mock()
        context.aws_request_id = 'test-request-123'
        context.function_name = 'CreateLivenessSession'
        context.get_remaining_time_in_millis.return_value = 10000  # 10 seconds
        return context
    
    @pytest.fixture
    def valid_event(self):
        """Create valid API Gateway event"""
        return {
            'body': json.dumps({
                'employee_id': 'EMP001'
            }),
            'headers': {
                'Content-Type': 'application/json'
            },
            'requestContext': {
                'requestId': 'test-request-123'
            }
        }
    
    @patch('create_session_handler.LivenessService')
    def test_handler_success(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: ハンドラー成功
        
        正常なリクエストでセッションが作成される
        
        Requirements: FR-1.1, FR-1.2, FR-1.3
        """
        # Arrange
        session_id = 'test-session-123'
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat() + 'Z'
        
        mock_service = Mock()
        mock_service.create_session.return_value = {
            'session_id': session_id,
            'expires_at': expires_at
        }
        mock_liveness_service_class.return_value = mock_service
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['session_id'] == session_id
        assert body['expires_at'] == expires_at
        
        # Verify service was called with correct employee_id
        mock_service.create_session.assert_called_once_with('EMP001')
    
    def test_handler_missing_employee_id(self, lambda_context):
        """
        Test: employee_idが欠落
        
        employee_idが提供されない場合、400エラーを返す
        
        Requirements: FR-5.1
        """
        # Arrange
        event = {
            'body': json.dumps({})
        }
        
        # Act
        response = handler(event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 400
        
        body = json.loads(response['body'])
        assert body['error'] == 'BAD_REQUEST'
        assert 'employee_id is required' in body['message']
    
    def test_handler_invalid_request(self, lambda_context):
        """
        Test: 無効なリクエスト形式
        
        JSONパースエラーの場合、400エラーを返す
        
        Requirements: FR-5.1
        """
        # Arrange
        event = {
            'body': 'invalid json'
        }
        
        # Act
        response = handler(event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 400
        
        body = json.loads(response['body'])
        assert body['error'] == 'BAD_REQUEST'
        assert 'Invalid JSON' in body['message']
    
    def test_handler_invalid_employee_id_format(self, lambda_context):
        """
        Test: 無効なemployee_id形式
        
        employee_idが英数字でない、または50文字を超える場合、400エラーを返す
        
        Requirements: FR-5.1
        """
        # Test non-alphanumeric
        event = {
            'body': json.dumps({
                'employee_id': 'EMP-001!'  # Contains special characters
            })
        }
        
        response = handler(event, lambda_context)
        assert response['statusCode'] == 400
        
        body = json.loads(response['body'])
        assert 'alphanumeric' in body['message']
        
        # Test too long
        event = {
            'body': json.dumps({
                'employee_id': 'A' * 51  # 51 characters
            })
        }
        
        response = handler(event, lambda_context)
        assert response['statusCode'] == 400
    
    @patch('create_session_handler.LivenessService')
    def test_handler_rekognition_error(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: Rekognitionエラー
        
        LivenessServiceがエラーを投げた場合、500エラーを返す
        
        Requirements: FR-5.4
        """
        # Arrange
        mock_service = Mock()
        mock_service.create_session.side_effect = LivenessServiceError("Rekognition API error")
        mock_liveness_service_class.return_value = mock_service
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 500
        
        body = json.loads(response['body'])
        assert body['error'] == 'INTERNAL_SERVER_ERROR'
        assert 'Failed to create liveness session' in body['message']
    
    @patch('create_session_handler.LivenessService')
    @patch('create_session_handler.TimeoutManager')
    def test_handler_timeout(self, mock_timeout_manager_class, mock_liveness_service_class, 
                            valid_event, lambda_context):
        """
        Test: タイムアウト
        
        処理がタイムアウトした場合、適切にハンドリングされる
        
        Requirements: TR-4
        """
        # Arrange
        mock_timeout_manager = Mock()
        mock_timeout_manager.operation.side_effect = TimeoutError("Operation timed out")
        mock_timeout_manager_class.return_value = mock_timeout_manager
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 500
    
    @patch('create_session_handler.LivenessService')
    def test_handler_response_format(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: レスポンス形式
        
        レスポンスが正しい形式で返される
        
        Requirements: FR-1
        """
        # Arrange
        session_id = 'test-session-123'
        expires_at = '2026-02-02T10:10:00Z'
        
        mock_service = Mock()
        mock_service.create_session.return_value = {
            'session_id': session_id,
            'expires_at': expires_at
        }
        mock_liveness_service_class.return_value = mock_service
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert 'statusCode' in response
        assert 'headers' in response
        assert 'body' in response
        
        # Verify headers
        headers = response['headers']
        assert headers['Content-Type'] == 'application/json'
        assert headers['Access-Control-Allow-Origin'] == '*'
        assert headers['Access-Control-Allow-Credentials'] == 'true'
        
        # Verify body is valid JSON
        body = json.loads(response['body'])
        assert isinstance(body, dict)
        assert 'session_id' in body
        assert 'expires_at' in body
    
    def test_handler_empty_body(self, lambda_context):
        """
        Test: 空のリクエストボディ
        
        bodyが空の場合、400エラーを返す
        
        Requirements: FR-5.1
        """
        # Arrange
        event = {
            'body': None
        }
        
        # Act
        response = handler(event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 400
        
        body = json.loads(response['body'])
        assert body['error'] == 'BAD_REQUEST'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
