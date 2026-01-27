"""
Face-Auth IdP System - DynamoDB Service

This module provides a service layer for DynamoDB operations,
including CRUD operations for CardTemplates and EmployeeFaces tables.

Requirements: 5.5, 7.4
"""

import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .models import (
    CardTemplate, 
    EmployeeFaceRecord, 
    FaceData, 
    AuthenticationSession,
    ErrorCodes
)

logger = logging.getLogger(__name__)


class DynamoDBService:
    """
    Service class for DynamoDB operations in Face-Auth system
    
    Handles operations for:
    - CardTemplates table
    - EmployeeFaces table  
    - AuthSessions table
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize DynamoDB service
        
        Args:
            region_name: AWS region name
        """
        self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
        self.card_templates_table = None
        self.employee_faces_table = None
        self.auth_sessions_table = None
        
    def initialize_tables(self, card_templates_table_name: str, 
                         employee_faces_table_name: str,
                         auth_sessions_table_name: str):
        """
        Initialize table references
        
        Args:
            card_templates_table_name: Name of CardTemplates table
            employee_faces_table_name: Name of EmployeeFaces table
            auth_sessions_table_name: Name of AuthSessions table
        """
        self.card_templates_table = self.dynamodb.Table(card_templates_table_name)
        self.employee_faces_table = self.dynamodb.Table(employee_faces_table_name)
        self.auth_sessions_table = self.dynamodb.Table(auth_sessions_table_name)
    
    # CardTemplates table operations
    
    def get_card_template(self, pattern_id: str) -> Optional[CardTemplate]:
        """
        Retrieve a card template by pattern ID
        
        Args:
            pattern_id: Template pattern identifier
            
        Returns:
            CardTemplate instance or None if not found
        """
        try:
            response = self.card_templates_table.get_item(
                Key={'pattern_id': pattern_id}
            )
            
            if 'Item' in response:
                return CardTemplate.from_dict(response['Item'])
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving card template {pattern_id}: {str(e)}")
            raise
    
    def get_active_card_templates(self) -> List[CardTemplate]:
        """
        Retrieve all active card templates
        
        Returns:
            List of active CardTemplate instances
        """
        try:
            response = self.card_templates_table.scan(
                FilterExpression=Attr('is_active').eq(True)
            )
            
            templates = []
            for item in response['Items']:
                templates.append(CardTemplate.from_dict(item))
                
            return templates
            
        except Exception as e:
            logger.error(f"Error retrieving active card templates: {str(e)}")
            raise
    
    def get_templates_by_card_type(self, card_type: str) -> List[CardTemplate]:
        """
        Retrieve card templates by card type using GSI
        
        Args:
            card_type: Type of card to search for
            
        Returns:
            List of CardTemplate instances
        """
        try:
            response = self.card_templates_table.query(
                IndexName='CardTypeIndex',
                KeyConditionExpression=Key('card_type').eq(card_type),
                FilterExpression=Attr('is_active').eq(True)
            )
            
            templates = []
            for item in response['Items']:
                templates.append(CardTemplate.from_dict(item))
                
            return templates
            
        except Exception as e:
            logger.error(f"Error retrieving templates for card type {card_type}: {str(e)}")
            raise
    
    def create_card_template(self, template: CardTemplate) -> bool:
        """
        Create a new card template
        
        Args:
            template: CardTemplate instance to create
            
        Returns:
            bool: True if successful
        """
        try:
            self.card_templates_table.put_item(
                Item=template.to_dict(),
                ConditionExpression=Attr('pattern_id').not_exists()
            )
            return True
            
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            logger.warning(f"Card template {template.pattern_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Error creating card template {template.pattern_id}: {str(e)}")
            raise
    
    def update_card_template(self, template: CardTemplate) -> bool:
        """
        Update an existing card template
        
        Args:
            template: CardTemplate instance with updated data
            
        Returns:
            bool: True if successful
        """
        try:
            self.card_templates_table.put_item(
                Item=template.to_dict(),
                ConditionExpression=Attr('pattern_id').exists()
            )
            return True
            
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            logger.warning(f"Card template {template.pattern_id} does not exist")
            return False
        except Exception as e:
            logger.error(f"Error updating card template {template.pattern_id}: {str(e)}")
            raise
    
    # EmployeeFaces table operations
    
    def get_employee_face_record(self, employee_id: str) -> Optional[EmployeeFaceRecord]:
        """
        Retrieve employee face record by employee ID
        
        Args:
            employee_id: Employee identifier
            
        Returns:
            EmployeeFaceRecord instance or None if not found
        """
        try:
            response = self.employee_faces_table.get_item(
                Key={'employee_id': employee_id}
            )
            
            if 'Item' in response:
                return EmployeeFaceRecord.from_dict(response['Item'])
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving employee face record {employee_id}: {str(e)}")
            raise
    
    def get_employee_by_face_id(self, face_id: str) -> Optional[EmployeeFaceRecord]:
        """
        Retrieve employee face record by face ID using GSI
        
        Args:
            face_id: Amazon Rekognition face identifier
            
        Returns:
            EmployeeFaceRecord instance or None if not found
        """
        try:
            response = self.employee_faces_table.query(
                IndexName='FaceIdIndex',
                KeyConditionExpression=Key('face_id').eq(face_id)
            )
            
            if response['Items']:
                return EmployeeFaceRecord.from_dict(response['Items'][0])
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving employee by face ID {face_id}: {str(e)}")
            raise
    
    def create_employee_face_record(self, record: EmployeeFaceRecord) -> bool:
        """
        Create a new employee face record
        
        Args:
            record: EmployeeFaceRecord instance to create
            
        Returns:
            bool: True if successful
        """
        try:
            self.employee_faces_table.put_item(
                Item=record.to_dict(),
                ConditionExpression=Attr('employee_id').not_exists()
            )
            return True
            
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            logger.warning(f"Employee face record {record.employee_id} already exists")
            return False
        except Exception as e:
            logger.error(f"Error creating employee face record {record.employee_id}: {str(e)}")
            raise
    
    def update_employee_face_record(self, record: EmployeeFaceRecord) -> bool:
        """
        Update an existing employee face record (for re-enrollment)
        
        Args:
            record: EmployeeFaceRecord instance with updated data
            
        Returns:
            bool: True if successful
        """
        try:
            self.employee_faces_table.put_item(
                Item=record.to_dict(),
                ConditionExpression=Attr('employee_id').exists()
            )
            return True
            
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            logger.warning(f"Employee face record {record.employee_id} does not exist")
            return False
        except Exception as e:
            logger.error(f"Error updating employee face record {record.employee_id}: {str(e)}")
            raise
    
    def update_last_login(self, employee_id: str, login_time: datetime) -> bool:
        """
        Update the last login timestamp for an employee
        
        Args:
            employee_id: Employee identifier
            login_time: Login timestamp
            
        Returns:
            bool: True if successful
        """
        try:
            self.employee_faces_table.update_item(
                Key={'employee_id': employee_id},
                UpdateExpression='SET last_login = :login_time',
                ExpressionAttributeValues={
                    ':login_time': login_time.isoformat()
                },
                ConditionExpression=Attr('employee_id').exists()
            )
            return True
            
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            logger.warning(f"Employee {employee_id} not found for login update")
            return False
        except Exception as e:
            logger.error(f"Error updating last login for {employee_id}: {str(e)}")
            raise
    
    def deactivate_employee_face(self, employee_id: str) -> bool:
        """
        Deactivate an employee's face data
        
        Args:
            employee_id: Employee identifier
            
        Returns:
            bool: True if successful
        """
        try:
            self.employee_faces_table.update_item(
                Key={'employee_id': employee_id},
                UpdateExpression='SET is_active = :inactive',
                ExpressionAttributeValues={
                    ':inactive': False
                },
                ConditionExpression=Attr('employee_id').exists()
            )
            return True
            
        except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            logger.warning(f"Employee {employee_id} not found for deactivation")
            return False
        except Exception as e:
            logger.error(f"Error deactivating employee face {employee_id}: {str(e)}")
            raise
    
    def get_all_active_employees(self) -> List[EmployeeFaceRecord]:
        """
        Retrieve all active employee face records
        
        Returns:
            List of active EmployeeFaceRecord instances
        """
        try:
            response = self.employee_faces_table.scan(
                FilterExpression=Attr('is_active').eq(True)
            )
            
            records = []
            for item in response['Items']:
                records.append(EmployeeFaceRecord.from_dict(item))
                
            return records
            
        except Exception as e:
            logger.error(f"Error retrieving active employees: {str(e)}")
            raise
    
    # AuthSessions table operations
    
    def create_auth_session(self, session: AuthenticationSession) -> bool:
        """
        Create a new authentication session
        
        Args:
            session: AuthenticationSession instance to create
            
        Returns:
            bool: True if successful
        """
        try:
            self.auth_sessions_table.put_item(
                Item=session.to_dict()
            )
            return True
            
        except Exception as e:
            logger.error(f"Error creating auth session {session.session_id}: {str(e)}")
            raise
    
    def get_auth_session(self, session_id: str) -> Optional[AuthenticationSession]:
        """
        Retrieve authentication session by session ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            AuthenticationSession instance or None if not found/expired
        """
        try:
            response = self.auth_sessions_table.get_item(
                Key={'session_id': session_id}
            )
            
            if 'Item' in response:
                return AuthenticationSession.from_dict(response['Item'])
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving auth session {session_id}: {str(e)}")
            raise
    
    def delete_auth_session(self, session_id: str) -> bool:
        """
        Delete an authentication session (logout)
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if successful
        """
        try:
            self.auth_sessions_table.delete_item(
                Key={'session_id': session_id}
            )
            return True
            
        except Exception as e:
            logger.error(f"Error deleting auth session {session_id}: {str(e)}")
            raise


