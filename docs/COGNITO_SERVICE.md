# AWS Cognito Service Documentation

## Overview

The `CognitoService` module provides comprehensive AWS Cognito integration for the Face-Auth IdP system. It handles user creation, authentication token generation, JWT validation, and session management.

**Requirements Addressed:** 2.3, 3.5

## Features

### Core Functionality

1. **User Management**
   - Create Cognito users without email/phone verification
   - Get existing users
   - Enable/disable user accounts
   - Global session revocation

2. **Token Management**
   - Generate JWT tokens using AdminInitiateAuth
   - Validate JWT tokens with signature verification
   - Refresh expired tokens
   - Automatic token expiration handling

3. **Session Management**
   - Create authentication sessions with metadata
   - Track IP addresses and user agents
   - Configurable session duration (default: 8 hours)
   - Integration with DynamoDB for session persistence

## Architecture

### Authentication Flow

```
Face Recognition / Emergency Auth
         ↓
Create/Get Cognito User (AdminCreateUser)
         ↓
Generate Tokens (AdminInitiateAuth)
         ↓
Create AuthenticationSession
         ↓
Store in DynamoDB
         ↓
Return Access Token to Client
```

### Token Validation Flow

```
Client Request with Bearer Token
         ↓
Extract JWT from Authorization Header
         ↓
Validate Signature using Cognito JWKS
         ↓
Verify Expiration and Claims
         ↓
Allow/Deny Request
```

## API Reference

### CognitoService Class

#### Initialization

```python
from cognito_service import CognitoService

service = CognitoService(
    user_pool_id='us-east-1_XXXXXXXXX',
    client_id='your-client-id',
    region='us-east-1'
)
```

Or use environment variables:

```python
from cognito_service import create_cognito_service_from_env

service = create_cognito_service_from_env()
```

**Required Environment Variables:**
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `COGNITO_CLIENT_ID`: Cognito User Pool Client ID
- `AWS_REGION`: AWS region (default: us-east-1)
- `SESSION_TIMEOUT_HOURS`: Session duration in hours (default: 8)

### Methods

#### create_or_get_user()

Create a new Cognito user or retrieve existing user.

```python
success, error = service.create_or_get_user(
    employee_id="123456",
    employee_name="홍길동"
)
```

**Parameters:**
- `employee_id` (str): Employee identifier (used as username)
- `employee_name` (str): Employee full name

**Returns:**
- `Tuple[bool, Optional[str]]`: (success, error_message)

**Behavior:**
- Checks if user exists using AdminGetUser
- Creates new user with AdminCreateUser if not found
- Sets a secure random password
- Suppresses welcome email
- Adds custom attributes (name, employee_id)

#### generate_auth_token()

Generate authentication tokens for a user.

```python
tokens, error = service.generate_auth_token(
    employee_id="123456",
    auth_method="face"
)
```

**Parameters:**
- `employee_id` (str): Employee identifier
- `auth_method` (str): Authentication method ('face' or 'emergency')

**Returns:**
- `Tuple[Optional[Dict], Optional[str]]`: (tokens_dict, error_message)

**Token Dictionary:**
```python
{
    'AccessToken': 'eyJraWQiOiI...',
    'IdToken': 'eyJraWQiOiI...',
    'RefreshToken': 'eyJjdHkiOiI...',
    'ExpiresIn': 3600,
    'TokenType': 'Bearer'
}
```

#### validate_token()

Validate a JWT access token.

```python
is_valid, claims = service.validate_token(access_token)
```

**Parameters:**
- `access_token` (str): JWT access token to validate

**Returns:**
- `Tuple[bool, Optional[Dict]]`: (is_valid, claims)

**Claims Dictionary:**
```python
{
    'username': '123456',
    'exp': 1234567890,
    'aud': 'client-id',
    'iss': 'https://cognito-idp.us-east-1.amazonaws.com/...'
}
```

**Validation Checks:**
- Token signature using Cognito's public keys (JWKS)
- Token expiration
- Token issuer and audience

#### create_authentication_session()

Create a complete authentication session with Cognito tokens.

```python
session, error = service.create_authentication_session(
    employee_id="123456",
    auth_method="face",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0..."
)
```

**Parameters:**
- `employee_id` (str): Employee identifier
- `auth_method` (str): Authentication method ('face' or 'emergency')
- `ip_address` (Optional[str]): Client IP address
- `user_agent` (Optional[str]): Client user agent

