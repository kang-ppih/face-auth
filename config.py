"""
Face-Auth IdP System - Configuration Settings

This module contains configuration settings and constants for the Face-Auth system.
These settings are used across the infrastructure and Lambda functions.
"""

import os
from typing import Dict, Any

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'ap-northeast-1')
AWS_ACCOUNT_ID = os.getenv('CDK_DEFAULT_ACCOUNT')

# Face Authentication Configuration
FACE_AUTH_CONFIG = {
    # Rekognition settings
    'REKOGNITION_COLLECTION_ID': 'face-auth-employees',
    'LIVENESS_CONFIDENCE_THRESHOLD': 90.0,
    'FACE_MATCH_CONFIDENCE_THRESHOLD': 95.0,
    
    # Image processing settings
    'THUMBNAIL_SIZE': (200, 200),
    'THUMBNAIL_QUALITY': 85,
    'MAX_IMAGE_SIZE_MB': 10,
    
    # Timeout settings (in seconds)
    'AD_CONNECTION_TIMEOUT': 10,
    'LAMBDA_TIMEOUT': 15,
    'API_GATEWAY_TIMEOUT': 29,
    
    # S3 bucket structure
    'S3_FOLDERS': {
        'ENROLL': 'enroll/',
        'LOGINS': 'logins/',
        'TEMP': 'temp/'
    },
    
    # DynamoDB table names (will be prefixed with stack name)
    'DYNAMODB_TABLES': {
        'CARD_TEMPLATES': 'FaceAuth-CardTemplates',
        'EMPLOYEE_FACES': 'FaceAuth-EmployeeFaces',
        'AUTH_SESSIONS': 'FaceAuth-AuthSessions'
    },
    
    # Cognito settings
    'COGNITO_CONFIG': {
        'ACCESS_TOKEN_VALIDITY_HOURS': 1,
        'ID_TOKEN_VALIDITY_HOURS': 1,
        'REFRESH_TOKEN_VALIDITY_DAYS': 30
    },
    
    # API Gateway settings
    'API_CONFIG': {
        'THROTTLE_RATE_LIMIT': 100,
        'THROTTLE_BURST_LIMIT': 200,
        'DAILY_QUOTA_LIMIT': 10000
    },
    
    # Security settings
    'SECURITY_CONFIG': {
        'MIN_PASSWORD_LENGTH': 12,
        'RATE_LIMIT_ATTEMPTS': 5,
        'RATE_LIMIT_WINDOW_MINUTES': 15,
        'SESSION_TIMEOUT_HOURS': 8
    }
}

# Active Directory Configuration
AD_CONFIG = {
    'SERVER_URL': 'ldaps://ad.company.com',  # Replace with actual AD server
    'BASE_DN': 'ou=employees,dc=company,dc=com',  # Replace with actual base DN
    'TIMEOUT': 10,
    'USE_SSL': True,
    'PORT': 636  # LDAPS port
}

# Error Messages Configuration
ERROR_MESSAGES = {
    # System judgment errors (specific messages)
    'ID_CARD_FORMAT_MISMATCH': '사원증 규격 불일치',
    'REGISTRATION_INFO_MISMATCH': '등록 정보 불일치',
    'ACCOUNT_DISABLED': '계정 비활성화',
    
    # Technical issues (generic message)
    'LIVENESS_FAILED': '밝은 곳에서 다시 시도해주세요',
    'CAMERA_ERROR': '밝은 곳에서 다시 시도해주세요',
    'NETWORK_ERROR': '밝은 곳에서 다시 시도해주세요',
    'GENERIC_ERROR': '밝은 곳에서 다시 시도해주세요'
}

# Card Template Configuration
CARD_TEMPLATE_EXAMPLE = {
    'pattern_id': 'company_standard_v1',
    'card_type': 'standard_employee',
    'logo_position': {
        'x': 50,
        'y': 30,
        'width': 100,
        'height': 50
    },
    'fields': [
        {
            'field_name': 'employee_id',
            'query_phrase': '사번은 무엇입니까?',
            'expected_format': r'\d{6}',
            'required': True
        },
        {
            'field_name': 'employee_name',
            'query_phrase': '성명은 무엇입니까?',
            'expected_format': r'[가-힣]{2,4}',
            'required': True
        },
        {
            'field_name': 'department',
            'query_phrase': '부서는 무엇입니까?',
            'expected_format': r'[가-힣\s]+',
            'required': False
        }
    ],
    'is_active': True
}

def get_environment_config() -> Dict[str, Any]:
    """
    Get environment-specific configuration
    
    Returns:
        Dictionary containing environment configuration
    """
    return {
        'aws_region': AWS_REGION,
        'aws_account_id': AWS_ACCOUNT_ID,
        'face_auth_config': FACE_AUTH_CONFIG,
        'ad_config': AD_CONFIG,
        'error_messages': ERROR_MESSAGES
    }

def get_lambda_environment_variables() -> Dict[str, str]:
    """
    Get environment variables for Lambda functions
    
    Returns:
        Dictionary of environment variables
    """
    return {
        'AWS_REGION': AWS_REGION,
        'REKOGNITION_COLLECTION_ID': FACE_AUTH_CONFIG['REKOGNITION_COLLECTION_ID'],
        'LIVENESS_CONFIDENCE_THRESHOLD': str(FACE_AUTH_CONFIG['LIVENESS_CONFIDENCE_THRESHOLD']),
        'FACE_MATCH_CONFIDENCE_THRESHOLD': str(FACE_AUTH_CONFIG['FACE_MATCH_CONFIDENCE_THRESHOLD']),
        'AD_CONNECTION_TIMEOUT': str(FACE_AUTH_CONFIG['AD_CONNECTION_TIMEOUT']),
        'LAMBDA_TIMEOUT': str(FACE_AUTH_CONFIG['LAMBDA_TIMEOUT']),
        'AD_SERVER_URL': AD_CONFIG['SERVER_URL'],
        'AD_BASE_DN': AD_CONFIG['BASE_DN']
    }