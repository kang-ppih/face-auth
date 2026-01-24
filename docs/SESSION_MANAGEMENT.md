# AuthenticationSession DynamoDB Management

## Overview

This document describes the complete implementation of AuthenticationSession management in the Face-Auth IdP system. The session management system integrates AWS Cognito for token generation with DynamoDB for session persistence and automatic cleanup using TTL (Time To Live).

**Requirements Addressed:** 2.5, 10.7  
**Task:** 10.2 AuthenticationSession DynamoDB 관리 구현

## Architecture

### Components

1. **CognitoService** (`lambda/shared/cognito_service.py`)
   - Creates Cognito users
   - Generates JWT tokens (Access, ID, Refresh)
   - Validates tokens
   - Creates AuthenticationSession objects

2. **DynamoDBService** (`lambda/shared/dynamodb_service.py`)
   - Stores sessions in DynamoDB
   - Retrieves sessions by session_id
   - Deletes sessions (logout)
   - Automatic cleanup via TTL

3. **AuthenticationSession Model** (`lambda/shared/models.py`)
   - Data structure for session information
   - Validation logic (expiration check)
   - Serialization for DynamoDB storage

### Data Flow

```
┌─────────────────┐
│  Lambda Handler │
│  (face_login,   │
│  emergency_auth)│
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│ CognitoService.create_authentication_session()     │
│ - Creates Cognito user (if needed)                 │
│ - Generates JWT tokens                             │
│ - Creates AuthenticationSession object             │
└────────┬────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│ DynamoDBService.create_auth_session()              │
│ - Converts session to DynamoDB format              │
│ - Sets TTL field (expires_at as epoch timestamp)   │
│ - Stores in AuthSessions table                     │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│ DynamoDB AuthSessions Table                        │
│ - Partition Key: session_id                        │
│ - TTL Attribute: expires_at                        │
│ - Automatic cleanup of expired sessions            │
└─────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Session Creation

**Method:** `CognitoService.create_authentication_session()`

```python
session, error = cognito_service.create_authentication_session(
    employee_id="123456",
    auth_method="face",  # or "emergency"
    ip_address="192.168.1.100",  # optional
    user_agent="Mozilla/5.0"     # optional
)
```

**Process:**
1. Creates or retrieves Cognito user
2. Generates authentication tokens using AdminInitiateAuth
3. Creates AuthenticationSession object with:
   - Unique session_id (UUID)
   - Employee identifier
   - Authentication method
   - Creation and expiration timestamps
   - Cognito access token
   - Optional metadata (IP, user agent)

**Configuration:**
- Session duration: 8 hours (configurable via `SESSION_TIMEOUT_HOURS` env var)
- Token expiration: 1 hour (Cognito configuration)
- Refresh token: 30 days (Cognito configuration)

### 2. Session Storage

**Method:** `DynamoDBService.create_auth_session()`

```python
success = db_service.create_auth_session(session)
```

**DynamoDB Item Structure:**
```python
{
    'session_id': 'uuid-string',           # Partition key
    'employee_id': '123456',
    'auth_method': 'face',
    'created_at': '2024-01-15T10:30:00',   # ISO format
    'expires_at': 1705329000,              # Epoch timestamp (TTL)
    'cognito_token': 'jwt-access-token',
    'ip_address': '192.168.1.100',         # Optional
    'user_agent': 'Mozilla/5.0'            # Optional
}
```

**Key Features:**
- **TTL Field:** `expires_at` is stored as epoch timestamp for DynamoDB TTL
- **Automatic Cleanup:** DynamoDB automatically deletes expired sessions
- **No Overwrite:** Each session has unique session_id
- **Encryption:** Table uses AWS-managed encryption

### 3. Session Retrieval

**Method:** `DynamoDBService.get_auth_session()`

```python
session = db_service.get_auth_session(session_id)

if session and session.is_valid():
    # Session is active
    employee_id = session.employee_id
else:
    # Session expired or not found
    pass
```

**Validation:**
- Checks if session exists in DynamoDB
- Validates expiration using `session.is_valid()`
- Returns None if session not found

### 4. Session Deletion (Logout)

**Method:** `DynamoDBService.delete_auth_session()`

```python
success = db_service.delete_auth_session(session_id)
```

**Additional Cleanup:**
- Can also revoke Cognito tokens: `cognito_service.revoke_user_sessions(employee_id)`
- Global sign-out invalidates all user sessions

## Integration with Lambda Handlers

### Face Login Handler

```python
# After successful face matching
session, error = cognito_service.create_authentication_session(
    employee_id=employee_id,
    auth_method='face',
    ip_address=event.get('requestContext', {}).get('identity', {}).get('sourceIp'),
    user_agent=event.get('headers', {}).get('User-Agent')
)

