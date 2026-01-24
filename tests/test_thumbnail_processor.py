"""
Unit tests for ThumbnailProcessor service

Tests cover:
- Thumbnail creation with various image formats and sizes
- S3 storage operations for enrollment and login attempts
- Original image deletion functionality
- Error handling and edge cases
- Image validation utilities

Requirements: 5.1, 5.2
"""

import pytest
import boto3
from moto import mock_aws
from PIL import Image
from io import BytesIO
import os
from datetime import datetime
from unittest.mock import patch, MagicMock

import sys
import os
import importlib.util

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Import the thumbnail processor module using importlib
spec = importlib.util.spec_from_file_location(
    "thumbnail_processor", 
    os.path.join(os.path.dirname(__file__), '..', 'lambda', 'shared', 'thumbnail_processor.py')
)
thumbnail_processor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(thumbnail_processor_module)

ThumbnailProcessor = thumbnail_processor_module.ThumbnailProcessor
create_thumbnail_processor = thumbnail_processor_module.create_thumbnail_processor
validate_employee_id_format = thumbnail_processor_module.validate_employee_id_format


class TestThumbnailProcessor:
    """Test cases for ThumbnailProcessor class"""
    
    @pytest.fixture
    def mock_s3_setup(self):
        """Set up mock S3 environment"""
        with mock_aws():
            # Create mock S3 client and bucket
            s3_client = boto3.client('s3', region_name='us-east-1')
            bucket_name = 'test-face-auth-bucket'
            s3_client.create_bucket(Bucket=bucket_name)
            
            yield s3_client, bucket_name
    
    @pytest.fixture
    def thumbnail_processor(self, mock_s3_setup):
        """Create ThumbnailProcessor instance with mock S3"""
        s3_client, bucket_name = mock_s3_setup
        return ThumbnailProcessor(bucket_name)
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Create sample image bytes for testing"""
        # Create a 400x300 RGB image
        img = Image.new('RGB', (400, 300), color='red')
        output = BytesIO()
        img.save(output, format='JPEG')
        return output.getvalue()
    
    @pytest.fixture
    def sample_square_image_bytes(self):
        """Create sample square image bytes for testing"""
        # Create a 300x300 RGB image
        img = Image.new('RGB', (300, 300), color='blue')
        output = BytesIO()
        img.save(output, format='JPEG')
        return output.getvalue()
    
    @pytest.fixture
    def sample_small_image_bytes(self):
        """Create sample small image bytes for testing"""
        # Create a 100x100 RGB image
        img = Image.new('RGB', (100, 100), color='green')
        output = BytesIO()
        img.save(output, format='JPEG')
        return output.getvalue()
    
    def test_create_thumbnail_basic(self, thumbnail_processor, sample_image_bytes):
        """Test basic thumbnail creation"""
        thumbnail_bytes = thumbnail_processor.create_thumbnail(sample_image_bytes)
        
        # Verify thumbnail is created
        assert thumbnail_bytes is not None
        assert len(thumbnail_bytes) > 0
        
        # Verify thumbnail dimensions
        with Image.open(BytesIO(thumbnail_bytes)) as img:
            assert img.size == (200, 200)
            assert img.format == 'JPEG'
    
    def test_create_thumbnail_square_image(self, thumbnail_processor, sample_square_image_bytes):
        """Test thumbnail creation with square input image"""
        thumbnail_bytes = thumbnail_processor.create_thumbnail(sample_square_image_bytes)
        
        # Verify thumbnail dimensions
        with Image.open(BytesIO(thumbnail_bytes)) as img:
            assert img.size == (200, 200)
            assert img.format == 'JPEG'
    
    def test_create_thumbnail_small_image(self, thumbnail_processor, sample_small_image_bytes):
        """Test thumbnail creation with small input image (upscaling)"""
        thumbnail_bytes = thumbnail_processor.create_thumbnail(sample_small_image_bytes)
        
        # Verify thumbnail dimensions (should be padded to 200x200)
        with Image.open(BytesIO(thumbnail_bytes)) as img:
            assert img.size == (200, 200)
            assert img.format == 'JPEG'
    
    def test_create_thumbnail_rgba_image(self, thumbnail_processor):
        """Test thumbnail creation with RGBA image (transparency)"""
        # Create RGBA image with transparency
        img = Image.new('RGBA', (300, 200), color=(255, 0, 0, 128))
        output = BytesIO()
        img.save(output, format='PNG')
        rgba_bytes = output.getvalue()
        
        thumbnail_bytes = thumbnail_processor.create_thumbnail(rgba_bytes)
        
        # Verify thumbnail is RGB (no transparency)
        with Image.open(BytesIO(thumbnail_bytes)) as img:
            assert img.size == (200, 200)
            assert img.mode == 'RGB'
            assert img.format == 'JPEG'
    
    def test_create_thumbnail_grayscale_image(self, thumbnail_processor):
        """Test thumbnail creation with grayscale image"""
        # Create grayscale image
        img = Image.new('L', (250, 150), color=128)
        output = BytesIO()
        img.save(output, format='JPEG')
        gray_bytes = output.getvalue()
        
        thumbnail_bytes = thumbnail_processor.create_thumbnail(gray_bytes)
        
        # Verify thumbnail is RGB
        with Image.open(BytesIO(thumbnail_bytes)) as img:
            assert img.size == (200, 200)
            assert img.mode == 'RGB'
            assert img.format == 'JPEG'
    
    def test_create_thumbnail_invalid_image(self, thumbnail_processor):
        """Test thumbnail creation with invalid image data"""
        invalid_bytes = b"not an image"
        
        with pytest.raises(ValueError, match="Failed to process image"):
            thumbnail_processor.create_thumbnail(invalid_bytes)
    
    def test_store_enrollment_thumbnail(self, thumbnail_processor, sample_image_bytes):
        """Test storing enrollment thumbnail in S3"""
        employee_id = "123456"
        thumbnail_bytes = thumbnail_processor.create_thumbnail(sample_image_bytes)
        
        s3_key = thumbnail_processor.store_enrollment_thumbnail(employee_id, thumbnail_bytes)
        
        # Verify S3 key format
        expected_key = f"enroll/{employee_id}/face_thumbnail.jpg"
        assert s3_key == expected_key
        
        # Verify object exists in S3
        info = thumbnail_processor.get_thumbnail_info(s3_key)
        assert info is not None
        assert info['content_type'] == 'image/jpeg'
        assert 'employee_id' in info['metadata']
        assert info['metadata']['employee_id'] == employee_id
    
    def test_store_login_attempt_thumbnail_with_employee_id(self, thumbnail_processor, sample_image_bytes):
        """Test storing login attempt thumbnail with known employee ID"""
        employee_id = "789012"
        thumbnail_bytes = thumbnail_processor.create_thumbnail(sample_image_bytes)
        
        s3_key = thumbnail_processor.store_login_attempt_thumbnail(employee_id, thumbnail_bytes)
        
        # Verify S3 key format
        assert s3_key.startswith("logins/")
        assert employee_id in s3_key
        assert s3_key.endswith(".jpg")
        
        # Verify object exists in S3
        info = thumbnail_processor.get_thumbnail_info(s3_key)
        assert info is not None
        assert info['content_type'] == 'image/jpeg'
        assert info['metadata']['employee_id'] == employee_id
    
    def test_store_login_attempt_thumbnail_unknown_employee(self, thumbnail_processor, sample_image_bytes):
        """Test storing login attempt thumbnail for unknown employee"""
        thumbnail_bytes = thumbnail_processor.create_thumbnail(sample_image_bytes)
        
        s3_key = thumbnail_processor.store_login_attempt_thumbnail(None, thumbnail_bytes)
        
        # Verify S3 key format
        assert s3_key.startswith("logins/")
        assert "unknown" in s3_key
        assert s3_key.endswith(".jpg")
        
        # Verify object exists in S3
        info = thumbnail_processor.get_thumbnail_info(s3_key)
        assert info is not None
        assert info['content_type'] == 'image/jpeg'
        assert info['metadata']['employee_id'] == 'unknown'
    
    def test_process_enrollment_image_complete_workflow(self, thumbnail_processor, sample_image_bytes):
        """Test complete enrollment image processing workflow"""
        employee_id = "456789"
        
        # First store original image to simulate deletion
        original_key = f"temp/{employee_id}/original.jpg"
        thumbnail_processor.s3_client.put_object(
            Bucket=thumbnail_processor.bucket_name,
            Key=original_key,
            Body=sample_image_bytes
        )
        
        # Process enrollment image
        thumbnail_s3_key = thumbnail_processor.process_enrollment_image(
            employee_id, sample_image_bytes, original_key
        )
        
        # Verify thumbnail was created and stored
        expected_key = f"enroll/{employee_id}/face_thumbnail.jpg"
        assert thumbnail_s3_key == expected_key
        
        # Verify thumbnail exists
        info = thumbnail_processor.get_thumbnail_info(thumbnail_s3_key)
        assert info is not None
        
        # Verify original image was deleted
        from botocore.exceptions import ClientError
        with pytest.raises(ClientError):
            thumbnail_processor.s3_client.head_object(
                Bucket=thumbnail_processor.bucket_name,
                Key=original_key
            )
    
    def test_process_enrollment_image_without_original_deletion(self, thumbnail_processor, sample_image_bytes):
        """Test enrollment image processing without original image deletion"""
        employee_id = "654321"
        
        # Process enrollment image without original S3 key
        thumbnail_s3_key = thumbnail_processor.process_enrollment_image(
            employee_id, sample_image_bytes
        )
        
        # Verify thumbnail was created and stored
        expected_key = f"enroll/{employee_id}/face_thumbnail.jpg"
        assert thumbnail_s3_key == expected_key
        
        # Verify thumbnail exists
        info = thumbnail_processor.get_thumbnail_info(thumbnail_s3_key)
        assert info is not None
    
    def test_process_login_attempt_image_complete_workflow(self, thumbnail_processor, sample_image_bytes):
        """Test complete login attempt image processing workflow"""
        employee_id = "987654"
        
        # First store original image to simulate deletion
        original_key = f"temp/login_attempt/original.jpg"
        thumbnail_processor.s3_client.put_object(
            Bucket=thumbnail_processor.bucket_name,
            Key=original_key,
            Body=sample_image_bytes
        )
        
        # Process login attempt image
        thumbnail_s3_key = thumbnail_processor.process_login_attempt_image(
            sample_image_bytes, employee_id, original_key
        )
        
        # Verify thumbnail was created and stored
        assert thumbnail_s3_key.startswith("logins/")
        assert employee_id in thumbnail_s3_key
        
        # Verify thumbnail exists
        info = thumbnail_processor.get_thumbnail_info(thumbnail_s3_key)
        assert info is not None
        
        # Verify original image was deleted
        from botocore.exceptions import ClientError
        with pytest.raises(ClientError):
            thumbnail_processor.s3_client.head_object(
                Bucket=thumbnail_processor.bucket_name,
                Key=original_key
            )
    
    def test_get_thumbnail_info_nonexistent(self, thumbnail_processor):
        """Test getting info for non-existent thumbnail"""
        info = thumbnail_processor.get_thumbnail_info("nonexistent/key.jpg")
        assert info is None
    
    def test_validate_image_format_valid(self, thumbnail_processor, sample_image_bytes):
        """Test image format validation with valid image"""
        is_valid, format_info = thumbnail_processor.validate_image_format(sample_image_bytes)
        assert is_valid is True
        assert format_info == 'JPEG'
    
    def test_validate_image_format_invalid(self, thumbnail_processor):
        """Test image format validation with invalid data"""
        invalid_bytes = b"not an image"
        is_valid, error_msg = thumbnail_processor.validate_image_format(invalid_bytes)
        assert is_valid is False
        assert "cannot identify image file" in error_msg.lower()
    
    def test_get_image_dimensions_valid(self, thumbnail_processor, sample_image_bytes):
        """Test getting image dimensions from valid image"""
        dimensions = thumbnail_processor.get_image_dimensions(sample_image_bytes)
        assert dimensions == (400, 300)  # Original sample image size
    
    def test_get_image_dimensions_invalid(self, thumbnail_processor):
        """Test getting image dimensions from invalid data"""
        invalid_bytes = b"not an image"
        dimensions = thumbnail_processor.get_image_dimensions(invalid_bytes)
        assert dimensions is None
    
    def test_s3_error_handling(self, thumbnail_processor, sample_image_bytes):
        """Test S3 error handling"""
        # Mock S3 client to raise exception
        with patch.object(thumbnail_processor.s3_client, 'put_object', side_effect=Exception("S3 Error")):
            thumbnail_bytes = thumbnail_processor.create_thumbnail(sample_image_bytes)
            
            with pytest.raises(Exception, match="S3 Error"):
                thumbnail_processor.store_enrollment_thumbnail("123456", thumbnail_bytes)


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_create_thumbnail_processor_with_bucket_name(self):
        """Test creating ThumbnailProcessor with explicit bucket name"""
        bucket_name = "test-bucket"
        processor = create_thumbnail_processor(bucket_name)
        assert processor.bucket_name == bucket_name
    
    def test_create_thumbnail_processor_from_environment(self):
        """Test creating ThumbnailProcessor from environment variable"""
        bucket_name = "env-bucket"
        with patch.dict(os.environ, {'FACE_AUTH_BUCKET_NAME': bucket_name}):
            processor = create_thumbnail_processor()
            assert processor.bucket_name == bucket_name
    
    def test_create_thumbnail_processor_no_bucket_name(self):
        """Test creating ThumbnailProcessor without bucket name"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Bucket name must be provided"):
                create_thumbnail_processor()
    
    def test_validate_employee_id_format_valid(self):
        """Test employee ID format validation with valid IDs"""
        assert validate_employee_id_format("123456") is True
        assert validate_employee_id_format("000000") is True
        assert validate_employee_id_format("999999") is True
    
    def test_validate_employee_id_format_invalid(self):
        """Test employee ID format validation with invalid IDs"""
        assert validate_employee_id_format("12345") is False  # Too short
        assert validate_employee_id_format("1234567") is False  # Too long
        assert validate_employee_id_format("12345a") is False  # Contains letter
        assert validate_employee_id_format("") is False  # Empty
        assert validate_employee_id_format("abc123") is False  # Contains letters


class TestThumbnailProcessorEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def thumbnail_processor(self):
        """Create ThumbnailProcessor without mock S3 for error testing"""
        return ThumbnailProcessor("test-bucket")
    
    def test_very_large_image(self, thumbnail_processor):
        """Test processing very large image"""
        # Create a large image (2000x1500)
        img = Image.new('RGB', (2000, 1500), color='purple')
        output = BytesIO()
        img.save(output, format='JPEG')
        large_image_bytes = output.getvalue()
        
        thumbnail_bytes = thumbnail_processor.create_thumbnail(large_image_bytes)
        
        # Verify thumbnail is still 200x200
        with Image.open(BytesIO(thumbnail_bytes)) as img:
            assert img.size == (200, 200)
    
    def test_very_small_image(self, thumbnail_processor):
        """Test processing very small image"""
        # Create a tiny image (50x30)
        img = Image.new('RGB', (50, 30), color='orange')
        output = BytesIO()
        img.save(output, format='JPEG')
        small_image_bytes = output.getvalue()
        
        thumbnail_bytes = thumbnail_processor.create_thumbnail(small_image_bytes)
        
        # Verify thumbnail is padded to 200x200
        with Image.open(BytesIO(thumbnail_bytes)) as img:
            assert img.size == (200, 200)
    
    def test_extreme_aspect_ratio(self, thumbnail_processor):
        """Test processing image with extreme aspect ratio"""
        # Create a very wide image (1000x50)
        img = Image.new('RGB', (1000, 50), color='yellow')
        output = BytesIO()
        img.save(output, format='JPEG')
        wide_image_bytes = output.getvalue()
        
        thumbnail_bytes = thumbnail_processor.create_thumbnail(wide_image_bytes)
        
        # Verify thumbnail maintains aspect ratio within 200x200
        with Image.open(BytesIO(thumbnail_bytes)) as img:
            assert img.size == (200, 200)
    
    def test_corrupted_image_data(self, thumbnail_processor):
        """Test processing corrupted image data"""
        # Create partially corrupted JPEG data
        img = Image.new('RGB', (100, 100), color='black')
        output = BytesIO()
        img.save(output, format='JPEG')
        valid_bytes = output.getvalue()
        
        # Corrupt the data by truncating it
        corrupted_bytes = valid_bytes[:len(valid_bytes)//2]
        
        with pytest.raises(ValueError, match="Failed to process image"):
            thumbnail_processor.create_thumbnail(corrupted_bytes)
    
    def test_empty_image_data(self, thumbnail_processor):
        """Test processing empty image data"""
        empty_bytes = b""
        
        with pytest.raises(ValueError, match="Failed to process image"):
            thumbnail_processor.create_thumbnail(empty_bytes)


if __name__ == "__main__":
    pytest.main([__file__])