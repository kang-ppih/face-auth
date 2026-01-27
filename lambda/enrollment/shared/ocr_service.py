"""
Face-Auth IdP System - OCR Service

This module provides OCR (Optical Character Recognition) capabilities using Amazon Textract
for processing employee ID cards. The service supports:
- Dynamic Textract Query configuration based on card templates
- Employee information extraction and validation
- Multiple card template support with logo-based identification
- Error handling for format mismatches and extraction failures

Requirements: 1.2, 7.1, 7.2, 7.6
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
    Amazon Textract-based OCR service for employee ID card processing
    
    This service handles:
    - Dynamic Textract Query configuration based on card templates
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
        self.textract = boto3.client('textract', region_name=region_name)
        self.db_service = DynamoDBService(region_name)
        self.confidence_threshold = 0.8  # Minimum confidence for text extraction
        
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
                user_message="밝은 곳에서 다시 시도해주세요",
                system_reason=f"OCR service error: {str(e)}",
                timestamp=datetime.now(),
                request_id=request_id or "unknown"
            )
    
    def _extract_with_template(self, image_bytes: bytes, template: CardTemplate, 
                             request_id: str = None) -> Tuple[Optional[EmployeeInfo], Optional[ErrorResponse]]:
        """
        Extract employee information using a specific card template
        
        Args:
            image_bytes: ID card image data
            template: CardTemplate to use for extraction
            request_id: Request identifier for error tracking
            
        Returns:
            Tuple of (EmployeeInfo or None, ErrorResponse or None)
        """
        try:
            # Build Textract queries from template
            queries = self._build_queries_from_template(template)
            
            if not queries:
                logger.warning(f"No queries built for template {template.pattern_id}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Template {template.pattern_id} has no valid fields",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Call Amazon Textract with dynamic queries
            logger.info(f"Calling Textract with {len(queries)} queries for template {template.pattern_id}")
            
            response = self.textract.analyze_document(
                Document={'Bytes': image_bytes},
                FeatureTypes=['QUERIES'],
                QueriesConfig={'Queries': queries}
            )
            
            # Parse Textract response
            extracted_data = self._parse_textract_response(response, template)
            
            if not extracted_data:
                logger.debug(f"No data extracted with template {template.pattern_id}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                    user_message="사원증 규격 불일치",
                    system_reason=f"Template {template.pattern_id} extracted no valid data",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            # Validate extracted data against template expectations
            if not template.validate_extracted_data(extracted_data):
                logger.debug(f"Extracted data failed validation for template {template.pattern_id}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                    user_message="사원증 규격 불일치",
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
                    user_message="사원증 규격 불일치",
                    system_reason=f"Employee info validation failed: {extracted_data}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            
            return employee_info, None
            
        except Exception as e:
            # Check if it's a Textract-specific exception
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            
            if error_code == 'InvalidParameterException':
                logger.error(f"Invalid Textract parameters for template {template.pattern_id}: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Textract parameter error: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            elif error_code == 'UnsupportedDocumentException':
                logger.error(f"Unsupported document format for template {template.pattern_id}: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
                    user_message="사원증 규격 불일치",
                    system_reason=f"Unsupported document format: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
            else:
                logger.error(f"Error extracting with template {template.pattern_id}: {str(e)}")
                return None, ErrorResponse(
                    error_code=ErrorCodes.GENERIC_ERROR,
                    user_message="밝은 곳에서 다시 시도해주세요",
                    system_reason=f"Template extraction error: {str(e)}",
                    timestamp=datetime.now(),
                    request_id=request_id or "unknown"
                )
    
    def _build_queries_from_template(self, template: CardTemplate) -> List[Dict[str, str]]:
        """
        Build Textract Query configuration from card template fields
        
        Args:
            template: CardTemplate containing field definitions
            
        Returns:
            List of Textract Query objects
        """
        queries = []
        
        for field in template.fields:
            if 'field_name' in field and 'query_phrase' in field:
                query = {
                    'Text': field['query_phrase'],
                    'Alias': field['field_name']
                }
                queries.append(query)
                logger.debug(f"Built query: {field['field_name']} -> {field['query_phrase']}")
            else:
                logger.warning(f"Invalid field configuration in template {template.pattern_id}: {field}")
        
        return queries
    
    def _parse_textract_response(self, response: Dict[str, Any], 
                               template: CardTemplate) -> Dict[str, str]:
        """
        Parse Textract analyze_document response to extract field values
        
        Args:
            response: Textract analyze_document response
            template: CardTemplate used for extraction
            
        Returns:
            Dictionary mapping field names to extracted values
        """
        extracted_data = {}
        
        # Parse query results from Textract response
        if 'Blocks' not in response:
            logger.warning("No blocks found in Textract response")
            return extracted_data
        
        # Find query result blocks
        query_blocks = {}
        answer_blocks = {}
        
        for block in response['Blocks']:
            if block['BlockType'] == 'QUERY':
                query_blocks[block['Id']] = block
            elif block['BlockType'] == 'QUERY_RESULT':
                answer_blocks[block['Id']] = block
        
        # Match queries to answers and extract text
        for query_id, query_block in query_blocks.items():
            if 'Relationships' in query_block:
                for relationship in query_block['Relationships']:
                    if relationship['Type'] == 'ANSWER':
                        for answer_id in relationship['Ids']:
                            if answer_id in answer_blocks:
                                answer_block = answer_blocks[answer_id]
                                
                                # Get the alias (field name) from query
                                alias = query_block.get('Query', {}).get('Alias', '')
                                
                                # Extract text from answer block
                                if answer_block.get('Confidence', 0) >= self.confidence_threshold * 100:
                                    text = answer_block.get('Text', '').strip()
                                    if text and alias:
                                        extracted_data[alias] = text
                                        logger.debug(f"Extracted {alias}: {text} (confidence: {answer_block.get('Confidence', 0)})")
                                else:
                                    logger.debug(f"Low confidence for {alias}: {answer_block.get('Confidence', 0)}")
        
        logger.info(f"Extracted {len(extracted_data)} fields from Textract response")
        return extracted_data
    
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
            
            # Check maximum size (5MB limit for Textract)
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
                'template_fields': len(template.fields),
                'queries_built': len(self._build_queries_from_template(template))
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


def validate_korean_name(name: str) -> bool:
    """
    Validate Korean name format
    
    Args:
        name: Name to validate
        
    Returns:
        bool: True if name contains Korean characters and is valid length
    """
    if len(name) < 2 or len(name) > 4:  # Korean names are typically 2-4 characters
        return False
    
    # Check that all characters are Korean
    korean_pattern = re.compile(r'^[가-힣]+$')
    return bool(korean_pattern.match(name))


def extract_confidence_from_textract_block(block: Dict[str, Any]) -> float:
    """
    Extract confidence score from Textract block
    
    Args:
        block: Textract block dictionary
        
    Returns:
        Confidence score as float between 0.0 and 1.0
    """
    confidence = block.get('Confidence', 0.0)
    return confidence / 100.0 if confidence > 1.0 else confidence