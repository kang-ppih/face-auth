# CloudFront アクセス制限オプション

**作成日:** 2026-02-06  
**目的:** CloudFrontへのアクセスを日本または特定IPに制限する方法の検討

---

## 現状

- **CloudFront:** IP制限なし（すべてのIPからアクセス可能）
- **API Gateway:** WAFでIP制限あり（`210.128.54.64/27`のみ）

---

## オプション比較

| オプション | 実装難易度 | コスト | 制限精度 | 推奨度 |
|-----------|----------|--------|---------|--------|
| **1. CloudFront WAF (us-east-1)** | 中 | 高 | 高 | ⭐⭐⭐⭐⭐ |
| **2. Lambda@Edge** | 高 | 中 | 高 | ⭐⭐⭐⭐ |
| **3. CloudFront Geo Restriction** | 低 | 無料 | 中 | ⭐⭐⭐ |
| **4. CloudFront Functions** | 中 | 低 | 高 | ⭐⭐⭐⭐ |

---

## オプション1: CloudFront WAF（推奨）

### 概要
CloudFront用のWAFを`us-east-1`リージョンに作成し、IP制限とGeo制限を実装。

### メリット
- ✅ 最も強力で柔軟な制限
- ✅ IP制限と地理的制限の両方が可能
- ✅ レート制限も同時に実装可能
- ✅ CloudWatch統合で詳細なモニタリング

### デメリット
- ❌ 別スタックまたは手動作成が必要（`us-east-1`制約）
- ❌ 追加コスト（月額約$7.60）

### 実装方法

#### A. 別CDKスタックで作成（推奨）

```python
# cloudfront_waf_stack.py (us-east-1専用)
from aws_cdk import Stack
from aws_cdk import aws_wafv2 as wafv2

class CloudFrontWAFStack(Stack):
    def __init__(self, scope, construct_id, allowed_ips, **kwargs):
        # 必ずus-east-1で作成
        super().__init__(scope, construct_id, 
                        env={'region': 'us-east-1'}, 
                        **kwargs)
        
        # IP Set作成
        ip_set = wafv2.CfnIPSet(
            self, "CloudFrontAllowedIPSet",
            name="FaceAuth-CloudFront-AllowedIPs",
            scope="CLOUDFRONT",
            ip_address_version="IPV4",
            addresses=allowed_ips
        )
        
        # Web ACL作成
        web_acl = wafv2.CfnWebACL(
            self, "CloudFrontWebACL",
            name="FaceAuth-CloudFront-WebACL",
            scope="CLOUDFRONT",
            default_action=wafv2.CfnWebACL.DefaultActionProperty(
                block={}
            ),
            rules=[
                # Rule 1: 日本からのアクセスを許可
                wafv2.CfnWebACL.RuleProperty(
                    name="AllowJapan",
                    priority=1,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        geo_match_statement=wafv2.CfnWebACL.GeoMatchStatementProperty(
                            country_codes=["JP"]
                        )
                    ),
                    action=wafv2.CfnWebACL.RuleActionProperty(allow={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="AllowJapan"
                    )
                ),
                # Rule 2: 特定IPからのアクセスを許可
                wafv2.CfnWebACL.RuleProperty(
                    name="AllowListedIPs",
                    priority=2,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        ip_set_reference_statement=wafv2.CfnWebACL.IPSetReferenceStatementProperty(
                            arn=ip_set.attr_arn
                        )
                    ),
                    action=wafv2.CfnWebACL.RuleActionProperty(allow={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="AllowListedIPs"
                    )
                ),
                # Rule 3: レート制限
                wafv2.CfnWebACL.RuleProperty(
                    name="RateLimitRule",
                    priority=3,
                    statement=wafv2.CfnWebACL.StatementProperty(
                        rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                            limit=1000,
                            aggregate_key_type="IP"
                        )
                    ),
                    action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                    visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                        sampled_requests_enabled=True,
                        cloud_watch_metrics_enabled=True,
                        metric_name="RateLimitRule"
                    )
                )
            ],
            visibility_config=wafv2.CfnWebACL.VisibilityConfigProperty(
                sampled_requests_enabled=True,
                cloud_watch_metrics_enabled=True,
                metric_name="FaceAuthCloudFrontWebACL"
            )
        )
        
        # Web ACL ARNを出力（メインスタックで使用）
        CfnOutput(self, "WebACLArn", value=web_acl.attr_arn)
```

**デプロイ:**
```bash
# 1. CloudFront WAFスタックをus-east-1にデプロイ
cdk deploy CloudFrontWAFStack --region us-east-1 --context allowed_ips="210.128.54.64/27"

# 2. Web ACL ARNを取得
WEB_ACL_ARN=$(aws cloudformation describe-stacks \
  --stack-name CloudFrontWAFStack \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='WebACLArn'].OutputValue" \
  --output text)

# 3. CloudFront DistributionにWeb ACLを関連付け
aws cloudfront update-distribution \
  --id EE7F2PTRFZ6WV \
  --if-match <etag> \
  --distribution-config file://distribution-config.json
```

