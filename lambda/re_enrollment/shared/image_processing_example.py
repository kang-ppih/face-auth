"""
Example usage of ThumbnailProcessor in Face-Auth Lambda functions

This module demonstrates how the ThumbnailProcessor service would be integrated
into the actual Lambda functions for enrollment and login processing.

Requirements: 5.1, 5.2
"""

import os
import logging
from typing import Optional, Dict, Any
from .thumbnail_processor import ThumbnailProcessor, create_thumbnail_processor

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """
    High-level service that integrates ThumbnailProcessor with Face-Auth workflows
    
    This service provides convenient methods for the common image processing
    patterns used in enrollment and login Lambda functions.
    """
    
    def __init__(self, bucket_name: Optional[str] = None):
        """
        Initialize ImageProcessingService
        
        Args:
            bucket_name: S3 bucket name (uses environment variable if not provided)
        """
        self.thumbnail_processor = create_thumbnail_processor(bucket_name)
        
    def process_enrollment_face_image(self, employee_id: str, face_image_bytes: bytes) -> Dict[str, Any]:
        """
        Process face image for employee enrollment
        
        This method:
        1. Validates the image format and dimensions
        2. Creates a 200x200 thumbnail
        3. Stores the thumbnail in S3 enroll/ folder
        4. Returns processing results for Lambda response
        
        Args:
            employee_id: Employee identifier (6-digit string)
            face_image_bytes: Original face image data
            
        Returns:
            Dict containing processing results and S3 key
            
        Raises:
            ValueError: If image processing fails
            Exception: If S3 operations fail
        """
        try:
            # Validate employee ID format
            if not (len(employee_id) == 6 and employee_id.isdigit()):
                raise ValueError(f"Invalid employee ID format: {employee_id}")
            
            # Validate image format
            is_valid, format_info = self.thumbnail_processor.validate_image_format(face_image_bytes)
            if not is_valid:
                raise ValueError(f"Invalid image format: {format_info}")
            
            # Get original image dimensions
            original_dimensions = self.thumbnail_processor.get_image_dimensions(face_image_bytes)
            
            # Process the enrollment image
            thumbnail_s3_key = self.thumbnail_processor.process_enrollment_image(
                employee_id, face_image_bytes
            )
            
            # Get thumbnail info for verification
            thumbnail_info = self.thumbnail_processor.get_thumbnail_info(thumbnail_s3_key)
            
            logger.info(f"Successfully processed enrollment image for employee {employee_id}")
            
            return {
                'success': True,
                'thumbnail_s3_key': thumbnail_s3_key,
                'original_dimensions': original_dimensions,
                'thumbnail_size': thumbnail_info['size'] if thumbnail_info else None,
                'processing_metadata': {
                    'employee_id': employee_id,
                    'image_type': 'enrollment',
                    'thumbnail_dimensions': '200x200'
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing enrollment image for {employee_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'employee_id': employee_id
            }
    
    def process_login_attempt_image(self, face_image_bytes: bytes, 
                                  employee_id: Optional[str] = None,
                                  login_successful: bool = False) -> Dict[str, Any]:
        """
        Process face image for login attempt
        
        This method:
        1. Validates the image format and dimensions
        2. Creates a 200x200 thumbnail
        3. Stores the thumbnail in S3 logins/ folder (30-day lifecycle)
        4. Returns processing results for Lambda response
        
        Args:
            face_image_bytes: Original face image data
            employee_id: Employee identifier if known (for successful logins)
            login_successful: Whether the login attempt was successful
            
        Returns:
            Dict containing processing results and S3 key
            
        Raises:
            ValueError: If image processing fails
            Exception: If S3 operations fail
        """
        try:
            # Validate image format
            is_valid, format_info = self.thumbnail_processor.validate_image_format(face_image_bytes)
            if not is_valid:
                raise ValueError(f"Invalid image format: {format_info}")
            
            # Get original image dimensions
            original_dimensions = self.thumbnail_processor.get_image_dimensions(face_image_bytes)
            
            # Process the login attempt image
            thumbnail_s3_key = self.thumbnail_processor.process_login_attempt_image(
                face_image_bytes, employee_id
            )
            
            # Get thumbnail info for verification
            thumbnail_info = self.thumbnail_processor.get_thumbnail_info(thumbnail_s3_key)
            
            logger.info(f"Successfully processed login attempt image (employee: {employee_id or 'unknown'})")
            
            return {
                'success': True,
                'thumbnail_s3_key': thumbnail_s3_key,
                'original_dimensions': original_dimensions,
                'thumbnail_size': thumbnail_info['size'] if thumbnail_info else None,
                'processing_metadata': {
                    'employee_id': employee_id or 'unknown',
                    'image_type': 'login_attempt',
                    'login_successful': login_successful,
                    'thumbnail_dimensions': '200x200'
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing login attempt image: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'employee_id': employee_id
            }
    
    def cleanup_temp_images(self, temp_s3_keys: list) -> Dict[str, Any]:
        """
        Clean up temporary images after processing
        
        Args:
            temp_s3_keys: List of S3 keys for temporary images to delete
            
        Returns:
            Dict containing cleanup results
        """
        cleanup_results = {
            'success': True,
            'deleted_keys': [],
            'failed_keys': [],
            'errors': []
        }
        
        for s3_key in temp_s3_keys:
            try:
                self.thumbnail_processor._delete_original_image(s3_key)
                cleanup_results['deleted_keys'].append(s3_key)
                logger.info(f"Deleted temporary image: {s3_key}")
            except Exception as e:
                cleanup_results['failed_keys'].append(s3_key)
                cleanup_results['errors'].append(str(e))
                cleanup_results['success'] = False
                logger.error(f"Failed to delete temporary image {s3_key}: {str(e)}")
        
        return cleanup_results


# Example Lambda function integration

def lambda_enrollment_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example Lambda function for employee enrollment with image processing
    
    This demonstrates how ThumbnailProcessor would be used in the actual
    enrollment Lambda function.
    """
    try:
        # Extract data from Lambda event
        employee_id = event.get('employee_id')
        face_image_base64 = event.get('face_image')
        
        if not employee_id or not face_image_base64:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Missing required fields: employee_id, face_image'
                }
            }
        
        # Decode base64 image
        import base64
        face_image_bytes = base64.b64decode(face_image_base64)
        
        # Initialize image processing service
        image_service = ImageProcessingService()
        
        # Process the enrollment image
        processing_result = image_service.process_enrollment_face_image(
            employee_id, face_image_bytes
        )
        
        if not processing_result['success']:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Image processing failed',
                    'details': processing_result['error']
                }
            }
        
        # Here you would typically:
        # 1. Index the face with Amazon Rekognition
        # 2. Store face data in DynamoDB
        # 3. Create authentication session
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Enrollment successful',
                'employee_id': employee_id,
                'thumbnail_s3_key': processing_result['thumbnail_s3_key'],
                'processing_metadata': processing_result['processing_metadata']
            }
        }
        
    except Exception as e:
        logger.error(f"Enrollment Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal server error',
                'details': str(e)
            }
        }


def lambda_face_login_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example Lambda function for face login with image processing
    
    This demonstrates how ThumbnailProcessor would be used in the actual
    face login Lambda function.
    """
    try:
        # Extract data from Lambda event
        face_image_base64 = event.get('face_image')
        
        if not face_image_base64:
            return {
                'statusCode': 400,
                'body': {
                    'error': 'Missing required field: face_image'
                }
            }
        
        # Decode base64 image
        import base64
        face_image_bytes = base64.b64decode(face_image_base64)
        
        # Initialize image processing service
        image_service = ImageProcessingService()
        
        # Here you would typically:
        # 1. Perform face recognition with Amazon Rekognition
        # 2. Determine if login was successful and get employee_id
        
        # For this example, assume login failed (employee_id = None)
        login_successful = False
        employee_id = None  # Would be set if face recognition succeeded
        
        # Process the login attempt image
        processing_result = image_service.process_login_attempt_image(
            face_image_bytes, employee_id, login_successful
        )
        
        if not processing_result['success']:
            logger.warning(f"Image processing failed during login attempt: {processing_result['error']}")
            # Continue with login flow even if image processing fails
        
        # Return appropriate response based on login result
        if login_successful:
            return {
                'statusCode': 200,
                'body': {
                    'message': 'Login successful',
                    'employee_id': employee_id,
                    'thumbnail_s3_key': processing_result.get('thumbnail_s3_key')
                }
            }
        else:
            return {
                'statusCode': 401,
                'body': {
                    'error': 'Face not recognized',
                    'message': '밝은 곳에서 다시 시도해주세요',
                    'thumbnail_s3_key': processing_result.get('thumbnail_s3_key')
                }
            }
        
    except Exception as e:
        logger.error(f"Face login Lambda error: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': 'Internal server error',
                'details': str(e)
            }
        }


# Environment configuration helper

def get_image_processing_config() -> Dict[str, str]:
    """
    Get image processing configuration from environment variables
    
    Returns:
        Dict containing configuration values
    """
    return {
        'bucket_name': os.environ.get('FACE_AUTH_BUCKET_NAME', 'face-auth-images'),
        'region': os.environ.get('AWS_REGION', 'us-east-1'),
        'thumbnail_quality': os.environ.get('THUMBNAIL_QUALITY', '85'),
        'max_image_size': os.environ.get('MAX_IMAGE_SIZE_MB', '10')
    }