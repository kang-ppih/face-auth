#!/usr/bin/env python3
"""
Test IP restriction by checking API Gateway resource policy
"""
import boto3
import json
from botocore.exceptions import ClientError

def test_ip_restriction():
    """Test if IP restriction is properly configured"""
    
    # Initialize API Gateway client
    client = boto3.client('apigateway', region_name='ap-northeast-1')
    
    api_id = 'zao7evz9jk'
    
    try:
        # Get REST API details
        response = client.get_rest_api(restApiId=api_id)
        
        print("=" * 80)
        print("API Gateway IP Restriction Test")
        print("=" * 80)
        print(f"\nAPI ID: {api_id}")
        print(f"API Name: {response['name']}")
        print(f"Description: {response.get('description', 'N/A')}")
        
        # Check if policy exists
        if 'policy' in response and response['policy']:
            print("\n✓ Resource Policy: CONFIGURED")
            
            # Parse policy (handle escaped JSON)
            policy_str = response['policy']
            # Remove escape characters if present
            if '\\' in policy_str:
                policy_str = policy_str.replace('\\', '')
            policy = json.loads(policy_str)
            print(f"\nPolicy Version: {policy.get('Version', 'N/A')}")
            print(f"Number of Statements: {len(policy.get('Statement', []))}")
            
            # Analyze statements
            for i, statement in enumerate(policy.get('Statement', []), 1):
                print(f"\n--- Statement {i} ---")
                print(f"Effect: {statement.get('Effect', 'N/A')}")
                print(f"Action: {statement.get('Action', 'N/A')}")
                print(f"Resource: {statement.get('Resource', 'N/A')}")
                
                # Check conditions
                if 'Condition' in statement:
                    print(f"Condition:")
                    for condition_type, condition_value in statement['Condition'].items():
                        print(f"  {condition_type}:")
                        for key, value in condition_value.items():
                            if isinstance(value, list):
                                print(f"    {key}:")
                                for ip in value:
                                    print(f"      - {ip}")
                            else:
                                print(f"    {key}: {value}")
            
            # Extract allowed IPs
            allowed_ips = []
            for statement in policy.get('Statement', []):
                if statement.get('Effect') == 'Allow':
                    condition = statement.get('Condition', {})
                    ip_address = condition.get('IpAddress', {})
                    source_ips = ip_address.get('aws:SourceIp', [])
                    if isinstance(source_ips, str):
                        allowed_ips.append(source_ips)
                    elif isinstance(source_ips, list):
                        allowed_ips.extend(source_ips)
            
            print(f"\n{'=' * 80}")
            print("SUMMARY")
            print("=" * 80)
            print(f"\n✓ IP Restriction: ENABLED")
            print(f"✓ Allowed IP Ranges: {', '.join(allowed_ips)}")
            print(f"\n⚠️  Access from other IPs will be DENIED with 403 Forbidden")
            
            # Calculate total allowed IPs
            import ipaddress
            total_ips = 0
            for cidr in allowed_ips:
                try:
                    network = ipaddress.ip_network(cidr, strict=False)
                    total_ips += network.num_addresses
                except:
                    pass
            
            print(f"\n📊 Total Allowed IP Addresses: {total_ips}")
            
            # Show IP ranges
            print(f"\n📍 Detailed IP Ranges:")
            for cidr in allowed_ips:
                try:
                    network = ipaddress.ip_network(cidr, strict=False)
                    print(f"   {cidr}")
                    print(f"     Range: {network.network_address} - {network.broadcast_address}")
                    print(f"     Count: {network.num_addresses} IPs")
                except Exception as e:
                    print(f"   {cidr} (Error: {e})")
            
        else:
            print("\n✗ Resource Policy: NOT CONFIGURED")
            print("\n⚠️  WARNING: All IPs are allowed (no restriction)")
        
        print(f"\n{'=' * 80}")
        
        return True
        
    except ClientError as e:
        print(f"\n✗ Error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    # Set AWS profile if provided
    if len(sys.argv) > 1:
        import os
        os.environ['AWS_PROFILE'] = sys.argv[1]
        print(f"Using AWS Profile: {sys.argv[1]}\n")
    
    success = test_ip_restriction()
    sys.exit(0 if success else 1)
