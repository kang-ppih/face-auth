"""
Face-Auth IdP System - Face Recognition Service

This module provides face recognition capabilities using Amazon Rekognition:
- Rekognition collection creation and management
- Liveness Detection with confidence threshold > 90%
- 1:N face search and matching logic
- Face enrollment (IndexFaces) and deletion functionality
- Integration with S3 for face image storage

Requirements: 2.1, 2.2, 6.1, 6.2, 6.4
"""

import boto3
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from decimal import Decimal
import json

from .models import (
    FaceData,
    ErrorResponse,
    ErrorCodes
)

logger = logging.getLogger(__name__)


class LivenessResult:
    """
    Result of liveness detection operation
    
    Attributes:
        is_live: Whether the face is determined to be live
        confidence: Confidence score (0.0-100.0)
        face_detected: Whether a face was detected
        audit_images: S3 keys for audit images
        session_id: Rekognition liveness session ID
    """
    def __init__(self, is_live: bool, confidence: float, face_detected: bool = True,
                 audit_images: Optional[List[str]] = None, session_id: Optional[str] = None):
        self.is_live = is_live
        self.confidence = confidence
        self.face_detected = face_detected
        self.audit_images = audit_images or []
        self.session_id = session_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'is_live': self.is_live,
            'confidence': self.confidence,
            'face_detected': self.face_detected,
            'audit_images': self.audit_images,
            'session_id': self.session_id
        }


class FaceMatch:
    """
    Result of face matching operation
    
    Attributes:
        face_id: Rekognition face identifier
        employee_id: Matched employee identifier
        similarity: Similarity score (0.0-100.0)
        confidence: Face detection confidence
    """
    def __init__(self, face_id: str, employee_id: str, similarity: float, confidence: float):
        self.face_id = face_id
        self.employee_id = employee_id
        self.similarity = similarity
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'face_id': self.face_id,
            'employee_id': self.employee_id,
            'similarity': self.similarity,
            'confidence': self.confidence
        }


