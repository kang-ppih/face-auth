"""
Backend System Integration Tests

This test suite verifies the integration of all backend services:
- OCR Service + DynamoDB (card templates)
- Face Recognition Service + Rekognition
- Cognito Service + Session Management
- Error Handler + Timeout Manager
- Complete service orchestration

Task 11: 체크포인트 - 백엔드 시스템 통합 검증
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import base64
from io import BytesIO
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared'))

from ocr_service import OCRService
from face_recognition_service import FaceRecognitionService
from cognito_service import CognitoService
from thumbnail_processor import ThumbnailProcessor
from error_handler import ErrorHandler
from timeout_manager import TimeoutManager
from dynamodb_service import DynamoDBService
from models import (
    EmployeeInfo, FaceData, AuthenticationSession, 
    CardTemplate, EmployeeFaceRecord, ErrorCodes
)


class TestBackendServiceIntegration:
    """Integration tests for backend services"""
    
    @pytest.fixture
    def test_image_bytes(self):
        """Create test image bytes"""
        img = Image.new('RGB', (200, 200), color='white')
        buffer = BytesIO()
        img.save(buffer, format='JPEG')
        return buffer.getvalue()
    
    @pytest.fixture
    def setup_environment(self):
        """Set up environment variables"""
        os.environ['FACE_AUTH_BUCKET'] = 'test-bucket'
        os.environ['CARD_TEMPLATES_TABLE'] = 'test-card-templates'
        os.environ['EMPLOYEE_FACES_TABLE'] = 'test-employee-faces'
        os.environ['AUTH_SESSIONS_TABLE'] = 'test-auth-sessions'
        os.environ['REKOGNITION_COLLECTION_ID'] = 'test-collection'
        os.environ['AWS_REGION'] = 'us-east-1'
        yield
    
    def test_enrollment_workflow_integration(self, test_image_bytes, setup_environment):
        """
        Test complete enrollment workflow integration:
        OCR → Face Recognition → Thumbnail → DynamoDB
        
        Verifies all services work together correctly
        """
        # Initialize services
        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:
            
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
                    },
                    {
                        'BlockType': 'QUERY_RESULT',
                        'Text': '개발팀',
                        'Confidence': 90.0,
                        'Query': {'Alias': 'department'}
                    }
                ]
            }
            
            # Mock Rekognition
            mock_rekognition = Mock()
            mock_rekognition.detect_faces.return_value = {
                'FaceDetails': [{
                    'Confidence': 99.5,
                    'BoundingBox': {
                        'Width': 0.5,
                        'Height': 0.5,
                        'Left': 0.25,
                        'Top': 0.25
                    },
                    'Landmarks': []
                }]
            }
            mock_rekognition.index_faces.return_value = {
                'FaceRecords': [{
                    'Face': {
                        'FaceId': 'test-face-id-123',
                        'Confidence': 99.5,
                        'BoundingBox': {
                            'Width': 0.5,
                            'Height': 0.5,
                            'Left': 0.25,
                            'Top': 0.25
                        }
                    }
                }]
            }
            
            # Mock S3
            mock_s3 = Mock()
            mock_s3.put_object.return_value = {}
            
            # Mock DynamoDB
            mock_dynamodb = Mock()
            mock_table = Mock()
            mock_table.scan.return_value = {
                'Items': [{
                    'pattern_id': 'test-pattern',
                    'card_type': 'standard_employee',
                    'is_active': True,
                    'fields': [
                        {
                            'field_name': 'employee_id',
                            'query_phrase': '사번은 무엇입니까?',
                            'expected_format': '\\d{6}'
                        },
                        {
                            'field_name': 'employee_name',
                            'query_phrase': '성명은 무엇입니까?',
                            'expected_format': '[가-힣]{2,4}'
                        },
                        {
                            'field_name': 'department',
                            'query_phrase': '부서는 무엇입니까?',
                            'expected_format': '.*'
                        }
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
            
            mock_client.side_effect = get_client
            mock_resource.side_effect = get_resource
            
            # Step 1: OCR Service extracts employee info
            ocr_service = OCRService()
            employee_info, error = ocr_service.extract_id_card_info(test_image_bytes)
            
            assert error is None
            assert employee_info is not None
            assert employee_info.employee_id == '123456'
            assert employee_info.name == '홍길동'
            assert employee_info.department == '개발팀'
            
            # Step 2: Face Recognition Service detects liveness
            face_service = FaceRecognitionService()
            liveness_result = face_service.detect_liveness(test_image_bytes)
            
            assert liveness_result.is_live is True
            assert liveness_result.confidence > 90.0
            
            # Step 3: Index face in Rekognition
            face_id = face_service.index_face(test_image_bytes, employee_info.employee_id)
            
            assert face_id == 'test-face-id-123'
            
            # Step 4: Create thumbnail
            thumbnail_processor = ThumbnailProcessor('test-bucket')
            thumbnail_bytes = thumbnail_processor.create_thumbnail(test_image_bytes)
            
            assert thumbnail_bytes is not None
            assert len(thumbnail_bytes) > 0
            
            # Step 5: Store in DynamoDB
            db_service = DynamoDBService()
            face_record = EmployeeFaceRecord(
                employee_id=employee_info.employee_id,
                face_id=face_id,
                enrollment_date=datetime.now(),
                last_login=None,
                thumbnail_s3_key=f"enroll/{employee_info.employee_id}/face_thumbnail.jpg",
                is_active=True,
                re_enrollment_count=0
            )
            
            result = db_service.create_employee_face_record(face_record)
            assert result is True
            
            # Verify all services worked together
            mock_textract.analyze_document.assert_called_once()
            mock_rekognition.detect_faces.assert_called()
            mock_rekognition.index_faces.assert_called_once()
            mock_s3.put_object.assert_called()
            mock_table.put_item.assert_called()
    
    def test_face_login_workflow_integration(self, test_image_bytes, setup_environment):
        """
        Test complete face login workflow:
        Face Recognition → Cognito → Session Management
        """
        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:
            
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
            
            def get_client(service_name, **kwargs):
                if service_name == 'rekognition':
                    return mock_rekognition
                elif service_name == 'cognito-idp':
                    return mock_cognito
                return Mock()
            
            def get_resource(service_name, **kwargs):
                if service_name == 'dynamodb':
                    return mock_dynamodb
                return Mock()
            
            mock_client.side_effect = get_client
            mock_resource.side_effect = get_resource
            
            # Step 1: Face Recognition - Liveness check
            face_service = FaceRecognitionService()
            liveness_result = face_service.detect_liveness(test_image_bytes)
            
            assert liveness_result.is_live is True
            
            # Step 2: Face Recognition - 1:N search
            matches = face_service.search_faces(test_image_bytes)
            
            assert len(matches) > 0
            assert matches[0].employee_id == '123456'
            assert matches[0].similarity > 95.0
            
            # Step 3: Cognito - Create session
            with patch('cognito_service.PyJWKClient'):
                cognito_service = CognitoService(
                    user_pool_id='us-east-1_TEST123',
                    client_id='test-client-id',
                    region='us-east-1'
                )
                cognito_service.cognito_client = mock_cognito
                
                session, error = cognito_service.create_authentication_session(
                    employee_id='123456',
                    auth_method='face',
                    ip_address='192.168.1.100',
                    user_agent='TestAgent/1.0'
                )
            
            assert error is None
            assert session is not None
            assert session.employee_id == '123456'
            assert session.auth_method == 'face'
            assert session.cognito_token == 'test-access-token'
            
            # Step 4: DynamoDB - Store session
            db_service = DynamoDBService()
            result = db_service.create_auth_session(session)
            
            assert result is True
            
            # Verify all services worked together
            mock_rekognition.detect_faces.assert_called()
            mock_rekognition.search_faces_by_image.assert_called_once()
            mock_cognito.admin_initiate_auth.assert_called_once()
            mock_table.put_item.assert_called()
    
    def test_error_handling_integration(self, setup_environment):
        """
        Test error handling across services
        """
        error_handler = ErrorHandler()
        
        # Test specific error codes
        error1 = error_handler.handle_error(
            ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            {'template_count': 0}
        )
        assert error1.user_message == "사원증 규격 불일치"
        assert error1.error_code == ErrorCodes.ID_CARD_FORMAT_MISMATCH
        
        error2 = error_handler.handle_error(
            ErrorCodes.ACCOUNT_DISABLED,
            {'employee_id': '123456'}
        )
        assert error2.user_message == "계정 비활성화"
        assert error2.error_code == ErrorCodes.ACCOUNT_DISABLED
        
        # Test generic error for technical issues
        error3 = error_handler.handle_error(
            ErrorCodes.LIVENESS_FAILED,
            {'confidence': 85.0}
        )
        assert error3.user_message == "밝은 곳에서 다시 시도해주세요"
        assert error3.error_code == ErrorCodes.LIVENESS_FAILED
    
    def test_timeout_management_integration(self):
        """
        Test timeout manager integration with services
        """
        timeout_mgr = TimeoutManager()
        
        # Verify initial state
        assert timeout_mgr.check_lambda_timeout() is True
        assert timeout_mgr.check_ad_timeout() is True
        assert timeout_mgr.get_remaining_time() > 0
        
        # Verify timeout constants
        assert timeout_mgr.AD_TIMEOUT == 10
        assert timeout_mgr.LAMBDA_TIMEOUT == 15
        
        # Verify buffer checking
        assert timeout_mgr.should_continue(buffer_seconds=2.0) is True


class TestServiceOrchestration:
    """Test orchestration of multiple services"""
    
    @pytest.fixture
    def setup_environment(self):
        """Set up environment"""
        os.environ['FACE_AUTH_BUCKET'] = 'test-bucket'
        os.environ['CARD_TEMPLATES_TABLE'] = 'test-card-templates'
        os.environ['EMPLOYEE_FACES_TABLE'] = 'test-employee-faces'
        os.environ['AUTH_SESSIONS_TABLE'] = 'test-auth-sessions'
        os.environ['REKOGNITION_COLLECTION_ID'] = 'test-collection'
        os.environ['AWS_REGION'] = 'us-east-1'
        yield
    
    def test_complete_enrollment_to_login_flow(self, setup_environment):
        """
        Test complete flow from enrollment to login
        
        Simulates:
        1. Employee enrolls with ID card and face
        2. Employee logs in with face
        3. Session is created and validated
        """
        with patch('boto3.client') as mock_client, \
             patch('boto3.resource') as mock_resource:
            
            # Setup mocks
            mock_rekognition = Mock()
            mock_cognito = Mock()
            mock_s3 = Mock()
            mock_dynamodb = Mock()
            mock_table = Mock()
            
            # Enrollment mocks
            mock_rekognition.detect_faces.return_value = {
                'FaceDetails': [{'Confidence': 99.5, 'BoundingBox': {}}]
            }
            mock_rekognition.index_faces.return_value = {
                'FaceRecords': [{'Face': {'FaceId': 'enrolled-face-id', 'Confidence': 99.5}}]
            }
            
            # Login mocks
            mock_rekognition.search_faces_by_image.return_value = {
                'FaceMatches': [{
                    'Face': {'FaceId': 'enrolled-face-id', 'ExternalImageId': '123456'},
                    'Similarity': 98.5
                }]
            }
            
            mock_cognito.admin_get_user.return_value = {'Username': '123456', 'UserStatus': 'CONFIRMED'}
            mock_cognito.admin_set_user_password.return_value = {}
            mock_cognito.admin_initiate_auth.return_value = {
                'AuthenticationResult': {
                    'AccessToken': 'token',
                    'IdToken': 'id',
                    'RefreshToken': 'refresh',
                    'ExpiresIn': 3600,
                    'TokenType': 'Bearer'
                }
            }
            
            mock_s3.put_object.return_value = {}
            mock_table.put_item.return_value = {}
            mock_table.get_item.return_value = {
                'Item': {'employee_id': '123456', 'face_id': 'enrolled-face-id', 'is_active': True}
            }
            mock_dynamodb.Table.return_value = mock_table
            
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
            
            mock_client.side_effect = get_client
            mock_resource.side_effect = get_resource
            
            # Phase 1: Enrollment
            face_service = FaceRecognitionService()
            test_image = b'test_image_data'
            
            # Detect liveness
            liveness = face_service.detect_liveness(test_image)
            assert liveness.is_live is True
            
            # Index face
            face_id = face_service.index_face(test_image, '123456')
            assert face_id == 'enrolled-face-id'
            
            # Store in DynamoDB
            db_service = DynamoDBService()
            face_record = EmployeeFaceRecord(
                employee_id='123456',
                face_id=face_id,
                enrollment_date=datetime.now(),
                last_login=None,
                thumbnail_s3_key='enroll/123456/face.jpg',
                is_active=True,
                re_enrollment_count=0
            )
            db_service.create_employee_face_record(face_record)
            
            # Phase 2: Login
            # Search for face
            matches = face_service.search_faces(test_image)
            assert len(matches) > 0
            assert matches[0].employee_id == '123456'
            
            # Create session
            with patch('cognito_service.PyJWKClient'):
                cognito_service = CognitoService(
                    user_pool_id='us-east-1_TEST123',
                    client_id='test-client-id',
                    region='us-east-1'
                )
                cognito_service.cognito_client = mock_cognito
                
                session, error = cognito_service.create_authentication_session(
                    employee_id='123456',
                    auth_method='face'
                )
            
            assert error is None
            assert session.employee_id == '123456'
            
            # Store session
            db_service.create_auth_session(session)
            
            # Phase 3: Validate session
            assert session.is_valid() is True
            
            # Verify complete flow
            assert mock_rekognition.index_faces.called
            assert mock_rekognition.search_faces_by_image.called
            assert mock_cognito.admin_initiate_auth.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