# Utility functions for DynamoDB operations

def create_default_card_templates(db_service: DynamoDBService) -> List[CardTemplate]:
    """
    Create default card templates for common ID card formats
    
    Args:
        db_service: DynamoDB service instance
        
    Returns:
        List of created CardTemplate instances
    """
    templates = [
        CardTemplate(
            pattern_id="company_card_v1",
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
            description="Standard employee ID card template"
        ),
        CardTemplate(
            pattern_id="contractor_card_v1",
            card_type="contractor",
            logo_position={"x": 40, "y": 25, "width": 120, "height": 60},
            fields=[
                {
                    "field_name": "employee_id",
                    "query_phrase": "계약자 번호는 무엇입니까?",
                    "expected_format": r"C\d{5}"
                },
                {
                    "field_name": "employee_name",
                    "query_phrase": "성명은 무엇입니까?",
                    "expected_format": r"[가-힣]{2,4}"
                },
                {
                    "field_name": "company",
                    "query_phrase": "소속 회사는 무엇입니까?",
                    "expected_format": r"[가-힣\s]+"
                }
            ],
            created_at=datetime.now(),
            is_active=True,
            description="Contractor ID card template"
        )
    ]
    
    created_templates = []
    for template in templates:
        if db_service.create_card_template(template):
            created_templates.append(template)
            logger.info(f"Created card template: {template.pattern_id}")
        else:
            logger.info(f"Card template already exists: {template.pattern_id}")
    
    return created_templates