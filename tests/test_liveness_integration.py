"""
Integration tests for Rekognition Liveness API

Tests the complete Liveness workflow with actual AWS services.
These tests require AWS credentials and will make real API calls.

Requirements: FR-1, FR-3, NFR-2
"""

import pytest
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import sys

# Add lambda paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'liveness'))

from liveness_service import (
    LivenessService,
    SessionNotFoundError,
    SessionExpiredError,
    ConfidenceThresholdError
)


@pytest.fixture
def liveness_service():
    """Create LivenessService instance for testing."""
    return LivenessService(
        confidence_threshold=90.0,
        session_timeout_minutes=10
    )


@pytest.fixture
def mock_aws_clients():
    """Mock AWS clients for integration tests."""
    with patch('boto3.client') as mock_client:
        # Mock Rekognition client
        mock_rekognition = MagicMock()
        mock_dynamodb = MagicMock()
        mock_s3 = MagicMock()
        
        def client_factory(service_name, **kwargs):
            if service_name == 'rekognition':
                return mock_rekognition
            elif service_name == 'dynamodb':
                return mock_dynamodb
            elif service_name == 's3':
                return mock_s3
            return MagicMock()
        
        mock_client.side_effect = client_factory
        
        yield {
            'rekognition': mock_rekognition,
            'dynamodb': mock_dynamodb,
            's3': mock_s3
        }


class TestLivenessIntegration:
    """Integration tests for Liveness workflow."""
    
    def test_full_liveness_flow(self, liveness_service, mock_aws_clients):
        """
        Test complete Liveness flow: create session → verify → get result
        
        Requirements: FR-1, FR-3
        """
        # Step 1: Create session
        employee_id = 'TEST001'
        session_id = 'test-session-123'
        
        mock_aws_clients['rekognition'].create_face_liveness_session.return_value = {
            'SessionId': session_id
        }
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        mock_aws_clients['dynamodb'].put_item.return_value = {}
        
        result = liveness_service.create_session(employee_id)
        
        assert result['session_id'] == session_id
        assert 'expires_at' in result
        
        # Verify DynamoDB put_item was called
        mock_aws_clients['dynamodb'].put_item.assert_called_once()
        call_args = mock_aws_clients['dynamodb'].put_item.call_args
        assert call_args[1]['Item']['session_id']['S'] == session_id
        assert call_args[1]['Item']['employee_id']['S'] == employee_id
        
        # Step 2: Get session result (live)
        expires_at_unix = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
        mock_aws_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'session_id': {'S': session_id},
                'employee_id': {'S': employee_id},
                'status': {'S': 'PENDING'},
                'expires_at': {'N': str(expires_at_unix)}
            }
        }
        
        mock_aws_clients['rekognition'].get_face_liveness_session_results.return_value = {
            'SessionId': session_id,
            'Status': 'SUCCEEDED',
            'Confidence': 95.5,
            'ReferenceImage': {
                'Bytes': b'fake_image_data'
            }
        }
        
        session_result = liveness_service.get_session_result(session_id)
        
        assert session_result.is_live is True
        assert session_result.confidence == 95.5
        assert session_result.session_id == session_id
        
    def test_session_creation_and_retrieval(self, liveness_service, mock_aws_clients):
        """
        Test session creation and immediate retrieval
        
        Requirements: FR-1.1, FR-1.2, FR-1.3
        """
        employee_id = 'TEST002'
        session_id = 'test-session-456'
        
        # Create session
        mock_aws_clients['rekognition'].create_face_liveness_session.return_value = {
            'SessionId': session_id
        }
        mock_aws_clients['dynamodb'].put_item.return_value = {}
        
        create_result = liveness_service.create_session(employee_id)
        
        assert create_result['session_id'] == session_id
        
        # Retrieve session
        expires_at_unix = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
        mock_aws_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'session_id': {'S': session_id},
                'employee_id': {'S': employee_id},
                'status': {'S': 'PENDING'},
                'expires_at': {'N': str(expires_at_unix)}
            }
        }
        
        mock_aws_clients['rekognition'].get_face_liveness_session_results.return_value = {
            'SessionId': session_id,
            'Status': 'SUCCEEDED',
            'Confidence': 92.0
        }
        
        result = liveness_service.get_session_result(session_id)
        
        assert result.session_id == session_id
        assert result.is_live is True
        
    def test_session_expiration(self, liveness_service, mock_aws_clients):
        """
        Test session expiration handling
        
        Requirements: FR-1.3, FR-5.1
        """
        session_id = 'expired-session'
        
        # Mock expired session
        expires_at_unix = int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp())
        mock_aws_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'session_id': {'S': session_id},
                'employee_id': {'S': 'TEST003'},
                'status': {'S': 'PENDING'},
                'expires_at': {'N': str(expires_at_unix)}
            }
        }
        
        with pytest.raises(SessionExpiredError) as exc_info:
            liveness_service.get_session_result(session_id)
        
        assert 'expired' in str(exc_info.value).lower()
        
    def test_confidence_threshold_validation(self, liveness_service, mock_aws_clients):
        """
        Test confidence threshold validation (90%)
        
        Requirements: FR-1.4, NFR-2.1
        """
        session_id = 'low-confidence-session'
        
        expires_at_unix = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
        mock_aws_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'session_id': {'S': session_id},
                'employee_id': {'S': 'TEST004'},
                'status': {'S': 'PENDING'},
                'expires_at': {'N': str(expires_at_unix)}
            }
        }
        
        # Low confidence (below 90%)
        mock_aws_clients['rekognition'].get_face_liveness_session_results.return_value = {
            'SessionId': session_id,
            'Status': 'SUCCEEDED',
            'Confidence': 85.0
        }
        
        result = liveness_service.get_session_result(session_id)
        
        assert result.is_live is False
        assert result.confidence == 85.0
        assert 'threshold' in result.reason.lower()
        
    def test_audit_log_storage(self, liveness_service, mock_aws_clients):
        """
        Test audit log storage in S3
        
        Requirements: FR-3.4, NFR-4.3
        """
        from liveness_service import LivenessSessionResult
        
        session_id = 'audit-test-session'
        employee_id = 'TEST005'
        
        result = LivenessSessionResult(
            session_id=session_id,
            is_live=True,
            confidence=95.0,
            status='SUCCEEDED'
        )
        
        mock_aws_clients['s3'].put_object.return_value = {}
        
        # Store audit log
        liveness_service.store_audit_log(
            session_id=session_id,
            employee_id=employee_id,
            result=result
        )
        
        # Verify S3 put_object was called
        mock_aws_clients['s3'].put_object.assert_called_once()
        call_args = mock_aws_clients['s3'].put_object.call_args
        
        assert 'liveness-audit/' in call_args[1]['Key']
        assert session_id in call_args[1]['Key']
        
        # Verify audit log content
        import json
        body = call_args[1]['Body']
        audit_data = json.loads(body)
        
        assert audit_data['session_id'] == session_id
        assert audit_data['employee_id'] == employee_id
        assert audit_data['result']['is_live'] is True
        assert audit_data['result']['confidence'] == 95.0


