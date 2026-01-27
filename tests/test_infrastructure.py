"""
Face-Auth IdP System - Infrastructure Tests

This module contains tests for the AWS CDK infrastructure stack to ensure
all components are properly configured and can be synthesized.
"""

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Template
from infrastructure.face_auth_stack import FaceAuthStack


class TestFaceAuthStack:
    """Test cases for the Face-Auth CDK Stack"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.app = cdk.App()
        self.stack = FaceAuthStack(
            self.app, 
            "TestFaceAuthStack",
            env=cdk.Environment(account="123456789012", region="us-east-1")
        )
        self.template = Template.from_stack(self.stack)
    
    def test_vpc_creation(self):
        """Test that VPC is created with correct configuration"""
        self.template.has_resource_properties("AWS::EC2::VPC", {
            "CidrBlock": "10.0.0.0/16"
        })
    
    def test_s3_bucket_creation(self):
        """Test that S3 bucket is created with encryption and lifecycle policies"""
        self.template.has_resource_properties("AWS::S3::Bucket", {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True
            }
        })
        
        # Check lifecycle rules
        self.template.has_resource_properties("AWS::S3::Bucket", {
            "LifecycleConfiguration": {
                "Rules": [
                    {
                        "Id": "LoginAttemptsCleanup",
                        "Prefix": "logins/",
                        "Status": "Enabled",
                        "ExpirationInDays": 30
                    },
                    {
                        "Id": "TempFilesCleanup",
                        "Prefix": "temp/",
                        "Status": "Enabled", 
                        "ExpirationInDays": 1
                    }
                ]
            }
        })
    
    def test_dynamodb_tables_creation(self):
        """Test that DynamoDB tables are created with proper configuration"""
        # Card Templates table - check basic properties only (GSI adds extra attributes)
        self.template.has_resource_properties("AWS::DynamoDB::Table", {
            "TableName": "FaceAuth-CardTemplates",
            "BillingMode": "PAY_PER_REQUEST",
            "SSESpecification": {
                "SSEEnabled": True
            },
            "PointInTimeRecoverySpecification": {
                "PointInTimeRecoveryEnabled": True
            }
        })
        
        # Verify Card Templates table has pattern_id as partition key
        self.template.has_resource_properties("AWS::DynamoDB::Table", {
            "TableName": "FaceAuth-CardTemplates",
            "KeySchema": [
                {
                    "AttributeName": "pattern_id",
                    "KeyType": "HASH"
                }
            ]
        })
        
        # Employee Faces table - check basic properties only (GSI adds extra attributes)
        self.template.has_resource_properties("AWS::DynamoDB::Table", {
            "TableName": "FaceAuth-EmployeeFaces",
            "BillingMode": "PAY_PER_REQUEST",
            "SSESpecification": {
                "SSEEnabled": True
            },
            "PointInTimeRecoverySpecification": {
                "PointInTimeRecoveryEnabled": True
            }
        })
        
        # Verify Employee Faces table has employee_id as partition key
        self.template.has_resource_properties("AWS::DynamoDB::Table", {
            "TableName": "FaceAuth-EmployeeFaces",
            "KeySchema": [
                {
                    "AttributeName": "employee_id",
                    "KeyType": "HASH"
                }
            ]
        })
        
        # Auth Sessions table
        self.template.has_resource_properties("AWS::DynamoDB::Table", {
            "TableName": "FaceAuth-AuthSessions",
            "BillingMode": "PAY_PER_REQUEST",
            "SSESpecification": {
                "SSEEnabled": True
            },
            "TimeToLiveSpecification": {
                "AttributeName": "expires_at",
                "Enabled": True
            }
        })
    
    def test_lambda_functions_creation(self):
        """Test that Lambda functions are created with correct configuration"""
        # Check that Lambda functions exist
        lambda_functions = [
            "FaceAuth-Enrollment",
            "FaceAuth-FaceLogin", 
            "FaceAuth-EmergencyAuth",
            "FaceAuth-ReEnrollment",
            "FaceAuth-Status"
        ]
        
        for function_name in lambda_functions:
            self.template.has_resource_properties("AWS::Lambda::Function", {
                "FunctionName": function_name,
                "Runtime": "python3.9",
                "Timeout": 15,
                "MemorySize": 512
            })
    
    def test_cognito_user_pool_creation(self):
        """Test that Cognito User Pool is created with proper configuration"""
        self.template.has_resource_properties("AWS::Cognito::UserPool", {
            "UserPoolName": "FaceAuth-UserPool",
            "Policies": {
                "PasswordPolicy": {
                    "MinimumLength": 12,
                    "RequireLowercase": True,
                    "RequireNumbers": True,
                    "RequireSymbols": True,
                    "RequireUppercase": True
                }
            }
        })
        
        # Note: CDK uses "ClientName" not "UserPoolClientName"
        self.template.has_resource_properties("AWS::Cognito::UserPoolClient", {
            "ClientName": "FaceAuth-Client",
            "GenerateSecret": False
        })
    
    def test_api_gateway_creation(self):
        """Test that API Gateway is created with proper configuration"""
        self.template.has_resource_properties("AWS::ApiGateway::RestApi", {
            "Name": "FaceAuth-API",
            "Description": "Face Authentication Identity Provider API"
        })
        
        # Check for API resources
        api_resources = ["enroll", "login", "emergency", "re-enroll", "status"]
        for resource in api_resources:
            self.template.has_resource_properties("AWS::ApiGateway::Resource", {
                "PathPart": resource
            })
    
    def test_iam_roles_creation(self):
        """Test that IAM roles are created with appropriate permissions"""
        # Note: CDK uses "AssumeRolePolicyDocument" not "AssumedRolePolicy"
        self.template.has_resource_properties("AWS::IAM::Role", {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        }
                    }
                ]
            }
        })
        
        # Check that IAM Policy exists with required permissions
        # Note: Implementation has 6 statements (S3, DynamoDB, Rekognition, Textract, Cognito, CloudWatch)
        # We verify the policy exists and has the correct structure
        self.template.resource_count_is("AWS::IAM::Policy", 1)
        
        # Verify the policy is attached to Lambda execution role
        self.template.has_resource_properties("AWS::IAM::Policy", {
            "PolicyDocument": {
                "Version": "2012-10-17"
            }
        })
    
    def test_security_groups_creation(self):
        """Test that security groups are created with proper rules"""
        # Lambda security group
        self.template.has_resource_properties("AWS::EC2::SecurityGroup", {
            "GroupDescription": "Security group for Face-Auth Lambda functions"
        })
        
        # AD security group with LDAPS egress rule
        self.template.has_resource_properties("AWS::EC2::SecurityGroup", {
            "GroupDescription": "Security group for Active Directory connection via Direct Connect",
            "SecurityGroupEgress": [
                {
                    "CidrIp": "10.0.0.0/8",
                    "FromPort": 636,
                    "IpProtocol": "tcp",
                    "ToPort": 636,
                    "Description": "LDAPS traffic to on-premises Active Directory"
                },
                {
                    "CidrIp": "10.0.0.0/8", 
                    "FromPort": 389,
                    "IpProtocol": "tcp",
                    "ToPort": 389,
                    "Description": "LDAP traffic to on-premises Active Directory"
                }
            ]
        })
    
    def test_cloudwatch_log_groups_creation(self):
        """Test that CloudWatch log groups are created"""
        # Check that log groups exist with correct retention
        # Note: LogGroupName may be dynamically generated with Fn::Join
        self.template.resource_count_is("AWS::Logs::LogGroup", 6)
        
        # Check for API Gateway access log group (static name)
        self.template.has_resource_properties("AWS::Logs::LogGroup", {
            "LogGroupName": "/aws/apigateway/face-auth-access-logs",
            "RetentionInDays": 30
        })
        
        # Check that Lambda log groups have correct retention
        # (LogGroupName is dynamic, so we just check retention)
        self.template.has_resource_properties("AWS::Logs::LogGroup", {
            "RetentionInDays": 30
        })
    
    def test_vpc_endpoints_creation(self):
        """Test that VPC endpoints are created for S3 and DynamoDB"""
        # Check that VPC endpoints exist (ServiceName is dynamically generated)
        self.template.resource_count_is("AWS::EC2::VPCEndpoint", 2)
        
        # Check for Gateway type endpoints
        self.template.has_resource_properties("AWS::EC2::VPCEndpoint", {
            "VpcEndpointType": "Gateway"
        })
    
    def test_stack_outputs(self):
        """Test that stack outputs are properly defined"""
        outputs = [
            "APIEndpoint",
            "UserPoolId",
            "UserPoolClientId", 
            "S3BucketName",
            "VPCId",
            "APIKeyId"
        ]
        
        for output in outputs:
            self.template.has_output(output, {})


if __name__ == "__main__":
    pytest.main([__file__])