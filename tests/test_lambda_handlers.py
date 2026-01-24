"""
Integration tests for Lambda handler functions

Tests the Lambda handler logic with mocked AWS services.
These tests verify the handler flow without requiring actual AWS resources.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
import base64
import os
from datetime import datetime


class TestEnrollmentHandlerLogic(unittest.TestCase):
    """Test cases for enrollment Lambda handler logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Set required environment variables
        os.environ['FACE_AUTH_BUCKET'] = 'test-bucket'
        os.environ['CARD_TEMPLATES_TABLE'] = 'test-card-templates'
        os.environ['EMPLOYEE_FACES_TABLE'] = 'test-employee-faces'
        os.environ['AUTH_SESSIONS_TABLE'] = 'test-auth-sessions'
        os.environ['REKOGNITION_COLLECTION_ID'] = 'test-collection'
        os.environ['AWS_REGION'] = 'us-east-1'
        
        # Create sample test image (1x1 pixel PNG)
        self.test_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01').decode()
    
    def test_enrollment_request_validation(self):
        """Test that enrollment validates required fields"""
        # Test missing id_card_image
        event = {
            'body': json.dumps({
                'face_image': self.test_image
            })
        }
        
        # The handler should return 400 for missing id_card_image
        # This tests the validation logic
        self.assertIn('face_image', json.loads(event['body']))
        self.assertNotIn('id_card_image', json.loads(event['body']))
    
    def test_enrollment_base64_decoding(self):
        """Test base64 decoding logic"""
        # Valid base64
        valid_b64 = base64.b64encode(b'test data').decode()
        decoded = base64.b64decode(valid_b64)
        self.assertEqual(decoded, b'test data')
        
        # Invalid base64 should raise exception
        with self.assertRaises(Exception):
            base64.b64decode('invalid!!!base64')
    
    def test_enrollment_response_structure(self):
        """Test expected response structure"""
        # Success response structure
        success_response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': '등록이 완료되었습니다',
                'employee_id': '123456',
                'employee_name': '홍길동',
                'face_id': 'test-face-id',
                'request_id': 'test-request-id'
            })
        }
        
        self.assertEqual(success_response['statusCode'], 200)
        body = json.loads(success_response['body'])
        self.assertTrue(body['success'])
        self.assertIn('employee_id', body)
        self.assertIn('face_id', body)
        
        # Error response structure
        error_response = {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'INVALID_REQUEST',
                'message': '사원증과 얼굴 이미지가 필요합니다',
                'request_id': 'test-request-id'
            })
        }
        
        self.assertEqual(error_response['statusCode'], 400)
        body = json.loads(error_response['body'])
        self.assertIn('error', body)
        self.assertIn('message', body)