if error:
    return error_response(500, "Session creation failed")

# Store in DynamoDB
db_service.create_auth_session(session)

# Return session info to client
return {
    'statusCode': 200,
    'body': json.dumps({
        'success': True,
        'session_id': session.session_id,
        'access_token': session.cognito_token,
        'expires_at': session.expires_at.isoformat()
    })
}
```

### Emergency Auth Handler

```python
# After successful AD authentication
session, error = cognito_service.create_authentication_session(
    employee_id=employee_id,
    auth_method='emergency',
    ip_address=ip_address,
    user_agent=user_agent
)

db_service.create_auth_session(session)
```

### Status Handler

```python
# Check session validity
session = db_service.get_auth_session(session_id)

if session and session.is_valid():
    return {
        'authenticated': True,
        'session_valid': True,
        'employee_id': session.employee_id,
        'expires_at': session.expires_at.isoformat()
    }
else:
    return {
        'authenticated': False,
        'session_valid': False
    }
```

## DynamoDB Table Configuration

### Table Definition (CDK)

```python
self.auth_sessions_table = dynamodb.Table(
    self, "AuthSessionsTable",
    table_name="FaceAuth-AuthSessions",
    partition_key=dynamodb.Attribute(
        name="session_id",
        type=dynamodb.AttributeType.STRING
    ),
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
    encryption=dynamodb.TableEncryption.AWS_MANAGED,
    removal_policy=RemovalPolicy.RETAIN,
    time_to_live_attribute="expires_at"  # Enable TTL
)
```

### TTL Configuration

- **Attribute:** `expires_at`
- **Format:** Epoch timestamp (integer)
- **Behavior:** DynamoDB automatically deletes items after expiration
- **Delay:** Up to 48 hours after expiration (DynamoDB TTL behavior)
- **Cost:** No additional charge for TTL deletions

## Security Considerations

### 1. Token Security

- **Access tokens** stored in DynamoDB are encrypted at rest
- **Refresh tokens** can be used to obtain new access tokens
- **Token validation** performed by Cognito JWT verification
- **Token revocation** available via global sign-out

### 2. Session Security

- **Unique session IDs** prevent session fixation attacks
- **IP tracking** enables audit logging and anomaly detection
- **User agent tracking** helps identify suspicious activity
- **Automatic expiration** limits exposure window

### 3. Data Protection

- **Encryption at rest:** AWS-managed KMS keys
- **Encryption in transit:** HTTPS/TLS for all API calls
- **Access control:** IAM policies restrict DynamoDB access
- **Audit logging:** CloudWatch logs all session operations

## Monitoring and Logging

### CloudWatch Metrics

- **Session creation rate:** Track authentication volume
- **Session validation failures:** Detect expired/invalid sessions
- **DynamoDB operations:** Monitor read/write capacity
- **TTL deletions:** Track automatic cleanup

### Log Events

```python
# Session creation
logger.info(f"Created authentication session {session_id} for employee {employee_id}")

# Session retrieval
logger.info(f"Checking session validity for session_id: {session_id}")

# Session expiration
logger.info(f"Session {session_id} has expired")

# Session deletion
logger.info(f"Deleted session {session_id}")
```

## Testing

### Unit Tests

**File:** `tests/test_cognito_service.py`
- Test session creation with Cognito
- Test token generation and validation
- Test session expiration handling
- Test error conditions

**File:** `tests/test_data_models.py`
- Test AuthenticationSession model
- Test DynamoDB operations
- Test TTL format conversion

### Integration Tests

**File:** `tests/test_session_management_integration.py`
- Test complete session lifecycle
- Test session expiration handling
- Test multiple sessions per user
- Test TTL format and automatic cleanup
- Test edge cases and error conditions

**Run Tests:**
```bash
# All session management tests
python -m pytest tests/test_session_management_integration.py -v

# Cognito service tests
python -m pytest tests/test_cognito_service.py -v

# Data model tests
python -m pytest tests/test_data_models.py::TestDynamoDBService::test_auth_session_operations -v
```

## Usage Examples

### Example 1: Complete Login Flow

```python
# 1. Authenticate user (face or emergency)
# ... authentication logic ...

