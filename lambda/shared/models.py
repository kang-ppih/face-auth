"""
Face-Auth IdP System - Data Models

This module defines the core data models for the Face-Auth system:
- EmployeeInfo: Employee information extracted from ID cards
- FaceData: Face recognition data and metadata
- AuthenticationSession: User session management
- CardTemplate: ID card template configuration

Requirements: 5.5, 7.4
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import re


@dataclass
class EmployeeInfo:
    """
    Employee information extracted from ID card OCR processing
    
    Attributes:
        employee_id: 6-digit employee identifier
        name: Employee full name (Korean characters)
        department: Employee department/division
        card_type: Type of ID card used
        extracted_confidence: OCR extraction confidence score (0.0-1.0)
    """
    employee_id: str
    name: str
    department: str
    card_type: str
    extracted_confidence: Union[float, Decimal]
    
    def validate(self) -> bool:
        """
        Validate extracted employee information
        
        Returns:
            bool: True if all validation checks pass
        """
        # Employee ID must be exactly 6 digits
        if not (len(self.employee_id) == 6 and self.employee_id.isdigit()):
            return False
            
        # Name must be at least 2 Korean characters
        if len(self.name) < 2:
            return False
            
        # Check for Korean characters in name
        korean_pattern = re.compile(r'[가-힣]')
        if not korean_pattern.search(self.name):
            return False
            
        # Confidence must be above threshold
        if self.extracted_confidence <= 0.8:
            return False
            
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        data = asdict(self)
        # Convert float confidence to Decimal for DynamoDB
        if isinstance(data['extracted_confidence'], float):
            data['extracted_confidence'] = Decimal(str(data['extracted_confidence']))
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmployeeInfo':
        """Create instance from dictionary"""
        return cls(**data)


@dataclass
class FaceData:
    """
    Face recognition data and metadata
    
    Attributes:
        face_id: Amazon Rekognition face identifier
        employee_id: Associated employee identifier
        bounding_box: Face bounding box coordinates
        confidence: Face detection confidence score
        landmarks: Facial landmark points
        thumbnail_s3_key: S3 key for 200x200 thumbnail image
    """
    face_id: str
    employee_id: str
    bounding_box: Dict[str, Union[float, Decimal]]
    confidence: Union[float, Decimal]
    landmarks: List[Dict[str, Any]]
    thumbnail_s3_key: str
    
    def to_rekognition_format(self) -> Dict[str, Any]:
        """
        Convert to Amazon Rekognition API format
        
        Returns:
            Dict formatted for Rekognition API calls
        """
        return {
            'FaceId': self.face_id,
            'BoundingBox': self.bounding_box,
            'Confidence': self.confidence,
            'ExternalImageId': self.employee_id
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        data = asdict(self)
        # Convert float values to Decimal for DynamoDB
        if isinstance(data['confidence'], float):
            data['confidence'] = Decimal(str(data['confidence']))
        
        # Convert bounding box floats to Decimals
        for key, value in data['bounding_box'].items():
            if isinstance(value, float):
                data['bounding_box'][key] = Decimal(str(value))
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FaceData':
        """Create instance from dictionary"""
        return cls(**data)
    
    @classmethod
    def from_rekognition_response(cls, response: Dict[str, Any], employee_id: str, 
                                 thumbnail_s3_key: str) -> 'FaceData':
        """
        Create FaceData from Amazon Rekognition response
        
        Args:
            response: Rekognition IndexFaces response
            employee_id: Employee identifier
            thumbnail_s3_key: S3 key for thumbnail
            
        Returns:
            FaceData instance
        """
        face_record = response['FaceRecords'][0]
        face = face_record['Face']
        
        return cls(
            face_id=face['FaceId'],
            employee_id=employee_id,
            bounding_box=face['BoundingBox'],
            confidence=face['Confidence'],
            landmarks=[landmark for landmark in face.get('Landmarks', [])],
            thumbnail_s3_key=thumbnail_s3_key
        )


@dataclass
class AuthenticationSession:
    """
    Authentication session management
    
    Attributes:
        session_id: Unique session identifier
        employee_id: Authenticated employee identifier
        auth_method: Authentication method used ('face', 'emergency')
        created_at: Session creation timestamp
        expires_at: Session expiration timestamp
        cognito_token: AWS Cognito JWT token
        ip_address: Client IP address (optional)
        user_agent: Client user agent (optional)
    """
    session_id: str
    employee_id: str
    auth_method: str
    created_at: datetime
    expires_at: datetime
    cognito_token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    def is_valid(self) -> bool:
        """
        Check if session is still valid
        
        Returns:
            bool: True if session has not expired
        """
        return datetime.now() < self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        data['created_at'] = self.created_at.isoformat()
        data['expires_at'] = int(self.expires_at.timestamp())  # TTL requires epoch time
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthenticationSession':
        """Create instance from dictionary"""
        # Convert ISO format strings back to datetime objects
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        # Handle expires_at which could be int, float, or Decimal
        expires_at = data['expires_at']
        if isinstance(expires_at, Decimal):
            expires_at = float(expires_at)
        data['expires_at'] = datetime.fromtimestamp(expires_at)
        
        return cls(**data)


@dataclass
class CardTemplate:
    """
    ID card template configuration for OCR processing
    
    Attributes:
        pattern_id: Unique template identifier
        card_type: Type of card (e.g., 'standard_employee', 'contractor')
        logo_position: Logo position coordinates for card identification
        fields: List of field extraction configurations
        created_at: Template creation timestamp
        is_active: Whether template is currently active
        description: Human-readable template description
    """
    pattern_id: str
    card_type: str
    logo_position: Dict[str, int]
    fields: List[Dict[str, str]]
    created_at: datetime
    is_active: bool
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CardTemplate':
        """Create instance from dictionary"""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)
    
    def build_textract_queries(self) -> List[Dict[str, str]]:
        """
        Build Textract Query configuration from template fields
        
        Returns:
            List of Textract Query objects
        """
        queries = []
        for field in self.fields:
            queries.append({
                'Text': field['query_phrase'],
                'Alias': field['field_name']
            })
        return queries
    
    def validate_extracted_data(self, extracted_data: Dict[str, str]) -> bool:
        """
        Validate extracted data against field format expectations
        
        Args:
            extracted_data: Data extracted by Textract
            
        Returns:
            bool: True if all required fields match expected formats
        """
        for field in self.fields:
            field_name = field['field_name']
            expected_format = field.get('expected_format')
            
            if field_name not in extracted_data:
                return False
                
            if expected_format:
                value = extracted_data[field_name]
                if not re.match(expected_format, value):
                    return False
                    
        return True


@dataclass
class EmployeeFaceRecord:
    """
    DynamoDB record structure for EmployeeFaces table
    
    Attributes:
        employee_id: Partition key - employee identifier
        face_id: Amazon Rekognition face identifier
        enrollment_date: Date of face enrollment
        last_login: Last successful login timestamp
        thumbnail_s3_key: S3 key for face thumbnail
        is_active: Whether face data is active
        re_enrollment_count: Number of re-enrollments
        face_data: Embedded face recognition data
    """
    employee_id: str
    face_id: str
    enrollment_date: datetime
    last_login: Optional[datetime]
    thumbnail_s3_key: str
    is_active: bool
    re_enrollment_count: int
    face_data: FaceData
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        data = {
            'employee_id': self.employee_id,
            'face_id': self.face_id,
            'enrollment_date': self.enrollment_date.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'thumbnail_s3_key': self.thumbnail_s3_key,
            'is_active': self.is_active,
            're_enrollment_count': self.re_enrollment_count,
            'face_data': self.face_data.to_dict()
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmployeeFaceRecord':
        """Create instance from dictionary"""
        return cls(
            employee_id=data['employee_id'],
            face_id=data['face_id'],
            enrollment_date=datetime.fromisoformat(data['enrollment_date']),
            last_login=datetime.fromisoformat(data['last_login']) if data.get('last_login') else None,
            thumbnail_s3_key=data['thumbnail_s3_key'],
            is_active=data['is_active'],
            re_enrollment_count=data['re_enrollment_count'],
            face_data=FaceData.from_dict(data['face_data'])
        )


# Error response models
@dataclass
class ErrorResponse:
    """
    Standardized error response structure
    
    Attributes:
        error_code: Machine-readable error code
        user_message: User-friendly error message
        system_reason: Detailed system reason for logging
        timestamp: Error occurrence timestamp
        request_id: Request identifier for tracing
    """
    error_code: str
    user_message: str
    system_reason: str
    timestamp: datetime
    request_id: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'error': self.error_code,
            'message': self.user_message,
            'timestamp': self.timestamp.isoformat(),
            'request_id': self.request_id
        }


# Error code constants
class ErrorCodes:
    """Standard error codes for the Face-Auth system"""
    ID_CARD_FORMAT_MISMATCH = "ID_CARD_FORMAT_MISMATCH"
    REGISTRATION_INFO_MISMATCH = "REGISTRATION_INFO_MISMATCH"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    LIVENESS_FAILED = "LIVENESS_FAILED"
    FACE_NOT_FOUND = "FACE_NOT_FOUND"
    AD_CONNECTION_ERROR = "AD_CONNECTION_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    GENERIC_ERROR = "GENERIC_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"