class TestLivenessErrorHandling:
    """Test error handling in Liveness integration."""
    
    def test_session_not_found(self, liveness_service, mock_aws_clients):
        """
        Test handling of non-existent session
        
        Requirements: FR-5.2
        """
        session_id = 'non-existent-session'
        
        mock_aws_clients['dynamodb'].get_item.return_value = {}
        
        with pytest.raises(SessionNotFoundError) as exc_info:
            liveness_service.get_session_result(session_id)
        
        assert session_id in str(exc_info.value)
        
    def test_rekognition_api_error(self, liveness_service, mock_aws_clients):
        """
        Test handling of Rekognition API errors
        
        Requirements: FR-5.3
        """
        from botocore.exceptions import ClientError
        
        employee_id = 'TEST006'
        
        # Mock Rekognition error
        mock_aws_clients['rekognition'].create_face_liveness_session.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'CreateFaceLivenessSession'
        )
        
        with pytest.raises(ClientError):
            liveness_service.create_session(employee_id)
            
    def test_dynamodb_error(self, liveness_service, mock_aws_clients):
        """
        Test handling of DynamoDB errors
        
        Requirements: FR-5.3
        """
        from botocore.exceptions import ClientError
        
        session_id = 'test-session'
        
        # Mock DynamoDB error
        mock_aws_clients['dynamodb'].get_item.side_effect = ClientError(
            {'Error': {'Code': 'ProvisionedThroughputExceededException', 'Message': 'Throughput exceeded'}},
            'GetItem'
        )
        
        with pytest.raises(ClientError):
            liveness_service.get_session_result(session_id)


class TestLivenessPerformance:
    """Test performance requirements for Liveness."""
    
    def test_session_creation_timeout(self, liveness_service, mock_aws_clients):
        """
        Test session creation completes within timeout
        
        Requirements: NFR-1.1 (< 3 seconds)
        """
        employee_id = 'TEST007'
        session_id = 'perf-test-session'
        
        mock_aws_clients['rekognition'].create_face_liveness_session.return_value = {
            'SessionId': session_id
        }
        mock_aws_clients['dynamodb'].put_item.return_value = {}
        
        start_time = time.time()
        result = liveness_service.create_session(employee_id)
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 3.0  # Must complete in < 3 seconds
        assert result['session_id'] == session_id
        
    def test_result_retrieval_timeout(self, liveness_service, mock_aws_clients):
        """
        Test result retrieval completes within timeout
        
        Requirements: NFR-1.2 (< 5 seconds)
        """
        session_id = 'perf-test-session-2'
        
        expires_at_unix = int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())
        mock_aws_clients['dynamodb'].get_item.return_value = {
            'Item': {
                'session_id': {'S': session_id},
                'employee_id': {'S': 'TEST008'},
                'status': {'S': 'PENDING'},
                'expires_at': {'N': str(expires_at_unix)}
            }
        }
        
        mock_aws_clients['rekognition'].get_face_liveness_session_results.return_value = {
            'SessionId': session_id,
            'Status': 'SUCCEEDED',
            'Confidence': 93.0
        }
        
        start_time = time.time()
        result = liveness_service.get_session_result(session_id)
        elapsed_time = time.time() - start_time
        
        assert elapsed_time < 5.0  # Must complete in < 5 seconds
        assert result.is_live is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
