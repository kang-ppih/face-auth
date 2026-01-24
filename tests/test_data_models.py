"""
Face-Auth IdP System - Data Models Tests

Unit tests for the data models and DynamoDB service classes.
Tests cover validation, serialization, and database operations.

Requirements: 5.5, 7.4
"""

import pytest
import boto3
from datetime import datetime, timedelta
from moto import mock_aws
import sys
import os

# Add lambda directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from shared.models import (
    EmployeeInfo,
    FaceData,
    AuthenticationSession,
    CardTemplate,
    EmployeeFaceRecord,
    ErrorResponse,
    ErrorCodes
)
from shared.dynamodb_service import DynamoDBService, create_default_card_templates


class TestEmployeeInfo:
    """Test cases for EmployeeInfo data model"""
    
    def test_valid_employee_info(self):
        """Test creation and validation of valid employee info"""
        employee = EmployeeInfo(
            employee_id="123456",
            name="김철수",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        
        assert employee.validate() is True
        assert employee.employee_id == "123456"
        assert employee.name == "김철수"
        assert employee.department == "개발팀"
    
    def test_invalid_employee_id(self):
        """Test validation with invalid employee ID"""
        # Too short
        employee = EmployeeInfo(
            employee_id="12345",
            name="김철수",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        assert employee.validate() is False
        
        # Non-numeric
        employee.employee_id = "12345A"
        assert employee.validate() is False
        
        # Too long
        employee.employee_id = "1234567"
        assert employee.validate() is False
    
    def test_invalid_name(self):
        """Test validation with invalid names"""
        # Too short
        employee = EmployeeInfo(
            employee_id="123456",
            name="김",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        assert employee.validate() is False
        
        # No Korean characters
        employee.name = "John Doe"
        assert employee.validate() is False
    
    def test_low_confidence(self):
        """Test validation with low extraction confidence"""
        employee = EmployeeInfo(
            employee_id="123456",
            name="김철수",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.7  # Below 0.8 threshold
        )
        assert employee.validate() is False
    
    def test_serialization(self):
        """Test dictionary conversion"""
        employee = EmployeeInfo(
            employee_id="123456",
            name="김철수",
            department="개발팀",
            card_type="standard_employee",
            extracted_confidence=0.95
        )
        
        data = employee.to_dict()
        assert data['employee_id'] == "123456"
        assert data['name'] == "김철수"
        
        # Test round-trip conversion
        employee2 = EmployeeInfo.from_dict(data)
        assert employee2.employee_id == employee.employee_id
        assert employee2.name == employee.name


class TestFaceData:
    """Test cases for FaceData data model"""
    
    def test_face_data_creation(self):
        """Test FaceData creation and methods"""
        face_data = FaceData(
            face_id="face-12345",
            employee_id="123456",
            bounding_box={"Width": 0.5, "Height": 0.6, "Left": 0.2, "Top": 0.1},
            confidence=95.5,
            landmarks=[{"Type": "eyeLeft", "X": 0.3, "Y": 0.4}],
            thumbnail_s3_key="enroll/123456/face_thumbnail.jpg"
        )
        
        assert face_data.face_id == "face-12345"
        assert face_data.employee_id == "123456"
        assert face_data.confidence == 95.5
    
    def test_rekognition_format(self):
        """Test conversion to Rekognition API format"""
        face_data = FaceData(
            face_id="face-12345",
            employee_id="123456",
            bounding_box={"Width": 0.5, "Height": 0.6, "Left": 0.2, "Top": 0.1},
            confidence=95.5,
            landmarks=[],
            thumbnail_s3_key="enroll/123456/face_thumbnail.jpg"
        )
        
        rekognition_format = face_data.to_rekognition_format()
        assert rekognition_format['FaceId'] == "face-12345"
        assert rekognition_format['ExternalImageId'] == "123456"
        assert rekognition_format['Confidence'] == 95.5
    
    def test_from_rekognition_response(self):
        """Test creation from Rekognition API response"""
        rekognition_response = {
            'FaceRecords': [{
                'Face': {
                    'FaceId': 'face-67890',
                    'BoundingBox': {'Width': 0.4, 'Height': 0.5, 'Left': 0.3, 'Top': 0.2},
                    'Confidence': 98.2,
                    'Landmarks': [{'Type': 'eyeLeft', 'X': 0.35, 'Y': 0.45}]
                }
            }]
        }
        
        face_data = FaceData.from_rekognition_response(
            rekognition_response, 
            "654321", 
            "enroll/654321/face_thumbnail.jpg"
        )
        
        assert face_data.face_id == "face-67890"
        assert face_data.employee_id == "654321"
        assert face_data.confidence == 98.2


class TestAuthenticationSession:
    """Test cases for AuthenticationSession data model"""
    
    def test_session_creation(self):
        """Test session creation and validation"""
        now = datetime.now()
        expires = now + timedelta(hours=1)
        
        session = AuthenticationSession(
            session_id="session-12345",
            employee_id="123456",
            auth_method="face",
            created_at=now,
            expires_at=expires,
            cognito_token="jwt-token-here",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0..."
        )
        
        assert session.is_valid() is True
        assert session.session_id == "session-12345"
        assert session.auth_method == "face"
    
    def test_expired_session(self):
        """Test expired session validation"""
        now = datetime.now()
        expired = now - timedelta(hours=1)
        
        session = AuthenticationSession(
            session_id="session-12345",
            employee_id="123456",
            auth_method="face",
            created_at=expired,
            expires_at=expired,
            cognito_token="jwt-token-here"
        )
        
        assert session.is_valid() is False
    
    def test_session_serialization(self):
        """Test session dictionary conversion with datetime handling"""
        now = datetime.now()
        expires = now + timedelta(hours=1)
        
        session = AuthenticationSession(
            session_id="session-12345",
            employee_id="123456",
            auth_method="face",
            created_at=now,
            expires_at=expires,
            cognito_token="jwt-token-here"
        )
        
        data = session.to_dict()
        assert 'created_at' in data
        assert 'expires_at' in data
        assert isinstance(data['expires_at'], int)  # TTL requires epoch time
        
        # Test round-trip conversion
        session2 = AuthenticationSession.from_dict(data)
        assert session2.session_id == session.session_id
        assert session2.employee_id == session.employee_id


class TestCardTemplate:
    """Test cases for CardTemplate data model"""
    
    def test_template_creation(self):
        """Test card template creation"""
        template = CardTemplate(
            pattern_id="test_card_v1",
            card_type="standard_employee",
            logo_position={"x": 50, "y": 30, "width": 100, "height": 50},
            fields=[
                {
                    "field_name": "employee_id",
                    "query_phrase": "사번은 무엇입니까?",
                    "expected_format": r"\d{6}"
                }
            ],
            created_at=datetime.now(),
            is_active=True,
            description="Test template"
        )
        
        assert template.pattern_id == "test_card_v1"
        assert template.is_active is True
        assert len(template.fields) == 1
    
    def test_textract_queries(self):
        """Test Textract query generation"""
        template = CardTemplate(
            pattern_id="test_card_v1",
            card_type="standard_employee",
            logo_position={"x": 50, "y": 30, "width": 100, "height": 50},
            fields=[
                {
                    "field_name": "employee_id",
                    "query_phrase": "사번은 무엇입니까?",
                    "expected_format": r"\d{6}"
                },
                {
                    "field_name": "employee_name",
                    "query_phrase": "성명은 무엇입니까?",
                    "expected_format": r"[가-힣]{2,4}"
                }
            ],
            created_at=datetime.now(),
            is_active=True
        )
        
        queries = template.build_textract_queries()
        assert len(queries) == 2
        assert queries[0]['Text'] == "사번은 무엇입니까?"
        assert queries[0]['Alias'] == "employee_id"
        assert queries[1]['Text'] == "성명은 무엇입니까?"
        assert queries[1]['Alias'] == "employee_name"
    
    def test_data_validation(self):
        """Test extracted data validation"""
        template = CardTemplate(
            pattern_id="test_card_v1",
            card_type="standard_employee",
            logo_position={"x": 50, "y": 30, "width": 100, "height": 50},
            fields=[
                {
                    "field_name": "employee_id",
                    "query_phrase": "사번은 무엇입니까?",
                    "expected_format": r"\d{6}"
                },
                {
                    "field_name": "employee_name",
                    "query_phrase": "성명은 무엇입니까?",
                    "expected_format": r"[가-힣]{2,4}"
                }
            ],
            created_at=datetime.now(),
            is_active=True
        )
        
        # Valid data
        valid_data = {
            "employee_id": "123456",
            "employee_name": "김철수"
        }
        assert template.validate_extracted_data(valid_data) is True
        
        # Invalid employee ID format
        invalid_data = {
            "employee_id": "12345A",
            "employee_name": "김철수"
        }
        assert template.validate_extracted_data(invalid_data) is False
        
        # Missing field
        incomplete_data = {
            "employee_id": "123456"
        }
        assert template.validate_extracted_data(incomplete_data) is False


@mock_aws
class TestDynamoDBService:
    """Test cases for DynamoDB service operations"""
    
    def setup_method(self, method):
        """Set up test DynamoDB tables"""
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        
        # Create CardTemplates table
        self.card_templates_table = self.dynamodb.create_table(
            TableName='test-card-templates',
            KeySchema=[
                {'AttributeName': 'pattern_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'pattern_id', 'AttributeType': 'S'},
                {'AttributeName': 'card_type', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'CardTypeIndex',
                    'KeySchema': [
                        {'AttributeName': 'card_type', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create EmployeeFaces table
        self.employee_faces_table = self.dynamodb.create_table(
            TableName='test-employee-faces',
            KeySchema=[
                {'AttributeName': 'employee_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'employee_id', 'AttributeType': 'S'},
                {'AttributeName': 'face_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'FaceIdIndex',
                    'KeySchema': [
                        {'AttributeName': 'face_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Create AuthSessions table
        self.auth_sessions_table = self.dynamodb.create_table(
            TableName='test-auth-sessions',
            KeySchema=[
                {'AttributeName': 'session_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'session_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Initialize service
        self.db_service = DynamoDBService(region_name='us-east-1')
        self.db_service.initialize_tables(
            'test-card-templates',
            'test-employee-faces',
            'test-auth-sessions'
        )
    
    def test_card_template_operations(self):
        """Test card template CRUD operations"""
        template = CardTemplate(
            pattern_id="test_template",
            card_type="test_card",
            logo_position={"x": 50, "y": 30, "width": 100, "height": 50},
            fields=[
                {
                    "field_name": "employee_id",
                    "query_phrase": "사번은 무엇입니까?",
                    "expected_format": r"\d{6}"
                }
            ],
            created_at=datetime.now(),
            is_active=True,
            description="Test template"
        )
        
        # Create template
        assert self.db_service.create_card_template(template) is True
        
        # Retrieve template
        retrieved = self.db_service.get_card_template("test_template")
        assert retrieved is not None
        assert retrieved.pattern_id == "test_template"
        assert retrieved.card_type == "test_card"
        
        # Update template
        template.description = "Updated test template"
        assert self.db_service.update_card_template(template) is True
        
        # Get active templates
        active_templates = self.db_service.get_active_card_templates()
        assert len(active_templates) >= 1
        
        # Get by card type
        type_templates = self.db_service.get_templates_by_card_type("test_card")
        assert len(type_templates) >= 1
    
    def test_employee_face_operations(self):
        """Test employee face record operations"""
        face_data = FaceData(
            face_id="test-face-123",
            employee_id="123456",
            bounding_box={"Width": 0.5, "Height": 0.6, "Left": 0.2, "Top": 0.1},
            confidence=95.5,
            landmarks=[],
            thumbnail_s3_key="enroll/123456/face_thumbnail.jpg"
        )
        
        record = EmployeeFaceRecord(
            employee_id="123456",
            face_id="test-face-123",
            enrollment_date=datetime.now(),
            last_login=None,
            thumbnail_s3_key="enroll/123456/face_thumbnail.jpg",
            is_active=True,
            re_enrollment_count=0,
            face_data=face_data
        )
        
        # Create record
        assert self.db_service.create_employee_face_record(record) is True
        
        # Retrieve by employee ID
        retrieved = self.db_service.get_employee_face_record("123456")
        assert retrieved is not None
        assert retrieved.employee_id == "123456"
        assert retrieved.face_id == "test-face-123"
        
        # Retrieve by face ID
        by_face = self.db_service.get_employee_by_face_id("test-face-123")
        assert by_face is not None
        assert by_face.employee_id == "123456"
        
        # Update last login
        login_time = datetime.now()
        assert self.db_service.update_last_login("123456", login_time) is True
        
        # Deactivate employee
        assert self.db_service.deactivate_employee_face("123456") is True
    
    def test_auth_session_operations(self):
        """Test authentication session operations"""
        now = datetime.now()
        expires = now + timedelta(hours=1)
        
        session = AuthenticationSession(
            session_id="test-session-123",
            employee_id="123456",
            auth_method="face",
            created_at=now,
            expires_at=expires,
            cognito_token="test-jwt-token"
        )
        
        # Create session
        assert self.db_service.create_auth_session(session) is True
        
        # Retrieve session
        retrieved = self.db_service.get_auth_session("test-session-123")
        assert retrieved is not None
        assert retrieved.session_id == "test-session-123"
        assert retrieved.employee_id == "123456"
        
        # Delete session
        assert self.db_service.delete_auth_session("test-session-123") is True
        
        # Verify deletion
        deleted = self.db_service.get_auth_session("test-session-123")
        assert deleted is None
    
    def test_default_templates_creation(self):
        """Test creation of default card templates"""
        templates = create_default_card_templates(self.db_service)
        assert len(templates) >= 2  # Should create at least 2 default templates
        
        # Verify templates are in database
        active_templates = self.db_service.get_active_card_templates()
        assert len(active_templates) >= 2


class TestErrorResponse:
    """Test cases for error response model"""
    
    def test_error_response_creation(self):
        """Test error response creation and serialization"""
        error = ErrorResponse(
            error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
            user_message="사원증 규격 불일치",
            system_reason="No matching card template found",
            timestamp=datetime.now(),
            request_id="req-12345"
        )
        
        assert error.error_code == ErrorCodes.ID_CARD_FORMAT_MISMATCH
        assert error.user_message == "사원증 규격 불일치"
        
        # Test dictionary conversion
        data = error.to_dict()
        assert data['error'] == ErrorCodes.ID_CARD_FORMAT_MISMATCH
        assert data['message'] == "사원증 규격 불일치"
        assert 'timestamp' in data
        assert 'request_id' in data


if __name__ == "__main__":
    pytest.main([__file__])