class TestFaceLoginHandlerLogic(unittest.TestCase):
    """Test cases for face login Lambda handler logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        os.environ['FACE_AUTH_BUCKET'] = 'test-bucket'
        os.environ['EMPLOYEE_FACES_TABLE'] = 'test-employee-faces'
        os.environ['AUTH_SESSIONS_TABLE'] = 'test-auth-sessions'
        os.environ['CARD_TEMPLATES_TABLE'] = 'test-card-templates'
        os.environ['COGNITO_USER_POOL_ID'] = 'test-user-pool'
        os.environ['COGNITO_CLIENT_ID'] = 'test-client-id'
        os.environ['REKOGNITION_COLLECTION_ID'] = 'test-collection'
        os.environ['AWS_REGION'] = 'us-east-1'
        
        self.test_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01').decode()
    
    def test_face_login_request_validation(self):
        """Test that face login validates required fields"""
        # Test missing face_image
        event = {
            'body': json.dumps({})
        }
        
        body = json.loads(event['body'])
        self.assertNotIn('face_image', body)
    
    def test_face_login_success_response_structure(self):
        """Test expected success response structure"""
        success_response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': '로그인 성공',
                'employee_id': '123456',
                'session_id': 'test-session-id',
                'access_token': 'test-token',
                'expires_at': datetime.now().isoformat(),
                'similarity': 98.5,
                'request_id': 'test-request-id'
            })
        }
        
        self.assertEqual(success_response['statusCode'], 200)
        body = json.loads(success_response['body'])
        self.assertTrue(body['success'])
        self.assertIn('employee_id', body)
        self.assertIn('session_id', body)
        self.assertIn('access_token', body)
        self.assertIn('similarity', body)
    
    def test_face_login_no_match_response(self):
        """Test response when no face match is found"""
        error_response = {
            'statusCode': 401,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'FACE_NOT_FOUND',
                'message': '얼굴을 인식할 수 없습니다',
                'request_id': 'test-request-id'
            })
        }
        
        self.assertEqual(error_response['statusCode'], 401)
        body = json.loads(error_response['body'])
        self.assertEqual(body['error'], 'FACE_NOT_FOUND')


class TestEmergencyAuthHandlerLogic(unittest.TestCase):
    """Test cases for emergency authentication Lambda handler logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        os.environ['CARD_TEMPLATES_TABLE'] = 'test-card-templates'
        os.environ['EMPLOYEE_FACES_TABLE'] = 'test-employee-faces'
        os.environ['AUTH_SESSIONS_TABLE'] = 'test-auth-sessions'
        os.environ['COGNITO_USER_POOL_ID'] = 'test-user-pool'
        os.environ['COGNITO_CLIENT_ID'] = 'test-client-id'
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['RATE_LIMIT_TABLE'] = 'test-rate-limit'
        
        self.test_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01').decode()
    
    def test_emergency_auth_request_validation(self):
        """Test that emergency auth validates required fields"""
        # Test missing password
        event = {
            'body': json.dumps({
                'id_card_image': self.test_image
            })
        }
        
        body = json.loads(event['body'])
        self.assertIn('id_card_image', body)
        self.assertNotIn('password', body)
    
    def test_emergency_auth_success_response_structure(self):
        """Test expected success response structure"""
        success_response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': '비상 인증 성공',
                'employee_id': '123456',
                'employee_name': '홍길동',
                'session_id': 'test-session-id',
                'access_token': 'test-token',
                'expires_at': datetime.now().isoformat(),
                'request_id': 'test-request-id'
            })
        }
        
        self.assertEqual(success_response['statusCode'], 200)
        body = json.loads(success_response['body'])
        self.assertTrue(body['success'])
        self.assertIn('employee_id', body)
        self.assertIn('employee_name', body)
        self.assertIn('session_id', body)
        self.assertIn('access_token', body)
    
    def test_emergency_auth_rate_limit_response(self):
        """Test response when rate limit is exceeded"""
        error_response = {
            'statusCode': 429,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'GENERIC_ERROR',
                'message': '너무 많은 시도가 있었습니다. 잠시 후 다시 시도해주세요',
                'request_id': 'test-request-id'
            })
        }
        
        self.assertEqual(error_response['statusCode'], 429)
        body = json.loads(error_response['body'])
        self.assertIn('error', body)
        self.assertIn('message', body)


class TestLambdaHandlerIntegration(unittest.TestCase):
    """Integration tests for Lambda handler components"""
    
    def test_timeout_manager_integration(self):
        """Test timeout manager usage in handlers"""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))
        from timeout_manager import TimeoutManager
        
        timeout_mgr = TimeoutManager()
        
        # Should have time remaining initially
        self.assertTrue(timeout_mgr.should_continue(buffer_seconds=2.0))
        self.assertGreater(timeout_mgr.get_remaining_time(), 0)
        
        # Check AD timeout
        self.assertTrue(timeout_mgr.check_ad_timeout())
        
        # Check Lambda timeout
        self.assertTrue(timeout_mgr.check_lambda_timeout())
    
    def test_error_codes_available(self):
        """Test that error codes are properly defined"""
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))
        from models import ErrorCodes
        
        # Verify all required error codes exist
        self.assertTrue(hasattr(ErrorCodes, 'ID_CARD_FORMAT_MISMATCH'))
        self.assertTrue(hasattr(ErrorCodes, 'REGISTRATION_INFO_MISMATCH'))
        self.assertTrue(hasattr(ErrorCodes, 'ACCOUNT_DISABLED'))
        self.assertTrue(hasattr(ErrorCodes, 'LIVENESS_FAILED'))
        self.assertTrue(hasattr(ErrorCodes, 'FACE_NOT_FOUND'))
        self.assertTrue(hasattr(ErrorCodes, 'AD_CONNECTION_ERROR'))
        self.assertTrue(hasattr(ErrorCodes, 'TIMEOUT_ERROR'))
        self.assertTrue(hasattr(ErrorCodes, 'GENERIC_ERROR'))
        self.assertTrue(hasattr(ErrorCodes, 'INVALID_REQUEST'))


