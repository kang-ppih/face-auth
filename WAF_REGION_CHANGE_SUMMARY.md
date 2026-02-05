# WAF リージョン変更完了レポート

**作成日:** 2026-02-05  
**ステータス:** ✅ 完了  
**デプロイ:** ✅ 成功

---

## 概要

CloudFront用WAFを削除し、API Gateway用WAFのみを`ap-northeast-1`リージョンで運用する構成に変更しました。

---

## 変更内容

### 1. CloudFront用WAF削除

**削除されたリソース:**
- ❌ `FaceAuthAllowedIPSetCloudFront` (CloudFront用IP Set)
- ❌ `FaceAuth-CloudFront-WebACL` (CloudFront用Web ACL)
- ❌ CloudFront DistributionへのWeb ACL関連付け

**理由:**
- CloudFront用WAFは`us-east-1`リージョンにのみ作成可能（AWS仕様）
- 現在のCDKスタックは`ap-northeast-1`で実行
- 単一スタックでの複数リージョン管理の複雑さを回避

---

### 2. API Gateway用WAF維持

**維持されたリソース:**
- ✅ `FaceAuthAllowedIPSet` (API Gateway用IP Set - REGIONAL)
- ✅ `FaceAuth-API-WebACL` (API Gateway用Web ACL - REGIONAL)
- ✅ API GatewayステージへのWeb ACL関連付け

**リージョン:** `ap-northeast-1`

**ルール:**
1. **AllowListedIPs** (Priority 1): 許可IPからのリクエストを許可
2. **RateLimitRule** (Priority 2): レート制限（1000リクエスト/5分/IP）

---

## 新しいアーキテクチャ

```
┌─────────────────────────────────────────┐
│  ユーザー（任意のIPアドレス）            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  CloudFront (Frontend)                  │
│  ❌ IP制限なし                          │
│  Region: Global                         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  AWS WAF (唯一のIP制限層)               │
│  ✅ IP制限あり                          │
│  Region: ap-northeast-1                 │
│  - IP Set: FaceAuthAllowedIPs           │
│  - Web ACL: FaceAuth-API-WebACL         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  API Gateway (Backend)                  │
│  ✅ IP制限あり（WAF）                   │
│  Region: ap-northeast-1                 │
└─────────────────────────────────────────┘
```

---

## IP制限の適用範囲

| コンポーネント | IP制限 | 実装方法 | リージョン |
|--------------|--------|---------|-----------|
| **CloudFront (フロントエンド)** | ❌ なし | - | Global |
| **API Gateway (バックエンド)** | ✅ あり | AWS WAF (REGIONAL) | ap-northeast-1 |

---

## デプロイ結果

### デプロイ情報

```
Stack: FaceAuthIdPStack
Region: ap-northeast-1
Status: CREATE_COMPLETE
Deployment Time: 301.7s (約5分)
Total Resources: 136
```

### 主要なリソース

**WAF関連:**
- ✅ IP Set: `FaceAuthAllowedIPSet` (REGIONAL)
- ✅ Web ACL: `FaceAuth-API-WebACL` (REGIONAL)
- ✅ Web ACL Association: API Gateway Stage

**許可IP範囲:**
```
210.128.54.64/27
```

**API Endpoint:**
```
https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/
```

**CloudFront URL:**
```
https://d2576ywp5ut1v8.cloudfront.net
```

---

## コスト削減

### 月間コスト比較

**変更前（API Gateway + CloudFront WAF）:**
- Web ACL × 2: $10.00
- ルール × 4: $4.00
- リクエスト（100万）: $1.20
- **合計: $15.20/月**

**変更後（API Gatewayのみ）:**
- Web ACL × 1: $5.00
- ルール × 2: $2.00
- リクエスト（100万）: $0.60
- **合計: $7.60/月**

**削減額: $7.60/月（約50%削減）**

---

## コード変更

### infrastructure/face_auth_stack.py

**変更箇所:** `_create_waf()` メソッド

**削除されたコード:**
- CloudFront用IP Set作成（約15行）
- CloudFront用Web ACL作成（約60行）
- CloudFront DistributionへのWeb ACL関連付け（約5行）
- **合計: 約80行削除**

**追加されたコード:**
- 詳細なdocstring（リージョン制約の説明）
- **合計: 約10行追加**

**正味削減: 約70行**

---

## ドキュメント更新

### WAF_IP_RESTRICTION_GUIDE.md

**バージョン:** 2.0 → 2.1

**主な変更:**
- CloudFront WAFに関する記述を削除
- API Gateway WAFのみの構成に更新
- リージョン情報を`ap-northeast-1`に統一
- コスト情報を更新（50%削減）
- トラブルシューティングセクションを更新

---

## Git コミット

