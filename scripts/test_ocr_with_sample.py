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
import json

# Configuration
SAMPLE_IMAGE_PATH = 'sample/社員証サンプル.png'
REGION = 'ap-northeast-1'
CARD_TEMPLATES_TABLE = 'FaceAuth-CardTemplates'


def test_ocr_with_textract_directly():
    """
    Test OCR processing directly with Textract API.
    This bypasses the OCRService to isolate the Textract behavior.
    """
    
    print("="*80)
    print("OCR SINGLE TEST - Direct Textract API Call")
    print("="*80)
    print()
    
    # Check if sample image exists
    if not os.path.exists(SAMPLE_IMAGE_PATH):
        print(f"❌ Sample image not found: {SAMPLE_IMAGE_PATH}")
        return False
    
    print(f"✅ Sample image found: {SAMPLE_IMAGE_PATH}")
    
    # Load image
    try:
        with open(SAMPLE_IMAGE_PATH, 'rb') as f:
            image_bytes = f.read()
        
        image_size_kb = len(image_bytes) / 1024
        print(f"   Image size: {image_size_kb:.2f} KB")
        
        # Check image with PIL
        img = Image.open(SAMPLE_IMAGE_PATH)
        print(f"   Image dimensions: {img.size[0]}x{img.size[1]}")
        print(f"   Image format: {img.format}")
        print()
    except Exception as e:
        print(f"❌ Error loading image: {str(e)}")
        return False
    
    # Initialize Textract client
    print("Initializing Textract client...")
    textract = boto3.client('textract', region_name=REGION)
    print()
    
    # Define queries based on CardTemplate
    queries = [
        {
            'Text': '社員番号は何ですか？',
            'Alias': 'employee_id'
        },
        {
            'Text': '氏名は何ですか？',
            'Alias': 'employee_name'
        },
        {
            'Text': '所属は何ですか？',
            'Alias': 'department'
        }
    ]
    
    print(f"Testing with {len(queries)} Textract queries:")
    for query in queries:
        print(f"  - {query['Alias']}: {query['Text']}")
    print()
    
    # Call Textract
    print("📤 Calling Amazon Textract analyze_document...")
    print("   (This may take 10-30 seconds)")
    print()
    
    try:
        import time
        start_time = time.time()
        
        response = textract.analyze_document(
            Document={'Bytes': image_bytes},
            FeatureTypes=['QUERIES'],
            QueriesConfig={'Queries': queries}
        )
        
        elapsed_time = time.time() - start_time
        print(f"✅ Textract completed in {elapsed_time:.2f} seconds")
        print()
        
    except Exception as e:
        print(f"❌ Textract API error: {str(e)}")
        return False
    
    # Parse response
    print("-"*80)
    print("TEXTRACT RESPONSE ANALYSIS")
    print("-"*80)
    print()
    
    blocks = response.get('Blocks', [])
    print(f"Total blocks returned: {len(blocks)}")
    
    # Count block types
    block_types = {}
    for block in blocks:
        block_type = block.get('BlockType', 'UNKNOWN')
        block_types[block_type] = block_types.get(block_type, 0) + 1
    
    print("\nBlock types:")
    for block_type, count in block_types.items():
        print(f"  - {block_type}: {count}")
    print()
    
    # Extract query results
    query_blocks = {}
    answer_blocks = {}
    
    for block in blocks:
        if block['BlockType'] == 'QUERY':
            query_blocks[block['Id']] = block
        elif block['BlockType'] == 'QUERY_RESULT':
            answer_blocks[block['Id']] = block
    
    print(f"Query blocks: {len(query_blocks)}")
    print(f"Answer blocks: {len(answer_blocks)}")
    print()
    
    # Match queries to answers
    print("-"*80)
    print("EXTRACTED DATA")
    print("-"*80)
    print()
    
    extracted_data = {}
    
    for query_id, query_block in query_blocks.items():
        alias = query_block.get('Query', {}).get('Alias', 'unknown')
        query_text = query_block.get('Query', {}).get('Text', '')
        
        print(f"Query: {alias}")
        print(f"  Text: {query_text}")
        
        if 'Relationships' in query_block:
            for relationship in query_block['Relationships']:
                if relationship['Type'] == 'ANSWER':
                    for answer_id in relationship['Ids']:
                        if answer_id in answer_blocks:
                            answer_block = answer_blocks[answer_id]
                            confidence = answer_block.get('Confidence', 0)
                            text = answer_block.get('Text', '')
                            
                            print(f"  Answer: {text}")
                            print(f"  Confidence: {confidence:.2f}%")
                            
                            if text:
                                extracted_data[alias] = text
        else:
            print(f"  Answer: (no answer found)")
        
        print()
    
    # Summary
    print("-"*80)
    print("SUMMARY")
    print("-"*80)
    print()
    
    if extracted_data:
        print(f"✅ Successfully extracted {len(extracted_data)} field(s):")
        for field, value in extracted_data.items():
            print(f"  - {field}: {value}")
        print()
        return True
    else:
        print("❌ No data extracted from the image")
        print()
        print("Possible reasons:")
        print("  1. The sample image does not contain the expected information")
        print("  2. The image quality is too low")
        print("  3. The Textract queries are not appropriate for this image")
        print("  4. The text in the image is not in a format Textract can recognize")
        print()
        return False


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
        employee_info, error = ocr_service.extract_id_card_info(
            image_bytes=image_bytes,
            request_id="test_ocr"
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
    
    # Run direct Textract test (no OCRService dependency)
    success = test_ocr_with_textract_directly()
    
    print("\n")
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
