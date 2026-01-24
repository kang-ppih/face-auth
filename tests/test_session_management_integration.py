"""
Integration tests for AuthenticationSession DynamoDB management

This test suite verifies the complete session management lifecycle:
- Session creation with Cognito integration
- Session storage in DynamoDB with TTL
- Session retrieval and validation
- Session deletion (logout)
- Automatic expiration handling

Requirements: 2.5, 10.7
Task: 10.2 AuthenticationSession DynamoDB 관리 구현
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from shared.cognito_service import CognitoService
from shared.dynamodb_service import DynamoDBService
from shared.models import AuthenticationSession


class TestSessionManagementIntegration:
    """Integration tests for session management with Cognito and DynamoDB"""
    
    @pytest.fixture
    def mock_dynamodb_table(self):
        """Create a mock DynamoDB table"""
        table = Mock()
        table.put_item = Mock(return_value={})
        table.get_item = Mock()
        table.delete_item = Mock(return_value={})
        return table
    
    @pytest.fixture
    def db_service(self, mock_dynamodb_table):
        """Create DynamoDB service with mocked table"""
        service = DynamoDBService()
        service.auth_sessions_table = mock_dynamodb_table
        return service
    
    @pytest.fixture
    def cognito_service(self):
        """Create Cognito service with mocked client"""
        with patch('shared.cognito_service.PyJWKClient'):
            service = CognitoService(
                user_pool_id='us-east-1_TEST123',
                client_id='test-client-id',
                region='us-east-1'
            )
            service.cognito_client = Mock()
            return service
    
    def test_complete_session_lifecycle(self, cognito_service, db_service, mock_dynamodb_table):
        """
        Test complete session lifecycle: create -> store -> retrieve -> validate -> delete
        
        This test verifies:
        1. Session creation with Cognito tokens
        2. Session storage in DynamoDB
        3. Session retrieval from DynamoDB
        4. Session validation (expiration check)
        5. Session deletion (logout)
        """
        # Step 1: Create session with Cognito
        employee_id = "123456"
        
        # Mock Cognito user exists
        cognito_service.cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        
        cognito_service.cognito_client.admin_set_user_password.return_value = {}
        
        # Mock successful authentication
        cognito_service.cognito_client.admin_initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock-access-token',
                'IdToken': 'mock-id-token',
                'RefreshToken': 'mock-refresh-token',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Create authentication session
        session, error = cognito_service.create_authentication_session(
            employee_id=employee_id,
            auth_method='face',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0'
        )
        
        assert error is None
        assert session is not None
        assert session.employee_id == employee_id
        assert session.auth_method == 'face'
        assert session.cognito_token == 'mock-access-token'
        assert session.is_valid()  # Should be valid immediately
        
        # Step 2: Store session in DynamoDB
        result = db_service.create_auth_session(session)
        assert result is True
        
        # Verify DynamoDB put_item was called with correct data
        mock_dynamodb_table.put_item.assert_called_once()
        call_args = mock_dynamodb_table.put_item.call_args
        stored_item = call_args[1]['Item']
        
        assert stored_item['session_id'] == session.session_id
        assert stored_item['employee_id'] == employee_id
        assert stored_item['auth_method'] == 'face'
        assert stored_item['cognito_token'] == 'mock-access-token'
        assert stored_item['ip_address'] == '192.168.1.100'
        assert stored_item['user_agent'] == 'Mozilla/5.0'
        assert 'expires_at' in stored_item  # TTL field
        
        # Step 3: Retrieve session from DynamoDB
        mock_dynamodb_table.get_item.return_value = {
            'Item': stored_item
        }
        
        retrieved_session = db_service.get_auth_session(session.session_id)
        assert retrieved_session is not None
        assert retrieved_session.session_id == session.session_id
        assert retrieved_session.employee_id == employee_id
        assert retrieved_session.is_valid()
        
        # Step 4: Delete session (logout)
        result = db_service.delete_auth_session(session.session_id)
        assert result is True
        
        mock_dynamodb_table.delete_item.assert_called_once_with(
            Key={'session_id': session.session_id}
        )
    
    def test_session_expiration_handling(self, cognito_service, db_service, mock_dynamodb_table):
        """
        Test that expired sessions are properly identified
        
        Verifies:
        1. Session creation with short expiration
        2. Session validation returns False for expired sessions
        3. TTL field is properly set for DynamoDB automatic cleanup
        """
        employee_id = "123456"
        
        # Mock Cognito
        cognito_service.cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        cognito_service.cognito_client.admin_set_user_password.return_value = {}
        cognito_service.cognito_client.admin_initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock-token',
                'IdToken': 'mock-id',
                'RefreshToken': 'mock-refresh',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Create session
        session, error = cognito_service.create_authentication_session(
            employee_id=employee_id,
            auth_method='face'
        )
        
        assert error is None
        assert session is not None
        
        # Verify session is initially valid
        assert session.is_valid() is True
        
        # Simulate expired session by modifying expires_at
        expired_session = AuthenticationSession(
            session_id=session.session_id,
            employee_id=employee_id,
            auth_method='face',
            created_at=datetime.now() - timedelta(hours=10),
            expires_at=datetime.now() - timedelta(hours=2),  # Expired 2 hours ago
            cognito_token=session.cognito_token
        )
        
        # Verify expired session is detected
        assert expired_session.is_valid() is False
        
        # Store expired session and verify TTL field
        db_service.create_auth_session(expired_session)
        
        call_args = mock_dynamodb_table.put_item.call_args
        stored_item = call_args[1]['Item']
        
        # Verify TTL field is set (as epoch timestamp)
        assert 'expires_at' in stored_item
        assert isinstance(stored_item['expires_at'], int)
        
        # TTL should be in the past for expired session
        current_time = int(datetime.now().timestamp())
        assert stored_item['expires_at'] < current_time
    
    def test_session_with_optional_metadata(self, cognito_service, db_service, mock_dynamodb_table):
        """
        Test session creation with optional IP address and user agent
        
        Verifies:
        1. Sessions can be created without optional fields
        2. Optional fields are properly stored when provided
        3. Session retrieval handles optional fields correctly
        """
        employee_id = "123456"
        
        # Mock Cognito
        cognito_service.cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        cognito_service.cognito_client.admin_set_user_password.return_value = {}
        cognito_service.cognito_client.admin_initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock-token',
                'IdToken': 'mock-id',
                'RefreshToken': 'mock-refresh',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Test 1: Session without optional fields
        session_no_metadata, error = cognito_service.create_authentication_session(
            employee_id=employee_id,
            auth_method='face'
        )
        
        assert error is None
        assert session_no_metadata.ip_address is None
        assert session_no_metadata.user_agent is None
        
        # Store and verify
        db_service.create_auth_session(session_no_metadata)
        call_args = mock_dynamodb_table.put_item.call_args
        stored_item = call_args[1]['Item']
        
        assert stored_item['ip_address'] is None
        assert stored_item['user_agent'] is None
        
        # Test 2: Session with optional fields
        session_with_metadata, error = cognito_service.create_authentication_session(
            employee_id=employee_id,
            auth_method='emergency',
            ip_address='10.0.0.1',
            user_agent='TestAgent/1.0'
        )
        
        assert error is None
        assert session_with_metadata.ip_address == '10.0.0.1'
        assert session_with_metadata.user_agent == 'TestAgent/1.0'
        
        # Store and verify
        db_service.create_auth_session(session_with_metadata)
        call_args = mock_dynamodb_table.put_item.call_args
        stored_item = call_args[1]['Item']
        
        assert stored_item['ip_address'] == '10.0.0.1'
        assert stored_item['user_agent'] == 'TestAgent/1.0'
    
    def test_session_retrieval_not_found(self, db_service, mock_dynamodb_table):
        """
        Test session retrieval when session doesn't exist
        
        Verifies:
        1. get_auth_session returns None for non-existent sessions
        2. No exceptions are raised
        """
        # Mock DynamoDB returning no item
        mock_dynamodb_table.get_item.return_value = {}
        
        # Attempt to retrieve non-existent session
        session = db_service.get_auth_session("non-existent-session-id")
        
        assert session is None
        mock_dynamodb_table.get_item.assert_called_once_with(
            Key={'session_id': 'non-existent-session-id'}
        )
    
    def test_multiple_sessions_same_user(self, cognito_service, db_service, mock_dynamodb_table):
        """
        Test that multiple sessions can exist for the same user
        
        Verifies:
        1. User can have multiple active sessions (different devices)
        2. Each session has unique session_id
        3. Sessions are independently managed
        """
        employee_id = "123456"
        
        # Mock Cognito
        cognito_service.cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        cognito_service.cognito_client.admin_set_user_password.return_value = {}
        cognito_service.cognito_client.admin_initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock-token',
                'IdToken': 'mock-id',
                'RefreshToken': 'mock-refresh',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Create first session (desktop)
        session1, error1 = cognito_service.create_authentication_session(
            employee_id=employee_id,
            auth_method='face',
            ip_address='192.168.1.100',
            user_agent='Desktop/Chrome'
        )
        
        assert error1 is None
        db_service.create_auth_session(session1)
        
        # Create second session (mobile)
        session2, error2 = cognito_service.create_authentication_session(
            employee_id=employee_id,
            auth_method='face',
            ip_address='192.168.1.101',
            user_agent='Mobile/Safari'
        )
        
        assert error2 is None
        db_service.create_auth_session(session2)
        
        # Verify sessions have different IDs
        assert session1.session_id != session2.session_id
        
        # Verify both sessions are for the same employee
        assert session1.employee_id == session2.employee_id == employee_id
        
        # Verify both sessions were stored
        assert mock_dynamodb_table.put_item.call_count == 2
    
    def test_session_ttl_format(self, db_service, mock_dynamodb_table):
        """
        Test that TTL field is in correct format for DynamoDB
        
        Verifies:
        1. expires_at is stored as epoch timestamp (integer)
        2. TTL is properly calculated from session expiration
        3. DynamoDB can use this field for automatic cleanup
        """
        now = datetime.now()
        expires = now + timedelta(hours=8)
        
        session = AuthenticationSession(
            session_id="test-session",
            employee_id="123456",
            auth_method="face",
            created_at=now,
            expires_at=expires,
            cognito_token="test-token"
        )
        
        # Store session
        db_service.create_auth_session(session)
        
        # Verify TTL format
        call_args = mock_dynamodb_table.put_item.call_args
        stored_item = call_args[1]['Item']
        
        # expires_at should be integer epoch timestamp
        assert isinstance(stored_item['expires_at'], int)
        
        # Verify it's approximately correct (within 1 second tolerance)
        expected_ttl = int(expires.timestamp())
        actual_ttl = stored_item['expires_at']
        assert abs(expected_ttl - actual_ttl) <= 1
        
        # Verify it's in the future
        current_timestamp = int(datetime.now().timestamp())
        assert actual_ttl > current_timestamp


class TestSessionManagementEdgeCases:
    """Test edge cases and error conditions for session management"""
    
    @pytest.fixture
    def db_service(self):
        """Create DynamoDB service with mocked table"""
        service = DynamoDBService()
        service.auth_sessions_table = Mock()
        return service
    
    def test_session_creation_with_exception(self, db_service):
        """Test handling of DynamoDB exceptions during session creation"""
        # Mock DynamoDB raising an exception
        db_service.auth_sessions_table.put_item.side_effect = Exception("DynamoDB error")
        
        session = AuthenticationSession(
            session_id="test-session",
            employee_id="123456",
            auth_method="face",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            cognito_token="test-token"
        )
        
        # Should raise exception
        with pytest.raises(Exception) as exc_info:
            db_service.create_auth_session(session)
        
        assert "DynamoDB error" in str(exc_info.value)
    
    def test_session_retrieval_with_exception(self, db_service):
        """Test handling of DynamoDB exceptions during session retrieval"""
        # Mock DynamoDB raising an exception
        db_service.auth_sessions_table.get_item.side_effect = Exception("DynamoDB error")
        
        # Should raise exception
        with pytest.raises(Exception) as exc_info:
            db_service.get_auth_session("test-session")
        
        assert "DynamoDB error" in str(exc_info.value)
    
    def test_session_deletion_with_exception(self, db_service):
        """Test handling of DynamoDB exceptions during session deletion"""
        # Mock DynamoDB raising an exception
        db_service.auth_sessions_table.delete_item.side_effect = Exception("DynamoDB error")
        
        # Should raise exception
        with pytest.raises(Exception) as exc_info:
            db_service.delete_auth_session("test-session")
        
        assert "DynamoDB error" in str(exc_info.value)
    
    def test_session_with_decimal_ttl(self, db_service):
        """Test that Decimal TTL values are handled correctly"""
        # Create session with Decimal expires_at (as returned from DynamoDB)
        now = datetime.now()
        expires_timestamp = Decimal(str((now + timedelta(hours=8)).timestamp()))
        
        session_data = {
            'session_id': 'test-session',
            'employee_id': '123456',
            'auth_method': 'face',
            'created_at': now.isoformat(),
            'expires_at': expires_timestamp,
            'cognito_token': 'test-token',
            'ip_address': None,
            'user_agent': None
        }
        
        # Mock DynamoDB returning session with Decimal
        db_service.auth_sessions_table.get_item.return_value = {
            'Item': session_data
        }
        
        # Retrieve and verify conversion
        session = db_service.get_auth_session('test-session')
        
        assert session is not None
        assert isinstance(session.expires_at, datetime)
        assert session.session_id == 'test-session'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
