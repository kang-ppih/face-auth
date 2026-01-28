#!/usr/bin/env python3
"""
Check Sample Image Information

This script displays information about the sample employee ID card image.
"""

import os
from PIL import Image

SAMPLE_IMAGE_PATH = 'sample/社員証サンプル.png'

def check_sample_image():
    """Check and display sample image information."""
    
    print("="*80)
    print("SAMPLE IMAGE INFORMATION")
    print("="*80)
    print()
    
    # Check if file exists
    if not os.path.exists(SAMPLE_IMAGE_PATH):
        print(f"❌ Sample image not found: {SAMPLE_IMAGE_PATH}")
        return False
    
    print(f"✅ Sample image found: {SAMPLE_IMAGE_PATH}")
    print()
    
    # Get file size
    file_size = os.path.getsize(SAMPLE_IMAGE_PATH)
    print(f"File size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
    
    # Open and analyze image
    try:
        with Image.open(SAMPLE_IMAGE_PATH) as img:
            print(f"Image format: {img.format}")
            print(f"Image mode: {img.mode}")
            print(f"Image dimensions: {img.size[0]} x {img.size[1]} pixels")
            
            # Check if image has transparency
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                print(f"Transparency: Yes")
            else:
                print(f"Transparency: No")
            
            # Get DPI if available
            dpi = img.info.get('dpi')
            if dpi:
                print(f"DPI: {dpi}")
            
            print()
            print("-"*80)
            print("IMAGE PREVIEW")
            print("-"*80)
            print()
            print("Please open the image file manually to verify it contains:")
            print("  1. 社員番号 (Employee Number) - 7 digits")
            print("  2. 氏名 (Name) - Japanese characters")
            print("  3. 所属 (Department) - Optional")
            print()
            print(f"Image path: {os.path.abspath(SAMPLE_IMAGE_PATH)}")
            print()
            
            # Try to open the image with default viewer
            try:
                import platform
                import subprocess
                
                system = platform.system()
                if system == 'Windows':
                    os.startfile(os.path.abspath(SAMPLE_IMAGE_PATH))
                    print("✅ Opening image with default viewer...")
                elif system == 'Darwin':  # macOS
                    subprocess.call(['open', os.path.abspath(SAMPLE_IMAGE_PATH)])
                    print("✅ Opening image with default viewer...")
                elif system == 'Linux':
                    subprocess.call(['xdg-open', os.path.abspath(SAMPLE_IMAGE_PATH)])
                    print("✅ Opening image with default viewer...")
            except Exception as e:
                print(f"⚠️  Could not open image automatically: {str(e)}")
                print(f"   Please open manually: {os.path.abspath(SAMPLE_IMAGE_PATH)}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error analyzing image: {str(e)}")
        return False


if __name__ == "__main__":
    check_sample_image()