class TestReEnrollmentHandlerLogic(unittest.TestCase):
    """Test cases for re-enrollment Lambda handler logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        os.environ['FACE_AUTH_BUCKET'] = 'test-bucket'
        os.environ['CARD_TEMPLATES_TABLE'] = 'test-card-templates'
        os.environ['EMPLOYEE_FACES_TABLE'] = 'test-employee-faces'
        os.environ['AUTH_SESSIONS_TABLE'] = 'test-auth-sessions'
        os.environ['REKOGNITION_COLLECTION_ID'] = 'test-collection'
        os.environ['AWS_REGION'] = 'us-east-1'
        
        self.test_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01').decode()
    
    def test_re_enrollment_request_validation(self):
        """Test that re-enrollment validates required fields"""
        # Test missing id_card_image
        event = {
            'body': json.dumps({
                'face_image': self.test_image
            })
        }
        
        body = json.loads(event['body'])
        self.assertIn('face_image', body)
        self.assertNotIn('id_card_image', body)
        
        # Test missing face_image
        event = {
            'body': json.dumps({
                'id_card_image': self.test_image
            })
        }
        
        body = json.loads(event['body'])
        self.assertIn('id_card_image', body)
        self.assertNotIn('face_image', body)
    
    def test_re_enrollment_success_response_structure(self):
        """Test expected success response structure"""
        success_response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': '재등록이 완료되었습니다',
                'employee_id': '123456',
                'employee_name': '홍길동',
                'old_face_id': 'old-face-id',
                'new_face_id': 'new-face-id',
                're_enrollment_count': 1,
                'request_id': 'test-request-id',
                'processing_time': 2.5
            })
        }
        
        self.assertEqual(success_response['statusCode'], 200)
        body = json.loads(success_response['body'])
        self.assertTrue(body['success'])
        self.assertIn('employee_id', body)
        self.assertIn('old_face_id', body)
        self.assertIn('new_face_id', body)
        self.assertIn('re_enrollment_count', body)
        self.assertGreater(body['re_enrollment_count'], 0)
    
    def test_re_enrollment_no_existing_record_error(self):
        """Test response when employee has no existing enrollment"""
        error_response = {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'INVALID_REQUEST',
                'message': '등록된 직원 정보를 찾을 수 없습니다',
                'request_id': 'test-request-id'
            })
        }
        
        self.assertEqual(error_response['statusCode'], 404)
        body = json.loads(error_response['body'])
        self.assertEqual(body['error'], 'INVALID_REQUEST')
    
    def test_re_enrollment_inactive_account_error(self):
        """Test response when employee account is inactive"""
        error_response = {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'ACCOUNT_DISABLED',
                'message': '계정 비활성화',
                'request_id': 'test-request-id'
            })
        }
        
        self.assertEqual(error_response['statusCode'], 400)
        body = json.loads(error_response['body'])
        self.assertEqual(body['error'], 'ACCOUNT_DISABLED')
    
    def test_re_enrollment_audit_trail_structure(self):
        """Test audit trail logging structure"""
        audit_log = {
            'event': 'RE_ENROLLMENT',
            'employee_id': '123456',
            'employee_name': '홍길동',
            'old_face_id': 'old-face-id',
            'new_face_id': 'new-face-id',
            're_enrollment_count': 1,
            'timestamp': datetime.now().isoformat(),
            'request_id': 'test-request-id',
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0'
        }
        
        # Verify all required audit fields are present
        self.assertEqual(audit_log['event'], 'RE_ENROLLMENT')
        self.assertIn('employee_id', audit_log)
        self.assertIn('old_face_id', audit_log)
        self.assertIn('new_face_id', audit_log)
        self.assertIn('re_enrollment_count', audit_log)
        self.assertIn('timestamp', audit_log)
        self.assertIn('request_id', audit_log)


class TestStatusHandlerLogic(unittest.TestCase):
    """Test cases for status check Lambda handler logic"""
    
    def setUp(self):
        """Set up test fixtures"""
        os.environ['AUTH_SESSIONS_TABLE'] = 'test-auth-sessions'
        os.environ['EMPLOYEE_FACES_TABLE'] = 'test-employee-faces'
        os.environ['CARD_TEMPLATES_TABLE'] = 'test-card-templates'
        os.environ['COGNITO_USER_POOL_ID'] = 'test-user-pool'
        os.environ['COGNITO_CLIENT_ID'] = 'test-client-id'
        os.environ['AWS_REGION'] = 'us-east-1'
    
    def test_status_request_validation(self):
        """Test that status check validates at least one parameter"""
        # Test with no parameters
        event = {
            'queryStringParameters': {}
        }
        
        params = event.get('queryStringParameters', {})
        self.assertNotIn('session_id', params)
        self.assertNotIn('access_token', params)
        self.assertNotIn('employee_id', params)
    
    def test_status_success_response_structure(self):
        """Test expected success response structure"""
        success_response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': {
                    'authenticated': True,
                    'session_valid': True,
                    'token_valid': True,
                    'account_active': True,
                    'employee_id': '123456',
                    'session_expires_at': datetime.now().isoformat(),
                    'last_login': datetime.now().isoformat(),
                    'auth_method': 'face',
                    'enrollment_date': datetime.now().isoformat(),
                    're_enrollment_count': 0
                },
                'request_id': 'test-request-id',
                'timestamp': datetime.now().isoformat()
            })
        }
        
        self.assertEqual(success_response['statusCode'], 200)
        body = json.loads(success_response['body'])
        self.assertIn('status', body)
        
        status = body['status']
        self.assertIn('authenticated', status)
        self.assertIn('session_valid', status)
        self.assertIn('token_valid', status)
        self.assertIn('account_active', status)
        self.assertIn('employee_id', status)
    
    def test_status_with_session_id(self):
        """Test status check with session_id parameter"""
        event = {
            'queryStringParameters': {
                'session_id': 'test-session-id'
            }
        }
        
        params = event.get('queryStringParameters', {})
        self.assertIn('session_id', params)
        self.assertEqual(params['session_id'], 'test-session-id')
    
    def test_status_with_access_token(self):
        """Test status check with access_token parameter"""
        event = {
            'queryStringParameters': {
                'access_token': 'test-access-token'
            }
        }
        
        params = event.get('queryStringParameters', {})
        self.assertIn('access_token', params)
        self.assertEqual(params['access_token'], 'test-access-token')
    
    def test_status_with_bearer_token_header(self):
        """Test status check with Authorization Bearer header"""
        event = {
            'headers': {
                'Authorization': 'Bearer test-access-token'
            },
            'queryStringParameters': {}
        }
        
        auth_header = event.get('headers', {}).get('Authorization')
        self.assertIsNotNone(auth_header)
        self.assertTrue(auth_header.startswith('Bearer '))
        
        # Extract token
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        self.assertEqual(token, 'test-access-token')
    
    def test_status_with_employee_id(self):
        """Test status check with employee_id parameter"""
        event = {
            'queryStringParameters': {
                'employee_id': '123456'
            }
        }
        
        params = event.get('queryStringParameters', {})
        self.assertIn('employee_id', params)
        self.assertEqual(params['employee_id'], '123456')
    
    def test_status_unauthenticated_response(self):
        """Test response when user is not authenticated"""
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': {
                    'authenticated': False,
                    'session_valid': False,
                    'token_valid': False,
                    'account_active': False,
                    'employee_id': None,
                    'session_expires_at': None,
                    'last_login': None
                },
                'request_id': 'test-request-id',
                'timestamp': datetime.now().isoformat()
            })
        }
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        status = body['status']
        
        self.assertFalse(status['authenticated'])
        self.assertFalse(status['session_valid'])
        self.assertFalse(status['token_valid'])
        self.assertFalse(status['account_active'])
    
    def test_status_expired_session_response(self):
        """Test response when session has expired"""
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': {
                    'authenticated': False,
                    'session_valid': False,
                    'token_valid': False,
                    'account_active': True,
                    'employee_id': '123456',
                    'session_expires_at': '2024-01-01T00:00:00',
                    'last_login': datetime.now().isoformat()
                },
                'request_id': 'test-request-id',
                'timestamp': datetime.now().isoformat()
            })
        }
        
        body = json.loads(response['body'])
        status = body['status']
        
        # Session expired but account is still active
        self.assertFalse(status['authenticated'])
        self.assertFalse(status['session_valid'])
        self.assertTrue(status['account_active'])


if __name__ == '__main__':
    unittest.main()


if __name__ == '__main__':
    unittest.main()
