#!/usr/bin/env python3
"""
End-to-End Enrollment Test

This script tests the complete enrollment flow:
1. Read sample employee ID card image
2. Read sample face image
3. Send enrollment request to API
4. Verify response
5. Check if images are stored in S3
6. Check if data is stored in DynamoDB
7. Check if face is indexed in Rekognition

Usage:
    python scripts/test_end_to_end_enrollment.py
"""

import requests
import boto3
import base64
import json
import time
import os
from datetime import datetime


class EndToEndEnrollmentTest:
    """End-to-end test for employee enrollment"""
    
    def __init__(self):
        """Initialize test configuration"""
        # API Configuration
        self.api_endpoint = os.environ.get(
            'API_ENDPOINT',
            'https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod'
        )
        self.enrollment_url = f"{self.api_endpoint}/auth/enroll"
        
        # AWS Configuration
        self.region = os.environ.get('AWS_REGION', 'ap-northeast-1')
        self.profile = os.environ.get('AWS_PROFILE', 'dev')
        self.s3_bucket = os.environ.get('S3_BUCKET', 'face-auth-images-979431736455-ap-northeast-1')
        self.dynamodb_table = os.environ.get('DYNAMODB_TABLE', 'FaceAuth-EmployeeFaces')
        self.rekognition_collection = os.environ.get('REKOGNITION_COLLECTION', 'face-auth-employees')
        
        # Test Data
        self.test_employee_id = f"TEST{int(time.time()) % 10000:03d}"  # TEST001-TEST999
        
        # Initialize AWS clients
        session = boto3.Session(profile_name=self.profile, region_name=self.region)
        self.s3_client = session.client('s3')
        self.dynamodb_client = session.client('dynamodb')
        self.rekognition_client = session.client('rekognition')
        
        print("="*80)
        print("END-TO-END ENROLLMENT TEST")
        print("="*80)
        print(f"\nConfiguration:")
        print(f"  API Endpoint: {self.api_endpoint}")
        print(f"  Region: {self.region}")
        print(f"  Profile: {self.profile}")
        print(f"  S3 Bucket: {self.s3_bucket}")
        print(f"  DynamoDB Table: {self.dynamodb_table}")
        print(f"  Rekognition Collection: {self.rekognition_collection}")
        print(f"  Test Employee ID: {self.test_employee_id}")
        print()
    
    def load_image_as_base64(self, image_path: str) -> str:
        """Load image file and convert to base64"""
        try:
            with open(image_path, 'rb') as f:
                image_bytes = f.read()
            return base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            print(f"❌ Error loading image {image_path}: {str(e)}")
            return None
    
    def test_step_1_prepare_images(self):
        """Step 1: Prepare test images"""
        print("-"*80)
        print("STEP 1: Preparing Test Images")
        print("-"*80)
        
        # Check if sample images exist
        id_card_path = 'sample/社員証サンプル.png'
        face_image_path = 'sample/face_sample.jpg'
        
        # If face sample doesn't exist, use ID card as placeholder
        if not os.path.exists(face_image_path):
            print(f"⚠️  Face sample not found, using ID card as placeholder")
            face_image_path = id_card_path
        
        if not os.path.exists(id_card_path):
            print(f"❌ ID card sample not found: {id_card_path}")
            return False, None, None
        
        print(f"✅ Loading ID card: {id_card_path}")
        id_card_b64 = self.load_image_as_base64(id_card_path)
        
        print(f"✅ Loading face image: {face_image_path}")
        face_image_b64 = self.load_image_as_base64(face_image_path)
        
        if not id_card_b64 or not face_image_b64:
            return False, None, None
        
        print(f"✅ Images loaded successfully")
        print(f"   ID card size: {len(id_card_b64)} bytes (base64)")
        print(f"   Face image size: {len(face_image_b64)} bytes (base64)")
        
        return True, id_card_b64, face_image_b64
    
    def test_step_2_send_enrollment_request(self, id_card_b64: str, face_image_b64: str):
        """Step 2: Send enrollment request to API"""
        print("\n" + "-"*80)
        print("STEP 2: Sending Enrollment Request to API")
        print("-"*80)
        
        payload = {
            "id_card_image": id_card_b64,
            "face_image": face_image_b64
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        print(f"📤 Sending POST request to: {self.enrollment_url}")
        print(f"   Payload size: {len(json.dumps(payload))} bytes")
        
        try:
            response = requests.post(
                self.enrollment_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            print(f"\n📥 Response received:")
            print(f"   Status Code: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            try:
                response_data = response.json()
                print(f"\n   Response Body:")
                print(f"   {json.dumps(response_data, indent=4, ensure_ascii=False)}")
            except:
                print(f"\n   Response Body (raw):")
                print(f"   {response.text}")
                response_data = {}
            
            if response.status_code == 200:
                print(f"\n✅ Enrollment request successful!")
                return True, response_data
            else:
                print(f"\n❌ Enrollment request failed with status {response.status_code}")
                return False, response_data
                
        except Exception as e:
            print(f"\n❌ Error sending request: {str(e)}")
            return False, {}
    
    def test_step_3_verify_s3_storage(self, employee_id: str):
        """Step 3: Verify images are stored in S3"""
        print("\n" + "-"*80)
        print("STEP 3: Verifying S3 Storage")
        print("-"*80)
        
        # Wait a bit for async processing
        print("⏳ Waiting 3 seconds for S3 upload...")
        time.sleep(3)
        
        # Check for enrollment images
        s3_prefix = f"enroll/{employee_id}/"
        
        print(f"🔍 Checking S3 bucket: {self.s3_bucket}")
        print(f"   Prefix: {s3_prefix}")
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=s3_prefix
            )
            
            objects = response.get('Contents', [])
            
            if objects:
                print(f"\n✅ Found {len(objects)} object(s) in S3:")
                for obj in objects:
                    print(f"   - {obj['Key']} ({obj['Size']} bytes)")
                return True
            else:
                print(f"\n❌ No objects found in S3 with prefix: {s3_prefix}")
                
                # List all objects to debug
                print(f"\n🔍 Listing all objects in bucket (first 10):")
                all_response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    MaxKeys=10
                )
                all_objects = all_response.get('Contents', [])
                if all_objects:
                    for obj in all_objects:
                        print(f"   - {obj['Key']}")
                else:
                    print(f"   (bucket is empty)")
                
                return False
                
        except Exception as e:
            print(f"\n❌ Error checking S3: {str(e)}")
            return False
    
    def test_step_4_verify_dynamodb_record(self, employee_id: str):
        """Step 4: Verify employee record in DynamoDB"""
        print("\n" + "-"*80)
        print("STEP 4: Verifying DynamoDB Record")
        print("-"*80)
        
        print(f"🔍 Checking DynamoDB table: {self.dynamodb_table}")
        print(f"   Employee ID: {employee_id}")
        
        try:
            response = self.dynamodb_client.get_item(
                TableName=self.dynamodb_table,
                Key={
                    'employee_id': {'S': employee_id}
                }
            )
            
            item = response.get('Item')
            
            if item:
                print(f"\n✅ Employee record found in DynamoDB:")
                print(f"   Employee ID: {item.get('employee_id', {}).get('S')}")
                print(f"   Name: {item.get('name', {}).get('S')}")
                print(f"   Face ID: {item.get('face_id', {}).get('S')}")
                print(f"   Enrolled At: {item.get('enrolled_at', {}).get('S')}")
                return True, item
            else:
                print(f"\n❌ No record found in DynamoDB for employee: {employee_id}")
                
                # Scan table to see what's there
                print(f"\n🔍 Scanning table (first 5 records):")
                scan_response = self.dynamodb_client.scan(
                    TableName=self.dynamodb_table,
                    Limit=5
                )
                items = scan_response.get('Items', [])
                if items:
                    for item in items:
                        emp_id = item.get('employee_id', {}).get('S', 'N/A')
                        print(f"   - Employee ID: {emp_id}")
                else:
                    print(f"   (table is empty)")
                
                return False, None
                
        except Exception as e:
            print(f"\n❌ Error checking DynamoDB: {str(e)}")
            return False, None
    
    def test_step_5_verify_rekognition_face(self, face_id: str):
        """Step 5: Verify face is indexed in Rekognition"""
        print("\n" + "-"*80)
        print("STEP 5: Verifying Rekognition Face Index")
        print("-"*80)
        
        if not face_id:
            print("⚠️  No face_id provided, skipping Rekognition check")
            return False
        
        print(f"🔍 Checking Rekognition collection: {self.rekognition_collection}")
        print(f"   Face ID: {face_id}")
        
        try:
            response = self.rekognition_client.list_faces(
                CollectionId=self.rekognition_collection,
                MaxResults=100
            )
            
            faces = response.get('Faces', [])
            
            # Check if our face_id exists
            face_found = any(face['FaceId'] == face_id for face in faces)
            
            if face_found:
                print(f"\n✅ Face found in Rekognition collection!")
                print(f"   Total faces in collection: {len(faces)}")
                return True
            else:
                print(f"\n❌ Face not found in Rekognition collection")
                print(f"   Total faces in collection: {len(faces)}")
                if faces:
                    print(f"   Sample face IDs:")
                    for face in faces[:3]:
                        print(f"   - {face['FaceId']}")
                return False
                
        except Exception as e:
            print(f"\n❌ Error checking Rekognition: {str(e)}")
            return False
    
    def run_test(self):
        """Run complete end-to-end test"""
        start_time = time.time()
        results = {
            'step_1_images': False,
            'step_2_api': False,
            'step_3_s3': False,
            'step_4_dynamodb': False,
            'step_5_rekognition': False
        }
        
        # Step 1: Prepare images
        success, id_card_b64, face_image_b64 = self.test_step_1_prepare_images()
        results['step_1_images'] = success
        if not success:
            self.print_summary(results, start_time)
            return False
        
        # Step 2: Send enrollment request
        success, response_data = self.test_step_2_send_enrollment_request(
            id_card_b64, face_image_b64
        )
        results['step_2_api'] = success
        
        # Extract employee_id from response
        employee_id = response_data.get('employee_id', self.test_employee_id)
        face_id = response_data.get('face_id')
        
        # Step 3: Verify S3 storage
        results['step_3_s3'] = self.test_step_3_verify_s3_storage(employee_id)
        
        # Step 4: Verify DynamoDB record
        success, item = self.test_step_4_verify_dynamodb_record(employee_id)
        results['step_4_dynamodb'] = success
        
        if item and not face_id:
            face_id = item.get('face_id', {}).get('S')
        
        # Step 5: Verify Rekognition face
        if face_id:
            results['step_5_rekognition'] = self.test_step_5_verify_rekognition_face(face_id)
        
        # Print summary
        self.print_summary(results, start_time)
        
        return all(results.values())
    
    def print_summary(self, results: dict, start_time: float):
        """Print test summary"""
        elapsed_time = time.time() - start_time
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        print(f"\nTest Results:")
        for step, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {step}: {status}")
        
        total_steps = len(results)
        passed_steps = sum(1 for success in results.values() if success)
        
        print(f"\nOverall: {passed_steps}/{total_steps} steps passed")
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        
        if all(results.values()):
            print("\n🎉 END-TO-END TEST PASSED!")
            print("\nThe complete enrollment flow is working:")
            print("  ✅ Images loaded successfully")
            print("  ✅ API request successful")
            print("  ✅ Images stored in S3")
            print("  ✅ Employee record in DynamoDB")
            print("  ✅ Face indexed in Rekognition")
        else:
            print("\n⚠️  END-TO-END TEST FAILED")
            print("\nPlease check the failed steps above for details.")
            print("\nCommon issues:")
            print("  - Lambda function errors (check CloudWatch Logs)")
            print("  - Missing Pillow dependency (check LAMBDA_IMPORT_ERROR_DIAGNOSIS.md)")
            print("  - IAM permission issues")
            print("  - Network/VPC configuration issues")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    import sys
    
    # Check for required environment variables
    required_env_vars = []
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Run test
    test = EndToEndEnrollmentTest()
    success = test.run_test()
    
    sys.exit(0 if success else 1)
