#!/usr/bin/env python3
"""
Test AWS Service Connectivity

This script tests connectivity to various AWS services from the local environment.
"""

import boto3
import sys
from botocore.exceptions import ClientError, EndpointConnectionError

def test_service_connectivity(service_name, region='ap-northeast-1', profile='dev'):
    """Test connectivity to an AWS service."""
    
    print(f"\nTesting {service_name}...")
    print("-" * 60)
    
    try:
        session = boto3.Session(profile_name=profile, region_name=region)
        client = session.client(service_name)
        
        # Try a simple operation
        if service_name == 'sts':
            response = client.get_caller_identity()
            print(f"✅ {service_name.upper()} connection successful")
            print(f"   Account: {response['Account']}")
            print(f"   User: {response['Arn']}")
            
        elif service_name == 's3':
            response = client.list_buckets()
            print(f"✅ {service_name.upper()} connection successful")
            print(f"   Buckets found: {len(response['Buckets'])}")
            
        elif service_name == 'dynamodb':
            response = client.list_tables(Limit=5)
            print(f"✅ {service_name.upper()} connection successful")
            print(f"   Tables found: {len(response['TableNames'])}")
            
        elif service_name == 'textract':
            # Textract doesn't have a simple list operation
            # Try to get service endpoint
            endpoint = client._endpoint
            print(f"✅ {service_name.upper()} client created successfully")
            print(f"   Endpoint: {endpoint.host}")
            
            # Try a minimal operation (this will fail but tests connectivity)
            try:
                client.detect_document_text(Document={'Bytes': b'test'})
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['InvalidParameterException', 'InvalidS3ObjectException']:
                    print(f"✅ {service_name.upper()} endpoint is reachable")
                    print(f"   (Got expected error: {error_code})")
                else:
                    print(f"⚠️  {service_name.upper()} returned error: {error_code}")
            except EndpointConnectionError as e:
                print(f"❌ {service_name.upper()} endpoint connection failed")
                print(f"   Error: {str(e)}")
                return False
                
        elif service_name == 'rekognition':
            # Try to list collections
            try:
                response = client.list_collections()
                print(f"✅ {service_name.upper()} connection successful")
                print(f"   Collections found: {len(response['CollectionIds'])}")
            except ClientError as e:
                print(f"⚠️  {service_name.upper()} error: {e.response['Error']['Code']}")
        
        return True
        
    except EndpointConnectionError as e:
        print(f"❌ {service_name.upper()} endpoint connection failed")
        print(f"   Error: {str(e)}")
        print(f"   This usually indicates:")
        print(f"   - Network connectivity issues")
        print(f"   - Proxy configuration needed")
        print(f"   - VPN connection required")
        return False
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"❌ {service_name.upper()} client error: {error_code}")
        print(f"   Message: {e.response['Error']['Message']}")
        return False
        
    except Exception as e:
        print(f"❌ {service_name.upper()} unexpected error: {str(e)}")
        return False


def check_network_settings():
    """Check network and proxy settings."""
    
    print("\n" + "="*80)
    print("NETWORK SETTINGS")
    print("="*80)
    
    import os
    
    # Check proxy settings
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
    no_proxy = os.environ.get('NO_PROXY') or os.environ.get('no_proxy')
    
    print("\nProxy Settings:")
    print(f"  HTTP_PROXY: {http_proxy or '(not set)'}")
    print(f"  HTTPS_PROXY: {https_proxy or '(not set)'}")
    print(f"  NO_PROXY: {no_proxy or '(not set)'}")
    
    # Check boto3 configuration
    print("\nBoto3 Configuration:")
    session = boto3.Session(profile_name='dev')
    print(f"  Profile: dev")
    print(f"  Region: {session.region_name}")
    
    # Check if using default credentials
    credentials = session.get_credentials()
    if credentials:
        print(f"  Access Key: {credentials.access_key[:10]}...")
        print(f"  Credentials Source: {credentials.method}")


def main():
    """Main test function."""
    
    print("="*80)
    print("AWS SERVICE CONNECTIVITY TEST")
    print("="*80)
    
    # Check network settings first
    check_network_settings()
    
    # Test services
    print("\n" + "="*80)
    print("SERVICE CONNECTIVITY TESTS")
    print("="*80)
    
    services = [
        'sts',       # Always works if credentials are valid
        's3',        # Basic service
        'dynamodb',  # Basic service
        'textract',  # The problematic service
        'rekognition'  # Another service we use
    ]
    
    results = {}
    for service in services:
        results[service] = test_service_connectivity(service)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print()
    
    success_count = sum(1 for success in results.values() if success)
    total_count = len(results)
    
    for service, success in results.items():
        status = "✅ OK" if success else "❌ FAILED"
        print(f"  {service.upper()}: {status}")
    
    print()
    print(f"Total: {success_count}/{total_count} services accessible")
    
    if not results.get('textract'):
        print("\n" + "="*80)
        print("TEXTRACT CONNECTION TROUBLESHOOTING")
        print("="*80)
        print()
        print("Textract connection failed. Possible solutions:")
        print()
        print("1. Check if you're behind a corporate proxy:")
        print("   Set environment variables:")
        print("   $env:HTTP_PROXY='http://proxy.company.com:8080'")
        print("   $env:HTTPS_PROXY='http://proxy.company.com:8080'")
        print()
        print("2. Check if VPN is required:")
        print("   Connect to company VPN and retry")
        print()
        print("3. Check firewall settings:")
        print("   Ensure outbound HTTPS (443) is allowed to AWS endpoints")
        print()
        print("4. Try using AWS CLI directly:")
        print("   aws textract detect-document-text --document '{\"Bytes\":\"test\"}' --profile dev")
        print()
        print("5. Alternative: Test via Lambda function")
        print("   The Lambda function in VPC can access Textract successfully")
        print()
    
    return success_count == total_count


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
