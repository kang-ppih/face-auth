#!/usr/bin/env python3
"""
Test OCR via Lambda Function

This script tests OCR processing by invoking the Lambda function directly,
bypassing local Textract connectivity issues.
"""

import boto3
import json
import base64
import os

SAMPLE_IMAGE_PATH = 'sample/社員証サンプル.png'
LAMBDA_FUNCTION_NAME = 'FaceAuth-Enrollment'
REGION = 'ap-northeast-1'


def test_ocr_via_lambda():
    """Test OCR by invoking the enrollment Lambda function."""
    
    print("="*80)
    print("OCR TEST VIA LAMBDA FUNCTION")
    print("="*80)
    print()
    
    # Check if sample image exists
    if not os.path.exists(SAMPLE_IMAGE_PATH):
        print(f"[ERROR] Sample image not found: {SAMPLE_IMAGE_PATH}")
        return False
    
    print(f"[OK] Sample image found: {SAMPLE_IMAGE_PATH}")
    
    # Load and encode image
    try:
        with open(SAMPLE_IMAGE_PATH, 'rb') as f:
            image_bytes = f.read()
        
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        image_size_kb = len(image_bytes) / 1024
        
        print(f"   Image size: {image_size_kb:.2f} KB")
        print(f"   Base64 size: {len(image_b64)} characters")
        print()
        
    except Exception as e:
        print(f"[ERROR] Error loading image: {str(e)}")
        return False
    
    # Create Lambda client
    print("Initializing Lambda client...")
    lambda_client = boto3.client('lambda', region_name=REGION)
    print()
    
    # Prepare payload
    # Use the same image for both ID card and face (for testing OCR only)
    payload = {
        'body': json.dumps({
            'id_card_image': image_b64,
            'face_image': image_b64
        }),
        'headers': {
            'Content-Type': 'application/json'
        },
        'requestContext': {
            'requestId': 'test-ocr-via-lambda',
            'identity': {
                'sourceIp': '127.0.0.1'
            }
        }
    }
    
    print(f"[SEND] Invoking Lambda function: {LAMBDA_FUNCTION_NAME}")
    print("   (This may take 10-30 seconds)")
    print()
    
    try:
        import time
        start_time = time.time()
        
        response = lambda_client.invoke(
            FunctionName=LAMBDA_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        elapsed_time = time.time() - start_time
        
        print(f"[OK] Lambda invocation completed in {elapsed_time:.2f} seconds")
        print()
        
    except Exception as e:
        print(f"[ERROR] Lambda invocation error: {str(e)}")
        return False
    
    # Parse response
    print("-"*80)
    print("LAMBDA RESPONSE")
    print("-"*80)
    print()
    
    try:
        response_payload = json.loads(response['Payload'].read())
        status_code = response_payload.get('statusCode', 0)
        
        print(f"Status Code: {status_code}")
        
        if 'body' in response_payload:
            body = json.loads(response_payload['body'])
            print(f"\nResponse Body:")
            print(json.dumps(body, indent=2, ensure_ascii=False))
            
            # Analyze response
            print()
            print("-"*80)
            print("ANALYSIS")
            print("-"*80)
            print()
            
            if status_code == 200:
                print("[OK] Enrollment successful!")
                print()
                print("Extracted Information:")
                if 'employee_id' in body:
                    print(f"  社員番号: {body['employee_id']}")
                if 'name' in body:
                    print(f"  氏名: {body.get('name', 'N/A')}")
                if 'department' in body:
                    print(f"  所属: {body.get('department', 'N/A')}")
                
                return True
                
            elif status_code == 400:
                error = body.get('error', 'UNKNOWN')
                message = body.get('message', 'No message')
                
                print(f"[WARN]  Enrollment failed with validation error")
                print(f"   Error: {error}")
                print(f"   Message: {message}")
                print()
                
                if error == 'ID_CARD_FORMAT_MISMATCH':
                    print("This indicates:")
                    print("  - The sample image does not match the CardTemplate")
                    print("  - OCR could not extract the required information")
                    print("  - The image may not contain employee ID card data")
                
                return False
                
            elif status_code == 408:
                print("[ERROR] Request timed out")
                print("   The OCR processing took too long (>30 seconds)")
                print("   This usually means the image doesn't contain expected data")
                return False
                
            else:
                print(f"[ERROR] Unexpected status code: {status_code}")
                return False
        
        else:
            print("[ERROR] No body in response")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error parsing response: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def check_lambda_logs():
    """Provide instructions to check Lambda logs."""
    
    print()
    print("="*80)
    print("CHECK LAMBDA LOGS FOR DETAILS")
    print("="*80)
    print()
    print("To see detailed OCR processing logs, run:")
    print()
    print(f"  aws logs tail /aws/lambda/{LAMBDA_FUNCTION_NAME} --follow --profile dev --region {REGION}")
    print()
    print("Look for:")
    print("  - 'Step 1: Processing ID card with OCR'")
    print("  - Textract response details")
    print("  - Extracted employee information")
    print("  - Any error messages")
    print()


def main():
    """Main test function."""
    
    success = test_ocr_via_lambda()
    
    if not success:
        check_lambda_logs()
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print()
    
    if success:
        print("[OK] OCR test via Lambda PASSED")
        print()
        print("The sample image contains valid employee ID card data")
        print("and the OCR processing is working correctly.")
    else:
        print("[ERROR] OCR test via Lambda FAILED")
        print()
        print("Possible reasons:")
        print("  1. Sample image does not contain employee ID card data")
        print("  2. CardTemplate configuration doesn't match the image")
        print("  3. Image quality is too low for OCR")
        print("  4. Lambda function timeout (processing took >30 seconds)")
        print()
        print("Next steps:")
        print("  1. Check Lambda logs for detailed error messages")
        print("  2. Verify sample image contains: 社員番号, 氏名, 所属")
        print("  3. Consider creating a new test image with clear text")
    
    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
