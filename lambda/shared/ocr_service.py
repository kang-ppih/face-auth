"""
Face-Auth IdP System - OCR Service

This module provides OCR (Optical Character Recognition) capabilities using Amazon Rekognition
for processing employee ID cards. The service supports:
- Text detection using Rekognition DetectText API
- Employee information extraction and validation
- Multiple card template support
- Error handling for format mismatches and extraction failures
- Fast processing with Rekognition (typically <5 seconds)

Requirements: 1.2, 7.1, 7.2, 7.6
Version: 2.0.0 - Switched from Textract to Rekognition for faster processing
"""

import boto3
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re
import json

from .models import (
    EmployeeInfo, 
    CardTemplate, 
    ErrorResponse, 
    ErrorCodes
)
from .dynamodb_service import DynamoDBService

logger = logging.getLogger(__name__)


class OCRService:
    """
    Amazon Rekognition-based OCR service for employee ID card processing
    
    This service handles:
    - Text detection using Rekognition DetectText
    - Employee information extraction from ID cards
    - Card template matching and validation
    - Error handling for unsupported card formats
    """
    
    def __init__(self, region_name: str = 'ap-northeast-1'):
        """
        Initialize OCR service
        
        Args:
            region_name: AWS region name
        """
        # Configure Rekognition client with timeout settings
        from botocore.config import Config
        
        config = Config(
            read_timeout=10,  # 10 seconds read timeout
            connect_timeout=5,  # 5 seconds connect timeout
            retries={'max_attempts': 1}  # No retries for faster failure
        )
        
        self.rekognition = boto3.client('rekognition', region_name=region_name, config=config)
        self.db_service = DynamoDBService(region_name)
        self.confidence_threshold = 80.0  # Minimum confidence for text detection (80%)
        
    def initialize_db_service(self, card_templates_table_name: str, 
                            employee_faces_table_name: str,
                            auth_sessions_table_name: str):
        """
        Initialize DynamoDB service with table names
        
        Args:
            card_templates_table_name: Name of CardTemplates table
            employee_faces_table_name: Name of EmployeeFaces table  
            auth_sessions_table_name: Name of AuthSessions table
        """
        self.db_service.initialize_tables(
            card_templates_table_name,
            employee_faces_table_name, 
            auth_sessions_table_name
        )
    
    def extract_id_card_info(self, image_bytes: bytes, 
                           request_id: str = None) -> Tuple[Optional[EmployeeInfo], Optional[ErrorResponse]]:
        """
        Extract employee information from ID card image using card templates
        
        This method:
        1. Retrieves all active card templates from DynamoDB
        2. Attempts to match the card against each template
        3. Extracts employee information using the matching template
        4. Validates the extracted information
        
        Args:
            image_bytes: ID card image data as bytes
            request_id: Request identifier for error tracking
            
        Returns:
            Tuple of (EmployeeInfo or None, ErrorResponse or None)
        """
        try:
            # Get all active card templates
            templates = self.db_service.get_active_card_templates()
            
            if not templates:
                logger.error("No active card templates found")
                return None, ErrorResponse(
                    error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                    user_message="社員証規格不一致",
                    system_reason="No active card templates available",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Try each template until one matches
            for template in templates:
                logger.info(f"Attempting extraction with template: {template.pattern_id}")
                
                employee_info, error = self._extract_with_template(
                    image_bytes, template, request_id
                )
                
                if employee_info:
                    logger.info(f"Successfully extracted info with template: {template.pattern_id}")
                    return employee_info, None
                    
                # Log template-specific failure but continue trying other templates
                if error:
                    logger.debug(f"Template {template.pattern_id} failed: {error.system_reason}")
            
            # No template matched
            logger.warning("No card template matched the provided image")
            return None, ErrorResponse(
                error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                user_message="社員証規格不一致",
                system_reason="Image does not match any active card template",
                timestamp=datetime.now(),
                request_id=request_id or "unknown"
            )
            
        except Exception as e:
            logger.error(f"Error in OCR extraction: {str(e)}")
            return None, ErrorResponse(
                error_code=ErrorCodes.GENERIC_ERROR,
                user_message="明るい場所で再度お試しください",
                system_reason=f"OCR service error: {str(e)}",
                timestamp=datetime.now(),
                request_id=request_id or "unknown"
            )
    
    def _extract_with_template(self, image_bytes: bytes, template: CardTemplate, 
                             request_id: str = None) -> Tuple[Optional[EmployeeInfo], Optional[ErrorResponse]]:
        """
        Extract employee information using Rekognition text detection
        
        Args:
            image_bytes: ID card image data
            template: CardTemplate to use for extraction
            request_id: Request identifier for error tracking
            
        Returns:
            Tuple of (EmployeeInfo or None, ErrorResponse or None)
        """
        try:
            # Call Amazon Rekognition DetectText
            logger.info(f"Calling Rekognition DetectText for template {template.pattern_id}")
            
            import time
            start_time = time.time()
            
            try:
                response = self.rekognition.detect_text(
                    Image={'Bytes': image_bytes}
                )
                
                elapsed_time = time.time() - start_time
                logger.info(f"Rekognition completed in {elapsed_time:.2f} seconds")
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"Rekognition failed after {elapsed_time:.2f} seconds: {str(e)}")
                
                # Check if it's a timeout
                if 'timeout' in str(e).lower() or 'timed out' in str(e).lower():
                    return None, ErrorResponse(
                        error_code=ErrorCodes.TIMEOUT_ERROR,
                        user_message="処理時間が超過しました",
                        system_reason=f"Rekognition timeout after {elapsed_time:.2f}s",
                        timestamp=datetime.now(),
                        request_id=request_id or "unknown"
                    )
                raise
            
            # Parse Rekognition response
            extracted_data = self._parse_rekognition_response(response, template)
            
            # Early exit if no data extracted
            if not extracted_data:
                logger.warning(f"No data extracted with template {template.pattern_id}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                    user_message="社員証規格不一致",
                    system_reason=f"Template {template.pattern_id} extracted no valid data",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Check if required fields are present
            required_fields = ['employee_id', 'employee_name']
            missing_fields = [f for f in required_fields if f not in extracted_data or not extracted_data[f]]
            
            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                    user_message="社員証規格不一致",
                    system_reason=f"Missing required fields: {', '.join(missing_fields)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Validate extracted data against template expectations
            if not template.validate_extracted_data(extracted_data):
                logger.debug(f"Extracted data failed validation for template {template.pattern_id}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                    user_message="社員証規格不一致",
                    system_reason=f"Template {template.pattern_id} data validation failed",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Create EmployeeInfo from extracted data
            employee_info = self._create_employee_info(extracted_data, template)
            
            # Final validation of EmployeeInfo
            if not employee_info.validate():
                logger.warning(f"EmployeeInfo validation failed for template {template.pattern_id}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                    user_message="社員証規格不一致",
                    system_reason=f"Employee info validation failed: {extracted_data}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            return employee_info, None
            
        except Exception as e:
            # Check if it's a Rekognition-specific exception
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            
            if error_code == 'InvalidParameterException':
                logger.error(f"Invalid Rekognition parameters for template {template.pattern_id}: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="明るい場所で再度お試しください",
                    system_reason=f"Rekognition parameter error: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            elif error_code == 'InvalidImageFormatException':
                logger.error(f"Invalid image format for template {template.pattern_id}: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                    user_message="社員証規格不一致",
                    system_reason=f"Invalid image format: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            else:
                logger.error(f"Error extracting with template {template.pattern_id}: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="明るい場所で再度お試しください",
                    system_reason=f"Template extraction error: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
    
    def _parse_rekognition_response(self, response: Dict[str, Any], 
                                   template: CardTemplate) -> Dict[str, str]:
        """
        Parse Rekognition DetectText response to extract employee information
        
        Args:
            response: Rekognition detect_text response
            template: CardTemplate used for extraction (for validation)
            
        Returns:
            Dictionary mapping field names to extracted values
        """
        extracted_data = {}
        
        # Parse text detections from Rekognition response
        if 'TextDetections' not in response:
            logger.warning("No text detections found in Rekognition response")
            return extracted_data
        
        # Collect all detected text with confidence above threshold
        detected_texts = []
        for detection in response['TextDetections']:
            if detection['Type'] == 'LINE':  # Use LINE type for better context
                confidence = detection.get('Confidence', 0.0)
                if confidence >= self.confidence_threshold:
                    text = detection.get('DetectedText', '').strip()
                    if text:
                        detected_texts.append(text)
                        logger.debug(f"Detected text: '{text}' (confidence: {confidence:.2f}%)")
        
        logger.info(f"Found {len(detected_texts)} text lines above confidence threshold")
        
        # Extract employee ID (7 digits)
        employee_id = self._extract_employee_id(detected_texts)
        if employee_id:
            extracted_data['employee_id'] = employee_id
            logger.info(f"Extracted employee_id: {employee_id}")
        
        # Extract employee name (Japanese characters)
        employee_name = self._extract_japanese_name(detected_texts)
        if employee_name:
            extracted_data['employee_name'] = employee_name
            logger.info(f"Extracted employee_name: {employee_name}")
        
        # Extract department (optional - Japanese text that's not the name)
        department = self._extract_department(detected_texts, employee_name)
        if department:
            extracted_data['department'] = department
            logger.info(f"Extracted department: {department}")
        
        logger.info(f"Extracted {len(extracted_data)} fields from Rekognition response")
        return extracted_data
    
    def _extract_employee_id(self, texts: List[str]) -> Optional[str]:
        """
        Extract 7-digit employee ID from detected texts
        
        Args:
            texts: List of detected text strings
            
        Returns:
            Employee ID string or None
        """
        # Pattern for 7 consecutive digits
        pattern = re.compile(r'\b(\d{7})\b')
        
        for text in texts:
            match = pattern.search(text)
            if match:
                employee_id = match.group(1)
                logger.debug(f"Found employee ID: {employee_id}")
                return employee_id
        
        logger.warning("No 7-digit employee ID found in detected texts")
        return None
    
    def _extract_japanese_name(self, texts: List[str]) -> Optional[str]:
        """
        Extract name from detected texts (Japanese or English)
        
        Args:
            texts: List of detected text strings
            
        Returns:
            Name string or None
        """
        # Pattern for Japanese characters (Hiragana, Katakana, Kanji)
        # Names are typically 2-5 characters
        japanese_pattern = re.compile(r'^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{2,5}$')
        
        # Pattern for English names (2-3 words, capitalized)
        english_pattern = re.compile(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+){0,2}$')
        
        for text in texts:
            # Clean the text (remove spaces and special characters)
            cleaned_text = text.strip()
            
            # Try Japanese pattern first
            if japanese_pattern.match(cleaned_text):
                logger.debug(f"Found Japanese name: {cleaned_text}")
                return cleaned_text
            
            # Try English pattern
            if english_pattern.match(cleaned_text):
                # Skip common company names
                skip_words = ['Pan', 'Pacific', 'International', 'Holdings', 'Corporation', 'Company', 'Ltd']
                if not any(word in cleaned_text for word in skip_words):
                    logger.debug(f"Found English name: {cleaned_text}")
                    return cleaned_text
        
        logger.warning("No name found in detected texts")
        return None
    
    def _extract_department(self, texts: List[str], exclude_name: Optional[str]) -> Optional[str]:
        """
        Extract department name from detected texts
        
        Args:
            texts: List of detected text strings
            exclude_name: Employee name to exclude from department search
            
        Returns:
            Department name string or None
        """
        # Pattern for Japanese text (longer than name, typically 3-10 characters)
        pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{3,10}')
        
        for text in texts:
            cleaned_text = text.strip()
            
            # Skip if it's the employee name
            if exclude_name and cleaned_text == exclude_name:
                continue
            
            # Skip if it contains digits (likely not a department name)
            if re.search(r'\d', cleaned_text):
                continue
            
            if pattern.match(cleaned_text):
                logger.debug(f"Found potential department: {cleaned_text}")
                return cleaned_text
        
        logger.debug("No department name found in detected texts")
        return None
    
    def _create_employee_info(self, extracted_data: Dict[str, str], 
                            template: CardTemplate) -> EmployeeInfo:
        """
        Create EmployeeInfo instance from extracted data
        
        Args:
            extracted_data: Data extracted from Textract
            template: CardTemplate used for extraction
            
        Returns:
            EmployeeInfo instance
        """
        # Calculate overall extraction confidence
        confidence = self._calculate_extraction_confidence(extracted_data, template)
        
        return EmployeeInfo(
            employee_id=extracted_data.get('employee_id', ''),
            name=extracted_data.get('employee_name', ''),
            department=extracted_data.get('department', extracted_data.get('company', '')),
            card_type=template.card_type,
            extracted_confidence=confidence
        )
    
    def _calculate_extraction_confidence(self, extracted_data: Dict[str, str], 
                                       template: CardTemplate) -> float:
        """
        Calculate overall extraction confidence based on required fields
        
        Args:
            extracted_data: Data extracted from Textract
            template: CardTemplate used for extraction
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        required_fields = ['employee_id', 'employee_name']
        extracted_required = sum(1 for field in required_fields if field in extracted_data and extracted_data[field])
        total_required = len(required_fields)
        
        # Base confidence from required fields
        base_confidence = extracted_required / total_required if total_required > 0 else 0.0
        
        # Bonus for additional fields (only if all required fields are present)
        if base_confidence == 1.0:
            total_fields = len(template.fields)
            extracted_total = len(extracted_data)
            # Bonus is capped to not exceed 0.2
            bonus = min((extracted_total - total_required) / max(total_fields - total_required, 1), 1.0) * 0.2
            final_confidence = min(base_confidence + bonus, 1.0)
        else:
            final_confidence = base_confidence
        
        logger.debug(f"Extraction confidence: {final_confidence} (required: {extracted_required}/{total_required}, total: {len(extracted_data)}/{len(template.fields)})")
        
        return final_confidence
    
    def get_card_template_by_id(self, pattern_id: str) -> Optional[CardTemplate]:
        """
        Retrieve a specific card template by pattern ID
        
        Args:
            pattern_id: Template pattern identifier
            
        Returns:
            CardTemplate instance or None if not found
        """
        try:
            return self.db_service.get_card_template(pattern_id)
        except Exception as e:
            logger.error(f"Error retrieving card template {pattern_id}: {str(e)}")
            return None
    
    def get_active_card_templates(self) -> List[CardTemplate]:
        """
        Retrieve all active card templates
        
        Returns:
            List of active CardTemplate instances
        """
        try:
            return self.db_service.get_active_card_templates()
        except Exception as e:
            logger.error(f"Error retrieving active card templates: {str(e)}")
            return []
    
    def validate_image_for_ocr(self, image_bytes: bytes) -> Tuple[bool, str]:
        """
        Validate image format and size for OCR processing
        
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
            elif image_bytes.startswith(b'GIF8'):
                return True, "GIF"
            elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:12]:
                return True, "WEBP"
            else:
                return False, "Unsupported image format"
                
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def test_template_extraction(self, template_id: str, image_bytes: bytes) -> Dict[str, Any]:
        """
        Test extraction with a specific template (for debugging/testing)
        
        Args:
            template_id: Template pattern identifier
            image_bytes: Test image data
            
        Returns:
            Dictionary with extraction results and debug information
        """
        try:
            template = self.get_card_template_by_id(template_id)
            if not template:
                return {
                    'success': False,
                    'error': f'Template {template_id} not found'
                }
            
            employee_info, error = self._extract_with_template(image_bytes, template, f"test_{template_id}")
            
            return {
                'success': employee_info is not None,
                'template_id': template_id,
                'employee_info': employee_info.to_dict() if employee_info else None,
                'error': error.to_dict() if error else None,
                'template_fields': len(template.fields)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Test extraction failed: {str(e)}'
            }


# Utility functions for OCR operations

def create_ocr_service(region_name: str = 'ap-northeast-1') -> OCRService:
    """
    Factory function to create OCRService instance
    
    Args:
        region_name: AWS region name
        
    Returns:
        OCRService instance
    """
    return OCRService(region_name)


def validate_employee_id_format(employee_id: str) -> bool:
    """
    Validate employee ID format according to system requirements
    
    Args:
        employee_id: Employee identifier to validate
        
    Returns:
        bool: True if format is valid (7 digits or contractor format)
    """
    # Standard employee: 7 digits
    if re.match(r'^\d{7}$', employee_id):
        return True
    
    # Contractor: C followed by 5 digits
    if re.match(r'^C\d{5}$', employee_id):
        return True
    
    return False


def validate_japanese_name(name: str) -> bool:
    """
    Validate Japanese name format
    
    Args:
        name: Name to validate
        
    Returns:
        bool: True if name contains Japanese characters and is valid length
    """
    if len(name) < 2 or len(name) > 5:  # Japanese names are typically 2-5 characters
        return False
    
    # Check that all characters are Japanese (Hiragana, Katakana, or Kanji)
    japanese_pattern = re.compile(r'^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+$')
    return bool(japanese_pattern.match(name))