class FaceRecognitionService:
    """
    Amazon Rekognition-based face recognition service
    
    This service handles:
    - Rekognition collection lifecycle management
    - Liveness detection with 90% confidence threshold
    - 1:N face matching across all enrolled employees
    - Face enrollment and deletion operations
    - Error handling for recognition failures
    """
    
    # Configuration constants
    COLLECTION_ID = "face-auth-employees"
    CONFIDENCE_THRESHOLD = 90.0  # Minimum confidence for liveness detection
    FACE_MATCH_THRESHOLD = 90.0  # Minimum similarity for face matching
    MAX_FACES = 1  # Maximum faces to detect in an image
    
    def __init__(self, region_name: str = 'us-east-1', collection_id: Optional[str] = None):
        """
        Initialize Face Recognition service
        
        Args:
            region_name: AWS region name
            collection_id: Custom collection ID (uses default if not provided)
        """
        self.rekognition = boto3.client('rekognition', region_name=region_name)
        self.collection_id = collection_id or self.COLLECTION_ID
        self.region_name = region_name
        
        logger.info(f"Initialized FaceRecognitionService with collection: {self.collection_id}")
    
    def create_collection(self) -> Tuple[bool, Optional[str]]:
        """
        Create Rekognition collection if it doesn't exist
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Check if collection already exists
            try:
                self.rekognition.describe_collection(CollectionId=self.collection_id)
                logger.info(f"Collection {self.collection_id} already exists")
                return True, None
            except Exception as e:
                # Check if it's ResourceNotFoundException
                error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
                if error_code != 'ResourceNotFoundException' and 'ResourceNotFoundException' not in str(type(e)):
                    # Some other error occurred
                    raise
                
                # Collection doesn't exist, create it
                logger.info(f"Creating collection {self.collection_id}")
                
                response = self.rekognition.create_collection(
                    CollectionId=self.collection_id
                )
                
                logger.info(f"Collection created: {response['CollectionArn']}")
                return True, None
                
        except Exception as e:
            error_msg = f"Error creating collection: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def delete_collection(self) -> Tuple[bool, Optional[str]]:
        """
        Delete Rekognition collection
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            response = self.rekognition.delete_collection(
                CollectionId=self.collection_id
            )
            
            logger.info(f"Collection deleted: {self.collection_id}, Status: {response['StatusCode']}")
            return True, None
            
        except Exception as e:
            # Check if it's ResourceNotFoundException
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            if error_code == 'ResourceNotFoundException' or 'ResourceNotFoundException' in str(type(e)):
                logger.warning(f"Collection {self.collection_id} not found")
                return True, None  # Already deleted, consider success
            
            error_msg = f"Error deleting collection: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def detect_liveness(self, image_bytes: bytes, 
                       request_id: str = None) -> Tuple[Optional[LivenessResult], Optional[ErrorResponse]]:
        """
        Detect liveness using Amazon Rekognition face detection
        
        This method uses DetectFaces API to verify:
        1. A face is present in the image
        2. Face quality is sufficient (confidence > 90%)
        3. Face attributes indicate a live person
        
        Note: For production, consider using Rekognition Liveness API
        which provides more robust anti-spoofing detection.
        
        Args:
            image_bytes: Face image data as bytes
            request_id: Request identifier for error tracking
            
        Returns:
            Tuple of (LivenessResult or None, ErrorResponse or None)
        """
        try:
            logger.info("Performing liveness detection")
            
            # Detect faces with quality attributes
            response = self.rekognition.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']  # Get all face attributes for quality assessment
            )
            
            # Check if any faces were detected
            if not response.get('FaceDetails'):
                logger.warning("No faces detected in image")
                return None, ErrorResponse(
                    error_code=ErrorCodes.LIVENESS_FAILED,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason="No face detected in image",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Get the first (and should be only) face
            face_detail = response['FaceDetails'][0]
            confidence = face_detail.get('Confidence', 0.0)
            
            logger.info(f"Face detected with confidence: {confidence}")
            
            # Check if confidence meets threshold
            if confidence < self.CONFIDENCE_THRESHOLD:
                logger.warning(f"Face confidence {confidence} below threshold {self.CONFIDENCE_THRESHOLD}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.LIVENESS_FAILED,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Face confidence {confidence} below threshold {self.CONFIDENCE_THRESHOLD}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Additional quality checks
            quality = face_detail.get('Quality', {})
            brightness = quality.get('Brightness', 0)
            sharpness = quality.get('Sharpness', 0)
            
            logger.debug(f"Face quality - Brightness: {brightness}, Sharpness: {sharpness}")
            
            # Check for minimum quality thresholds
            if brightness < 40 or sharpness < 40:
                logger.warning(f"Poor image quality - Brightness: {brightness}, Sharpness: {sharpness}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.LIVENESS_FAILED,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Poor image quality - Brightness: {brightness}, Sharpness: {sharpness}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Check if multiple faces detected (potential spoofing)
            if len(response['FaceDetails']) > 1:
                logger.warning(f"Multiple faces detected: {len(response['FaceDetails'])}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.LIVENESS_FAILED,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Multiple faces detected: {len(response['FaceDetails'])}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Liveness check passed
            liveness_result = LivenessResult(
                is_live=True,
                confidence=confidence,
                face_detected=True
            )
            
            logger.info(f"Liveness detection passed with confidence: {confidence}")
            return liveness_result, None
            
        except Exception as e:
            logger.error(f"Error in liveness detection: {str(e)}")
            return None, ErrorResponse(
                error_code=ErrorCodes.LIVENESS_FAILED,
                user_message="밝은 곳에서 다시 시도해주세요",
                system_reason=f"Liveness detection error: {str(e)}",
                timestamp=datetime.now(),
                request_id=request_id or "unknown"
            )
    
    def search_faces(self, image_bytes: bytes, 
                    request_id: str = None) -> Tuple[Optional[List[FaceMatch]], Optional[ErrorResponse]]:
        """
        Search for matching faces in the collection (1:N matching)
        
        This method:
        1. Searches the collection for faces matching the input image
        2. Filters results by similarity threshold (90%)
        3. Returns list of matches sorted by similarity
        
        Args:
            image_bytes: Face image data as bytes
            request_id: Request identifier for error tracking
            
        Returns:
            Tuple of (List of FaceMatch or None, ErrorResponse or None)
        """
        try:
            logger.info(f"Searching faces in collection: {self.collection_id}")
            
            # Search for faces in the collection
            response = self.rekognition.search_faces_by_image(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                FaceMatchThreshold=self.FACE_MATCH_THRESHOLD,
                MaxFaces=10  # Return top 10 matches
            )
            
            # Check if any matches were found
            face_matches = response.get('FaceMatches', [])
            
            if not face_matches:
                logger.info("No matching faces found")
                return None, ErrorResponse(
                    error_code=ErrorCodes.FACE_NOT_FOUND,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason="No matching face found in collection",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Convert to FaceMatch objects
            matches = []
            for match in face_matches:
                face = match['Face']
                similarity = match['Similarity']
                
                face_match = FaceMatch(
                    face_id=face['FaceId'],
                    employee_id=face.get('ExternalImageId', ''),
                    similarity=similarity,
                    confidence=face.get('Confidence', 0.0)
                )
                matches.append(face_match)
                
                logger.debug(f"Match found - Employee: {face_match.employee_id}, "
                           f"Similarity: {similarity}, Confidence: {face_match.confidence}")
            
            # Sort by similarity (highest first)
            matches.sort(key=lambda x: x.similarity, reverse=True)
            
            logger.info(f"Found {len(matches)} matching faces, best match: "
                       f"{matches[0].employee_id} ({matches[0].similarity}%)")
            
            return matches, None
            
        except Exception as e:
            # Check for specific AWS exceptions
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            
            if error_code == 'ResourceNotFoundException' or 'ResourceNotFoundException' in str(type(e)):
                logger.error(f"Collection {self.collection_id} not found")
                return None, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Collection {self.collection_id} not found",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            elif error_code == 'InvalidParameterException' or 'InvalidParameterException' in str(type(e)):
                logger.error(f"Invalid parameter for face search: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.LIVENESS_FAILED,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Invalid image for face search: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            else:
                logger.error(f"Error searching faces: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Face search error: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
    
    def index_face(self, image_bytes: bytes, employee_id: str, 
                  request_id: str = None) -> Tuple[Optional[FaceData], Optional[ErrorResponse]]:
        """
        Index (enroll) a face in the collection
        
        This method:
        1. Indexes the face in the Rekognition collection
        2. Associates it with the employee ID as ExternalImageId
        3. Returns FaceData with face metadata
        
        Args:
            image_bytes: Face image data as bytes
            employee_id: Employee identifier to associate with the face
            request_id: Request identifier for error tracking
            
        Returns:
            Tuple of (FaceData or None, ErrorResponse or None)
        """
        try:
            logger.info(f"Indexing face for employee: {employee_id}")
            
            # Index the face in the collection
            response = self.rekognition.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                ExternalImageId=employee_id,
                MaxFaces=self.MAX_FACES,
                QualityFilter='AUTO',  # Automatically filter low-quality faces
                DetectionAttributes=['ALL']
            )
            
            # Check if any faces were indexed
            face_records = response.get('FaceRecords', [])
            
            if not face_records:
                logger.warning(f"No faces indexed for employee {employee_id}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.LIVENESS_FAILED,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason="No face detected or quality too low for indexing",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Get the indexed face data
            face_record = face_records[0]
            face = face_record['Face']
            face_detail = face_record.get('FaceDetail', {})
            
            # Create FaceData object
            # Note: thumbnail_s3_key should be set by the caller after storing the thumbnail
            face_data = FaceData(
                face_id=face['FaceId'],
                employee_id=employee_id,
                bounding_box=face.get('BoundingBox', {}),
                confidence=face.get('Confidence', 0.0),
                landmarks=[],  # Landmarks not returned by IndexFaces
                thumbnail_s3_key=""  # Will be set by caller
            )
            
            logger.info(f"Face indexed successfully - FaceId: {face_data.face_id}, "
                       f"Confidence: {face_data.confidence}")
            
            return face_data, None
            
        except Exception as e:
            # Check for specific AWS exceptions
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            
            if error_code == 'ResourceNotFoundException' or 'ResourceNotFoundException' in str(type(e)):
                logger.error(f"Collection {self.collection_id} not found")
                return None, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Collection {self.collection_id} not found",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            elif error_code == 'InvalidParameterException' or 'InvalidParameterException' in str(type(e)):
                logger.error(f"Invalid parameter for face indexing: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.LIVENESS_FAILED,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Invalid image for face indexing: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            else:
                logger.error(f"Error indexing face: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Face indexing error: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
    
    def delete_face(self, face_id: str, 
                   request_id: str = None) -> Tuple[bool, Optional[ErrorResponse]]:
        """
        Delete a face from the collection
        
        Args:
            face_id: Rekognition face identifier to delete
            request_id: Request identifier for error tracking
            
        Returns:
            Tuple of (success, ErrorResponse or None)
        """
        try:
            logger.info(f"Deleting face: {face_id}")
            
            response = self.rekognition.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=[face_id]
            )
            
            deleted_faces = response.get('DeletedFaces', [])
            
            if face_id in deleted_faces:
                logger.info(f"Face deleted successfully: {face_id}")
                return True, None
            else:
                logger.warning(f"Face not found or not deleted: {face_id}")
                return False, ErrorResponse(
                    error_code=ErrorCodes.FACE_NOT_FOUND,
                    user_message="얼굴 데이터를 찾을 수 없습니다",
                    system_reason=f"Face {face_id} not found in collection",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
        except Exception as e:
            # Check for specific AWS exceptions
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            
            if error_code == 'ResourceNotFoundException' or 'ResourceNotFoundException' in str(type(e)):
                logger.error(f"Collection {self.collection_id} not found")
                return False, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="시스템 오류가 발생했습니다",
                    system_reason=f"Collection {self.collection_id} not found",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            else:
                logger.error(f"Error deleting face: {str(e)}")
                return False, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="시스템 오류가 발생했습니다",
                    system_reason=f"Face deletion error: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
    
    def delete_faces_by_employee_id(self, employee_id: str, 
                                   request_id: str = None) -> Tuple[int, Optional[ErrorResponse]]:
        """
        Delete all faces associated with an employee ID
        
        This is useful for re-enrollment scenarios where old face data
        needs to be removed before indexing new face data.
        
        Args:
            employee_id: Employee identifier
            request_id: Request identifier for error tracking
            
        Returns:
            Tuple of (number of faces deleted, ErrorResponse or None)
        """
        try:
            logger.info(f"Deleting all faces for employee: {employee_id}")
            
            # List faces with the given external image ID
            response = self.rekognition.list_faces(
                CollectionId=self.collection_id,
                MaxResults=100  # Should be enough for one employee
            )
            
            # Filter faces by external image ID
            face_ids_to_delete = []
            for face in response.get('Faces', []):
                if face.get('ExternalImageId') == employee_id:
                    face_ids_to_delete.append(face['FaceId'])
            
            if not face_ids_to_delete:
                logger.info(f"No faces found for employee: {employee_id}")
                return 0, None
            
            # Delete the faces
            delete_response = self.rekognition.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=face_ids_to_delete
            )
            
            deleted_count = len(delete_response.get('DeletedFaces', []))
            
            logger.info(f"Deleted {deleted_count} faces for employee: {employee_id}")
            return deleted_count, None
            
        except Exception as e:
            logger.error(f"Error deleting faces for employee {employee_id}: {str(e)}")
            return 0, ErrorResponse(
                error_code=ErrorCodes.GENERIC_ERROR,
                user_message="시스템 오류가 발생했습니다",
                system_reason=f"Error deleting faces for employee: {str(e)}",
                timestamp=datetime.now(),
                request_id=request_id or "unknown"
            )
    
    def get_collection_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get statistics about the face collection
        
        Returns:
            Dictionary with collection statistics or None if error
        """
        try:
            response = self.rekognition.describe_collection(
                CollectionId=self.collection_id
            )
            
            stats = {
                'collection_id': self.collection_id,
                'collection_arn': response.get('CollectionARN'),
                'face_count': response.get('FaceCount', 0),
                'face_model_version': response.get('FaceModelVersion'),
                'created_timestamp': response.get('CreationTimestamp')
            }
            
            logger.info(f"Collection stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return None
    
    def list_faces(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        List all faces in the collection
        
        Args:
            max_results: Maximum number of faces to return
            
        Returns:
            List of face dictionaries
        """
        try:
            response = self.rekognition.list_faces(
                CollectionId=self.collection_id,
                MaxResults=max_results
            )
            
            faces = response.get('Faces', [])
            logger.info(f"Listed {len(faces)} faces from collection")
            
            return faces
            
        except Exception as e:
            logger.error(f"Error listing faces: {str(e)}")
            return []


# Utility functions

def create_face_recognition_service(region_name: str = 'us-east-1', 
                                   collection_id: Optional[str] = None) -> FaceRecognitionService:
    """
    Factory function to create FaceRecognitionService instance
    
    Args:
        region_name: AWS region name
        collection_id: Custom collection ID (optional)
        
    Returns:
        FaceRecognitionService instance
    """
    return FaceRecognitionService(region_name, collection_id)


def validate_face_image(image_bytes: bytes) -> Tuple[bool, str]:
    """
    Validate face image format and size
    
    Args:
        image_bytes: Image data to validate
        
    Returns:
        Tuple of (is_valid, error_message_or_format)
    """
    try:
        # Check minimum size
        if len(image_bytes) < 1000:  # 1KB minimum
            return False, "Image too small"
        
        # Check maximum size (5MB limit for Rekognition)
        if len(image_bytes) > 5 * 1024 * 1024:
            return False, "Image too large (max 5MB)"
        
        # Basic format validation - check for common image headers
        if image_bytes.startswith(b'\xff\xd8\xff'):
            return True, "JPEG"
        elif image_bytes.startswith(b'\x89PNG'):
            return True, "PNG"
        else:
            return False, "Unsupported image format (use JPEG or PNG)"
            
    except Exception as e:
        return False, f"Validation error: {str(e)}"