**Returns:**
- `Tuple[Optional[AuthenticationSession], Optional[str]]`: (session, error_message)

**AuthenticationSession Object:**
```python
AuthenticationSession(
    session_id='uuid',
    employee_id='123456',
    auth_method='face',
    created_at=datetime.now(),
    expires_at=datetime.now() + timedelta(hours=8),
    cognito_token='access-token',
    ip_address='192.168.1.100',
    user_agent='Mozilla/5.0...'
)
```

#### refresh_token()

Refresh access and ID tokens using a refresh token.

```python
tokens, error = service.refresh_token(refresh_token)
```

**Parameters:**
- `refresh_token` (str): Cognito refresh token

**Returns:**
- `Tuple[Optional[Dict], Optional[str]]`: (tokens_dict, error_message)

#### revoke_user_sessions()

Revoke all sessions for a user (global sign out).

```python
success, error = service.revoke_user_sessions(employee_id="123456")
```

**Parameters:**
- `employee_id` (str): Employee identifier

**Returns:**
- `Tuple[bool, Optional[str]]`: (success, error_message)

#### disable_user() / enable_user()

Disable or enable a user account.

```python
success, error = service.disable_user(employee_id="123456")
success, error = service.enable_user(employee_id="123456")
```

**Parameters:**
- `employee_id` (str): Employee identifier

**Returns:**
- `Tuple[bool, Optional[str]]`: (success, error_message)

## Usage Examples

### Example 1: Face Login Flow

```python
import os
from cognito_service import create_cognito_service_from_env
from dynamodb_service import DynamoDBService

def handle_face_login(employee_id: str, ip_address: str):
    # Initialize services
    cognito_service = create_cognito_service_from_env()
    db_service = DynamoDBService()
    db_service.initialize_tables(
        card_templates_table_name=os.getenv('CARD_TEMPLATES_TABLE'),
        employee_faces_table_name=os.getenv('EMPLOYEE_FACES_TABLE'),
        auth_sessions_table_name=os.getenv('AUTH_SESSIONS_TABLE')
    )
    
    # Create authentication session
    session, error = cognito_service.create_authentication_session(
        employee_id=employee_id,
        auth_method='face',
        ip_address=ip_address
    )
    
    if error:
        return {'error': error}
    
    # Store session in DynamoDB
    db_service.create_auth_session(session)
    
    # Update last login
    from datetime import datetime
    db_service.update_last_login(employee_id, datetime.now())
    
    return {
        'session_id': session.session_id,
        'access_token': session.cognito_token,
        'expires_at': session.expires_at.isoformat()
    }
```

### Example 2: Token Validation Middleware

```python
def validate_request(event):
    # Extract token from Authorization header
    auth_header = event.get('headers', {}).get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None, 'Missing or invalid Authorization header'
    
    access_token = auth_header[7:]  # Remove 'Bearer ' prefix
    
    # Validate token
    cognito_service = create_cognito_service_from_env()
    is_valid, claims = cognito_service.validate_token(access_token)
    
    if not is_valid:
        return None, 'Invalid or expired token'
    
    return claims.get('username'), None
```

### Example 3: Emergency Authentication

```python
def handle_emergency_auth(employee_id: str, employee_name: str):
    cognito_service = create_cognito_service_from_env()
    
    # Create authentication session
    session, error = cognito_service.create_authentication_session(
        employee_id=employee_id,
        auth_method='emergency'
    )
    
    if error:
        return {'error': error}
    
    return {
        'access_token': session.cognito_token,
        'expires_at': session.expires_at.isoformat()
    }
```

### Example 4: User Enrollment

```python
def enroll_employee(employee_id: str, employee_name: str):
    cognito_service = create_cognito_service_from_env()
    
    # Create Cognito user during enrollment
    success, error = cognito_service.create_or_get_user(
        employee_id=employee_id,
        employee_name=employee_name
    )
    
    if not success:
        return {'error': f'Failed to create user: {error}'}
    
    return {'success': True, 'message': 'User enrolled successfully'}
```

### Example 5: Logout

```python
def handle_logout(employee_id: str, session_id: str):
    cognito_service = create_cognito_service_from_env()
    db_service = DynamoDBService()
    db_service.initialize_tables(
        card_templates_table_name=os.getenv('CARD_TEMPLATES_TABLE'),
        employee_faces_table_name=os.getenv('EMPLOYEE_FACES_TABLE'),
        auth_sessions_table_name=os.getenv('AUTH_SESSIONS_TABLE')
    )
    
    # Revoke all Cognito sessions
    cognito_service.revoke_user_sessions(employee_id)
    
    # Delete session from DynamoDB
    db_service.delete_auth_session(session_id)
    
    return {'success': True, 'message': 'Logged out successfully'}
```

