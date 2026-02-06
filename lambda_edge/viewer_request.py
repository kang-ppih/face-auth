"""
CloudFront Lambda@Edge - Viewer Request Handler

CloudFrontへのアクセスを制限するLambda@Edge関数
- 日本からのアクセスを許可（CloudFront-Viewer-Countryヘッダー）
- 特定IPアドレスからのアクセスを許可
- それ以外はブロック

Requirements: Security, Access Control
"""

import json
import ipaddress


# 許可するIPアドレス範囲（CIDR形式）
ALLOWED_IP_RANGES = [
    "210.128.54.64/27",  # 社内ネットワーク
]


def lambda_handler(event, context):
    """
    CloudFront Viewer Requestイベントハンドラ
    
    Args:
        event: CloudFront Viewer Requestイベント
        context: Lambda実行コンテキスト
        
    Returns:
        リクエストオブジェクト（許可）またはエラーレスポンス（拒否）
    """
    request = event['Records'][0]['cf']['request']
    headers = request['headers']
    client_ip = request['clientIp']
    
    # CloudFront-Viewer-Countryヘッダーで国を確認
    country_header = headers.get('cloudfront-viewer-country', [])
    country = country_header[0]['value'] if country_header else ''
    
    # 日本からのアクセスを許可
    if country == 'JP':
        print(f"Access allowed from Japan: {client_ip}")
        return request
    
    # 特定IPアドレスからのアクセスを許可
    if is_ip_allowed(client_ip):
        print(f"Access allowed from whitelisted IP: {client_ip}")
        return request
    
    # それ以外はブロック
    print(f"Access denied: IP={client_ip}, Country={country}")
    return {
        'status': '403',
        'statusDescription': 'Forbidden',
        'headers': {
            'content-type': [{
                'key': 'Content-Type',
                'value': 'text/html; charset=utf-8'
            }]
        },
        'body': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>アクセス拒否</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
            background-color: #f5f5f5;
        }
        .error-container {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 600px;
            margin: 0 auto;
        }
        h1 {
            color: #d32f2f;
            margin-bottom: 20px;
        }
        p {
            color: #666;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="error-container">
        <h1>アクセスが拒否されました</h1>
        <p>このサイトは日本国内または許可されたIPアドレスからのみアクセス可能です。</p>
        <p>This site is only accessible from Japan or authorized IP addresses.</p>
    </div>
</body>
</html>
        '''
    }


def is_ip_allowed(client_ip: str) -> bool:
    """
    クライアントIPが許可リストに含まれているかチェック
    
    Args:
        client_ip: クライアントのIPアドレス
        
    Returns:
        許可されている場合True、それ以外False
    """
    try:
        client_ip_obj = ipaddress.ip_address(client_ip)
        
        for ip_range in ALLOWED_IP_RANGES:
            network = ipaddress.ip_network(ip_range, strict=False)
            if client_ip_obj in network:
                return True
        
        return False
    except ValueError as e:
        print(f"Invalid IP address: {client_ip}, error: {e}")
        return False
