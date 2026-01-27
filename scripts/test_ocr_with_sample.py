#!/usr/bin/env python3
"""
Test OCR with Sample Employee ID Card

This script tests the OCR service with the sample employee ID card
to verify that the CardTemplate is correctly configured.

Usage:
    python scripts/test_ocr_with_sample.py
"""

import boto3
import os
import sys
from PIL import Image

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lambda.shared.ocr_service import OCRService
from lambda.shared.dynamodb_service import DynamoDBService


def test_ocr_with_sample_card():
    """
    Test OCR processing with the sample employee ID card.
    """
    
    # Configuration
    sample_image_path = 'sample/社員証サンプル.png'
    region = os.environ.get('AWS_REGION', 'ap-northeast-1')
    card_templates_table = os.environ.get('CARD_TEMPLATES_TABLE', 'FaceAuth-CardTemplates')
    
    print("="*80)
    print("OCR TEST WITH SAMPLE EMPLOYEE ID CARD")
    print("="*80)
    print(f"\nSample Image: {sample_image_path}")
    print(f"Region: {region}")
    print(f"Card Templates Table: {card_templates_table}")
    
    # Check if sample image exists
    if not os.path.exists(sample_image_path):
        print(f"\n❌ Error: Sample image not found: {sample_image_path}")
        print("Please ensure the sample image is in the correct location.")
        return False
    
    # Get image info
    with Image.open(sample_image_path) as img:
        width, height = img.size
        print(f"Image dimensions: {width}x{height} pixels")
        print(f"Image format: {img.format}")
    
    # Read image bytes
    with open(sample_image_path, 'rb') as f:
        image_bytes = f.read()
    print(f"Image size: {len(image_bytes)} bytes")
    
    # Initialize services
    print("\n" + "-"*80)
    print("Initializing services...")
    print("-"*80)
    
    try:
        ocr_service = OCRService(region_name=region)
        db_service = DynamoDBService(region_name=region)
        db_service.initialize_tables(
            card_templates_table=card_templates_table,
            employee_faces_table='FaceAuth-EmployeeFaces',
            auth_sessions_table='FaceAuth-AuthSessions'
        )
        
        print("✅ Services initialized successfully")
        
    except Exception as e:
        print(f"❌ Error initializing services: {str(e)}")
        return False
    
    # Test OCR extraction
    print("\n" + "-"*80)
    print("Testing OCR extraction...")
    print("-"*80)
    
    try:
        employee_info, error = ocr_service.extract_employee_info(
            image_bytes=image_bytes,
            db_service=db_service
        )
        
        if error:
            print(f"\n❌ OCR extraction failed:")
            print(f"   Error Code: {error.error_code}")
            print(f"   User Message: {error.user_message}")
            print(f"   System Reason: {error.system_reason}")
            return False
        
        if not employee_info:
            print(f"\n❌ No employee information extracted")
            return False
        
        # Display results
        print(f"\n✅ OCR extraction successful!")
        print("\n" + "="*80)
        print("EXTRACTED EMPLOYEE INFORMATION")
        print("="*80)
        print(f"\n社員番号 (Employee ID): {employee_info.employee_id}")
        print(f"氏名 (Name): {employee_info.name}")
        print(f"所属 (Department): {employee_info.department or '(not extracted)'}")
        
        # Validate employee info
        print("\n" + "-"*80)
        print("Validating extracted information...")
        print("-"*80)
        
        is_valid = employee_info.validate()
        
        if is_valid:
            print("✅ Employee information is valid")
            print(f"   - Employee ID format: 7 digits ✓")
            print(f"   - Name present: ✓")
        else:
            print("❌ Employee information validation failed")
            if not employee_info.employee_id or len(employee_info.employee_id) != 7:
                print(f"   - Employee ID format: Invalid (expected 7 digits)")
            if not employee_info.name:
                print(f"   - Name: Missing")
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        if is_valid:
            print("\n✅ OCR test PASSED")
            print("\nThe CardTemplate is correctly configured for this ID card format.")
            print("You can now use this template for employee enrollment.")
        else:
            print("\n⚠️ OCR test PASSED with warnings")
            print("\nThe OCR extracted information, but validation failed.")
            print("Please check:")
            print("1. Employee number format (should be 7 digits)")
            print("2. Name field extraction")
            print("3. CardTemplate bounding boxes")
        
        return is_valid
        
    except Exception as e:
        print(f"\n❌ Error during OCR test: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n")
    success = test_ocr_with_sample_card()
    print("\n")
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