# 2. Create session
session, error = cognito_service.create_authentication_session(
    employee_id="123456",
    auth_method="face",
    ip_address="192.168.1.100",
    user_agent="Mozilla/5.0"
)

if error:
    return {"error": error}

# 3. Store in DynamoDB
db_service.create_auth_session(session)

# 4. Return to client
return {
    "session_id": session.session_id,
    "access_token": session.cognito_token,
    "expires_at": session.expires_at.isoformat()
}
```

### Example 2: Validate Session

```python
# 1. Get session from DynamoDB
session = db_service.get_auth_session(session_id)

# 2. Check validity
if not session:
    return {"error": "Session not found"}

if not session.is_valid():
    return {"error": "Session expired"}

# 3. Optionally validate Cognito token
is_valid, claims = cognito_service.validate_token(session.cognito_token)

if not is_valid:
    return {"error": "Token invalid"}

# 4. Session is valid
return {"employee_id": session.employee_id}
```

### Example 3: Logout

```python
# 1. Delete session from DynamoDB
db_service.delete_auth_session(session_id)

# 2. Optionally revoke all Cognito sessions
cognito_service.revoke_user_sessions(employee_id)

return {"message": "Logged out successfully"}
```

### Example 4: Multiple Device Support

```python
# User can have multiple active sessions
# Each device gets its own session_id

# Desktop login
session1, _ = cognito_service.create_authentication_session(
    employee_id="123456",
    auth_method="face",
    user_agent="Desktop/Chrome"
)
db_service.create_auth_session(session1)

# Mobile login
session2, _ = cognito_service.create_authentication_session(
    employee_id="123456",
    auth_method="face",
    user_agent="Mobile/Safari"
)
db_service.create_auth_session(session2)

# Both sessions are independent and valid
```

## Troubleshooting

### Issue: Session not found after creation

**Cause:** DynamoDB eventual consistency  
**Solution:** Use consistent reads or wait briefly after creation

### Issue: Session still accessible after expiration

**Cause:** DynamoDB TTL has up to 48-hour delay  
**Solution:** Always check `session.is_valid()` in application code

### Issue: Token expired but session valid

**Cause:** Token expiration (1 hour) is shorter than session (8 hours)  
**Solution:** Use refresh token to obtain new access token

### Issue: Multiple sessions for same user

**Cause:** This is expected behavior (multi-device support)  
**Solution:** Use global sign-out to revoke all sessions if needed

## Performance Considerations

### DynamoDB Optimization

- **On-demand billing:** Automatically scales with traffic
- **Single-item operations:** Fast reads/writes by session_id
- **No GSI needed:** Partition key is sufficient for lookups
- **TTL cleanup:** Automatic, no manual maintenance required

### Cognito Optimization

- **Token caching:** Cache JWT validation results
- **Batch operations:** Use AdminInitiateAuth for efficiency
- **Connection pooling:** Reuse boto3 clients

### Lambda Optimization

- **Environment variables:** Pre-configure service instances
- **Connection reuse:** Keep DynamoDB/Cognito clients warm
- **Minimal data transfer:** Only store essential session data

## Future Enhancements

### Potential Improvements

1. **Session refresh endpoint:** Allow extending session without re-authentication
2. **Session activity tracking:** Update last_activity timestamp on each request
3. **Device fingerprinting:** Enhanced security with device identification
4. **Geolocation tracking:** Store and validate user location
5. **Session limits:** Enforce maximum concurrent sessions per user
6. **Session analytics:** Track login patterns and anomalies

### Scalability Considerations

- **DynamoDB auto-scaling:** Already handled by on-demand billing
- **Cognito limits:** 120 requests/second per user pool (can be increased)
- **Lambda concurrency:** 1000 concurrent executions (can be increased)
- **Session storage:** Unlimited with DynamoDB

## Conclusion

The AuthenticationSession DynamoDB management system provides:

✅ **Secure session storage** with encryption at rest  
✅ **Automatic cleanup** via DynamoDB TTL  
✅ **Multi-device support** with independent sessions  
✅ **Comprehensive logging** for audit and debugging  
✅ **Integration with Cognito** for token management  
✅ **Scalable architecture** with on-demand billing  
✅ **Thorough testing** with unit and integration tests  

The implementation is complete, tested, and ready for production use.