#### B. 手動作成（簡単）

```bash
# 1. IP Setを作成（us-east-1）
aws wafv2 create-ip-set \
  --name FaceAuth-CloudFront-AllowedIPs \
  --scope CLOUDFRONT \
  --ip-address-version IPV4 \
  --addresses 210.128.54.64/27 \
  --region us-east-1

# 2. Web ACLを作成
aws wafv2 create-web-acl \
  --name FaceAuth-CloudFront-WebACL \
  --scope CLOUDFRONT \
  --default-action Block={} \
  --rules file://waf-rules.json \
  --visibility-config SampledRequestsEnabled=true,CloudWatchMetricsEnabled=true,MetricName=FaceAuthCloudFront \
  --region us-east-1

# 3. CloudFrontに関連付け
aws cloudfront update-distribution \
  --id EE7F2PTRFZ6WV \
  --web-acl-id <web-acl-arn>
```

### コスト
- Web ACL: $5.00/月
- ルール × 3: $3.00/月
- リクエスト（100万）: $0.60/月
- **合計: 約$8.60/月**

---

## オプション2: Lambda@Edge

### 概要
CloudFrontのViewer Requestイベントで実行されるLambda関数でIP/地理的制限を実装。

### メリット
- ✅ 柔軟なカスタムロジック実装可能
- ✅ 複雑な条件分岐が可能
- ✅ リージョン制約なし

### デメリット
- ❌ 実装が複雑
- ❌ すべてのリクエストでLambda実行（コスト増）
- ❌ デバッグが困難

### 実装例

```python
# lambda_edge/viewer_request.py
import json

# 日本のIPレンジ（例）
JAPAN_IP_RANGES = [
    "210.128.54.0/24",
    # ... 他の日本のIPレンジ
]

# 許可するIP
ALLOWED_IPS = [
    "210.128.54.64/27"
]

def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    client_ip = request['clientIp']
    headers = request['headers']
    
    # CloudFront-Viewer-Countryヘッダーで国を確認
    country = headers.get('cloudfront-viewer-country', [{}])[0].get('value', '')
    
    # 日本からのアクセスを許可
    if country == 'JP':
        return request
    
    # 特定IPからのアクセスを許可
    if is_ip_allowed(client_ip, ALLOWED_IPS):
        return request
    
    # それ以外はブロック
    return {
        'status': '403',
        'statusDescription': 'Forbidden',
        'body': 'Access denied'
    }

def is_ip_allowed(ip, allowed_ranges):
    # IPアドレスチェックロジック
    import ipaddress
    client_ip = ipaddress.ip_address(ip)
    for range_str in allowed_ranges:
        if client_ip in ipaddress.ip_network(range_str):
            return True
    return False
```

**デプロイ:**
```python
# CDKでLambda@Edge作成
lambda_edge = lambda_.Function(
    self, "ViewerRequestFunction",
    runtime=lambda_.Runtime.PYTHON_3_9,
    handler="viewer_request.lambda_handler",
    code=lambda_.Code.from_asset("lambda_edge"),
    timeout=Duration.seconds(5)
)

# CloudFront Distributionに関連付け
distribution = cloudfront.Distribution(
    self, "Distribution",
    default_behavior=cloudfront.BehaviorOptions(
        origin=origin,
        edge_lambdas=[
            cloudfront.EdgeLambda(
                function_version=lambda_edge.current_version,
                event_type=cloudfront.LambdaEdgeEventType.VIEWER_REQUEST
            )
        ]
    )
)
```

### コスト
- Lambda実行: $0.60/100万リクエスト
- Lambda@Edge追加料金: $0.50/100万リクエスト
- **合計: 約$1.10/100万リクエスト**

---

## オプション3: CloudFront Geo Restriction（最も簡単）

### 概要
CloudFrontの組み込み地理的制限機能を使用。

### メリット
- ✅ 最も簡単に実装可能
- ✅ 追加コストなし
- ✅ 設定変更のみで完了

### デメリット
- ❌ 国単位の制限のみ（IP単位は不可）
- ❌ 日本国外からのアクセスを完全にブロック

### 実装方法

```python
# infrastructure/face_auth_stack.py
self.frontend_distribution = cloudfront.Distribution(
    self, "FaceAuthFrontendDistribution",
    # ... 既存の設定 ...
    geo_restriction=cloudfront.GeoRestriction.allowlist("JP")  # 日本のみ許可
)
```

**または手動設定:**
```bash
# CloudFront Distribution設定を更新
aws cloudfront update-distribution \
  --id EE7F2PTRFZ6WV \
  --distribution-config '{
    "Restrictions": {
      "GeoRestriction": {
        "RestrictionType": "whitelist",
        "Quantity": 1,
        "Items": ["JP"]
      }
    }
  }'
```