## Security Considerations

### Password Management

- Passwords are automatically generated using `secrets` module
- Minimum 16 characters with uppercase, lowercase, digits, and symbols
- Passwords are set as permanent immediately after user creation
- No password is ever exposed to the client

### Token Security

- JWT tokens are signed by Cognito using RS256 algorithm
- Token validation uses Cognito's public keys (JWKS)
- Tokens expire after configured duration (default: 1 hour for access tokens)
- Refresh tokens valid for 30 days

### Session Management

- Sessions stored in both Cognito and DynamoDB
- DynamoDB sessions use TTL for automatic cleanup
- IP address and user agent tracked for audit purposes
- Global sign-out revokes all user sessions

## Error Handling

### Common Errors

1. **UserNotFoundException**
   - User doesn't exist in Cognito
   - Automatically handled by creating new user

2. **NotAuthorizedException**
   - Invalid credentials or disabled user
   - Returns authentication failed error

3. **ExpiredSignatureError**
   - JWT token has expired
   - Client should use refresh token

4. **InvalidTokenError**
   - Malformed or invalid JWT
   - Returns invalid token error

### Error Response Format

```python
{
    'error': 'ERROR_CODE',
    'message': 'User-friendly message',
    'system_reason': 'Detailed technical reason (logged only)'
}
```

## Performance Considerations

### Token Caching

- JWKS keys are cached by PyJWKClient
- Reduces latency for token validation
- Keys automatically refreshed when needed

### Connection Pooling

- Boto3 client reuses connections
- Reduces overhead for repeated API calls

### Best Practices

1. **Reuse Service Instances**: Create CognitoService once per Lambda execution
2. **Validate Tokens Locally**: Use JWT validation instead of calling Cognito API
3. **Use Refresh Tokens**: Avoid creating new sessions frequently
4. **Monitor Rate Limits**: Cognito has API rate limits per user pool

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
python -m pytest tests/test_cognito_service.py -v
```

**Test Coverage:**
- User creation and retrieval
- Token generation and validation
- Session creation and management
- Error handling and edge cases
- Password generation security

### Integration Testing

For integration tests with real Cognito:

```python
# Set environment variables
os.environ['COGNITO_USER_POOL_ID'] = 'us-east-1_XXXXXXXXX'
os.environ['COGNITO_CLIENT_ID'] = 'your-client-id'
os.environ['AWS_REGION'] = 'us-east-1'

# Run integration test
service = create_cognito_service_from_env()
success, error = service.create_or_get_user('test123', 'Test User')
assert success
```

## Troubleshooting

### Issue: "No module named 'jwt'"

**Solution:** Install PyJWT library
```bash
pip install PyJWT==2.8.0 cryptography==41.0.7
```

### Issue: "Invalid token signature"

**Possible Causes:**
- Token from different user pool
- Token has been tampered with
- JWKS keys not properly loaded

**Solution:** Verify user pool ID and client ID match

### Issue: "Token has expired"

**Solution:** Use refresh token to get new access token
```python
tokens, error = service.refresh_token(refresh_token)
```

### Issue: "User creation failed"

**Possible Causes:**
- Invalid user pool configuration
- Missing IAM permissions
- User pool limits reached

**Solution:** Check CloudWatch logs for detailed error

## IAM Permissions Required

The Lambda execution role needs these Cognito permissions:

```json
{
    "Effect": "Allow",
    "Action": [
        "cognito-idp:AdminCreateUser",
        "cognito-idp:AdminSetUserPassword",
        "cognito-idp:AdminInitiateAuth",
        "cognito-idp:AdminGetUser",
        "cognito-idp:AdminUpdateUserAttributes",
        "cognito-idp:AdminUserGlobalSignOut",
        "cognito-idp:AdminDisableUser",
        "cognito-idp:AdminEnableUser"
    ],
    "Resource": "arn:aws:cognito-idp:REGION:ACCOUNT:userpool/POOL_ID"
}
```

## References

- [AWS Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [PyJWT Documentation](https://pyjwt.readthedocs.io/)
- [Face-Auth Requirements](../requirements.md)
- [Face-Auth Design](../design.md)
