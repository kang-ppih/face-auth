# AWS WAF IP制限設定ガイド

**作成日:** 2026-02-04  
**更新日:** 2026-02-05  
**バージョン:** 2.1  
**対象:** API Gateway（バックエンドのみ）  
**実装状態:** ✅ WAF専用IP制限（API Gatewayのみ）

---

## 概要

このガイドでは、Face-Auth IdPシステムの**API Gateway**に**AWS WAFを使用したIP制限メカニズム**を説明します。

**重要な変更点:**
- ✅ **API Gateway（バックエンド）:** WAFによるIP制限あり（`ap-northeast-1`リージョン）
- ❌ **CloudFront（フロントエンド）:** IP制限なし

**理由:**
- CloudFront用WAFは`us-east-1`リージョンにのみ作成可能（AWS仕様）
- 単一CDKスタックでの複数リージョン管理の複雑さを避けるため
- API Gatewayのみに制限を適用することでシンプルな構成を実現

---

## アーキテクチャ

### WAF構成（API Gatewayのみ）

```
┌─────────────────────────────────────────┐
│  ユーザー（任意のIPアドレス）            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  CloudFront (Frontend)                  │
│  ❌ IP制限なし                          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  AWS WAF (唯一のIP制限層)               │
│  - IP Set: 許可IPリスト                 │
│  - Rule 1: IP許可ルール                 │
│  - Rule 2: レート制限 (1000 req/5min)   │
│  - Default Action: Block                │
│  - Region: ap-northeast-1               │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  API Gateway (Backend)                  │
│  ✅ IP制限あり（WAF）                   │
└─────────────────────────────────────────┘
```

**注意:**
- Network ACLは基本的なネットワーク制御のみ（HTTPS/HTTP許可）
- API Gateway Resource Policyは削除済み
- **WAFがすべてのIP制限を担当（API Gatewayのみ）**

---

## 実装内容

### 1. IP Set（IPアドレスセット）

**1つのIP Setを作成:**

#### Regional IP Set（API Gateway用）
- **名前:** `FaceAuth-AllowedIPs`
- **スコープ:** `REGIONAL`
- **リージョン:** `ap-northeast-1`
- **用途:** API Gateway用
- **IPアドレス:** `allowed_ips`コンテキストから取得

---

### 2. Web ACL（ウェブアクセス制御リスト）

**1つのWeb ACLを作成:**

#### API Gateway Web ACL
- **名前:** `FaceAuth-API-WebACL`
- **スコープ:** `REGIONAL`
- **リージョン:** `ap-northeast-1`
- **デフォルトアクション:** Block（ブロック）
- **ルール:**
  1. **AllowListedIPs** (Priority 1): 許可IPからのリクエストを許可
  2. **RateLimitRule** (Priority 2): レート制限（1000リクエスト/5分/IP）

---

## 環境変数設定

### ALLOWED_IPS環境変数

**重要:** この環境変数は**WAF（API Gateway用）でのみ**使用されます。

```bash
# .env または .env.sample
# WAF IP制限設定（カンマ区切りのCIDR形式）
# この環境変数はWAF（API Gateway用）でのみ使用されます
ALLOWED_IPS=203.0.113.10/32,198.51.100.0/24

# または開発環境では空にする（すべてのIPを許可）
# ALLOWED_IPS=
```

**使用箇所:**
- ✅ AWS WAF IP Set作成（API Gateway用）
- ❌ CloudFront WAF（削除済み）
- ❌ Network ACL（削除済み）
- ❌ API Gateway Resource Policy（削除済み）

---

## デプロイ方法

### 1. IP制限なし（開発モード）

```bash
# IP制限なしでデプロイ（すべてのIPを許可）
cdk deploy

# または明示的に指定
cdk deploy --context allowed_ips="0.0.0.0/0"
```

**動作:**
- WAFは作成されません
- すべてのIPアドレスからアクセス可能

---

### 2. 単一IPアドレスを許可

```bash
# 特定のIPアドレスのみ許可
cdk deploy --context allowed_ips="203.0.113.10/32"
```

**動作:**
- WAFが作成されます
- `203.0.113.10`からのみアクセス可能

---

### 3. 複数のIPアドレス/範囲を許可