```bash
commit 8a2ed10
Author: Kiro AI Assistant
Date: 2026-02-05

refactor(waf): Remove CloudFront WAF, keep API Gateway WAF only in ap-northeast-1

- CloudFront用 WAF 제거 (us-east-1 리전 제약으로 인한 복잡성 회피)
- API Gateway용 WAF만 ap-northeast-1 리전에서 유지
- CloudFront용 IP Set 및 Web ACL 삭제
- CloudFront Distribution의 Web ACL 연결 제거
- WAF_IP_RESTRICTION_GUIDE.md 업데이트 (v2.1)
- 월간 WAF 비용 약 48% 절감 ($14.60 → $7.60)

Benefits:
- 단일 리전에서 모든 WAF 리소스 관리
- 단순화된 아키텍처
- 비용 절감
- CloudFront는 IP 제한 없이 모든 사용자 접근 가능
- API Gateway는 WAF로 보호됨
```

---

## 動作確認

### 1. WAF設定確認

```bash
# IP Set確認
aws wafv2 list-ip-sets --scope REGIONAL --region ap-northeast-1

# Web ACL確認
aws wafv2 list-web-acls --scope REGIONAL --region ap-northeast-1
```

### 2. API Gateway確認

```bash
# API GatewayのWeb ACL関連付け確認
aws apigateway get-stage \
  --rest-api-id ivgbc7glnl \
  --stage-name prod \
  --query 'webAclArn'
```

### 3. CloudFront確認

```bash
# CloudFront DistributionのWeb ACL確認（なしであることを確認）
aws cloudfront get-distribution \
  --id EE7F2PTRFZ6WV \
  --query 'Distribution.DistributionConfig.WebACLId'
```

**期待結果:** `null` または空

---

## セキュリティ影響

### API Gateway（バックエンド）

**変更なし:**
- ✅ IP制限あり（WAF）
- ✅ 許可されたIPアドレスからのみアクセス可能
- ✅ レート制限あり（1000リクエスト/5分/IP）

### CloudFront（フロントエンド）

**変更あり:**
- ❌ IP制限なし
- ⚠️ すべてのIPアドレスからアクセス可能

**影響:**
- フロントエンド静的ファイル（HTML, CSS, JS）は誰でもアクセス可能
- バックエンドAPI（認証、登録など）は引き続きIP制限で保護
- 実際のデータ処理はすべてAPI Gateway経由のため、セキュリティリスクは限定的

---

## 今後の推奨事項

### 1. CloudFrontへのIP制限が必要な場合

**オプション1: 別スタックでCloudFront WAFを作成**
```bash
# us-east-1リージョンで別スタックを作成
cdk deploy CloudFrontWAFStack --region us-east-1
```

**オプション2: Lambda@Edgeでカスタム認証**
```python
# CloudFront Viewer Requestで実行
def lambda_handler(event, context):
    request = event['Records'][0]['cf']['request']
    client_ip = request['clientIp']
    
    if client_ip not in ALLOWED_IPS:
        return {
            'status': '403',
            'statusDescription': 'Forbidden'
        }
    
    return request
```

### 2. モニタリング強化

**CloudWatch Alarms:**
- API Gateway 4xx/5xx エラー率
- WAF ブロック率
- 異常なトラフィックパターン

**WAF Logs:**
```bash
# WAFログをS3に保存
aws wafv2 put-logging-configuration \
  --logging-configuration \
    ResourceArn=<web-acl-arn>,\
    LogDestinationConfigs=<s3-bucket-arn>
```

---

## トラブルシューティング

### 問題: 許可されたIPからAPI Gatewayにアクセスできない

**確認事項:**
1. IP Setに正しいIPアドレスが登録されているか
2. Web ACLがAPI Gatewayに関連付けられているか
3. 自分のIPアドレスが許可範囲内か

**確認コマンド:**
```bash
# 自分のIPアドレス確認
curl https://checkip.amazonaws.com

# IP Set確認
aws wafv2 get-ip-set \
  --scope REGIONAL \
  --name FaceAuthAllowedIPs \
  --region ap-northeast-1
```

### 問題: CloudFrontにアクセスできない

**原因:**
- CloudFrontにはIP制限がないため、すべてのIPからアクセス可能

**確認:**
```bash
# CloudFront URLにアクセス
curl https://d2576ywp5ut1v8.cloudfront.net/
```

**期待結果:** 200 OK（index.htmlが返される）

---

## 参考資料

- [AWS WAF Documentation](https://docs.aws.amazon.com/waf/)
- [CloudFront WAF Requirements](https://docs.aws.amazon.com/waf/latest/developerguide/cloudfront-features.html)
- [WAF_IP_RESTRICTION_GUIDE.md](WAF_IP_RESTRICTION_GUIDE.md)
- [IP_RESTRICTION_UPDATE.md](IP_RESTRICTION_UPDATE.md)

---

**最終更新:** 2026-02-05  
**作成者:** Face-Auth Development Team  
**ステータス:** ✅ 完了・デプロイ成功
