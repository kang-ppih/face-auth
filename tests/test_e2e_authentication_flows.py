"""
End-to-End Integration Tests for Face-Auth Authentication Flows

This test suite verifies the complete authentication flows:
1. Enrollment flow: ID card OCR → AD verification → Face capture → Storage
2. Face login flow: Face capture → 1:N matching → Session creation
3. Re-enrollment flow: ID card OCR → AD verification → Face update
4. Emergency auth flow: ID card OCR → AD password → Session creation

Task 11: 체크포인트 - 백엔드 시스템 통합 검증
"""

import pytest
import sys
import os
import json
import base64
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda'))

# Import handlers
from enrollment.handler import handler as enrollment_handler
from face_login.handler import handler as face_login_handler
from re_enrollment.handler import handler as re_enrollment_handler
from emergency_auth.handler import handler as emergency_auth_handler
from status.handler import handler as status_handler


class TestEndToEndAuthenticationFlows:
    """End-to-end tests for complete authentication flows"""
    
    @pytest.fixture
    def test_image(self):
        """Create a test image"""
        img = Image.new('RGB', (200, 200), color='white')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        return base64.b64encode(buffer.getvalue()).decode()
    
    @pytest.fixture
    def setup_environment(self):
        """Set up environment variables for testing"""
        os.environ['FACE_AUTH_BUCKET'] = 'test-bucket'
        os.environ['CARD_TEMPLATES_TABLE'] = 'test-card-templates'
        os.environ['EMPLOYEE_FACES_TABLE'] = 'test-employee-faces'
        os.environ['AUTH_SESSIONS_TABLE'] = 'test-auth-sessions'
        os.environ['REKOGNITION_COLLECTION_ID'] = 'test-collection'
        os.environ['COGNITO_USER_POOL_ID'] = 'us-east-1_TEST123'
        os.environ['COGNITO_CLIENT_ID'] = 'test-client-id'
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['RATE_LIMIT_TABLE'] = 'test-rate-limit'
        yield
    
    def test_enrollment_flow_success(self, test_image, setup_environment):
        """
        Test complete enrollment flow: ID card → AD verification → Face capture → Storage
        
        Verifies:
        - ID card OCR processing
        - AD employee verification
        - Face liveness detection
        - Thumbnail creation and S3 storage
        - DynamoDB record creation
        """
        # Create enrollment request
        event = {
            'body': json.dumps({
                'id_card_image': test_image,
                'face_image': test_image
            }),
            'requestContext': {
                'requestId': 'test-request-id'
            }
        }
        
        context = Mock()
        context.get_remaining_time_in_millis = Mock(return_value=15000)
        
        # Mock AWS services
        with patch('enrollment.handler.boto3') as mock_boto3:
            # Mock Textract
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = {
                'Blocks': [
                    {
                        'BlockType': 'QUERY_RESULT',
                        'Text': '123456',
                        'Confidence': 95.0,
                        'Query': {'Alias': 'employee_id'}
                    },
                    {
                        'BlockType': 'QUERY_RESULT',
                        'Text': '홍길동',
                        'Confidence': 95.0,
                        'Query': {'Alias': 'employee_name'}
                    }
                ]
            }
            
            # Mock Rekognition
            mock_rekognition = Mock()
            mock_rekognition.detect_faces.return_value = {
                'FaceDetails': [{
                    'Confidence': 99.5,
                    'BoundingBox': {'Width': 0.5, 'Height': 0.5, 'Left': 0.25, 'Top': 0.25}
                }]
            }
            mock_rekognition.index_faces.return_value = {
                'FaceRecords': [{
                    'Face': {
                        'FaceId': 'test-face-id',
                        'Confidence': 99.5
                    }
                }]
            }
            
            # Mock S3
            mock_s3 = Mock()
            mock_s3.put_object.return_value = {}
            
            # Mock DynamoDB
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_table.put_item.return_value = {}
            mock_table.get_item.return_value = {
                'Item': {
                    'pattern_id': 'test-pattern',
                    'fields': [
                        {'field_name': 'employee_id', 'query_phrase': '사번은?'},
                        {'field_name': 'employee_name', 'query_phrase': '성명은?'}
                    ]
                }
            }
            mock_table.scan.return_value = {
                'Items': [{
                    'pattern_id': 'test-pattern',
                    'is_active': True,
                    'fields': [
                        {'field_name': 'employee_id', 'query_phrase': '사번은?'},
                        {'field_name': 'employee_name', 'query_phrase': '성명은?'}
                    ]
                }]
            }
            mock_dynamodb.Table.return_value = mock_table
            
            # Configure boto3 client factory
            def get_client(service_name, **kwargs):
                if service_name == 'textract':
                    return mock_textract
                elif service_name == 'rekognition':
                    return mock_rekognition
                elif service_name == 's3':
                    return mock_s3
                return Mock()
            
            def get_resource(service_name, **kwargs):
                if service_name == 'dynamodb':
                    return mock_dynamodb
                return Mock()
            
            mock_boto3.client.side_effect = get_client
            mock_boto3.resource.side_effect = get_resource
            
            # Mock AD connector (graceful fallback)
            with patch('enrollment.handler.ADConnector') as mock_ad:
                mock_ad_instance = Mock()
                mock_ad_instance.verify_employee.return_value = Mock(
                    success=True,
                    employee_data={'employee_id': '123456', 'name': '홍길동'}
                )
                mock_ad.return_value = mock_ad_instance
                
                # Execute enrollment
                response = enrollment_handler(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'employee_id' in body
        assert 'face_id' in body
    
    def test_face_login_flow_success(self, test_image, setup_environment):
        """
        Test complete face login flow: Face capture → 1:N matching → Session creation
        
        Verifies:
        - Face liveness detection
        - 1:N face matching against enrolled faces
        - Cognito session creation
        - DynamoDB session storage
        """
        event = {
            'body': json.dumps({
                'face_image': test_image
            }),
            'requestContext': {
                'requestId': 'test-request-id'
            }
        }
        
        context = Mock()
        context.get_remaining_time_in_millis = Mock(return_value=15000)
        
        with patch('face_login.handler.boto3') as mock_boto3:
            # Mock Rekognition
            mock_rekognition = Mock()
            mock_rekognition.detect_faces.return_value = {
                'FaceDetails': [{
                    'Confidence': 99.5,
                    'BoundingBox': {'Width': 0.5, 'Height': 0.5, 'Left': 0.25, 'Top': 0.25}
                }]
            }
            mock_rekognition.search_faces_by_image.return_value = {
                'FaceMatches': [{
                    'Face': {
                        'FaceId': 'test-face-id',
                        'ExternalImageId': '123456',
                        'Confidence': 99.5
                    },
                    'Similarity': 98.5
                }]
            }
            
            # Mock DynamoDB
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_table.get_item.return_value = {
                'Item': {
                    'employee_id': '123456',
                    'face_id': 'test-face-id',
                    'is_active': True
                }
            }
            mock_table.put_item.return_value = {}
            mock_dynamodb.Table.return_value = mock_table
            
            # Mock Cognito
            mock_cognito = Mock()
            mock_cognito.admin_get_user.return_value = {
                'Username': '123456',
                'UserStatus': 'CONFIRMED'
            }
            mock_cognito.admin_set_user_password.return_value = {}
            mock_cognito.admin_initiate_auth.return_value = {
                'AuthenticationResult': {
                    'AccessToken': 'test-access-token',
                    'IdToken': 'test-id-token',
                    'RefreshToken': 'test-refresh-token',
                    'ExpiresIn': 3600,
                    'TokenType': 'Bearer'
                }
            }
            
            # Mock S3
            mock_s3 = Mock()
            mock_s3.put_object.return_value = {}
            
            def get_client(service_name, **kwargs):
                if service_name == 'rekognition':
                    return mock_rekognition
                elif service_name == 'cognito-idp':
                    return mock_cognito
                elif service_name == 's3':
                    return mock_s3
                return Mock()
            
            def get_resource(service_name, **kwargs):
                if service_name == 'dynamodb':
                    return mock_dynamodb
                return Mock()
            
            mock_boto3.client.side_effect = get_client
            mock_boto3.resource.side_effect = get_resource
            
            # Execute face login
            response = face_login_handler(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'employee_id' in body
        assert 'session_id' in body
        assert 'access_token' in body
    
    def test_re_enrollment_flow_success(self, test_image, setup_environment):
        """
        Test complete re-enrollment flow: ID card → AD verification → Face update
        
        Verifies:
        - ID card OCR processing
        - AD employee verification
        - Existing enrollment check
        - Old face deletion from Rekognition
        - New face indexing
        - DynamoDB record update
        """
        event = {
            'body': json.dumps({
                'id_card_image': test_image,
                'face_image': test_image
            }),
            'requestContext': {
                'requestId': 'test-request-id'
            }
        }
        
        context = Mock()
        context.get_remaining_time_in_millis = Mock(return_value=15000)
        
        with patch('re_enrollment.handler.boto3') as mock_boto3:
            # Mock Textract
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = {
                'Blocks': [
                    {
                        'BlockType': 'QUERY_RESULT',
                        'Text': '123456',
                        'Confidence': 95.0,
                        'Query': {'Alias': 'employee_id'}
                    }
                ]
            }
            
            # Mock Rekognition
            mock_rekognition = Mock()
            mock_rekognition.detect_faces.return_value = {
                'FaceDetails': [{
                    'Confidence': 99.5,
                    'BoundingBox': {'Width': 0.5, 'Height': 0.5, 'Left': 0.25, 'Top': 0.25}
                }]
            }
            mock_rekognition.delete_faces.return_value = {}
            mock_rekognition.index_faces.return_value = {
                'FaceRecords': [{
                    'Face': {
                        'FaceId': 'new-face-id',
                        'Confidence': 99.5
                    }
                }]
            }
            
            # Mock S3
            mock_s3 = Mock()
            mock_s3.put_object.return_value = {}
            
            # Mock DynamoDB
            mock_dynamodb = Mock()
            mock_table = Mock()
            # Existing enrollment
            mock_table.get_item.side_effect = [
                {  # Card template
                    'Item': {
                        'pattern_id': 'test-pattern',
                        'fields': [
                            {'field_name': 'employee_id', 'query_phrase': '사번은?'}
                        ]
                    }
                },
                {  # Existing employee face record
                    'Item': {
                        'employee_id': '123456',
                        'face_id': 'old-face-id',
                        'is_active': True,
                        're_enrollment_count': 0
                    }
                }
            ]
            mock_table.scan.return_value = {
                'Items': [{
                    'pattern_id': 'test-pattern',
                    'is_active': True,
                    'fields': [
                        {'field_name': 'employee_id', 'query_phrase': '사번은?'}
                    ]
                }]
            }
            mock_table.put_item.return_value = {}
            mock_dynamodb.Table.return_value = mock_table
            
            def get_client(service_name, **kwargs):
                if service_name == 'textract':
                    return mock_textract
                elif service_name == 'rekognition':
                    return mock_rekognition
                elif service_name == 's3':
                    return mock_s3
                return Mock()
            
            def get_resource(service_name, **kwargs):
                if service_name == 'dynamodb':
                    return mock_dynamodb
                return Mock()
            
            mock_boto3.client.side_effect = get_client
            mock_boto3.resource.side_effect = get_resource
            
            # Mock AD connector
            with patch('re_enrollment.handler.ADConnector') as mock_ad:
                mock_ad_instance = Mock()
                mock_ad_instance.verify_employee.return_value = Mock(
                    success=True,
                    employee_data={'employee_id': '123456'}
                )
                mock_ad.return_value = mock_ad_instance
                
                # Execute re-enrollment
                response = re_enrollment_handler(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert body['old_face_id'] == 'old-face-id'
        assert body['new_face_id'] == 'new-face-id'
        assert body['re_enrollment_count'] == 1
    
    def test_emergency_auth_flow_success(self, test_image, setup_environment):
        """
        Test complete emergency auth flow: ID card → AD password → Session creation
        
        Verifies:
        - ID card OCR processing
        - AD password authentication
        - Rate limiting check
        - Cognito session creation
        """
        event = {
            'body': json.dumps({
                'id_card_image': test_image,
                'password': 'test_password'
            }),
            'requestContext': {
                'requestId': 'test-request-id'
            }
        }
        
        context = Mock()
        context.get_remaining_time_in_millis = Mock(return_value=15000)
        
        with patch('emergency_auth.handler.boto3') as mock_boto3:
            # Mock Textract
            mock_textract = Mock()
            mock_textract.analyze_document.return_value = {
                'Blocks': [
                    {
                        'BlockType': 'QUERY_RESULT',
                        'Text': '123456',
                        'Confidence': 95.0,
                        'Query': {'Alias': 'employee_id'}
                    }
                ]
            }
            
            # Mock DynamoDB
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_table.get_item.side_effect = [
                {  # Card template
                    'Item': {
                        'pattern_id': 'test-pattern',
                        'fields': [
                            {'field_name': 'employee_id', 'query_phrase': '사번은?'}
                        ]
                    }
                },
                {  # Rate limit check - no existing record
                    'Item': None
                }
            ]
            mock_table.scan.return_value = {
                'Items': [{
                    'pattern_id': 'test-pattern',
                    'is_active': True,
                    'fields': [
                        {'field_name': 'employee_id', 'query_phrase': '사번은?'}
                    ]
                }]
            }
            mock_table.put_item.return_value = {}
            mock_dynamodb.Table.return_value = mock_table
            
            # Mock Cognito
            mock_cognito = Mock()
            mock_cognito.admin_get_user.return_value = {
                'Username': '123456',
                'UserStatus': 'CONFIRMED'
            }
            mock_cognito.admin_set_user_password.return_value = {}
            mock_cognito.admin_initiate_auth.return_value = {
                'AuthenticationResult': {
                    'AccessToken': 'test-access-token',
                    'IdToken': 'test-id-token',
                    'RefreshToken': 'test-refresh-token',
                    'ExpiresIn': 3600,
                    'TokenType': 'Bearer'
                }
            }
            
            def get_client(service_name, **kwargs):
                if service_name == 'textract':
                    return mock_textract
                elif service_name == 'cognito-idp':
                    return mock_cognito
                return Mock()
            
            def get_resource(service_name, **kwargs):
                if service_name == 'dynamodb':
                    return mock_dynamodb
                return Mock()
            
            mock_boto3.client.side_effect = get_client
            mock_boto3.resource.side_effect = get_resource
            
            # Mock AD connector
            with patch('emergency_auth.handler.ADConnector') as mock_ad:
                mock_ad_instance = Mock()
                mock_ad_instance.authenticate_password.return_value = Mock(
                    success=True,
                    employee_data={'employee_id': '123456'}
                )
                mock_ad.return_value = mock_ad_instance
                
                # Execute emergency auth
                response = emergency_auth_handler(event, context)
        
        # Verify response
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['success'] is True
        assert 'employee_id' in body
        assert 'session_id' in body
        assert 'access_token' in body


class TestErrorHandlingScenarios:
    """Test error handling across authentication flows"""
    
    @pytest.fixture
    def setup_environment(self):
        """Set up environment variables"""
        os.environ['FACE_AUTH_BUCKET'] = 'test-bucket'
        os.environ['CARD_TEMPLATES_TABLE'] = 'test-card-templates'
        os.environ['EMPLOYEE_FACES_TABLE'] = 'test-employee-faces'
        os.environ['AUTH_SESSIONS_TABLE'] = 'test-auth-sessions'
        os.environ['REKOGNITION_COLLECTION_ID'] = 'test-collection'
        os.environ['COGNITO_USER_POOL_ID'] = 'us-east-1_TEST123'
        os.environ['COGNITO_CLIENT_ID'] = 'test-client-id'
        os.environ['AWS_REGION'] = 'us-east-1'
        yield
    
    def test_enrollment_missing_fields(self, setup_environment):
        """Test enrollment with missing required fields"""
        event = {
            'body': json.dumps({
                'face_image': 'test'
                # Missing id_card_image
            }),
            'requestContext': {
                'requestId': 'test-request-id'
            }
        }
        
        context = Mock()
        context.get_remaining_time_in_millis = Mock(return_value=15000)
        
        response = enrollment_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body
    
    def test_face_login_no_match(self, setup_environment):
        """Test face login when no matching face is found"""
        test_image = base64.b64encode(b'test_image').decode()
        
        event = {
            'body': json.dumps({
                'face_image': test_image
            }),
            'requestContext': {
                'requestId': 'test-request-id'
            }
        }
        
        context = Mock()
        context.get_remaining_time_in_millis = Mock(return_value=15000)
        
        with patch('face_login.handler.boto3') as mock_boto3:
            # Mock Rekognition with no matches
            mock_rekognition = Mock()
            mock_rekognition.detect_faces.return_value = {
                'FaceDetails': [{
                    'Confidence': 99.5,
                    'BoundingBox': {'Width': 0.5, 'Height': 0.5, 'Left': 0.25, 'Top': 0.25}
                }]
            }
            mock_rekognition.search_faces_by_image.return_value = {
                'FaceMatches': []  # No matches
            }
            
            # Mock S3 for storing failed attempt
            mock_s3 = Mock()
            mock_s3.put_object.return_value = {}
            
            # Mock DynamoDB
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_dynamodb.Table.return_value = mock_table
            
            def get_client(service_name, **kwargs):
                if service_name == 'rekognition':
                    return mock_rekognition
                elif service_name == 's3':
                    return mock_s3
                return Mock()
            
            def get_resource(service_name, **kwargs):
                if service_name == 'dynamodb':
                    return mock_dynamodb
                return Mock()
            
            mock_boto3.client.side_effect = get_client
            mock_boto3.resource.side_effect = get_resource
            
            response = face_login_handler(event, context)
        
        # Should return 401 for no match
        assert response['statusCode'] == 401
        body = json.loads(response['body'])
        assert body['error'] == 'FACE_NOT_FOUND'
    
    def test_emergency_auth_rate_limit(self, setup_environment):
        """Test emergency auth rate limiting"""
        test_image = base64.b64encode(b'test_image').decode()
        
        event = {
            'body': json.dumps({
                'id_card_image': test_image,
                'password': 'test_password'
            }),
            'requestContext': {
                'requestId': 'test-request-id',
                'identity': {
                    'sourceIp': '192.168.1.1'
                }
            }
        }
        
        context = Mock()
        context.get_remaining_time_in_millis = Mock(return_value=15000)
        
        with patch('emergency_auth.handler.boto3') as mock_boto3:
            # Mock DynamoDB with rate limit exceeded
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_table.get_item.return_value = {
                'Item': {
                    'ip_address': '192.168.1.1',
                    'attempt_count': 10,  # Exceeded limit
                    'last_attempt': datetime.now().isoformat()
                }
            }
            mock_dynamodb.Table.return_value = mock_table
            
            def get_resource(service_name, **kwargs):
                if service_name == 'dynamodb':
                    return mock_dynamodb
                return Mock()
            
            mock_boto3.resource.side_effect = get_resource
            
            response = emergency_auth_handler(event, context)
        
        # Should return 429 for rate limit
        assert response['statusCode'] == 429
        body = json.loads(response['body'])
        assert 'error' in body


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