```bash
# 複数のIPアドレスを許可（カンマ区切り）
cdk deploy --context allowed_ips="203.0.113.10/32,198.51.100.0/24,192.0.2.0/24"
```

**動作:**
- WAFが作成されます
- 指定された3つのIP範囲からアクセス可能

---

### 4. 社内ネットワーク全体を許可

```bash
# 社内ネットワーク全体を許可
cdk deploy --context allowed_ips="10.0.0.0/8"
```

**動作:**
- WAFが作成されます
- `10.0.0.0/8`範囲（社内ネットワーク）からアクセス可能

---

## WAF設定の確認

### 1. IP Setの確認

```bash
# Regional IP Set確認
aws wafv2 list-ip-sets --scope REGIONAL --region ap-northeast-1

# IP Set詳細確認
aws wafv2 get-ip-set \
  --scope REGIONAL \
  --id <ip-set-id> \
  --name FaceAuth-AllowedIPs \
  --region ap-northeast-1
```

---

### 2. Web ACLの確認

```bash
# Regional Web ACL確認（API Gateway用）
aws wafv2 list-web-acls --scope REGIONAL --region ap-northeast-1

# Web ACL詳細確認
aws wafv2 get-web-acl \
  --scope REGIONAL \
  --id <web-acl-id> \
  --name FaceAuth-API-WebACL \
  --region ap-northeast-1
```

---

### 3. API Gateway関連付け確認

```bash
# API GatewayのWeb ACL関連付け確認
aws apigateway get-stage \
  --rest-api-id <api-id> \
  --stage-name prod \
  --query 'webAclArn'
```

---

## WAFメトリクスとログ

### CloudWatchメトリクス

WAFは以下のメトリクスを自動的に収集します：

| メトリクス名 | 説明 |
|-------------|------|
| `AllowedRequests` | 許可されたリクエスト数 |
| `BlockedRequests` | ブロックされたリクエスト数 |
| `CountedRequests` | カウントされたリクエスト数 |
| `AllowListedIPs` | IP許可ルールにマッチしたリクエスト数 |
| `RateLimitRule` | レート制限ルールにマッチしたリクエスト数 |

### メトリクス確認

```bash
# ブロックされたリクエスト数確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=Rule,Value=ALL Name=WebACL,Value=FaceAuth-API-WebACL \
  --start-time 2026-02-04T00:00:00Z \
  --end-time 2026-02-04T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --region ap-northeast-1
```

---

### WAFログ

WAFログをS3またはCloudWatch Logsに保存できます。

#### S3へのログ保存設定

```bash
# WAFログ設定
aws wafv2 put-logging-configuration \
  --logging-configuration \
    ResourceArn=arn:aws:wafv2:ap-northeast-1:123456789012:regional/webacl/FaceAuth-API-WebACL/...,\
    LogDestinationConfigs=arn:aws:s3:::face-auth-waf-logs-123456789012 \
  --region ap-northeast-1
```

#### CloudWatch Logsへのログ保存設定

```bash
# WAFログ設定
aws wafv2 put-logging-configuration \
  --logging-configuration \
    ResourceArn=arn:aws:wafv2:ap-northeast-1:123456789012:regional/webacl/FaceAuth-API-WebACL/...,\
    LogDestinationConfigs=arn:aws:logs:ap-northeast-1:123456789012:log-group:aws-waf-logs-face-auth \
  --region ap-northeast-1
```

---

## IP制限のテスト

### 1. 許可されたIPからのアクセステスト

```bash
# 許可されたIPからAPIアクセス
curl -X POST https://your-api-endpoint/auth/enroll \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "E123456", ...}'

# 期待結果: 200 OK
```

---

### 2. 許可されていないIPからのアクセステスト

```bash
# 許可されていないIPからAPIアクセス
curl -X POST https://your-api-endpoint/auth/enroll \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "E123456", ...}'

# 期待結果: 403 Forbidden
# {
#   "message": "Forbidden"
# }
```

---

### 3. CloudFrontアクセステスト

```bash
# CloudFront URLにアクセス
curl https://your-cloudfront-domain.cloudfront.net/

# すべてのIP: 200 OK（index.htmlが返される）
# CloudFrontにはIP制限がありません
```

---

## IP制限の更新

### 1. IP Setの更新

