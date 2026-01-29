#!/usr/bin/env python3
"""Fix emoji encoding issues in test scripts."""

import sys

def fix_emoji_in_file(filepath):
    """Replace emoji with ASCII equivalents."""
    
    replacements = {
        '✅': '[OK]',
        '❌': '[ERROR]',
        '⚠️': '[WARN]',
        '🎉': '[SUCCESS]',
        '📤': '[SEND]',
        '📥': '[RECV]',
        '🔍': '[CHECK]',
        '⏳': '[WAIT]'
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        for emoji, replacement in replacements.items():
            content = content.replace(emoji, replacement)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed: {filepath}")
        return True
        
    except Exception as e:
        print(f"Error fixing {filepath}: {str(e)}")
        return False

if __name__ == "__main__":
    files = [
        'scripts/test_end_to_end_enrollment.py',
        'scripts/test_ocr_via_lambda.py',
        'scripts/test_aws_connectivity.py'
    ]
    
    for filepath in files:
        fix_emoji_in_file(filepath)
