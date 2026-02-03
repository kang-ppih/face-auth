"""
Unit tests for OCRService class

Tests cover:
- Card template-based OCR extraction
- Dynamic Textract query configuration
- Employee information validation
- Error handling for unsupported formats
- Integration with DynamoDB service

Requirements: 1.2, 7.1, 7.2, 7.6
"""

import pytest
import boto3
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from decimal import Decimal
import sys
import os

# Add lambda directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from shared.ocr_service import (
    OCRService,
    create_ocr_service,
    validate_employee_id_format
)
from shared.models import (
    CardTemplate,
    EmployeeInfo,
    ErrorCodes
)


class TestOCRService:
    """Test cases for OCRService class"""
    
    @pytest.fixture
    def mock_textract_client(self):
        """Mock Textract client"""
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_db_service(self):
        """Mock DynamoDB service"""
        with patch('shared.ocr_service.DynamoDBService') as mock_db:
            mock_service = Mock()
            mock_db.return_value = mock_service
            yield mock_service
    
    @pytest.fixture
    def sample_card_template(self):
        """Sample card template for testing"""
        return CardTemplate(
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
                },
                {
                    "field_name": "department",
                    "query_phrase": "부서는 무엇입니까?",
                    "expected_format": r"[가-힣\s]+"
                }
            ],
            created_at=datetime.now(),
            is_active=True,
            description="Test card template"
        )
    
    @pytest.fixture
    def sample_textract_response(self):
        """Sample Textract response for testing"""
        return {
            'Blocks': [
                {
                    'Id': 'query-1',
                    'BlockType': 'QUERY',
                    'Query': {
                        'Text': '사번은 무엇입니까?',
                        'Alias': 'employee_id'
                    },
                    'Relationships': [
                        {
                            'Type': 'ANSWER',
                            'Ids': ['answer-1']
                        }
                    ]
                },
                {
                    'Id': 'answer-1',
                    'BlockType': 'QUERY_RESULT',
                    'Text': '123456',
                    'Confidence': 95.5
                },
                {
                    'Id': 'query-2',
                    'BlockType': 'QUERY',
                    'Query': {
                        'Text': '성명은 무엇입니까?',
                        'Alias': 'employee_name'
                    },
                    'Relationships': [
                        {
                            'Type': 'ANSWER',
                            'Ids': ['answer-2']
                        }
                    ]
                },
                {
                    'Id': 'answer-2',
                    'BlockType': 'QUERY_RESULT',
                    'Text': '김철수',
                    'Confidence': 92.3
                },
                {
                    'Id': 'query-3',
                    'BlockType': 'QUERY',
                    'Query': {
                        'Text': '부서는 무엇입니까?',
                        'Alias': 'department'
                    },
                    'Relationships': [
                        {
                            'Type': 'ANSWER',
                            'Ids': ['answer-3']
                        }
                    ]
                },
                {
                    'Id': 'answer-3',
                    'BlockType': 'QUERY_RESULT',
                    'Text': '개발팀',
                    'Confidence': 88.7
                }
            ]
        }
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Sample image bytes (JPEG header)"""
        return b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 1000
    
    def test_ocr_service_initialization(self, mock_textract_client, mock_db_service):
        """Test OCRService initialization"""
        ocr_service = OCRService('us-east-1')
        
        assert ocr_service.textract is not None
        assert ocr_service.db_service is not None
        assert ocr_service.confidence_threshold == 0.8
    
    def test_initialize_db_service(self, mock_textract_client, mock_db_service):
        """Test DynamoDB service initialization"""
        ocr_service = OCRService()
        
        ocr_service.initialize_db_service(
            'CardTemplates',
            'EmployeeFaces', 
            'AuthSessions'
        )
        
        mock_db_service.initialize_tables.assert_called_once_with(
            'CardTemplates',
            'EmployeeFaces',
            'AuthSessions'
        )
    
    def test_build_queries_from_template(self, mock_textract_client, mock_db_service, sample_card_template):
        """Test building Textract queries from card template"""
        ocr_service = OCRService()
        
        queries = ocr_service._build_queries_from_template(sample_card_template)
        
        assert len(queries) == 3
        assert queries[0]['Text'] == '사번은 무엇입니까?'
        assert queries[0]['Alias'] == 'employee_id'
        assert queries[1]['Text'] == '성명은 무엇입니까?'
        assert queries[1]['Alias'] == 'employee_name'
        assert queries[2]['Text'] == '부서는 무엇입니까?'
        assert queries[2]['Alias'] == 'department'
    
    def test_parse_textract_response(self, mock_textract_client, mock_db_service, 
                                   sample_card_template, sample_textract_response):
        """Test parsing Textract response"""
        ocr_service = OCRService()
        
        extracted_data = ocr_service._parse_textract_response(
            sample_textract_response, 
            sample_card_template
        )
        
        assert extracted_data['employee_id'] == '123456'
        assert extracted_data['employee_name'] == '김철수'
        assert extracted_data['department'] == '개발팀'
    
    def test_create_employee_info(self, mock_textract_client, mock_db_service, sample_card_template):
        """Test creating EmployeeInfo from extracted data"""
        ocr_service = OCRService()
        
        extracted_data = {
            'employee_id': '123456',
            'employee_name': '김철수',
            'department': '개발팀'
        }
        
        employee_info = ocr_service._create_employee_info(extracted_data, sample_card_template)
        
        assert employee_info.employee_id == '123456'
        assert employee_info.name == '김철수'
        assert employee_info.department == '개발팀'
        assert employee_info.card_type == 'standard_employee'
        assert employee_info.extracted_confidence > 0.8
    
    def test_calculate_extraction_confidence(self, mock_textract_client, mock_db_service, sample_card_template):
        """Test extraction confidence calculation"""
        ocr_service = OCRService()
        
        # All required fields present
        extracted_data = {
            'employee_id': '123456',
            'employee_name': '김철수',
            'department': '개발팀'
        }
        
        confidence = ocr_service._calculate_extraction_confidence(extracted_data, sample_card_template)
        
        assert confidence >= 1.0  # All required fields + bonus
        
        # Only required fields (should still be 1.0 since all required fields are present)
        extracted_data = {
            'employee_id': '123456',
            'employee_name': '김철수'
        }
        
        confidence = ocr_service._calculate_extraction_confidence(extracted_data, sample_card_template)
        
        assert confidence == 1.0  # All required fields present = 1.0 base confidence
        
        # Missing one required field
        extracted_data = {
            'employee_id': '123456'
        }
        
        confidence = ocr_service._calculate_extraction_confidence(extracted_data, sample_card_template)
        
        assert confidence == 0.5  # Only 1 out of 2 required fields
    
    def test_extract_with_template_success(self, mock_textract_client, mock_db_service, 
                                         sample_card_template, sample_textract_response, sample_image_bytes):
        """Test successful extraction with template"""
        ocr_service = OCRService()
        mock_textract_client.analyze_document.return_value = sample_textract_response
        
        employee_info, error = ocr_service._extract_with_template(
            sample_image_bytes, 
            sample_card_template,
            'test-request'
        )
        
        assert employee_info is not None
        assert error is None
        assert employee_info.employee_id == '123456'
        assert employee_info.name == '김철수'
        assert employee_info.department == '개발팀'
        
        # Verify Textract was called with correct parameters
        mock_textract_client.analyze_document.assert_called_once()
        call_args = mock_textract_client.analyze_document.call_args
        assert call_args[1]['Document']['Bytes'] == sample_image_bytes
        assert call_args[1]['FeatureTypes'] == ['QUERIES']
        assert len(call_args[1]['QueriesConfig']['Queries']) == 3
    
    def test_extract_with_template_textract_error(self, mock_textract_client, mock_db_service, 
                                                sample_card_template, sample_image_bytes):
        """Test extraction with Textract error"""
        ocr_service = OCRService()
        mock_textract_client.analyze_document.side_effect = Exception("Textract error")
        
        employee_info, error = ocr_service._extract_with_template(
            sample_image_bytes,
            sample_card_template,
            'test-request'
        )
        
        assert employee_info is None
        assert error is not None
        assert error.error_code == ErrorCodes.GENERIC_ERROR
        assert error.user_message == "밝은 곳에서 다시 시도해주세요"
        assert "Textract error" in error.system_reason
    
    def test_extract_id_card_info_success(self, mock_textract_client, mock_db_service, 
                                        sample_card_template, sample_textract_response, sample_image_bytes):
        """Test successful ID card information extraction"""
        ocr_service = OCRService()
        
        # Mock DB service to return active templates
        mock_db_service.get_active_card_templates.return_value = [sample_card_template]
        mock_textract_client.analyze_document.return_value = sample_textract_response
        
        employee_info, error = ocr_service.extract_id_card_info(sample_image_bytes, 'test-request')
        
        assert employee_info is not None
        assert error is None
        assert employee_info.employee_id == '123456'
        assert employee_info.name == '김철수'
        assert employee_info.validate()
    
    def test_extract_id_card_info_no_templates(self, mock_textract_client, mock_db_service, sample_image_bytes):
        """Test extraction with no active templates"""
        ocr_service = OCRService()
        
        # Mock DB service to return no templates
        mock_db_service.get_active_card_templates.return_value = []
        
        employee_info, error = ocr_service.extract_id_card_info(sample_image_bytes, 'test-request')
        
        assert employee_info is None
        assert error is not None
        assert error.error_code == ErrorCodes.ID_CARD_FORMAT_MISMATCH
        assert error.user_message == "사원증 규격 불일치"
        assert "No active card templates" in error.system_reason
    
    def test_extract_id_card_info_no_match(self, mock_textract_client, mock_db_service, 
                                         sample_card_template, sample_image_bytes):
        """Test extraction with no template match"""
        ocr_service = OCRService()
        
        # Mock DB service to return templates
        mock_db_service.get_active_card_templates.return_value = [sample_card_template]
        
        # Mock Textract to return empty response
        mock_textract_client.analyze_document.return_value = {'Blocks': []}
        
        employee_info, error = ocr_service.extract_id_card_info(sample_image_bytes, 'test-request')
        
        assert employee_info is None
        assert error is not None
        assert error.error_code == ErrorCodes.ID_CARD_FORMAT_MISMATCH
        assert error.user_message == "사원증 규격 불일치"
        assert "does not match any active card template" in error.system_reason
    
    def test_validate_image_for_ocr(self, mock_textract_client, mock_db_service):
        """Test image validation for OCR"""
        ocr_service = OCRService()
        
        # Valid JPEG image
        jpeg_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 1000
        is_valid, format_info = ocr_service.validate_image_for_ocr(jpeg_bytes)
        assert is_valid
        assert format_info == "JPEG"
        
        # Valid PNG image
        png_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 1000
        is_valid, format_info = ocr_service.validate_image_for_ocr(png_bytes)
        assert is_valid
        assert format_info == "PNG"
        
        # Too small image
        small_bytes = b'\xff\xd8\xff' + b'\x00' * 100
        is_valid, error_msg = ocr_service.validate_image_for_ocr(small_bytes)
        assert not is_valid
        assert "too small" in error_msg
        
        # Too large image
        large_bytes = b'\xff\xd8\xff' + b'\x00' * (6 * 1024 * 1024)
        is_valid, error_msg = ocr_service.validate_image_for_ocr(large_bytes)
        assert not is_valid
        assert "too large" in error_msg
        
        # Unsupported format
        invalid_bytes = b'INVALID' + b'\x00' * 1000
        is_valid, error_msg = ocr_service.validate_image_for_ocr(invalid_bytes)
        assert not is_valid
        assert "Unsupported" in error_msg
    
    def test_get_card_template_by_id(self, mock_textract_client, mock_db_service, sample_card_template):
        """Test retrieving card template by ID"""
        ocr_service = OCRService()
        
        mock_db_service.get_card_template.return_value = sample_card_template
        
        template = ocr_service.get_card_template_by_id('test_card_v1')
        
        assert template is not None
        assert template.pattern_id == 'test_card_v1'
        mock_db_service.get_card_template.assert_called_once_with('test_card_v1')
    
    def test_get_active_card_templates(self, mock_textract_client, mock_db_service, sample_card_template):
        """Test retrieving active card templates"""
        ocr_service = OCRService()
        
        mock_db_service.get_active_card_templates.return_value = [sample_card_template]
        
        templates = ocr_service.get_active_card_templates()
        
        assert len(templates) == 1
        assert templates[0].pattern_id == 'test_card_v1'
        mock_db_service.get_active_card_templates.assert_called_once()
    
    def test_test_template_extraction(self, mock_textract_client, mock_db_service, 
                                    sample_card_template, sample_textract_response, sample_image_bytes):
        """Test template extraction testing function"""
        ocr_service = OCRService()
        
        mock_db_service.get_card_template.return_value = sample_card_template
        mock_textract_client.analyze_document.return_value = sample_textract_response
        
        result = ocr_service.test_template_extraction('test_card_v1', sample_image_bytes)
        
        assert result['success']
        assert result['template_id'] == 'test_card_v1'
        assert result['employee_info'] is not None
        assert result['error'] is None
        assert result['template_fields'] == 3
        assert result['queries_built'] == 3


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_create_ocr_service(self):
        """Test OCR service factory function"""
        with patch('shared.ocr_service.OCRService') as mock_ocr:
            create_ocr_service('us-west-2')
            mock_ocr.assert_called_once_with('us-west-2')
    
    def test_validate_employee_id_format(self):
        """Test employee ID format validation"""
        # Valid standard employee IDs
        assert validate_employee_id_format('123456')
        assert validate_employee_id_format('000001')
        assert validate_employee_id_format('999999')
        
        # Valid contractor IDs
        assert validate_employee_id_format('C12345')
        assert validate_employee_id_format('C00001')
        assert validate_employee_id_format('C99999')
        
        # Invalid formats
        assert not validate_employee_id_format('12345')  # Too short
        assert not validate_employee_id_format('1234567')  # Too long
        assert not validate_employee_id_format('12345a')  # Contains letter
        assert not validate_employee_id_format('C1234')  # Contractor too short
        assert not validate_employee_id_format('C123456')  # Contractor too long
        assert not validate_employee_id_format('D12345')  # Wrong prefix
        assert not validate_employee_id_format('')  # Empty
    
    def test_validate_korean_name(self):
        """Test Korean name validation"""
        # Valid Korean names
        assert validate_korean_name('김철수')
        assert validate_korean_name('이영희')
        assert validate_korean_name('박지성')
        assert validate_korean_name('최민수')
        
        # Invalid names
        assert not validate_korean_name('김')  # Too short
        assert not validate_korean_name('김철수박지성이영희최')  # Too long
        assert not validate_korean_name('John')  # No Korean characters
        assert not validate_korean_name('김철수123')  # Contains numbers
        assert not validate_korean_name('')  # Empty
    
    def test_extract_confidence_from_textract_block(self):
        """Test confidence extraction from Textract block"""
        # Confidence as percentage (> 1.0)
        block1 = {'Confidence': 95.5}
        assert extract_confidence_from_textract_block(block1) == 0.955
        
        # Confidence as decimal (< 1.0)
        block2 = {'Confidence': 0.85}
        assert extract_confidence_from_textract_block(block2) == 0.85
        
        # No confidence field
        block3 = {}
        assert extract_confidence_from_textract_block(block3) == 0.0
        
        # Zero confidence
        block4 = {'Confidence': 0.0}
        assert extract_confidence_from_textract_block(block4) == 0.0


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.fixture
    def mock_textract_client(self):
        """Mock Textract client"""
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_db_service(self):
        """Mock DynamoDB service"""
        with patch('shared.ocr_service.DynamoDBService') as mock_db:
            mock_service = Mock()
            mock_db.return_value = mock_service
            yield mock_service
    
    def test_textract_invalid_parameter_exception(self, mock_textract_client, mock_db_service):
        """Test handling of Textract InvalidParameterException"""
        ocr_service = OCRService()
        
        # Mock Textract to raise InvalidParameterException
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'InvalidParameterException', 'Message': 'Invalid parameter'}}
        mock_textract_client.exceptions.InvalidParameterException = ClientError
        mock_textract_client.analyze_document.side_effect = ClientError(error_response, 'AnalyzeDocument')
        
        template = CardTemplate(
            pattern_id="test",
            card_type="test",
            logo_position={},
            fields=[{"field_name": "test", "query_phrase": "test"}],
            created_at=datetime.now(),
            is_active=True
        )
        
        employee_info, error = ocr_service._extract_with_template(b'test', template)
        
        assert employee_info is None
        assert error is not None
        assert error.error_code == ErrorCodes.GENERIC_ERROR
        assert "밝은 곳에서 다시 시도해주세요" in error.user_message
    
    def test_low_confidence_extraction(self, mock_textract_client, mock_db_service):
        """Test handling of low confidence extraction results"""
        ocr_service = OCRService()
        
        # Mock Textract response with low confidence
        low_confidence_response = {
            'Blocks': [
                {
                    'Id': 'query-1',
                    'BlockType': 'QUERY',
                    'Query': {
                        'Text': '사번은 무엇입니까?',
                        'Alias': 'employee_id'
                    },
                    'Relationships': [
                        {
                            'Type': 'ANSWER',
                            'Ids': ['answer-1']
                        }
                    ]
                },
                {
                    'Id': 'answer-1',
                    'BlockType': 'QUERY_RESULT',
                    'Text': '123456',
                    'Confidence': 50.0  # Low confidence
                }
            ]
        }
        
        template = CardTemplate(
            pattern_id="test",
            card_type="test",
            logo_position={},
            fields=[{"field_name": "employee_id", "query_phrase": "사번은 무엇입니까?"}],
            created_at=datetime.now(),
            is_active=True
        )
        
        extracted_data = ocr_service._parse_textract_response(low_confidence_response, template)
        
        # Should not extract data due to low confidence
        assert 'employee_id' not in extracted_data or extracted_data['employee_id'] == ''


if __name__ == '__main__':
    pytest.main([__file__])