### コスト
- **無料**

---

## オプション4: CloudFront Functions

### 概要
CloudFront Functionsを使用してViewer Requestでカスタムロジックを実行。

### メリット
- ✅ Lambda@Edgeより安価
- ✅ 低レイテンシ
- ✅ JavaScriptで実装

### デメリット
- ❌ 機能制限あり（外部API呼び出し不可）
- ❌ 実行時間制限（1ms未満）

### 実装例

```javascript
// cloudfront-function.js
function handler(event) {
    var request = event.request;
    var clientIP = event.viewer.ip;
    var country = request.headers['cloudfront-viewer-country'] 
                  ? request.headers['cloudfront-viewer-country'].value 
                  : '';
    
    // 日本からのアクセスを許可
    if (country === 'JP') {
        return request;
    }
    
    // 特定IPからのアクセスを許可
    var allowedIPs = ['210.128.54.64'];
    if (allowedIPs.indexOf(clientIP) !== -1) {
        return request;
    }
    
    // それ以外はブロック
    return {
        statusCode: 403,
        statusDescription: 'Forbidden'
    };
}
```

### コスト
- $0.10/100万リクエスト
- **非常に安価**

---

## 推奨実装パターン

### パターンA: 最大セキュリティ（推奨）

**組み合わせ:** CloudFront WAF + Geo Restriction

```
[ユーザー]
    |
    ▼
[CloudFront Geo Restriction] ← 日本のみ許可
    |
    ▼
[CloudFront WAF (us-east-1)] ← 特定IP + レート制限
    |
    ▼
[CloudFront Distribution]
    |
    ▼
[S3 Static Files]
```

**メリット:**
- 二重の保護
- 日本国外からのアクセスを完全ブロック
- 日本国内でも特定IPのみ許可

**コスト:** 約$8.60/月

---

### パターンB: コスト重視

**組み合わせ:** Geo Restriction のみ

```
[ユーザー]
    |
    ▼
[CloudFront Geo Restriction] ← 日本のみ許可
    |
    ▼
[CloudFront Distribution]
    |
    ▼
[S3 Static Files]
```

**メリット:**
- 無料
- 簡単に実装可能

**デメリット:**
- 日本国内からはすべてアクセス可能

**コスト:** 無料

---

### パターンC: 柔軟性重視

**組み合わせ:** CloudFront Functions + Geo Restriction

```
[ユーザー]
    |
    ▼
[CloudFront Functions] ← カスタムロジック
    |
    ▼
[CloudFront Geo Restriction] ← 日本のみ許可
    |
    ▼
[CloudFront Distribution]
```

**メリット:**
- 柔軟なカスタムロジック
- 低コスト

**コスト:** 約$0.10/100万リクエスト

---

## 実装手順（パターンA推奨）

### ステップ1: CloudFront Geo Restrictionを追加

```python
# infrastructure/face_auth_stack.py
self.frontend_distribution = cloudfront.Distribution(
    self, "FaceAuthFrontendDistribution",
    # ... 既存の設定 ...
    geo_restriction=cloudfront.GeoRestriction.allowlist("JP")
)
```

### ステップ2: CloudFront WAFスタックを作成

```bash
# 新しいファイル: cloudfront_waf_stack.py を作成
# app.pyに追加:
cloudfront_waf_stack = CloudFrontWAFStack(
    app, "CloudFrontWAFStack",
    allowed_ips=["210.128.54.64/27"],
    env={'region': 'us-east-1'}
)
```

### ステップ3: デプロイ

```bash
# 1. メインスタックを更新（Geo Restriction追加）
cdk deploy FaceAuthIdPStack --context allowed_ips="210.128.54.64/27" --profile dev

# 2. CloudFront WAFスタックをデプロイ
cdk deploy CloudFrontWAFStack --region us-east-1 --profile dev

# 3. Web ACL ARNを取得してCloudFrontに関連付け
```

---

## まとめ

| 要件 | 推奨オプション | 理由 |
|------|--------------|------|
| **日本のみ許可** | Geo Restriction | 無料で簡単 |
| **特定IPのみ許可** | CloudFront WAF | 最も強力 |
| **日本 + 特定IP** | WAF + Geo Restriction | 二重保護 |
| **コスト重視** | Geo Restriction | 無料 |
| **柔軟性重視** | Lambda@Edge | カスタムロジック |

**最終推奨:** パターンA（CloudFront WAF + Geo Restriction）
- 最大のセキュリティ
- 月額約$8.60で実装可能
- 日本国外からのアクセスを完全ブロック
- 日本国内でも特定IPのみ許可

---

**作成日:** 2026-02-06  
**作成者:** Face-Auth Development Team
