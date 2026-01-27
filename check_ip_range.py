#!/usr/bin/env python3
"""
Check if an IP address is within a CIDR range
"""
import ipaddress
import sys

def check_ip_in_range(ip_str, cidr_str):
    """Check if IP is in CIDR range"""
    try:
        ip = ipaddress.ip_address(ip_str)
        network = ipaddress.ip_network(cidr_str, strict=False)
        return ip in network
    except ValueError as e:
        print(f"Error: {e}")
        return False

# Test with the configured range
cidr_range = "210.128.54.64/27"
network = ipaddress.ip_network(cidr_range, strict=False)

print(f"CIDR Range: {cidr_range}")
print(f"Network Address: {network.network_address}")
print(f"Broadcast Address: {network.broadcast_address}")
print(f"Total IPs: {network.num_addresses}")
print(f"\nIP Range: {network.network_address} - {network.broadcast_address}")
print(f"\nAll IPs in range:")
for i, ip in enumerate(network.hosts(), 1):
    print(f"  {i}. {ip}")

# Test specific IPs
test_ips = [
    "210.128.54.64",
    "210.128.54.70",
    "210.128.54.80",
    "210.128.54.95",
    "210.128.54.96",  # Outside range
    "203.0.113.1",    # Outside range
]

print(f"\n\nTest Results:")
for test_ip in test_ips:
    in_range = check_ip_in_range(test_ip, cidr_range)
    status = "✓ ALLOWED" if in_range else "✗ DENIED"
    print(f"  {test_ip}: {status}")
