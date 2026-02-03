"""
Unit tests for GetLivenessResult Lambda Handler

Tests the Lambda handler for retrieving Rekognition Liveness session results.

Requirements: FR-3
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

# Import the handler
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'liveness'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))

from get_result_handler import handler
from liveness_service import (
    LivenessSessionResult,
    LivenessServiceError,
    SessionNotFoundError,
    SessionExpiredError
)


class TestGetLivenessResultHandler:
    """GetLivenessResult Lambda Handler単体テスト"""
    
    @pytest.fixture
    def lambda_context(self):
        """Create mock Lambda context"""
        context = Mock()
        context.aws_request_id = 'test-request-123'
        context.function_name = 'GetLivenessResult'
        context.get_remaining_time_in_millis.return_value = 15000  # 15 seconds
        return context
    
    @pytest.fixture
    def valid_event(self):
        """Create valid API Gateway event"""
        return {
            'pathParameters': {
                'sessionId': 'test-session-123'
            },
            'requestContext': {
                'requestId': 'test-request-123'
            }
        }
    
    @patch('get_result_handler.LivenessService')
    def test_handler_success_live(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: ハンドラー成功（生体検出）
        
        Liveness検証が成功した場合、200とis_live=trueを返す
        
        Requirements: FR-3.2, FR-3.3
        """
        # Arrange
        session_id = 'test-session-123'
        confidence = 95.5
        
        mock_result = LivenessSessionResult(
            session_id=session_id,
            is_live=True,
            confidence=confidence,
            status='SUCCESS'
        )
        
        mock_service = Mock()
        mock_service.get_session_result.return_value = mock_result
        mock_service.confidence_threshold = 90.0
        mock_liveness_service_class.return_value = mock_service
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        
        body = json.loads(response['body'])
        assert body['session_id'] == session_id
        assert body['is_live'] is True
        assert body['confidence'] == confidence
        assert body['status'] == 'SUCCESS'
        
        # Verify service was called with correct session_id
        mock_service.get_session_result.assert_called_once_with(session_id)
    
    @patch('get_result_handler.LivenessService')
    def test_handler_success_not_live(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: ハンドラー成功（生体検出失敗）
        
        Liveness検証が失敗した場合、401とis_live=falseを返す
        
        Requirements: FR-3.2, FR-3.3
        """
        # Arrange
        session_id = 'test-session-123'
        confidence = 75.0
        
        mock_result = LivenessSessionResult(
            session_id=session_id,
            is_live=False,
            confidence=confidence,
            status='FAILED',
            error_message='Confidence below threshold'
        )
        
        mock_service = Mock()
        mock_service.get_session_result.return_value = mock_result
        mock_service.confidence_threshold = 90.0
        mock_liveness_service_class.return_value = mock_service
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 401
        
        body = json.loads(response['body'])
        assert body['error'] == 'UNAUTHORIZED'
        assert 'Liveness verification failed' in body['message']
        assert 'details' in body
        assert body['details']['confidence'] == confidence
        assert body['details']['threshold'] == 90.0
    
    def test_handler_missing_session_id(self, lambda_context):
        """
        Test: sessionIdが欠落
        
        sessionIdが提供されない場合、400エラーを返す
        
        Requirements: FR-5.1
        """
        # Arrange
        event = {
            'pathParameters': {}
        }
        
        # Act
        response = handler(event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 400
        
        body = json.loads(response['body'])
        assert body['error'] == 'BAD_REQUEST'
        assert 'sessionId is required' in body['message']
    
    @patch('get_result_handler.LivenessService')
    def test_handler_session_not_found(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: セッションが存在しない
        
        セッションが見つからない場合、404エラーを返す
        
        Requirements: FR-5.1
        """
        # Arrange
        mock_service = Mock()
        mock_service.get_session_result.side_effect = SessionNotFoundError("Session not found")
        mock_liveness_service_class.return_value = mock_service
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 404
        
        body = json.loads(response['body'])
        assert body['error'] == 'NOT_FOUND'
        assert 'Session not found or expired' in body['message']
    
    @patch('get_result_handler.LivenessService')
    def test_handler_session_expired(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: セッションが期限切れ
        
        セッションが期限切れの場合、410エラーを返す
        
        Requirements: FR-1.3, FR-5.1
        """
        # Arrange
        mock_service = Mock()
        mock_service.get_session_result.side_effect = SessionExpiredError("Session expired")
        mock_liveness_service_class.return_value = mock_service
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 410
        
        body = json.loads(response['body'])
        assert body['error'] == 'GONE'
        assert 'Session has expired' in body['message']
    
    @patch('get_result_handler.LivenessService')
    def test_handler_timeout(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: タイムアウト
        
        処理がタイムアウトした場合、500エラーを返す
        
        Requirements: TR-4
        """
        # Arrange
        mock_service = Mock()
        mock_service.get_session_result.side_effect = TimeoutError("Operation timed out")
        mock_liveness_service_class.return_value = mock_service
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 500
    
    @patch('get_result_handler.LivenessService')
    def test_handler_response_format(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: レスポンス形式
        
        レスポンスが正しい形式で返される
        
        Requirements: FR-3
        """
        # Arrange
        session_id = 'test-session-123'
        
        mock_result = LivenessSessionResult(
            session_id=session_id,
            is_live=True,
            confidence=95.5,
            status='SUCCESS'
        )
        
        mock_service = Mock()
        mock_service.get_session_result.return_value = mock_result
        mock_service.confidence_threshold = 90.0
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
        assert 'is_live' in body
        assert 'confidence' in body
        assert 'status' in body
    
    def test_handler_no_path_parameters(self, lambda_context):
        """
        Test: pathParametersが存在しない
        
        pathParametersがない場合、400エラーを返す
        
        Requirements: FR-5.1
        """
        # Arrange
        event = {}
        
        # Act
        response = handler(event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 400
        
        body = json.loads(response['body'])
        assert body['error'] == 'BAD_REQUEST'
    
    @patch('get_result_handler.LivenessService')
    def test_handler_liveness_service_error(self, mock_liveness_service_class, valid_event, lambda_context):
        """
        Test: LivenessServiceエラー
        
        LivenessServiceがエラーを投げた場合、500エラーを返す
        
        Requirements: FR-5.4
        """
        # Arrange
        mock_service = Mock()
        mock_service.get_session_result.side_effect = LivenessServiceError("Rekognition API error")
        mock_liveness_service_class.return_value = mock_service
        
        # Act
        response = handler(valid_event, lambda_context)
        
        # Assert
        assert response['statusCode'] == 500
        
        body = json.loads(response['body'])
        assert body['error'] == 'INTERNAL_SERVER_ERROR'
        assert 'Failed to get liveness session result' in body['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
