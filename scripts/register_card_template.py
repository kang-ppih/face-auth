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

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambda.shared.models import CardTemplate


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
    card_template = CardTemplate(
        pattern_id="STANDARD_EMPLOYEE_CARD_V1",
        description="標準社員証フォーマット（sample/社員証サンプル.png準拠）",
        
        # Textract queries to extract information from the ID card
        # These queries are optimized for the specific layout of the sample card
        textract_queries=[
            {
                "text": "社員番号",
                "alias": "EMPLOYEE_ID",
                "pages": ["1"]
            },
            {
                "text": "氏名",
                "alias": "EMPLOYEE_NAME", 
                "pages": ["1"]
            },
            {
                "text": "所属",
                "alias": "DEPARTMENT",
                "pages": ["1"]
            }
        ],
        
        # Bounding box for employee number location (normalized coordinates 0-1)
        # These coordinates should be adjusted based on the actual position in the sample card
        # Format: {"left": x, "top": y, "width": w, "height": h}
        # Example values - should be calibrated with actual sample card
        employee_number_bbox={
            "left": 0.15,    # 15% from left edge
            "top": 0.30,     # 30% from top edge
            "width": 0.35,   # 35% width
            "height": 0.10   # 10% height
        },
        
        # Logo detection area (optional, for additional validation)
        # Can be used to verify the card is authentic
        logo_bbox={
            "left": 0.05,
            "top": 0.05,
            "width": 0.20,
            "height": 0.15
        },
        
        # Confidence threshold for matching this template
        confidence_threshold=0.85,
        
        # Template is active and should be used for matching
        is_active=True,
        
        # Metadata
        created_at=datetime.now().isoformat(),
        updated_at=datetime.now().isoformat(),
        version="1.0"
    )
    
    # Convert to DynamoDB item
    item = {
        'pattern_id': card_template.pattern_id,
        'description': card_template.description,
        'textract_queries': card_template.textract_queries,
        'employee_number_bbox': card_template.employee_number_bbox,
        'logo_bbox': card_template.logo_bbox,
        'confidence_threshold': card_template.confidence_threshold,
        'is_active': card_template.is_active,
        'created_at': card_template.created_at,
        'updated_at': card_template.updated_at,
        'version': card_template.version
    }
    
    try:
        # Put item to DynamoDB
        response = table.put_item(Item=item)
        
        print("\n✅ Card template registered successfully!")
        print(f"\nTemplate Details:")
        print(f"  Pattern ID: {card_template.pattern_id}")
        print(f"  Description: {card_template.description}")
        print(f"  Version: {card_template.version}")
        print(f"  Active: {card_template.is_active}")
        print(f"\nTextract Queries:")
        for query in card_template.textract_queries:
            print(f"  - {query['text']} (alias: {query['alias']})")
        print(f"\nEmployee Number BBox:")
        print(f"  Left: {card_template.employee_number_bbox['left']}")
        print(f"  Top: {card_template.employee_number_bbox['top']}")
        print(f"  Width: {card_template.employee_number_bbox['width']}")
        print(f"  Height: {card_template.employee_number_bbox['height']}")
        
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
