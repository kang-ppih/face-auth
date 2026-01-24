"""
Unit tests for CognitoService

Tests cover:
- User creation and management
- Token generation and validation
- Session creation and management
- Error handling

Requirements: 2.3, 3.5
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import jwt
from botocore.exceptions import ClientError

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))

from cognito_service import CognitoService
from models import AuthenticationSession


class TestCognitoService:
    """Test suite for CognitoService class"""
    
    @pytest.fixture
    def cognito_service(self):
        """Create a CognitoService instance for testing"""
        with patch('cognito_service.PyJWKClient'):
            service = CognitoService(
                user_pool_id='us-east-1_TEST123',
                client_id='test-client-id',
                region='us-east-1'
            )
            return service
    
    @pytest.fixture
    def mock_cognito_client(self, cognito_service):
        """Mock the Cognito client"""
        cognito_service.cognito_client = Mock()
        return cognito_service.cognito_client
    
    def test_create_new_user_success(self, cognito_service, mock_cognito_client):
        """Test successful creation of a new Cognito user"""
        # Arrange
        employee_id = "123456"
        employee_name = "홍길동"
        
        # Create a proper exception class
        class UserNotFoundException(Exception):
            pass
        
        # User doesn't exist
        mock_cognito_client.exceptions = Mock()
        mock_cognito_client.exceptions.UserNotFoundException = UserNotFoundException
        mock_cognito_client.admin_get_user.side_effect = UserNotFoundException()
        
        # Mock successful user creation
        mock_cognito_client.admin_create_user.return_value = {
            'User': {
                'Username': employee_id,
                'UserStatus': 'FORCE_CHANGE_PASSWORD'
            }
        }
        
        mock_cognito_client.admin_set_user_password.return_value = {}
        
        # Act
        success, error = cognito_service.create_or_get_user(employee_id, employee_name)
        
        # Assert
        assert success is True
        assert error is None
        mock_cognito_client.admin_create_user.assert_called_once()
        mock_cognito_client.admin_set_user_password.assert_called_once()
        
        # Verify user attributes
        call_args = mock_cognito_client.admin_create_user.call_args
        user_attributes = call_args[1]['UserAttributes']
        assert any(attr['Name'] == 'name' and attr['Value'] == employee_name 
                  for attr in user_attributes)
        assert any(attr['Name'] == 'custom:employee_id' and attr['Value'] == employee_id 
                  for attr in user_attributes)
    
    def test_get_existing_user(self, cognito_service, mock_cognito_client):
        """Test getting an existing Cognito user"""
        # Arrange
        employee_id = "123456"
        employee_name = "홍길동"
        
        # User already exists
        mock_cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        
        # Act
        success, error = cognito_service.create_or_get_user(employee_id, employee_name)
        
        # Assert
        assert success is True
        assert error is None
        mock_cognito_client.admin_get_user.assert_called_once()
        mock_cognito_client.admin_create_user.assert_not_called()
    
    def test_create_user_failure(self, cognito_service, mock_cognito_client):
        """Test handling of user creation failure"""
        # Arrange
        employee_id = "123456"
        employee_name = "홍길동"
        
        # Create a proper exception class
        class UserNotFoundException(Exception):
            pass
        
        # User doesn't exist
        mock_cognito_client.exceptions = Mock()
        mock_cognito_client.exceptions.UserNotFoundException = UserNotFoundException
        mock_cognito_client.admin_get_user.side_effect = UserNotFoundException()
        
        # Mock creation failure
        mock_cognito_client.admin_create_user.side_effect = ClientError(
            {'Error': {'Code': 'InvalidParameterException', 'Message': 'Invalid parameter'}},
            'AdminCreateUser'
        )
        
        # Act
        success, error = cognito_service.create_or_get_user(employee_id, employee_name)
        
        # Assert
        assert success is False
        assert error is not None
        assert "User creation failed" in error
    
    def test_generate_auth_token_success(self, cognito_service, mock_cognito_client):
        """Test successful token generation"""
        # Arrange
        employee_id = "123456"
        
        # Mock user exists
        mock_cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        
        mock_cognito_client.admin_set_user_password.return_value = {}
        
        # Mock successful authentication
        mock_cognito_client.admin_initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock-access-token',
                'IdToken': 'mock-id-token',
                'RefreshToken': 'mock-refresh-token',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Act
        tokens, error = cognito_service.generate_auth_token(employee_id, 'face')
        
        # Assert
        assert error is None
        assert tokens is not None
        assert tokens['AccessToken'] == 'mock-access-token'
        assert tokens['IdToken'] == 'mock-id-token'
        assert tokens['RefreshToken'] == 'mock-refresh-token'
        assert tokens['ExpiresIn'] == 3600
        assert tokens['TokenType'] == 'Bearer'
        
        # Verify AdminInitiateAuth was called with correct parameters
        call_args = mock_cognito_client.admin_initiate_auth.call_args
        assert call_args[1]['AuthFlow'] == 'ADMIN_NO_SRP_AUTH'
        assert call_args[1]['AuthParameters']['USERNAME'] == employee_id
    
    def test_generate_auth_token_no_result(self, cognito_service, mock_cognito_client):
        """Test token generation when no authentication result is returned"""
        # Arrange
        employee_id = "123456"
        
        mock_cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        
        mock_cognito_client.admin_set_user_password.return_value = {}
        
        # Mock authentication with no result
        mock_cognito_client.admin_initiate_auth.return_value = {}
        
        # Act
        tokens, error = cognito_service.generate_auth_token(employee_id, 'face')
        
        # Assert
        assert tokens is None
        assert error is not None
        assert "No tokens returned" in error
    
    def test_generate_auth_token_failure(self, cognito_service, mock_cognito_client):
        """Test handling of token generation failure"""
        # Arrange
        employee_id = "123456"
        
        mock_cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        
        mock_cognito_client.admin_set_user_password.return_value = {}
        
        # Mock authentication failure
        mock_cognito_client.admin_initiate_auth.side_effect = ClientError(
            {'Error': {'Code': 'NotAuthorizedException', 'Message': 'User is disabled'}},
            'AdminInitiateAuth'
        )
        
        # Act
        tokens, error = cognito_service.generate_auth_token(employee_id, 'face')
        
        # Assert
        assert tokens is None
        assert error is not None
        assert "Authentication failed" in error
    
    def test_validate_token_success(self, cognito_service):
        """Test successful token validation"""
        # Arrange
        access_token = "mock-jwt-token"
        expected_claims = {
            'username': '123456',
            'exp': (datetime.now() + timedelta(hours=1)).timestamp(),
            'aud': cognito_service.client_id
        }
        
        # Mock JWT validation
        mock_signing_key = Mock()
        mock_signing_key.key = "mock-key"
        cognito_service.jwk_client.get_signing_key_from_jwt = Mock(return_value=mock_signing_key)
        
        with patch('cognito_service.jwt.decode', return_value=expected_claims):
            # Act
            is_valid, claims = cognito_service.validate_token(access_token)
        
        # Assert
        assert is_valid is True
        assert claims == expected_claims
        assert claims['username'] == '123456'
    
    def test_validate_token_expired(self, cognito_service):
        """Test validation of expired token"""
        # Arrange
        access_token = "expired-jwt-token"
        
        mock_signing_key = Mock()
        mock_signing_key.key = "mock-key"
        cognito_service.jwk_client.get_signing_key_from_jwt = Mock(return_value=mock_signing_key)
        
        with patch('cognito_service.jwt.decode', side_effect=jwt.ExpiredSignatureError):
            # Act
            is_valid, claims = cognito_service.validate_token(access_token)
        
        # Assert
        assert is_valid is False
        assert claims is None
    
    def test_validate_token_invalid(self, cognito_service):
        """Test validation of invalid token"""
        # Arrange
        access_token = "invalid-jwt-token"
        
        mock_signing_key = Mock()
        mock_signing_key.key = "mock-key"
        cognito_service.jwk_client.get_signing_key_from_jwt = Mock(return_value=mock_signing_key)
        
        with patch('cognito_service.jwt.decode', side_effect=jwt.InvalidTokenError):
            # Act
            is_valid, claims = cognito_service.validate_token(access_token)
        
        # Assert
        assert is_valid is False
        assert claims is None
    
    def test_create_authentication_session_success(self, cognito_service, mock_cognito_client):
        """Test successful authentication session creation"""
        # Arrange
        employee_id = "123456"
        auth_method = "face"
        ip_address = "192.168.1.100"
        user_agent = "Mozilla/5.0"
        
        # Mock user exists
        mock_cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        
        mock_cognito_client.admin_set_user_password.return_value = {}
        
        # Mock successful authentication
        mock_cognito_client.admin_initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock-access-token',
                'IdToken': 'mock-id-token',
                'RefreshToken': 'mock-refresh-token',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Act
        session, error = cognito_service.create_authentication_session(
            employee_id, auth_method, ip_address, user_agent
        )
        
        # Assert
        assert error is None
        assert session is not None
        assert isinstance(session, AuthenticationSession)
        assert session.employee_id == employee_id
        assert session.auth_method == auth_method
        assert session.cognito_token == 'mock-access-token'
        assert session.ip_address == ip_address
        assert session.user_agent == user_agent
        assert session.is_valid()  # Should be valid immediately after creation
    
    def test_create_authentication_session_token_failure(self, cognito_service, mock_cognito_client):
        """Test session creation when token generation fails"""
        # Arrange
        employee_id = "123456"
        auth_method = "face"
        
        mock_cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        
        mock_cognito_client.admin_set_user_password.return_value = {}
        
        # Mock authentication failure
        mock_cognito_client.admin_initiate_auth.side_effect = ClientError(
            {'Error': {'Code': 'NotAuthorizedException', 'Message': 'User is disabled'}},
            'AdminInitiateAuth'
        )
        
        # Act
        session, error = cognito_service.create_authentication_session(
            employee_id, auth_method
        )
        
        # Assert
        assert session is None
        assert error is not None
        assert "Authentication failed" in error
    
    def test_refresh_token_success(self, cognito_service, mock_cognito_client):
        """Test successful token refresh"""
        # Arrange
        refresh_token = "mock-refresh-token"
        
        mock_cognito_client.admin_initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'new-access-token',
                'IdToken': 'new-id-token',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Act
        tokens, error = cognito_service.refresh_token(refresh_token)
        
        # Assert
        assert error is None
        assert tokens is not None
        assert tokens['AccessToken'] == 'new-access-token'
        assert tokens['IdToken'] == 'new-id-token'
        
        # Verify correct auth flow was used
        call_args = mock_cognito_client.admin_initiate_auth.call_args
        assert call_args[1]['AuthFlow'] == 'REFRESH_TOKEN_AUTH'
        assert call_args[1]['AuthParameters']['REFRESH_TOKEN'] == refresh_token
    
    def test_refresh_token_failure(self, cognito_service, mock_cognito_client):
        """Test handling of token refresh failure"""
        # Arrange
        refresh_token = "invalid-refresh-token"
        
        mock_cognito_client.admin_initiate_auth.side_effect = ClientError(
            {'Error': {'Code': 'NotAuthorizedException', 'Message': 'Refresh token expired'}},
            'AdminInitiateAuth'
        )
        
        # Act
        tokens, error = cognito_service.refresh_token(refresh_token)
        
        # Assert
        assert tokens is None
        assert error is not None
        assert "Token refresh failed" in error
    
    def test_revoke_user_sessions_success(self, cognito_service, mock_cognito_client):
        """Test successful session revocation"""
        # Arrange
        employee_id = "123456"
        mock_cognito_client.admin_user_global_sign_out.return_value = {}
        
        # Act
        success, error = cognito_service.revoke_user_sessions(employee_id)
        
        # Assert
        assert success is True
        assert error is None
        mock_cognito_client.admin_user_global_sign_out.assert_called_once_with(
            UserPoolId=cognito_service.user_pool_id,
            Username=employee_id
        )
    
    def test_revoke_user_sessions_failure(self, cognito_service, mock_cognito_client):
        """Test handling of session revocation failure"""
        # Arrange
        employee_id = "123456"
        
        mock_cognito_client.admin_user_global_sign_out.side_effect = ClientError(
            {'Error': {'Code': 'UserNotFoundException', 'Message': 'User not found'}},
            'AdminUserGlobalSignOut'
        )
        
        # Act
        success, error = cognito_service.revoke_user_sessions(employee_id)
        
        # Assert
        assert success is False
        assert error is not None
        assert "Session revocation failed" in error
    
    def test_disable_user_success(self, cognito_service, mock_cognito_client):
        """Test successful user disabling"""
        # Arrange
        employee_id = "123456"
        mock_cognito_client.admin_disable_user.return_value = {}
        
        # Act
        success, error = cognito_service.disable_user(employee_id)
        
        # Assert
        assert success is True
        assert error is None
        mock_cognito_client.admin_disable_user.assert_called_once_with(
            UserPoolId=cognito_service.user_pool_id,
            Username=employee_id
        )
    
    def test_enable_user_success(self, cognito_service, mock_cognito_client):
        """Test successful user enabling"""
        # Arrange
        employee_id = "123456"
        mock_cognito_client.admin_enable_user.return_value = {}
        
        # Act
        success, error = cognito_service.enable_user(employee_id)
        
        # Assert
        assert success is True
        assert error is None
        mock_cognito_client.admin_enable_user.assert_called_once_with(
            UserPoolId=cognito_service.user_pool_id,
            Username=employee_id
        )
    
    def test_generate_secure_password(self):
        """Test secure password generation"""
        # Act
        password = CognitoService._generate_secure_password()
        
        # Assert
        assert len(password) >= 12
        assert any(c.isupper() for c in password)
        assert any(c.islower() for c in password)
        assert any(c.isdigit() for c in password)
        # Check for special characters
        import string
        assert any(c in string.punctuation for c in password)
    
    def test_generate_secure_password_uniqueness(self):
        """Test that generated passwords are unique"""
        # Act
        passwords = [CognitoService._generate_secure_password() for _ in range(10)]
        
        # Assert - all passwords should be unique
        assert len(set(passwords)) == 10
    
    def test_session_expiration(self, cognito_service, mock_cognito_client):
        """Test that session expiration is set correctly"""
        # Arrange
        employee_id = "123456"
        
        mock_cognito_client.admin_get_user.return_value = {
            'Username': employee_id,
            'UserStatus': 'CONFIRMED'
        }
        
        mock_cognito_client.admin_set_user_password.return_value = {}
        
        mock_cognito_client.admin_initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock-access-token',
                'IdToken': 'mock-id-token',
                'RefreshToken': 'mock-refresh-token',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Act
        session, error = cognito_service.create_authentication_session(employee_id, 'face')
        
        # Assert
        assert error is None
        assert session is not None
        
        # Check that expiration is set to configured hours in the future
        expected_expiration = session.created_at + timedelta(hours=cognito_service.session_duration_hours)
        # Allow 1 second tolerance for test execution time
        assert abs((session.expires_at - expected_expiration).total_seconds()) < 1


class TestCognitoServiceEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def cognito_service(self):
        """Create a CognitoService instance for testing"""
        with patch('cognito_service.PyJWKClient'):
            service = CognitoService(
                user_pool_id='us-east-1_TEST123',
                client_id='test-client-id',
                region='us-east-1'
            )
            return service
    
    def test_create_user_with_empty_name(self, cognito_service):
        """Test user creation with empty name"""
        cognito_service.cognito_client = Mock()
        
        # Create a proper exception class
        class UserNotFoundException(Exception):
            pass
        
        # User doesn't exist
        cognito_service.cognito_client.exceptions = Mock()
        cognito_service.cognito_client.exceptions.UserNotFoundException = UserNotFoundException
        cognito_service.cognito_client.admin_get_user.side_effect = UserNotFoundException()
        
        cognito_service.cognito_client.admin_create_user.return_value = {
            'User': {'Username': '123456'}
        }
        cognito_service.cognito_client.admin_set_user_password.return_value = {}
        
        # Act
        success, error = cognito_service.create_or_get_user("123456", "")
        
        # Assert - should still succeed (validation is done elsewhere)
        assert success is True
    
    def test_token_validation_with_malformed_token(self, cognito_service):
        """Test token validation with malformed JWT"""
        # Arrange
        malformed_token = "not.a.valid.jwt.token"
        
        cognito_service.jwk_client.get_signing_key_from_jwt = Mock(
            side_effect=jwt.InvalidTokenError
        )
        
        # Act
        is_valid, claims = cognito_service.validate_token(malformed_token)
        
        # Assert
        assert is_valid is False
        assert claims is None
    
    def test_create_session_with_missing_optional_fields(self, cognito_service):
        """Test session creation without optional IP and user agent"""
        cognito_service.cognito_client = Mock()
        
        cognito_service.cognito_client.admin_get_user.return_value = {
            'Username': '123456',
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
        
        # Act
        session, error = cognito_service.create_authentication_session("123456", "face")
        
        # Assert
        assert error is None
        assert session is not None
        assert session.ip_address is None
        assert session.user_agent is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
