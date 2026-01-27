"""
Face-Auth IdP System - AWS Cognito Service

This module provides Cognito integration for user management and token issuance.
Handles:
- User creation (AdminCreateUser)
- Authentication and token generation (AdminInitiateAuth)
- JWT token validation
- Session expiration management

Requirements: 2.3, 3.5
"""

import boto3
import logging
import uuid
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import jwt
from jwt import PyJWKClient
import os

# Handle imports for both Lambda and local testing
try:
    from .models import AuthenticationSession, ErrorCodes
except ImportError:
    from models import AuthenticationSession, ErrorCodes

logger = logging.getLogger(__name__)


class CognitoService:
    """
    Service class for AWS Cognito operations in Face-Auth system
    
    Handles:
    - User creation and management
    - Token generation and validation
    - Session management
    """
    
    def __init__(self, user_pool_id: str, client_id: str, region: str = 'us-east-1'):
        """
        Initialize Cognito service
        
        Args:
            user_pool_id: Cognito User Pool ID
            client_id: Cognito User Pool Client ID
            region: AWS region
        """
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.region = region
        
        # JWT validation setup
        self.jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        self.jwk_client = PyJWKClient(self.jwks_url)
        
        # Session configuration
        self.session_duration_hours = int(os.getenv('SESSION_TIMEOUT_HOURS', '8'))
        
    def create_or_get_user(self, employee_id: str, employee_name: str) -> Tuple[bool, Optional[str]]:
        """
        Create a new Cognito user or get existing user
        
        Uses AdminCreateUser to create a user without requiring email/phone verification.
        The user is created with a temporary password that is immediately set to permanent.
        
        Args:
            employee_id: Employee identifier (used as username)
            employee_name: Employee full name
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Check if user already exists
            try:
                self.cognito_client.admin_get_user(
                    UserPoolId=self.user_pool_id,
                    Username=employee_id
                )
                logger.info(f"User {employee_id} already exists in Cognito")
                return True, None
                
            except self.cognito_client.exceptions.UserNotFoundException:
                # User doesn't exist, create new user
                logger.info(f"Creating new Cognito user for employee {employee_id}")
                
                # Generate a secure random password
                temp_password = self._generate_secure_password()
                
                # Create user with AdminCreateUser
                response = self.cognito_client.admin_create_user(
                    UserPoolId=self.user_pool_id,
                    Username=employee_id,
                    UserAttributes=[
                        {
                            'Name': 'name',
                            'Value': employee_name
                        },
                        {
                            'Name': 'custom:employee_id',
                            'Value': employee_id
                        }
                    ],
                    TemporaryPassword=temp_password,
                    MessageAction='SUPPRESS'  # Don't send welcome email
                )
                
                # Set permanent password immediately
                self.cognito_client.admin_set_user_password(
                    UserPoolId=self.user_pool_id,
                    Username=employee_id,
                    Password=temp_password,
                    Permanent=True
                )
                
                logger.info(f"Successfully created Cognito user {employee_id}")
                return True, None
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Cognito user creation error for {employee_id}: {error_code} - {error_message}")
            return False, f"User creation failed: {error_message}"
            
        except Exception as e:
            logger.error(f"Unexpected error creating Cognito user {employee_id}: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
    
    def generate_auth_token(self, employee_id: str, auth_method: str = 'face') -> Tuple[Optional[Dict], Optional[str]]:
        """
        Generate authentication tokens for a user using AdminInitiateAuth
        
        This method uses the ADMIN_NO_SRP_AUTH flow to generate tokens without
        requiring a password, since face authentication has already verified identity.
        
        Args:
            employee_id: Employee identifier (username)
            auth_method: Authentication method used ('face' or 'emergency')
            
        Returns:
            Tuple of (tokens_dict: Optional[Dict], error_message: Optional[str])
            tokens_dict contains: AccessToken, IdToken, RefreshToken, ExpiresIn
        """
        try:
            # For face authentication, we use a custom auth flow
            # Since the user is already verified via face recognition,
            # we use AdminInitiateAuth with ADMIN_NO_SRP_AUTH
            
            # First, ensure user exists
            success, error = self.create_or_get_user(employee_id, employee_id)
            if not success:
                return None, error
            
            # Generate a temporary password for this auth session
            temp_password = self._generate_secure_password()
            
            # Set the password
            self.cognito_client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=employee_id,
                Password=temp_password,
                Permanent=True
            )
            
            # Initiate authentication
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='ADMIN_NO_SRP_AUTH',
                AuthParameters={
                    'USERNAME': employee_id,
                    'PASSWORD': temp_password
                }
            )
            
            # Extract tokens from response
            auth_result = response.get('AuthenticationResult')
            if not auth_result:
                logger.error(f"No authentication result in Cognito response for {employee_id}")
                return None, "Authentication failed: No tokens returned"
            
            tokens = {
                'AccessToken': auth_result['AccessToken'],
                'IdToken': auth_result['IdToken'],
                'RefreshToken': auth_result.get('RefreshToken'),
                'ExpiresIn': auth_result['ExpiresIn'],
                'TokenType': auth_result['TokenType']
            }
            
            logger.info(f"Successfully generated auth tokens for {employee_id} via {auth_method}")
            return tokens, None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Cognito auth error for {employee_id}: {error_code} - {error_message}")
            return None, f"Authentication failed: {error_message}"
            
        except Exception as e:
            logger.error(f"Unexpected error generating tokens for {employee_id}: {str(e)}")
            return None, f"Unexpected error: {str(e)}"
    
    def validate_token(self, access_token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate a JWT access token
        
        Verifies:
        - Token signature using Cognito's public keys
        - Token expiration
        - Token issuer and audience
        
        Args:
            access_token: JWT access token to validate
            
        Returns:
            Tuple of (is_valid: bool, claims: Optional[Dict])
        """
        try:
            # Get the signing key from Cognito's JWKS
            signing_key = self.jwk_client.get_signing_key_from_jwt(access_token)
            
            # Decode and verify the token
            claims = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            )
            
            logger.info(f"Token validated successfully for user: {claims.get('username')}")
            return True, claims
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: Token has expired")
            return False, None
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return False, None
            
        except Exception as e:
            logger.error(f"Unexpected error validating token: {str(e)}")
            return False, None
    
    def create_authentication_session(self, employee_id: str, auth_method: str,
                                     ip_address: Optional[str] = None,
                                     user_agent: Optional[str] = None) -> Tuple[Optional[AuthenticationSession], Optional[str]]:
        """
        Create a complete authentication session with Cognito tokens
        
        This is the main method to call after successful authentication.
        It creates a Cognito user (if needed), generates tokens, and creates
        an AuthenticationSession object.
        
        Args:
            employee_id: Employee identifier
            auth_method: Authentication method ('face' or 'emergency')
            ip_address: Client IP address (optional)
            user_agent: Client user agent (optional)
            
        Returns:
            Tuple of (session: Optional[AuthenticationSession], error_message: Optional[str])
        """
        try:
            # Generate authentication tokens
            tokens, error = self.generate_auth_token(employee_id, auth_method)
            if error or not tokens:
                return None, error or "Failed to generate tokens"
            
            # Create session object
            session_id = str(uuid.uuid4())
            now = datetime.now()
            expires_at = now + timedelta(hours=self.session_duration_hours)
            
            session = AuthenticationSession(
                session_id=session_id,
                employee_id=employee_id,
                auth_method=auth_method,
                created_at=now,
                expires_at=expires_at,
                cognito_token=tokens['AccessToken'],
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            logger.info(f"Created authentication session {session_id} for employee {employee_id}")
            return session, None
            
        except Exception as e:
            logger.error(f"Error creating authentication session for {employee_id}: {str(e)}")
            return None, f"Session creation failed: {str(e)}"
    
    def refresh_token(self, refresh_token: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Refresh access and ID tokens using a refresh token
        
        Args:
            refresh_token: Cognito refresh token
            
        Returns:
            Tuple of (tokens_dict: Optional[Dict], error_message: Optional[str])
        """
        try:
            response = self.cognito_client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            auth_result = response.get('AuthenticationResult')
            if not auth_result:
                return None, "Token refresh failed: No tokens returned"
            
            tokens = {
                'AccessToken': auth_result['AccessToken'],
                'IdToken': auth_result['IdToken'],
                'ExpiresIn': auth_result['ExpiresIn'],
                'TokenType': auth_result['TokenType']
            }
            
            logger.info("Successfully refreshed authentication tokens")
            return tokens, None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Token refresh error: {error_code} - {error_message}")
            return None, f"Token refresh failed: {error_message}"
            
        except Exception as e:
            logger.error(f"Unexpected error refreshing token: {str(e)}")
            return None, f"Unexpected error: {str(e)}"
    
    def revoke_user_sessions(self, employee_id: str) -> Tuple[bool, Optional[str]]:
        """
        Revoke all sessions for a user (sign out globally)
        
        Args:
            employee_id: Employee identifier
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            self.cognito_client.admin_user_global_sign_out(
                UserPoolId=self.user_pool_id,
                Username=employee_id
            )
            
            logger.info(f"Successfully revoked all sessions for user {employee_id}")
            return True, None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Session revocation error for {employee_id}: {error_code} - {error_message}")
            return False, f"Session revocation failed: {error_message}"
            
        except Exception as e:
            logger.error(f"Unexpected error revoking sessions for {employee_id}: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
    
    def disable_user(self, employee_id: str) -> Tuple[bool, Optional[str]]:
        """
        Disable a user account (for account deactivation)
        
        Args:
            employee_id: Employee identifier
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            self.cognito_client.admin_disable_user(
                UserPoolId=self.user_pool_id,
                Username=employee_id
            )
            
            logger.info(f"Successfully disabled user {employee_id}")
            return True, None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"User disable error for {employee_id}: {error_code} - {error_message}")
            return False, f"User disable failed: {error_message}"
            
        except Exception as e:
            logger.error(f"Unexpected error disabling user {employee_id}: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
    
    def enable_user(self, employee_id: str) -> Tuple[bool, Optional[str]]:
        """
        Enable a previously disabled user account
        
        Args:
            employee_id: Employee identifier
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            self.cognito_client.admin_enable_user(
                UserPoolId=self.user_pool_id,
                Username=employee_id
            )
            
            logger.info(f"Successfully enabled user {employee_id}")
            return True, None
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"User enable error for {employee_id}: {error_code} - {error_message}")
            return False, f"User enable failed: {error_message}"
            
        except Exception as e:
            logger.error(f"Unexpected error enabling user {employee_id}: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
    
    @staticmethod
    def _generate_secure_password() -> str:
        """
        Generate a secure random password for Cognito users
        
        Returns:
            Secure random password string
        """
        import secrets
        import string
        
        # Generate a password that meets Cognito requirements:
        # - At least 12 characters
        # - Contains uppercase, lowercase, numbers, and symbols
        alphabet = string.ascii_letters + string.digits + string.punctuation
        password = ''.join(secrets.choice(alphabet) for _ in range(16))
        
        # Ensure it has at least one of each required character type
        if not any(c.isupper() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_uppercase)
        if not any(c.islower() for c in password):
            password = password[:-1] + secrets.choice(string.ascii_lowercase)
        if not any(c.isdigit() for c in password):
            password = password[:-1] + secrets.choice(string.digits)
        if not any(c in string.punctuation for c in password):
            password = password[:-1] + secrets.choice(string.punctuation)
        
        return password


# Utility functions

def create_cognito_service_from_env() -> CognitoService:
    """
    Create CognitoService instance from environment variables
    
    Returns:
        Configured CognitoService instance
    """
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
    client_id = os.getenv('COGNITO_CLIENT_ID')
    region = os.getenv('AWS_REGION', 'us-east-1')
    
    if not user_pool_id or not client_id:
        raise ValueError("COGNITO_USER_POOL_ID and COGNITO_CLIENT_ID must be set in environment")
    
    return CognitoService(user_pool_id, client_id, region)
