#!/usr/bin/env python3
"""
Register Card Template for Employee ID Card

This script registers the card template based on the sample employee ID card
(sample/社員証サンプル.png) into DynamoDB.

Usage:
    python scripts/register_card_template.py
"""

import boto3
import os
import sys
from datetime import datetime
import json
from decimal import Decimal


def register_card_template():
    """
    Register the standard employee ID card template to DynamoDB.
    
    This template is based on sample/社員証サンプル.png and defines:
    - Pattern ID for identification
    - Textract queries for extracting employee information
    - Bounding box for employee number location
    - Active status
    """
    
    # Get environment variables
    table_name = os.environ.get('CARD_TEMPLATES_TABLE', 'FaceAuth-CardTemplates')
    region = os.environ.get('AWS_REGION', 'ap-northeast-1')
    
    print(f"Registering card template to table: {table_name}")
    print(f"Region: {region}")
    
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    
    # Define the card template based on sample/社員証サンプル.png
    # This template matches the specific format of the sample ID card
    template_data = {
        'pattern_id': "STANDARD_EMPLOYEE_CARD_V1",
        'card_type': "STANDARD",
        'description': "標準社員証フォーマット（7桁数値ベース）",
        
        # Fields to extract with Textract queries
        # Using simpler queries to find 7-digit numbers directly
        'fields': [
            {
                'field_name': 'employee_id',
                'query_phrase': '7桁の数字は何ですか？',
                'required': True
            },
            {
                'field_name': 'employee_name',
                'query_phrase': '名前は何ですか？',
                'required': True
            },
            {
                'field_name': 'department',
                'query_phrase': '部署は何ですか？',
                'required': False
            }
        ],
        
        # Bounding box for employee number location (normalized coordinates 0-1)
        'employee_number_bbox': {
            "left": Decimal('0.15'),    # 15% from left edge
            "top": Decimal('0.30'),     # 30% from top edge
            "width": Decimal('0.35'),   # 35% width
            "height": Decimal('0.10')   # 10% height
        },
        
        # Confidence threshold for matching this template
        'confidence_threshold': Decimal('0.85'),
        
        # Template is active and should be used for matching
        'is_active': True,
        
        # Metadata
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat(),
        'version': "1.0"
    }
    
    try:
        # Put item to DynamoDB
        response = table.put_item(Item=template_data)
        
        print("\n✅ Card template registered successfully!")
        print(f"\nTemplate Details:")
        print(f"  Pattern ID: {template_data['pattern_id']}")
        print(f"  Description: {template_data['description']}")
        print(f"  Version: {template_data['version']}")
        print(f"  Active: {template_data['is_active']}")
        print(f"\nFields to Extract:")
        for field in template_data['fields']:
            print(f"  - {field['field_name']}: {field['query_phrase']} (required: {field['required']})")
        print(f"\nEmployee Number BBox:")
        print(f"  Left: {template_data['employee_number_bbox']['left']}")
        print(f"  Top: {template_data['employee_number_bbox']['top']}")
        print(f"  Width: {template_data['employee_number_bbox']['width']}")
        print(f"  Height: {template_data['employee_number_bbox']['height']}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error registering card template: {str(e)}")
        return False


def list_card_templates():
    """List all card templates in DynamoDB."""
    
    table_name = os.environ.get('CARD_TEMPLATES_TABLE', 'FaceAuth-CardTemplates')
    region = os.environ.get('AWS_REGION', 'ap-northeast-1')
    
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        print(f"\n📋 Card Templates in {table_name}:")
        print(f"Total: {len(items)} template(s)\n")
        
        for item in items:
            print(f"Pattern ID: {item.get('pattern_id')}")
            print(f"  Description: {item.get('description')}")
            print(f"  Active: {item.get('is_active')}")
            print(f"  Version: {item.get('version')}")
            print(f"  Created: {item.get('created_at')}")
            print()
        
        return items
        
    except Exception as e:
        print(f"❌ Error listing templates: {str(e)}")
        return []


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage Card Templates')
    parser.add_argument('--list', action='store_true', help='List all card templates')
    parser.add_argument('--register', action='store_true', help='Register new card template')
    
    args = parser.parse_args()
    
    if args.list:
        list_card_templates()
    elif args.register:
        register_card_template()
    else:
        # Default: register template
        print("Registering card template based on sample/社員証サンプル.png\n")
        success = register_card_template()
        
        if success:
            print("\n" + "="*60)
            print("Next steps:")
            print("1. Verify the template in DynamoDB")
            print("2. Test OCR with the sample card")
            print("3. Adjust bounding boxes if needed")
            print("="*60)
