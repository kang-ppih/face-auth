#!/usr/bin/env python3
"""
Face-Auth IdP System - Data Models Demonstration

This script demonstrates the usage of the data models and DynamoDB schemas
implemented for the Face-Auth system.

Requirements: 5.5, 7.4
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add the lambda directory to the path so we can import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda'))

from shared.models import (
    EmployeeInfo,
    FaceData,
    AuthenticationSession,
    CardTemplate,
    EmployeeFaceRecord,
    ErrorResponse,
    ErrorCodes
)


def demonstrate_employee_info():
    """Demonstrate EmployeeInfo data model"""
    print("=== EmployeeInfo Data Model ===")
    
    # Create a valid employee info
    employee = EmployeeInfo(
        employee_id="123456",
        name="김철수",
        department="개발팀",
        card_type="standard_employee",
        extracted_confidence=0.95
    )
    
    print(f"Employee ID: {employee.employee_id}")
    print(f"Name: {employee.name}")
    print(f"Department: {employee.department}")
    print(f"Valid: {employee.validate()}")
    
    # Convert to dictionary for DynamoDB storage
    data = employee.to_dict()
    print(f"DynamoDB format: {data}")
    
    # Round-trip conversion
    employee2 = EmployeeInfo.from_dict(data)
    print(f"Round-trip successful: {employee.employee_id == employee2.employee_id}")
    print()


def demonstrate_face_data():
    """Demonstrate FaceData data model"""
    print("=== FaceData Data Model ===")
    
    face_data = FaceData(
        face_id="face-abc123",
        employee_id="123456",
        bounding_box={"Width": 0.5, "Height": 0.6, "Left": 0.2, "Top": 0.1},
        confidence=95.5,
        landmarks=[{"Type": "eyeLeft", "X": 0.3, "Y": 0.4}],
        thumbnail_s3_key="enroll/123456/face_thumbnail.jpg"
    )
    
    print(f"Face ID: {face_data.face_id}")
    print(f"Employee ID: {face_data.employee_id}")
    print(f"Confidence: {face_data.confidence}")
    
    # Convert to Rekognition format
    rekognition_format = face_data.to_rekognition_format()
    print(f"Rekognition format: {rekognition_format}")
    
    # Convert to DynamoDB format (handles float to Decimal conversion)
    data = face_data.to_dict()
    print(f"DynamoDB format confidence type: {type(data['confidence'])}")
    print()


def demonstrate_card_template():
    """Demonstrate CardTemplate data model"""
    print("=== CardTemplate Data Model ===")
    
    template = CardTemplate(
        pattern_id="company_card_v1",
        card_type="standard_employee",
        logo_position={"x": 50, "y": 30, "width": 100, "height": 50},
        fields=[
            {
                "field_name": "employee_id",
                "query_phrase": "사번은 무엇입니까?",
                "expected_format": r"\d{6}"
            },
            {
                "field_name": "employee_name",
                "query_phrase": "성명은 무엇입니까?",
                "expected_format": r"[가-힣]{2,4}"
            }
        ],
        created_at=datetime.now(),
        is_active=True,
        description="Standard employee ID card template"
    )
    
    print(f"Pattern ID: {template.pattern_id}")
    print(f"Card Type: {template.card_type}")
    print(f"Fields: {len(template.fields)}")
    
    # Generate Textract queries
    queries = template.build_textract_queries()
    print(f"Textract queries: {queries}")
    
    # Validate extracted data
    valid_data = {"employee_id": "123456", "employee_name": "김철수"}
    invalid_data = {"employee_id": "12345A", "employee_name": "김철수"}
    
    print(f"Valid data passes: {template.validate_extracted_data(valid_data)}")
    print(f"Invalid data passes: {template.validate_extracted_data(invalid_data)}")
    print()


def demonstrate_authentication_session():
    """Demonstrate AuthenticationSession data model"""
    print("=== AuthenticationSession Data Model ===")
    
    now = datetime.now()
    expires = now + timedelta(hours=1)
    
    session = AuthenticationSession(
        session_id="session-xyz789",
        employee_id="123456",
        auth_method="face",
        created_at=now,
        expires_at=expires,
        cognito_token="jwt-token-here",
        ip_address="192.168.1.100"
    )
    
    print(f"Session ID: {session.session_id}")
    print(f"Employee ID: {session.employee_id}")
    print(f"Auth Method: {session.auth_method}")
    print(f"Valid: {session.is_valid()}")
    
    # Convert to DynamoDB format (handles datetime to epoch conversion)
    data = session.to_dict()
    print(f"DynamoDB expires_at type: {type(data['expires_at'])}")
    
    # Round-trip conversion
    session2 = AuthenticationSession.from_dict(data)
    print(f"Round-trip successful: {session.session_id == session2.session_id}")
    print()


def demonstrate_employee_face_record():
    """Demonstrate EmployeeFaceRecord data model"""
    print("=== EmployeeFaceRecord Data Model ===")
    
    face_data = FaceData(
        face_id="face-def456",
        employee_id="123456",
        bounding_box={"Width": 0.4, "Height": 0.5, "Left": 0.3, "Top": 0.2},
        confidence=97.8,
        landmarks=[],
        thumbnail_s3_key="enroll/123456/face_thumbnail.jpg"
    )
    
    record = EmployeeFaceRecord(
        employee_id="123456",
        face_id="face-def456",
        enrollment_date=datetime.now(),
        last_login=None,
        thumbnail_s3_key="enroll/123456/face_thumbnail.jpg",
        is_active=True,
        re_enrollment_count=0,
        face_data=face_data
    )
    
    print(f"Employee ID: {record.employee_id}")
    print(f"Face ID: {record.face_id}")
    print(f"Active: {record.is_active}")
    print(f"Re-enrollment count: {record.re_enrollment_count}")
    
    # Convert to DynamoDB format
    data = record.to_dict()
    print(f"DynamoDB format has face_data: {'face_data' in data}")
    print()


def demonstrate_error_response():
    """Demonstrate ErrorResponse data model"""
    print("=== ErrorResponse Data Model ===")
    
    error = ErrorResponse(
        error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
        user_message="사원증 규격 불일치",
        system_reason="No matching card template found in database",
        timestamp=datetime.now(),
        request_id="req-12345"
    )
    
    print(f"Error Code: {error.error_code}")
    print(f"User Message: {error.user_message}")
    print(f"System Reason: {error.system_reason}")
    
    # Convert to API response format
    api_response = error.to_dict()
    print(f"API Response: {api_response}")
    print()


def main():
    """Main demonstration function"""
    print("Face-Auth IdP System - Data Models Demonstration")
    print("=" * 60)
    print()
    
    demonstrate_employee_info()
    demonstrate_face_data()
    demonstrate_card_template()
    demonstrate_authentication_session()
    demonstrate_employee_face_record()
    demonstrate_error_response()
    
    print("=" * 60)
    print("Data models demonstration completed!")
    print("\nKey Features Demonstrated:")
    print("✓ Data validation and type checking")
    print("✓ DynamoDB-compatible serialization (float to Decimal conversion)")
    print("✓ Round-trip data conversion")
    print("✓ Amazon Rekognition API format conversion")
    print("✓ Amazon Textract query generation")
    print("✓ Error handling and response formatting")


if __name__ == "__main__":
    main()