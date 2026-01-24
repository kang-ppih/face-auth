#!/usr/bin/env python3
"""
Face-Auth IdP System - DynamoDB Initialization Script

This script initializes the DynamoDB tables with proper schemas and seed data.
It should be run after the CDK stack is deployed to set up the initial data.

Requirements: 5.5, 7.4
"""

import boto3
import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add the lambda directory to the path so we can import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from shared.models import CardTemplate
from shared.dynamodb_service import DynamoDBService, create_default_card_templates


def get_stack_outputs() -> Dict[str, str]:
    """
    Retrieve CloudFormation stack outputs to get table names
    
    Returns:
        Dictionary of stack outputs
    """
    try:
        cloudformation = boto3.client('cloudformation')
        
        # Get stack name from environment or use default
        stack_name = os.environ.get('STACK_NAME', 'FaceAuthStack')
        
        response = cloudformation.describe_stacks(StackName=stack_name)
        stack = response['Stacks'][0]
        
        outputs = {}
        for output in stack.get('Outputs', []):
            outputs[output['OutputKey']] = output['OutputValue']
            
        return outputs
        
    except Exception as e:
        print(f"Error retrieving stack outputs: {str(e)}")
        print("Make sure the CDK stack is deployed and accessible")
        sys.exit(1)


def verify_table_exists(table_name: str) -> bool:
    """
    Verify that a DynamoDB table exists and is active
    
    Args:
        table_name: Name of the table to check
        
    Returns:
        bool: True if table exists and is active
    """
    try:
        dynamodb = boto3.client('dynamodb')
        response = dynamodb.describe_table(TableName=table_name)
        return response['Table']['TableStatus'] == 'ACTIVE'
        
    except dynamodb.exceptions.ResourceNotFoundException:
        return False
    except Exception as e:
        print(f"Error checking table {table_name}: {str(e)}")
        return False


def initialize_card_templates_table(db_service: DynamoDBService) -> None:
    """
    Initialize the CardTemplates table with default templates
    
    Args:
        db_service: DynamoDB service instance
    """
    print("Initializing CardTemplates table...")
    
    # Create default card templates
    templates = create_default_card_templates(db_service)
    
    print(f"Created {len(templates)} default card templates:")
    for template in templates:
        print(f"  - {template.pattern_id}: {template.description}")
    
    # Verify templates were created
    active_templates = db_service.get_active_card_templates()
    print(f"Total active templates in database: {len(active_templates)}")


def create_rekognition_collection(collection_id: str) -> bool:
    """
    Create Amazon Rekognition collection for face storage
    
    Args:
        collection_id: Collection identifier
        
    Returns:
        bool: True if successful
    """
    try:
        rekognition = boto3.client('rekognition')
        
        # Check if collection already exists
        try:
            rekognition.describe_collection(CollectionId=collection_id)
            print(f"Rekognition collection '{collection_id}' already exists")
            return True
        except rekognition.exceptions.ResourceNotFoundException:
            pass
        
        # Create the collection
        response = rekognition.create_collection(CollectionId=collection_id)
        print(f"Created Rekognition collection: {collection_id}")
        print(f"Collection ARN: {response['CollectionArn']}")
        return True
        
    except Exception as e:
        print(f"Error creating Rekognition collection: {str(e)}")
        return False


def main():
    """Main initialization function"""
    print("Face-Auth IdP System - DynamoDB Initialization")
    print("=" * 50)
    
    # Get AWS region
    region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
    print(f"Using AWS region: {region}")
    
    # Get stack outputs to find table names
    print("\nRetrieving CloudFormation stack outputs...")
    outputs = get_stack_outputs()
    
    # Extract table names from outputs or use defaults
    card_templates_table = "FaceAuth-CardTemplates"
    employee_faces_table = "FaceAuth-EmployeeFaces"
    auth_sessions_table = "FaceAuth-AuthSessions"
    
    print(f"CardTemplates table: {card_templates_table}")
    print(f"EmployeeFaces table: {employee_faces_table}")
    print(f"AuthSessions table: {auth_sessions_table}")
    
    # Verify all tables exist
    print("\nVerifying DynamoDB tables...")
    tables_to_check = [
        ("CardTemplates", card_templates_table),
        ("EmployeeFaces", employee_faces_table),
        ("AuthSessions", auth_sessions_table)
    ]
    
    for table_type, table_name in tables_to_check:
        if verify_table_exists(table_name):
            print(f"✓ {table_type} table '{table_name}' is active")
        else:
            print(f"✗ {table_type} table '{table_name}' not found or not active")
            print("Make sure the CDK stack is fully deployed")
            sys.exit(1)
    
    # Initialize DynamoDB service
    print("\nInitializing DynamoDB service...")
    db_service = DynamoDBService(region_name=region)
    db_service.initialize_tables(
        card_templates_table,
        employee_faces_table,
        auth_sessions_table
    )
    
    # Initialize card templates
    print("\n" + "=" * 30)
    initialize_card_templates_table(db_service)
    
    # Create Rekognition collection
    print("\n" + "=" * 30)
    print("Setting up Amazon Rekognition...")
    collection_id = "face-auth-employees"
    if create_rekognition_collection(collection_id):
        print(f"✓ Rekognition collection '{collection_id}' is ready")
    else:
        print(f"✗ Failed to create Rekognition collection")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("DynamoDB initialization completed successfully!")
    print("\nNext steps:")
    print("1. Deploy the Lambda functions")
    print("2. Test the API endpoints")
    print("3. Deploy the frontend application")


if __name__ == "__main__":
    main()