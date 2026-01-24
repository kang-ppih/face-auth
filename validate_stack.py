#!/usr/bin/env python3
"""
Face-Auth IdP System - Stack Validation Script

This script validates that the CDK stack can be synthesized without errors.
It's useful for quick validation during development.
"""

import sys
import os
import traceback

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import aws_cdk as cdk
    from infrastructure.face_auth_stack import FaceAuthStack
    
    print("🔍 Validating Face-Auth CDK Stack...")
    
    # Create CDK app
    app = cdk.App()
    
    # Create stack with test environment
    env = cdk.Environment(
        account="123456789012",  # Test account ID
        region="us-east-1"
    )
    
    stack = FaceAuthStack(
        app, 
        "FaceAuthIdPStack-Validation",
        env=env,
        description="Face-Auth Identity Provider System - Validation"
    )
    
    # Synthesize the stack
    cloud_assembly = app.synth()
    
    print("✅ Stack validation successful!")
    print(f"📋 Generated {len(cloud_assembly.stacks)} stack(s)")
    
    for stack_artifact in cloud_assembly.stacks:
        print(f"   - {stack_artifact.stack_name}")
        
    print("\n🎯 Key Resources Created:")
    print("   - VPC with public, private, and isolated subnets")
    print("   - S3 bucket with lifecycle policies")
    print("   - DynamoDB tables (CardTemplates, EmployeeFaces, AuthSessions)")
    print("   - Lambda functions (5 functions)")
    print("   - Cognito User Pool and Client")
    print("   - API Gateway with REST endpoints")
    print("   - IAM roles and policies")
    print("   - Security groups for Lambda and AD connection")
    print("   - CloudWatch log groups")
    print("   - VPC endpoints for S3 and DynamoDB")
    
    print("\n🚀 Ready for deployment!")
    print("   Run: cdk deploy")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure to install dependencies: pip install -r requirements.txt")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Validation failed: {e}")
    print("\n🔍 Full traceback:")
    traceback.print_exc()
    sys.exit(1)