```bash
# IP Setを更新（新しいIPアドレスを追加）
aws wafv2 update-ip-set \
  --scope REGIONAL \
  --id <ip-set-id> \
  --name FaceAuth-AllowedIPs \
  --addresses "203.0.113.10/32" "198.51.100.0/24" "192.0.2.0/24" "203.0.113.20/32" \
  --lock-token <lock-token> \
  --region ap-northeast-1
```

**注意:** `lock-token`は`get-ip-set`コマンドで取得できます。

---

### 2. CDKでの更新

```bash
# allowed_ipsコンテキストを更新して再デプロイ
cdk deploy --context allowed_ips="203.0.113.10/32,198.51.100.0/24,203.0.113.20/32"
```

---

## トラブルシューティング

### 問題1: 許可されたIPからアクセスできない

**症状:**
```
403 Forbidden
```

**原因:**
1. IP Setに正しいIPアドレスが登録されていない
2. CIDR表記が間違っている
3. Web ACLがAPI Gatewayに関連付けられていない

**対応:**
```bash
# 1. IP Set確認
aws wafv2 get-ip-set \
  --scope REGIONAL \
  --id <ip-set-id> \
  --name FaceAuth-AllowedIPs \
  --region ap-northeast-1

# 2. 自分のIPアドレス確認
curl https://checkip.amazonaws.com

# 3. IP Setに追加
aws wafv2 update-ip-set \
  --scope REGIONAL \
  --id <ip-set-id> \
  --name FaceAuth-AllowedIPs \
  --addresses "<your-ip>/32" \
  --lock-token <lock-token> \
  --region ap-northeast-1
```

---

### 問題2: レート制限に引っかかる

**症状:**
```
429 Too Many Requests
```

**原因:**
- 5分間に1000リクエストを超えた

**対応:**
```bash
# レート制限を緩和（2000リクエスト/5分に変更）
# CDKコードを編集してlimitを2000に変更
# infrastructure/face_auth_stack.py:
# limit=2000

# 再デプロイ
cdk deploy
```

---

### 問題3: WAFログが記録されない

**症状:**
- CloudWatch MetricsにWAFメトリクスが表示されない

**原因:**
- ログ設定が有効になっていない

**対応:**
```bash
# ログ設定を有効化
aws wafv2 put-logging-configuration \
  --logging-configuration \
    ResourceArn=<web-acl-arn>,\
    LogDestinationConfigs=<log-destination-arn> \
  --region ap-northeast-1
```

---

## セキュリティベストプラクティス

### 1. 最小権限の原則

- 必要最小限のIPアドレス範囲のみを許可
- 社内ネットワーク全体ではなく、特定のサブネットのみを許可

### 2. 定期的なレビュー

- 月次でIP Setをレビュー
- 不要になったIPアドレスを削除

### 3. レート制限の設定

- DDoS攻撃を防ぐためにレート制限を設定
- 通常のトラフィックパターンに基づいて調整

### 4. ログとモニタリング

- WAFログを有効化
- CloudWatchアラームを設定
- ブロックされたリクエストを定期的に確認

---

## コスト

### WAF料金（2026年2月時点）

| 項目 | 料金 |
|------|------|
| Web ACL | $5.00/月 |
| ルール | $1.00/月/ルール |
| リクエスト | $0.60/100万リクエスト |

**月間コスト例（API Gatewayのみ）:**
- Web ACL × 1: $5.00
- ルール × 2（IP許可 + レート制限）: $2.00
- リクエスト（100万リクエスト）: $0.60
- **合計: 約$7.60/月**

**CloudFront WAFを削除したことによるコスト削減:**
- 以前: $14.60/月（API Gateway + CloudFront）
- 現在: $7.60/月（API Gatewayのみ）
- **削減額: $7.00/月（約48%削減）**

---

## 参考資料

- [AWS WAF Documentation](https://docs.aws.amazon.com/waf/)
- [AWS WAF Pricing](https://aws.amazon.com/waf/pricing/)
- [IP Access Control Guide](docs/IP_ACCESS_CONTROL.md)
- [CORS and IP Restriction Guide](CORS_AND_IP_RESTRICTION_GUIDE.md)

---

**最終更新:** 2026-02-05  
**作成者:** Face-Auth Development Team  
**バージョン:** 2.1 (CloudFront WAF削除、API Gateway WAFのみ)
