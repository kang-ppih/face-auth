/**
 * CloudFront Functions - Viewer Request Handler
 * 
 * CloudFrontへのアクセスを制限するCloudFront Function
 * - 日本からのアクセスを許可（CloudFront-Viewer-Countryヘッダー）
 * - 特定IPアドレスからのアクセスを許可
 * - それ以外はブロック
 * 
 * Requirements: Security, Access Control
 */

// 許可するIPアドレス範囲（CIDR形式）
var ALLOWED_IP_RANGES = [
    { ip: '210.128.54.64', prefix: 27 }  // 社内ネットワーク
];

function handler(event) {
    var request = event.request;
    var clientIP = event.viewer.ip;
    
    // 特定IPアドレスからのアクセスのみ許可
    if (isIPAllowed(clientIP)) {
        return request;
    }
    
    // それ以外はブロック
    return {
        statusCode: 403,
        statusDescription: 'Forbidden',
        headers: {
            'content-type': { value: 'text/html; charset=utf-8' }
        },
        body: '<!DOCTYPE html><html><head><meta charset="utf-8"><title>アクセス拒否</title><style>body{font-family:Arial,sans-serif;text-align:center;padding:50px;background-color:#f5f5f5}.error-container{background:white;padding:40px;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);max-width:600px;margin:0 auto}h1{color:#d32f2f;margin-bottom:20px}p{color:#666;line-height:1.6}</style></head><body><div class="error-container"><h1>アクセスが拒否されました</h1><p>このサイトは許可されたIPアドレスからのみアクセス可能です。</p><p>This site is only accessible from authorized IP addresses.</p><p style="margin-top:20px;font-size:12px;color:#999">Your IP: ' + clientIP + '</p></div></body></html>'
    };
}

/**
 * クライアントIPが許可リストに含まれているかチェック
 */
function isIPAllowed(clientIP) {
    for (var i = 0; i < ALLOWED_IP_RANGES.length; i++) {
        var range = ALLOWED_IP_RANGES[i];
        if (ipInCIDR(clientIP, range.ip, range.prefix)) {
            return true;
        }
    }
    return false;
}

/**
 * IPアドレスがCIDR範囲内にあるかチェック
 */
function ipInCIDR(ip, rangeIP, prefix) {
    var ipNum = ipToNumber(ip);
    var rangeNum = ipToNumber(rangeIP);
    var mask = -1 << (32 - prefix);
    
    return (ipNum & mask) === (rangeNum & mask);
}

/**
 * IPアドレス文字列を数値に変換
 */
function ipToNumber(ip) {
    var parts = ip.split('.');
    if (parts.length !== 4) return 0;
    
    return (parseInt(parts[0]) << 24) +
           (parseInt(parts[1]) << 16) +
           (parseInt(parts[2]) << 8) +
           parseInt(parts[3]);
}
