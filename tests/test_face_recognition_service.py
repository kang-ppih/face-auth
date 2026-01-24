"""
Unit tests for FaceRecognitionService class

Tests cover:
- Rekognition collection creation and management
- Liveness detection with 90% confidence threshold
- 1:N face search and matching
- Face enrollment (IndexFaces) and deletion
- Error handling for recognition failures

Requirements: 2.1, 2.2, 6.1, 6.2, 6.4
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

from shared.face_recognition_service import (
    FaceRecognitionService,
    LivenessResult,
    FaceMatch,
    create_face_recognition_service,
    validate_face_image
)
from shared.models import (
    FaceData,
    ErrorCodes
)


class TestFaceRecognitionService:
    """Test cases for FaceRecognitionService class"""
    
    @pytest.fixture
    def mock_rekognition_client(self):
        """Mock Rekognition client"""
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def sample_face_image(self):
        """Sample face image bytes (JPEG header)"""
        return b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 2000
    
    @pytest.fixture
    def sample_detect_faces_response(self):
        """Sample Rekognition DetectFaces response"""
        return {
            'FaceDetails': [
                {
                    'Confidence': 95.5,
                    'BoundingBox': {
                        'Width': 0.5,
                        'Height': 0.7,
                        'Left': 0.25,
                        'Top': 0.15
                    },
                    'Quality': {
                        'Brightness': 75.0,
                        'Sharpness': 85.0
                    },
                    'Landmarks': [
                        {'Type': 'eyeLeft', 'X': 0.3, 'Y': 0.3},
                        {'Type': 'eyeRight', 'X': 0.7, 'Y': 0.3}
                    ]
                }
            ]
        }
    
    @pytest.fixture
    def sample_search_faces_response(self):
        """Sample Rekognition SearchFacesByImage response"""
        return {
            'FaceMatches': [
                {
                    'Similarity': 98.5,
                    'Face': {
                        'FaceId': 'face-123',
                        'ExternalImageId': '123456',
                        'Confidence': 99.0,
                        'BoundingBox': {
                            'Width': 0.5,
                            'Height': 0.7,
                            'Left': 0.25,
                            'Top': 0.15
                        }
                    }
                },
                {
                    'Similarity': 92.3,
                    'Face': {
                        'FaceId': 'face-456',
                        'ExternalImageId': '654321',
                        'Confidence': 97.0,
                        'BoundingBox': {
                            'Width': 0.5,
                            'Height': 0.7,
                            'Left': 0.25,
                            'Top': 0.15
                        }
                    }
                }
            ]
        }

    @pytest.fixture
    def sample_index_faces_response(self):
        """Sample Rekognition IndexFaces response"""
        return {
            'FaceRecords': [
                {
                    'Face': {
                        'FaceId': 'face-new-123',
                        'BoundingBox': {
                            'Width': 0.5,
                            'Height': 0.7,
                            'Left': 0.25,
                            'Top': 0.15
                        },
                        'Confidence': 99.5,
                        'ExternalImageId': '123456'
                    },
                    'FaceDetail': {
                        'Confidence': 99.5,
                        'BoundingBox': {
                            'Width': 0.5,
                            'Height': 0.7,
                            'Left': 0.25,
                            'Top': 0.15
                        }
                    }
                }
            ]
        }
    
    def test_service_initialization(self, mock_rekognition_client):
        """Test FaceRecognitionService initialization"""
        service = FaceRecognitionService('us-east-1')
        
        assert service.rekognition is not None
        assert service.collection_id == FaceRecognitionService.COLLECTION_ID
        assert service.region_name == 'us-east-1'
        assert service.CONFIDENCE_THRESHOLD == 90.0
        assert service.FACE_MATCH_THRESHOLD == 90.0
    
    def test_service_initialization_custom_collection(self, mock_rekognition_client):
        """Test FaceRecognitionService initialization with custom collection"""
        service = FaceRecognitionService('us-west-2', 'custom-collection')
        
        assert service.collection_id == 'custom-collection'
        assert service.region_name == 'us-west-2'
    
    def test_create_collection_new(self, mock_rekognition_client):
        """Test creating a new collection"""
        service = FaceRecognitionService()
        
        # Mock collection doesn't exist - raise exception on describe
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Collection not found'}}
        mock_rekognition_client.describe_collection.side_effect = \
            ClientError(error_response, 'DescribeCollection')
        
        # Mock successful creation
        mock_rekognition_client.create_collection.return_value = {
            'CollectionArn': 'arn:aws:rekognition:us-east-1:123456789012:collection/face-auth-employees',
            'StatusCode': 200
        }
        
        success, error = service.create_collection()
        
        assert success
        assert error is None
        mock_rekognition_client.create_collection.assert_called_once()

    def test_create_collection_already_exists(self, mock_rekognition_client):
        """Test creating collection when it already exists"""
        service = FaceRecognitionService()
        
        # Mock collection already exists
        mock_rekognition_client.describe_collection.return_value = {
            'CollectionARN': 'arn:aws:rekognition:us-east-1:123456789012:collection/face-auth-employees',
            'FaceCount': 10
        }
        
        success, error = service.create_collection()
        
        assert success
        assert error is None
        mock_rekognition_client.create_collection.assert_not_called()
    
    def test_delete_collection_success(self, mock_rekognition_client):
        """Test deleting a collection"""
        service = FaceRecognitionService()
        
        mock_rekognition_client.delete_collection.return_value = {
            'StatusCode': 200
        }
        
        success, error = service.delete_collection()
        
        assert success
        assert error is None
        mock_rekognition_client.delete_collection.assert_called_once_with(
            CollectionId=service.collection_id
        )
    
    def test_detect_liveness_success(self, mock_rekognition_client, sample_face_image, 
                                    sample_detect_faces_response):
        """Test successful liveness detection"""
        service = FaceRecognitionService()
        
        mock_rekognition_client.detect_faces.return_value = sample_detect_faces_response
        
        liveness_result, error = service.detect_liveness(sample_face_image, 'test-request')
        
        assert liveness_result is not None
        assert error is None
        assert liveness_result.is_live
        assert liveness_result.confidence == 95.5
        assert liveness_result.face_detected
        
        # Verify Rekognition was called correctly
        mock_rekognition_client.detect_faces.assert_called_once()
        call_args = mock_rekognition_client.detect_faces.call_args
        assert call_args[1]['Image']['Bytes'] == sample_face_image
        assert call_args[1]['Attributes'] == ['ALL']
    
    def test_detect_liveness_no_face(self, mock_rekognition_client, sample_face_image):
        """Test liveness detection with no face detected"""
        service = FaceRecognitionService()
        
        # Mock no faces detected
        mock_rekognition_client.detect_faces.return_value = {
            'FaceDetails': []
        }
        
        liveness_result, error = service.detect_liveness(sample_face_image, 'test-request')
        
        assert liveness_result is None
        assert error is not None
        assert error.error_code == ErrorCodes.LIVENESS_FAILED
        assert error.user_message == "밝은 곳에서 다시 시도해주세요"
        assert "No face detected" in error.system_reason

    def test_detect_liveness_low_confidence(self, mock_rekognition_client, sample_face_image):
        """Test liveness detection with low confidence"""
        service = FaceRecognitionService()
        
        # Mock low confidence face
        mock_rekognition_client.detect_faces.return_value = {
            'FaceDetails': [
                {
                    'Confidence': 85.0,  # Below 90% threshold
                    'Quality': {
                        'Brightness': 75.0,
                        'Sharpness': 85.0
                    }
                }
            ]
        }
        
        liveness_result, error = service.detect_liveness(sample_face_image, 'test-request')
        
        assert liveness_result is None
        assert error is not None
        assert error.error_code == ErrorCodes.LIVENESS_FAILED
        assert "confidence" in error.system_reason.lower()
        assert "below threshold" in error.system_reason.lower()
    
    def test_detect_liveness_poor_quality(self, mock_rekognition_client, sample_face_image):
        """Test liveness detection with poor image quality"""
        service = FaceRecognitionService()
        
        # Mock poor quality image
        mock_rekognition_client.detect_faces.return_value = {
            'FaceDetails': [
                {
                    'Confidence': 95.0,
                    'Quality': {
                        'Brightness': 20.0,  # Too dark
                        'Sharpness': 30.0    # Too blurry
                    }
                }
            ]
        }
        
        liveness_result, error = service.detect_liveness(sample_face_image, 'test-request')
        
        assert liveness_result is None
        assert error is not None
        assert error.error_code == ErrorCodes.LIVENESS_FAILED
        assert "quality" in error.system_reason.lower()
    
    def test_detect_liveness_multiple_faces(self, mock_rekognition_client, sample_face_image):
        """Test liveness detection with multiple faces"""
        service = FaceRecognitionService()
        
        # Mock multiple faces detected
        mock_rekognition_client.detect_faces.return_value = {
            'FaceDetails': [
                {
                    'Confidence': 95.0,
                    'Quality': {'Brightness': 75.0, 'Sharpness': 85.0}
                },
                {
                    'Confidence': 93.0,
                    'Quality': {'Brightness': 70.0, 'Sharpness': 80.0}
                }
            ]
        }
        
        liveness_result, error = service.detect_liveness(sample_face_image, 'test-request')
        
        assert liveness_result is None
        assert error is not None
        assert error.error_code == ErrorCodes.LIVENESS_FAILED
        assert "Multiple faces" in error.system_reason

    def test_search_faces_success(self, mock_rekognition_client, sample_face_image, 
                                 sample_search_faces_response):
        """Test successful face search (1:N matching)"""
        service = FaceRecognitionService()
        
        mock_rekognition_client.search_faces_by_image.return_value = sample_search_faces_response
        
        matches, error = service.search_faces(sample_face_image, 'test-request')
        
        assert matches is not None
        assert error is None
        assert len(matches) == 2
        
        # Check first match (highest similarity)
        assert matches[0].employee_id == '123456'
        assert matches[0].similarity == 98.5
        assert matches[0].face_id == 'face-123'
        
        # Check second match
        assert matches[1].employee_id == '654321'
        assert matches[1].similarity == 92.3
        
        # Verify Rekognition was called correctly
        mock_rekognition_client.search_faces_by_image.assert_called_once()
        call_args = mock_rekognition_client.search_faces_by_image.call_args
        assert call_args[1]['CollectionId'] == service.collection_id
        assert call_args[1]['Image']['Bytes'] == sample_face_image
        assert call_args[1]['FaceMatchThreshold'] == 90.0
    
    def test_search_faces_no_match(self, mock_rekognition_client, sample_face_image):
        """Test face search with no matches"""
        service = FaceRecognitionService()
        
        # Mock no matches found
        mock_rekognition_client.search_faces_by_image.return_value = {
            'FaceMatches': []
        }
        
        matches, error = service.search_faces(sample_face_image, 'test-request')
        
        assert matches is None
        assert error is not None
        assert error.error_code == ErrorCodes.FACE_NOT_FOUND
        assert error.user_message == "밝은 곳에서 다시 시도해주세요"
        assert "No matching face" in error.system_reason
    
    def test_search_faces_collection_not_found(self, mock_rekognition_client, sample_face_image):
        """Test face search with collection not found"""
        service = FaceRecognitionService()
        
        # Mock collection not found
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'Collection not found'}}
        mock_rekognition_client.search_faces_by_image.side_effect = \
            ClientError(error_response, 'SearchFacesByImage')
        
        matches, error = service.search_faces(sample_face_image, 'test-request')
        
        assert matches is None
        assert error is not None
        assert error.error_code == ErrorCodes.GENERIC_ERROR
        assert "Collection" in error.system_reason
        assert "not found" in error.system_reason

    def test_index_face_success(self, mock_rekognition_client, sample_face_image, 
                               sample_index_faces_response):
        """Test successful face indexing (enrollment)"""
        service = FaceRecognitionService()
        
        mock_rekognition_client.index_faces.return_value = sample_index_faces_response
        
        face_data, error = service.index_face(sample_face_image, '123456', 'test-request')
        
        assert face_data is not None
        assert error is None
        assert face_data.face_id == 'face-new-123'
        assert face_data.employee_id == '123456'
        assert face_data.confidence == 99.5
        assert face_data.bounding_box is not None
        
        # Verify Rekognition was called correctly
        mock_rekognition_client.index_faces.assert_called_once()
        call_args = mock_rekognition_client.index_faces.call_args
        assert call_args[1]['CollectionId'] == service.collection_id
        assert call_args[1]['Image']['Bytes'] == sample_face_image
        assert call_args[1]['ExternalImageId'] == '123456'
        assert call_args[1]['MaxFaces'] == 1
        assert call_args[1]['QualityFilter'] == 'AUTO'
    
    def test_index_face_no_face_detected(self, mock_rekognition_client, sample_face_image):
        """Test face indexing with no face detected"""
        service = FaceRecognitionService()
        
        # Mock no faces indexed
        mock_rekognition_client.index_faces.return_value = {
            'FaceRecords': []
        }
        
        face_data, error = service.index_face(sample_face_image, '123456', 'test-request')
        
        assert face_data is None
        assert error is not None
        assert error.error_code == ErrorCodes.LIVENESS_FAILED
        assert "No face detected" in error.system_reason
    
    def test_delete_face_success(self, mock_rekognition_client):
        """Test successful face deletion"""
        service = FaceRecognitionService()
        
        mock_rekognition_client.delete_faces.return_value = {
            'DeletedFaces': ['face-123']
        }
        
        success, error = service.delete_face('face-123', 'test-request')
        
        assert success
        assert error is None
        
        mock_rekognition_client.delete_faces.assert_called_once_with(
            CollectionId=service.collection_id,
            FaceIds=['face-123']
        )
    
    def test_delete_face_not_found(self, mock_rekognition_client):
        """Test face deletion when face not found"""
        service = FaceRecognitionService()
        
        # Mock face not deleted
        mock_rekognition_client.delete_faces.return_value = {
            'DeletedFaces': []
        }
        
        success, error = service.delete_face('face-123', 'test-request')
        
        assert not success
        assert error is not None
        assert error.error_code == ErrorCodes.FACE_NOT_FOUND

    def test_delete_faces_by_employee_id(self, mock_rekognition_client):
        """Test deleting all faces for an employee"""
        service = FaceRecognitionService()
        
        # Mock list faces response
        mock_rekognition_client.list_faces.return_value = {
            'Faces': [
                {'FaceId': 'face-1', 'ExternalImageId': '123456'},
                {'FaceId': 'face-2', 'ExternalImageId': '654321'},
                {'FaceId': 'face-3', 'ExternalImageId': '123456'}
            ]
        }
        
        # Mock delete faces response
        mock_rekognition_client.delete_faces.return_value = {
            'DeletedFaces': ['face-1', 'face-3']
        }
        
        deleted_count, error = service.delete_faces_by_employee_id('123456', 'test-request')
        
        assert deleted_count == 2
        assert error is None
        
        # Verify delete was called with correct face IDs
        call_args = mock_rekognition_client.delete_faces.call_args
        assert set(call_args[1]['FaceIds']) == {'face-1', 'face-3'}
    
    def test_delete_faces_by_employee_id_no_faces(self, mock_rekognition_client):
        """Test deleting faces when employee has no faces"""
        service = FaceRecognitionService()
        
        # Mock list faces with no matching employee
        mock_rekognition_client.list_faces.return_value = {
            'Faces': [
                {'FaceId': 'face-1', 'ExternalImageId': '654321'}
            ]
        }
        
        deleted_count, error = service.delete_faces_by_employee_id('123456', 'test-request')
        
        assert deleted_count == 0
        assert error is None
        mock_rekognition_client.delete_faces.assert_not_called()
    
    def test_get_collection_stats(self, mock_rekognition_client):
        """Test getting collection statistics"""
        service = FaceRecognitionService()
        
        mock_rekognition_client.describe_collection.return_value = {
            'CollectionARN': 'arn:aws:rekognition:us-east-1:123456789012:collection/face-auth-employees',
            'FaceCount': 42,
            'FaceModelVersion': '6.0',
            'CreationTimestamp': datetime(2024, 1, 1)
        }
        
        stats = service.get_collection_stats()
        
        assert stats is not None
        assert stats['collection_id'] == service.collection_id
        assert stats['face_count'] == 42
        assert stats['face_model_version'] == '6.0'
    
    def test_list_faces(self, mock_rekognition_client):
        """Test listing faces in collection"""
        service = FaceRecognitionService()
        
        mock_rekognition_client.list_faces.return_value = {
            'Faces': [
                {'FaceId': 'face-1', 'ExternalImageId': '123456'},
                {'FaceId': 'face-2', 'ExternalImageId': '654321'}
            ]
        }
        
        faces = service.list_faces(max_results=100)
        
        assert len(faces) == 2
        assert faces[0]['FaceId'] == 'face-1'
        assert faces[1]['FaceId'] == 'face-2'



class TestLivenessResult:
    """Test LivenessResult class"""
    
    def test_liveness_result_creation(self):
        """Test creating LivenessResult"""
        result = LivenessResult(
            is_live=True,
            confidence=95.5,
            face_detected=True,
            audit_images=['s3://bucket/image1.jpg'],
            session_id='session-123'
        )
        
        assert result.is_live
        assert result.confidence == 95.5
        assert result.face_detected
        assert len(result.audit_images) == 1
        assert result.session_id == 'session-123'
    
    def test_liveness_result_to_dict(self):
        """Test converting LivenessResult to dictionary"""
        result = LivenessResult(
            is_live=True,
            confidence=95.5,
            face_detected=True
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['is_live'] == True
        assert result_dict['confidence'] == 95.5
        assert result_dict['face_detected'] == True
        assert result_dict['audit_images'] == []
        assert result_dict['session_id'] is None


class TestFaceMatch:
    """Test FaceMatch class"""
    
    def test_face_match_creation(self):
        """Test creating FaceMatch"""
        match = FaceMatch(
            face_id='face-123',
            employee_id='123456',
            similarity=98.5,
            confidence=99.0
        )
        
        assert match.face_id == 'face-123'
        assert match.employee_id == '123456'
        assert match.similarity == 98.5
        assert match.confidence == 99.0
    
    def test_face_match_to_dict(self):
        """Test converting FaceMatch to dictionary"""
        match = FaceMatch(
            face_id='face-123',
            employee_id='123456',
            similarity=98.5,
            confidence=99.0
        )
        
        match_dict = match.to_dict()
        
        assert match_dict['face_id'] == 'face-123'
        assert match_dict['employee_id'] == '123456'
        assert match_dict['similarity'] == 98.5
        assert match_dict['confidence'] == 99.0


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_create_face_recognition_service(self):
        """Test factory function"""
        with patch('shared.face_recognition_service.FaceRecognitionService') as mock_service:
            create_face_recognition_service('us-west-2', 'custom-collection')
            mock_service.assert_called_once_with('us-west-2', 'custom-collection')
    
    def test_validate_face_image_jpeg(self):
        """Test validating JPEG image"""
        jpeg_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF' + b'\x00' * 2000
        is_valid, format_info = validate_face_image(jpeg_bytes)
        
        assert is_valid
        assert format_info == "JPEG"
    
    def test_validate_face_image_png(self):
        """Test validating PNG image"""
        png_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 2000
        is_valid, format_info = validate_face_image(png_bytes)
        
        assert is_valid
        assert format_info == "PNG"
    
    def test_validate_face_image_too_small(self):
        """Test validating image that's too small"""
        small_bytes = b'\xff\xd8\xff' + b'\x00' * 100
        is_valid, error_msg = validate_face_image(small_bytes)
        
        assert not is_valid
        assert "too small" in error_msg
    
    def test_validate_face_image_too_large(self):
        """Test validating image that's too large"""
        large_bytes = b'\xff\xd8\xff' + b'\x00' * (6 * 1024 * 1024)
        is_valid, error_msg = validate_face_image(large_bytes)
        
        assert not is_valid
        assert "too large" in error_msg
    
    def test_validate_face_image_unsupported_format(self):
        """Test validating unsupported image format"""
        invalid_bytes = b'INVALID' + b'\x00' * 2000
        is_valid, error_msg = validate_face_image(invalid_bytes)
        
        assert not is_valid
        assert "Unsupported" in error_msg


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.fixture
    def mock_rekognition_client(self):
        """Mock Rekognition client"""
        with patch('boto3.client') as mock_boto:
            mock_client = Mock()
            mock_boto.return_value = mock_client
            yield mock_client
    
    def test_detect_liveness_exception(self, mock_rekognition_client):
        """Test liveness detection with exception"""
        service = FaceRecognitionService()
        
        mock_rekognition_client.detect_faces.side_effect = Exception("Rekognition error")
        
        liveness_result, error = service.detect_liveness(b'test', 'test-request')
        
        assert liveness_result is None
        assert error is not None
        assert error.error_code == ErrorCodes.LIVENESS_FAILED
        assert "Rekognition error" in error.system_reason
    
    def test_search_faces_invalid_parameter(self, mock_rekognition_client):
        """Test face search with invalid parameter"""
        service = FaceRecognitionService()
        
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'InvalidParameterException', 'Message': 'Invalid image'}}
        mock_rekognition_client.search_faces_by_image.side_effect = \
            ClientError(error_response, 'SearchFacesByImage')
        
        matches, error = service.search_faces(b'test', 'test-request')
        
        assert matches is None
        assert error is not None
        assert error.error_code == ErrorCodes.LIVENESS_FAILED
        assert "Invalid image" in error.system_reason
    
    def test_index_face_exception(self, mock_rekognition_client):
        """Test face indexing with exception"""
        service = FaceRecognitionService()
        
        mock_rekognition_client.index_faces.side_effect = Exception("Indexing error")
        
        face_data, error = service.index_face(b'test', '123456', 'test-request')
        
        assert face_data is None
        assert error is not None
        assert error.error_code == ErrorCodes.GENERIC_ERROR
        assert "Indexing error" in error.system_reason


if __name__ == '__main__':
    pytest.main([__file__])
