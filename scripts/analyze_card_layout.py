#!/usr/bin/env python3
"""
Analyze Employee ID Card Layout

This script analyzes the sample employee ID card image to determine:
- Employee number position (bounding box)
- Text locations
- Optimal Textract query positions

Usage:
    python scripts/analyze_card_layout.py sample/社員証サンプル.png
"""

import boto3
import sys
import os
import json
from PIL import Image


def analyze_card_with_textract(image_path: str):
    """
    Analyze card image using Amazon Textract to find text positions.
    
    Args:
        image_path: Path to the employee ID card image
        
    Returns:
        Dictionary containing analysis results
    """
    
    region = os.environ.get('AWS_REGION', 'ap-northeast-1')
    textract = boto3.client('textract', region_name=region)
    
    # Read image file
    with open(image_path, 'rb') as image_file:
        image_bytes = image_file.read()
    
    print(f"Analyzing card image: {image_path}")
    print(f"Image size: {len(image_bytes)} bytes")
    
    # Get image dimensions
    with Image.open(image_path) as img:
        width, height = img.size
        print(f"Image dimensions: {width}x{height} pixels")
    
    try:
        # Detect text using Textract
        response = textract.detect_document_text(
            Document={'Bytes': image_bytes}
        )
        
        print(f"\n✅ Textract analysis complete")
        print(f"Blocks detected: {len(response.get('Blocks', []))}")
        
        # Analyze blocks
        results = {
            'image_dimensions': {'width': width, 'height': height},
            'text_blocks': [],
            'employee_number_candidates': [],
            'name_candidates': [],
            'department_candidates': []
        }
        
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text = block.get('Text', '')
                bbox = block.get('Geometry', {}).get('BoundingBox', {})
                confidence = block.get('Confidence', 0)
                
                block_info = {
                    'text': text,
                    'confidence': confidence,
                    'bbox': bbox,
                    'bbox_pixels': {
                        'left': int(bbox.get('Left', 0) * width),
                        'top': int(bbox.get('Top', 0) * height),
                        'width': int(bbox.get('Width', 0) * width),
                        'height': int(bbox.get('Height', 0) * height)
                    }
                }
                
                results['text_blocks'].append(block_info)
                
                # Check if this might be employee number (7 digits)
                if text.replace('-', '').replace(' ', '').isdigit():
                    digits_only = text.replace('-', '').replace(' ', '')
                    if len(digits_only) == 7:
                        results['employee_number_candidates'].append(block_info)
                
                # Check for name indicators
                if '氏名' in text or '名前' in text or 'Name' in text.upper():
                    results['name_candidates'].append(block_info)
                
                # Check for department indicators
                if '所属' in text or '部署' in text or 'Department' in text.upper():
                    results['department_candidates'].append(block_info)
        
        return results
        
    except Exception as e:
        print(f"❌ Error analyzing card: {str(e)}")
        return None


def print_analysis_results(results: dict):
    """Print analysis results in a readable format."""
    
    if not results:
        return
    
    print("\n" + "="*80)
    print("CARD LAYOUT ANALYSIS RESULTS")
    print("="*80)
    
    # Image dimensions
    dims = results['image_dimensions']
    print(f"\n📐 Image Dimensions: {dims['width']}x{dims['height']} pixels")
    
    # All text blocks
    print(f"\n📝 All Text Blocks ({len(results['text_blocks'])} found):")
    print("-" * 80)
    for i, block in enumerate(results['text_blocks'], 1):
        print(f"\n{i}. Text: '{block['text']}'")
        print(f"   Confidence: {block['confidence']:.2f}%")
        print(f"   Position (normalized): L={block['bbox']['Left']:.3f}, T={block['bbox']['Top']:.3f}, "
              f"W={block['bbox']['Width']:.3f}, H={block['bbox']['Height']:.3f}")
        print(f"   Position (pixels): x={block['bbox_pixels']['left']}, y={block['bbox_pixels']['top']}, "
              f"w={block['bbox_pixels']['width']}, h={block['bbox_pixels']['height']}")
    
    # Employee number candidates
    if results['employee_number_candidates']:
        print(f"\n🔢 Employee Number Candidates ({len(results['employee_number_candidates'])} found):")
        print("-" * 80)
        for candidate in results['employee_number_candidates']:
            print(f"\nText: '{candidate['text']}'")
            print(f"Confidence: {candidate['confidence']:.2f}%")
            print(f"Normalized BBox: {json.dumps(candidate['bbox'], indent=2)}")
            print(f"\n✅ Recommended employee_number_bbox for CardTemplate:")
            print(f"   {json.dumps(candidate['bbox'], indent=4)}")
    else:
        print(f"\n⚠️ No 7-digit employee numbers found")
    
    # Name field candidates
    if results['name_candidates']:
        print(f"\n👤 Name Field Candidates ({len(results['name_candidates'])} found):")
        print("-" * 80)
        for candidate in results['name_candidates']:
            print(f"Text: '{candidate['text']}' at position {candidate['bbox']}")
    
    # Department field candidates
    if results['department_candidates']:
        print(f"\n🏢 Department Field Candidates ({len(results['department_candidates'])} found):")
        print("-" * 80)
        for candidate in results['department_candidates']:
            print(f"Text: '{candidate['text']}' at position {candidate['bbox']}")
    
    print("\n" + "="*80)
    print("RECOMMENDED TEXTRACT QUERIES")
    print("="*80)
    print("""
Based on the analysis, use these Textract queries in your CardTemplate:

textract_queries = [
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
]
""")
    
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("""
1. Copy the recommended employee_number_bbox to scripts/register_card_template.py
2. Update the CardTemplate with accurate bounding box coordinates
3. Run: python scripts/register_card_template.py --register
4. Test OCR with: python scripts/test_ocr_with_sample.py
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_card_layout.py <image_path>")
        print("Example: python scripts/analyze_card_layout.py sample/社員証サンプル.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not os.path.exists(image_path):
        print(f"❌ Error: Image file not found: {image_path}")
        sys.exit(1)
    
    results = analyze_card_with_textract(image_path)
    
    if results:
        print_analysis_results(results)
        
        # Save results to JSON file
        output_file = 'card_layout_analysis.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Analysis results saved to: {output_file}")
