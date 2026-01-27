"""
Face-Auth IdP System - Thumbnail Processor Service

This module provides image processing capabilities for the Face-Auth system:
- Creates 200x200 pixel thumbnails from original images
- Handles S3 storage operations for thumbnails
- Manages original image deletion after processing
- Supports both enrollment and login attempt image processing

Requirements: 5.1, 5.2
"""

import boto3
import logging
from io import BytesIO
from PIL import Image, ImageOps
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import uuid
import os

logger = logging.getLogger(__name__)


class ThumbnailProcessor:
    """
    Service for processing face images into standardized thumbnails
    
    This service handles:
    - Creating 200x200 pixel thumbnails with proper aspect ratio preservation
    - Uploading thumbnails to appropriate S3 folders (enroll/ or logins/)
    - Deleting original images after successful processing
    - Applying consistent image quality and format standards
    """
    
    TARGET_SIZE = (200, 200)
    QUALITY = 85
    FORMAT = 'JPEG'
    BACKGROUND_COLOR = (255, 255, 255)  # White background for padding
    
    def __init__(self, bucket_name: str, region_name: str = 'us-east-1'):
        """
        Initialize ThumbnailProcessor
        
        Args:
            bucket_name: S3 bucket name for image storage
            region_name: AWS region name
        """
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3', region_name=region_name)
        
    def create_thumbnail(self, image_bytes: bytes) -> bytes:
        """
        Create a 200x200 pixel thumbnail from image bytes
        
        This method:
        1. Opens the image from bytes
        2. Resizes while maintaining aspect ratio
        3. Adds white padding to make it exactly 200x200
        4. Compresses to JPEG format with specified quality
        
        Args:
            image_bytes: Original image data as bytes
            
        Returns:
            bytes: Processed thumbnail image as JPEG bytes
            
        Raises:
            ValueError: If image cannot be processed
            IOError: If image format is not supported
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calculate resize dimensions maintaining aspect ratio
                img.thumbnail(self.TARGET_SIZE, Image.Resampling.LANCZOS)
                
                # Create new image with target size and white background
                padded_img = Image.new('RGB', self.TARGET_SIZE, self.BACKGROUND_COLOR)
                
                # Calculate position to center the resized image
                offset = (
                    (self.TARGET_SIZE[0] - img.size[0]) // 2,
                    (self.TARGET_SIZE[1] - img.size[1]) // 2
                )
                
                # Paste the resized image onto the padded background
                padded_img.paste(img, offset)
                
                # Save to bytes with specified quality
                output = BytesIO()
                padded_img.save(output, format=self.FORMAT, quality=self.QUALITY, optimize=True)
                
                thumbnail_bytes = output.getvalue()
                logger.info(f"Created thumbnail: {len(image_bytes)} bytes -> {len(thumbnail_bytes)} bytes")
                
                return thumbnail_bytes
                
        except Exception as e:
            logger.error(f"Error creating thumbnail: {str(e)}")
            raise ValueError(f"Failed to process image: {str(e)}")
    
    def store_enrollment_thumbnail(self, employee_id: str, thumbnail_bytes: bytes) -> str:
        """
        Store enrollment thumbnail in S3 enroll/ folder
        
        Enrollment thumbnails are stored permanently in the structure:
        enroll/{employee_id}/face_thumbnail.jpg
        
        Args:
            employee_id: Employee identifier (6-digit string)
            thumbnail_bytes: Processed thumbnail image bytes
            
        Returns:
            str: S3 key of the stored thumbnail
            
        Raises:
            Exception: If S3 upload fails
        """
        s3_key = f"enroll/{employee_id}/face_thumbnail.jpg"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=thumbnail_bytes,
                ContentType='image/jpeg',
                Metadata={
                    'employee_id': employee_id,
                    'image_type': 'enrollment_thumbnail',
                    'processed_at': datetime.now().isoformat(),
                    'size': '200x200'
                },
                ServerSideEncryption='AES256'  # Apply S3 encryption
            )
            
            logger.info(f"Stored enrollment thumbnail: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error storing enrollment thumbnail for {employee_id}: {str(e)}")
            raise
    
    def store_login_attempt_thumbnail(self, employee_id: Optional[str], thumbnail_bytes: bytes) -> str:
        """
        Store login attempt thumbnail in S3 logins/ folder
        
        Login attempt thumbnails are stored with 30-day lifecycle in the structure:
        logins/{date}/{timestamp}_{employee_id_or_unknown}.jpg
        
        Args:
            employee_id: Employee identifier if known, None for failed attempts
            thumbnail_bytes: Processed thumbnail image bytes
            
        Returns:
            str: S3 key of the stored thumbnail
            
        Raises:
            Exception: If S3 upload fails
        """
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        
        # Use employee_id if known, otherwise use 'unknown' with UUID
        if employee_id:
            filename = f"{timestamp}_{employee_id}.jpg"
        else:
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_unknown_{unique_id}.jpg"
        
        s3_key = f"logins/{date_str}/{filename}"
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=thumbnail_bytes,
                ContentType='image/jpeg',
                Metadata={
                    'employee_id': employee_id or 'unknown',
                    'image_type': 'login_attempt_thumbnail',
                    'processed_at': now.isoformat(),
                    'size': '200x200'
                },
                ServerSideEncryption='AES256'  # Apply S3 encryption
            )
            
            logger.info(f"Stored login attempt thumbnail: {s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Error storing login attempt thumbnail: {str(e)}")
            raise
    
    def process_enrollment_image(self, employee_id: str, original_image_bytes: bytes, 
                               original_s3_key: Optional[str] = None) -> str:
        """
        Complete enrollment image processing workflow
        
        This method:
        1. Creates a 200x200 thumbnail from the original image
        2. Stores the thumbnail in S3 enroll/ folder
        3. Deletes the original image if S3 key is provided
        
        Args:
            employee_id: Employee identifier
            original_image_bytes: Original image data
            original_s3_key: S3 key of original image to delete (optional)
            
        Returns:
            str: S3 key of the stored thumbnail
            
        Raises:
            ValueError: If image processing fails
            Exception: If S3 operations fail
        """
        try:
            # Create thumbnail
            thumbnail_bytes = self.create_thumbnail(original_image_bytes)
            
            # Store thumbnail in enroll/ folder
            thumbnail_s3_key = self.store_enrollment_thumbnail(employee_id, thumbnail_bytes)
            
            # Delete original image if provided
            if original_s3_key:
                self._delete_original_image(original_s3_key)
            
            logger.info(f"Completed enrollment image processing for employee {employee_id}")
            return thumbnail_s3_key
            
        except Exception as e:
            logger.error(f"Error processing enrollment image for {employee_id}: {str(e)}")
            raise
    
    def process_login_attempt_image(self, original_image_bytes: bytes, 
                                  employee_id: Optional[str] = None,
                                  original_s3_key: Optional[str] = None) -> str:
        """
        Complete login attempt image processing workflow
        
        This method:
        1. Creates a 200x200 thumbnail from the original image
        2. Stores the thumbnail in S3 logins/ folder (30-day lifecycle)
        3. Deletes the original image if S3 key is provided
        
        Args:
            original_image_bytes: Original image data
            employee_id: Employee identifier if known (for successful logins)
            original_s3_key: S3 key of original image to delete (optional)
            
        Returns:
            str: S3 key of the stored thumbnail
            
        Raises:
            ValueError: If image processing fails
            Exception: If S3 operations fail
        """
        try:
            # Create thumbnail
            thumbnail_bytes = self.create_thumbnail(original_image_bytes)
            
            # Store thumbnail in logins/ folder
            thumbnail_s3_key = self.store_login_attempt_thumbnail(employee_id, thumbnail_bytes)
            
            # Delete original image if provided
            if original_s3_key:
                self._delete_original_image(original_s3_key)
            
            logger.info(f"Completed login attempt image processing")
            return thumbnail_s3_key
            
        except Exception as e:
            logger.error(f"Error processing login attempt image: {str(e)}")
            raise
    
    def _delete_original_image(self, s3_key: str) -> bool:
        """
        Delete original image from S3 after successful thumbnail creation
        
        Args:
            s3_key: S3 key of the original image to delete
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            Exception: If S3 deletion fails
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"Deleted original image: {s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting original image {s3_key}: {str(e)}")
            raise
    
    def get_thumbnail_info(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata information about a stored thumbnail
        
        Args:
            s3_key: S3 key of the thumbnail
            
        Returns:
            Dict containing thumbnail metadata or None if not found
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                'size': response['ContentLength'],
                'last_modified': response['LastModified'],
                'metadata': response.get('Metadata', {}),
                'content_type': response.get('ContentType')
            }
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Thumbnail not found: {s3_key}")
            return None
        except Exception as e:
            # Handle both NoSuchKey and ClientError for compatibility
            if 'NoSuchKey' in str(e) or '404' in str(e):
                logger.warning(f"Thumbnail not found: {s3_key}")
                return None
            logger.error(f"Error getting thumbnail info for {s3_key}: {str(e)}")
            raise
    
    def validate_image_format(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate that image bytes represent a valid image format
        
        Args:
            image_bytes: Image data to validate
            
        Returns:
            Tuple of (is_valid, format_or_error_message)
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                return True, img.format
        except Exception as e:
            return False, str(e)
    
    def get_image_dimensions(self, image_bytes: bytes) -> Optional[Tuple[int, int]]:
        """
        Get dimensions of an image without fully loading it
        
        Args:
            image_bytes: Image data
            
        Returns:
            Tuple of (width, height) or None if invalid
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                return img.size
        except Exception as e:
            logger.error(f"Error getting image dimensions: {str(e)}")
            return None


# Utility functions for common operations

def create_thumbnail_processor(bucket_name: Optional[str] = None, 
                             region_name: str = 'us-east-1') -> ThumbnailProcessor:
    """
    Factory function to create ThumbnailProcessor instance
    
    Args:
        bucket_name: S3 bucket name (uses environment variable if not provided)
        region_name: AWS region name
        
    Returns:
        ThumbnailProcessor instance
        
    Raises:
        ValueError: If bucket name is not provided and not in environment
    """
    if not bucket_name:
        bucket_name = os.environ.get('FACE_AUTH_BUCKET_NAME')
        if not bucket_name:
            raise ValueError("Bucket name must be provided or set in FACE_AUTH_BUCKET_NAME environment variable")
    
    return ThumbnailProcessor(bucket_name, region_name)


def validate_employee_id_format(employee_id: str) -> bool:
    """
    Validate employee ID format (6 digits)
    
    Args:
        employee_id: Employee identifier to validate
        
    Returns:
        bool: True if format is valid
    """
    return len(employee_id) == 6 and employee_id.isdigit()