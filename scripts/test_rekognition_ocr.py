"""
Test Rekognition-based OCR locally

This script tests the Rekognition DetectText API directly with the sample image.
"""

import boto3
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_rekognition_ocr():
    """Test Rekognition DetectText with sample image"""
    
    print("=" * 80)
    print("REKOGNITION OCR TEST")
    print("=" * 80)
    print()
    
    # Load sample image
    sample_image_path = Path("sample/社員証サンプル.png")
    
    if not sample_image_path.exists():
        print(f"[ERROR] Sample image not found: {sample_image_path}")
        return False
    
    print(f"[OK] Sample image found: {sample_image_path}")
    
    with open(sample_image_path, 'rb') as f:
        image_bytes = f.read()
    
    print(f"   Image size: {len(image_bytes) / 1024:.2f} KB")
    print()
    
    # Initialize Rekognition client
    print("Initializing Rekognition client...")
    rekognition = boto3.client('rekognition', region_name='ap-northeast-1')
    print()
    
    # Call DetectText
    print("[SEND] Calling Rekognition DetectText...")
    try:
        response = rekognition.detect_text(
            Image={'Bytes': image_bytes}
        )
        print("[OK] Rekognition DetectText completed")
        print()
        
    except Exception as e:
        print(f"[ERROR] Rekognition DetectText failed: {e}")
        return False
    
    # Parse response
    print("-" * 80)
    print("DETECTED TEXT")
    print("-" * 80)
    print()
    
    if 'TextDetections' not in response:
        print("[ERROR] No TextDetections in response")
        return False
    
    # Show all detected text
    line_texts = []
    word_texts = []
    
    for detection in response['TextDetections']:
        text = detection.get('DetectedText', '')
        confidence = detection.get('Confidence', 0.0)
        detection_type = detection.get('Type', '')
        
        if detection_type == 'LINE':
            line_texts.append((text, confidence))
            print(f"[LINE] {text:30s} (confidence: {confidence:.2f}%)")
        elif detection_type == 'WORD':
            word_texts.append((text, confidence))
    
    print()
    print(f"Total: {len(line_texts)} lines, {len(word_texts)} words")
    print()
    
    # Extract employee information
    print("-" * 80)
    print("EXTRACTED INFORMATION")
    print("-" * 80)
    print()
    
    import re
    
    # Extract employee ID (7 digits)
    employee_id = None
    for text, confidence in line_texts + word_texts:
        match = re.search(r'\b(\d{7})\b', text)
        if match:
            employee_id = match.group(1)
            print(f"[OK] Employee ID: {employee_id}")
            break
    
    if not employee_id:
        print("[WARN] No 7-digit employee ID found")
    
    # Extract Japanese name
    japanese_pattern = re.compile(r'^[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]{2,5}$')
    english_pattern = re.compile(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+){0,2}$')
    employee_name = None
    
    print("[INFO] Searching for name in detected text...")
    for text, confidence in line_texts:
        cleaned = text.strip()
        print(f"   Checking: '{cleaned}'")
        
        if japanese_pattern.match(cleaned):
            employee_name = cleaned
            print(f"[OK] Employee Name (Japanese): {employee_name}")
            break
        elif english_pattern.match(cleaned):
            # Skip common company names
            skip_words = ['Pan', 'Pacific', 'International', 'Holdings', 'Corporation', 'Company', 'Ltd', 'PPIH']
            if not any(word in cleaned for word in skip_words):
                employee_name = cleaned
                print(f"[OK] Employee Name (English): {employee_name}")
                break
    
    if not employee_name:
        print("[WARN] No name found - sample image may not contain employee name")
        print("[INFO] For testing, using 'PPIH' as placeholder name")
    
    # Extract department
    department = None
    for text, confidence in line_texts:
        cleaned = text.strip()
        if employee_name and cleaned == employee_name:
            continue
        if re.search(r'\d', cleaned):
            continue
        if japanese_pattern.match(cleaned) and len(cleaned) >= 3:
            department = cleaned
            print(f"[OK] Department: {department}")
            break
    
    if not department:
        print("[INFO] No department found")
    
    print()
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    if employee_id and employee_name:
        print("[SUCCESS] OCR test PASSED")
        print(f"   Employee ID: {employee_id}")
        print(f"   Employee Name: {employee_name}")
        if department:
            print(f"   Department: {department}")
        return True
    else:
        print("[FAILED] OCR test FAILED")
        print(f"   Employee ID: {'Found' if employee_id else 'NOT FOUND'}")
        print(f"   Employee Name: {'Found' if employee_name else 'NOT FOUND'}")
        return False


if __name__ == '__main__':
    success = test_rekognition_ocr()
    sys.exit(0 if success else 1)
