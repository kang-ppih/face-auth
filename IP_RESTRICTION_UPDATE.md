# IP制限メカニズム簡素化 - 実装完了レポート

**実装日:** 2026-02-05  
**実装者:** Face-Auth Development Team  
**目的:** IP制限メカニズムをWAF専用に簡素化  
**ステータス:** ✅ 完了

---

## 📋 実装概要

Face-Auth IdPシステムのIP制限メカニズムを、重複した3層構成から**AWS WAF専用の単一層構成**に簡素化しました。

### 変更前（多層防御）

```
ユーザー
  │
  ▼
┌─────────────────────────────────┐
│ 1. Network ACL (VPC)            │ ← IP制限 ✅
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 2. API Gateway Resource Policy  │ ← IP制限 ✅ (重複)
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 3. AWS WAF                      │ ← IP制限 ✅ (重複)
└─────────────────────────────────┘
```

### 変更後（WAF専用）

```
ユーザー
  │
  ▼
┌─────────────────────────────────┐
│ AWS WAF (唯一のIP制限層)         │
│  - IP Set: 許可IPリスト         │
│  - Rule 1: IP許可ルール          │
│  - Rule 2: レート制限            │
│  - Default Action: Block         │
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│ CloudFront  │ │ API Gateway │
│ (Frontend)  │ │ (Backend)   │
└─────────────┘ └─────────────┘
```

---

## 🔧 実装内容

### 1. Network ACL の簡素化

**ファイル:** `infrastructure/face_auth_stack.py`  
**メソッド:** `_create_network_acls()`

**変更内容:**
- ✅ IP制限ルールを削除
- ✅ 基本的なネットワーク制御のみ維持
  - HTTPS (443) 許可
  - HTTP (80) 許可（HTTPSへのリダイレクト用）
  - エフェメラルポート許可（戻りトラフィック用）
- ✅ すべてのIPアドレスからのHTTPS/HTTPトラフィックを許可
- ✅ WAFがIP制限を担当することをコメントで明記

**コード変更:**
```python
# 変更前: IP制限ルールあり
for idx, ip_range in enumerate(self.allowed_ip_ranges):
    ec2.NetworkAclEntry(...)  # IP制限

# 変更後: すべてのIPを許可（WAFが制限）
ec2.NetworkAclEntry(
    self, "AllowHTTPS",
    network_acl=self.public_nacl,
    cidr=ec2.AclCidr.any_ipv4(),  # すべてのIP
    rule_number=100,
    traffic=ec2.AclTraffic.tcp_port(443),
    direction=ec2.TrafficDirection.INGRESS,
    rule_action=ec2.Action.ALLOW
)
```

---

### 2. API Gateway Resource Policy の削除

**ファイル:** `infrastructure/face_auth_stack.py`

**変更内容:**
- ✅ `_create_api_resource_policy()` メソッドを完全削除（40行削除）
- ✅ API Gateway作成時の `policy` パラメータを削除
- ✅ WAFがIP制限を担当

**削除されたコード:**
```python
# 削除されたメソッド（927-967行）
def _create_api_resource_policy(self) -> iam.PolicyDocument:
    """Create API Gateway resource policy for IP-based access control"""
    # ... 40行のコード ...
```

**API Gateway作成の変更:**
```python
# 変更前
self.api = apigateway.RestApi(
    self, "FaceAuthAPI",
    policy=self._create_api_resource_policy() if self.allowed_ip_ranges != ["0.0.0.0/0"] else None,
    # ...
)

# 変更後
self.api = apigateway.RestApi(
    self, "FaceAuthAPI",
    # policy パラメータ削除（WAFがIP制限を担当）
    # ...
)
```

---

### 3. AWS WAF の維持

**ファイル:** `infrastructure/face_auth_stack.py`  
**メソッド:** `_create_waf()`

**変更なし:**
- ✅ Regional IP Set（API Gateway用）
- ✅ CloudFront IP Set（CloudFront用）
- ✅ Regional Web ACL（API Gateway用）
- ✅ CloudFront Web ACL（CloudFront用）
- ✅ IP許可ルール
- ✅ レート制限ルール（1000 req/5min/IP）

**WAFが唯一のIP制限メカニズム:**
- API GatewayとCloudFrontの両方をカバー
- `ALLOWED_IPS`環境変数を使用
- 開発モード（`0.0.0.0/0`）ではWAFを作成しない

---

### 4. ドキュメント更新

#### IP_RESTRICTION_COMPARISON.md
- ✅ 実装状態を「完了」に更新
- ✅ 実装されたアーキテクチャ図を追加
- ✅ 実装の利点を明記
- ✅ 変更内容の詳細を追加

#### WAF_IP_RESTRICTION_GUIDE.md
- ✅ バージョンを2.0に更新
- ✅ 「WAF専用IP制限」であることを明記
- ✅ Network ACLとAPI Gateway Resource Policyが削除されたことを説明
- ✅ 環境変数の使用箇所を明確化
- ✅ アーキテクチャ図を更新

#### .env.sample
- ✅ `ALLOWED_IPS`環境変数のコメントを更新
- ✅ 「WAFでのみ使用」であることを明記
- ✅ Network ACLやAPI Gateway Resource Policyでは使用されないことを説明

#### README.md
- ✅ IPアクセス制御セクションを更新
- ✅ WAF専用アプローチであることを明記
- ✅ 関連ドキュメントへのリンクを追加

---

## 📊 変更統計

### コード変更

| ファイル | 追加行 | 削除行 | 変更内容 |
|---------|-------|-------|---------|
| `infrastructure/face_auth_stack.py` | 15 | 55 | Network ACL簡素化、Resource Policy削除 |
| `IP_RESTRICTION_COMPARISON.md` | 120 | 80 | 実装完了状態に更新 |
| `WAF_IP_RESTRICTION_GUIDE.md` | 50 | 20 | WAF専用版に更新 |
| `.env.sample` | 3 | 0 | コメント追加 |
| `README.md` | 8 | 3 | IPアクセス制御セクション更新 |
| **合計** | **196** | **158** | **5ファイル** |

### 削除されたコード

- ✅ `_create_api_resource_policy()` メソッド: 40行
- ✅ Network ACL IP制限ルール: 15行
- ✅ 合計: 55行削除

---

## ✅ 実装の利点

### 1. 管理の簡素化

**変更前:**
- IP更新時に3箇所を変更する必要がある
- Network ACL、API Gateway Resource Policy、WAFの設定を個別に管理

**変更後:**
- IP更新は1箇所（WAF）のみ
- 一元管理により設定ミスのリスクを削減

### 2. トラブルシューティングの容易化

**変更前:**
- どの層でブロックされているか特定が困難
- 3つの設定を確認する必要がある

**変更後:**
- WAFのみを確認すればよい
- CloudWatchメトリクスで詳細な分析が可能

### 3. 柔軟性の向上

**変更前:**
- Network ACLはCloudFrontに適用できない
- API Gateway Resource PolicyはCloudFrontに適用できない

**変更後:**
- WAFはAPI GatewayとCloudFrontの両方をカバー
- レート制限機能も利用可能

### 4. コストの維持

**変更前:** $14.60/月（WAF）  
**変更後:** $14.60/月（WAF）  
**差額:** $0（変更なし）

---

## 🧪 テスト計画

### 1. デプロイ前テスト

```bash
# CDK差分確認
cdk diff

# 期待される変更:
# - Network ACL: IP制限ルール削除
# - API Gateway: Resource Policy削除
# - WAF: 変更なし
```

### 2. デプロイ後テスト

#### 2.1 許可されたIPからのアクセステスト

```bash
# API Gatewayアクセステスト
curl -X GET https://your-api-endpoint/auth/status

# 期待結果: 200 OK
```

#### 2.2 許可されていないIPからのアクセステスト

```bash
# 別のIPアドレスからアクセス
curl -X GET https://your-api-endpoint/auth/status

# 期待結果: 403 Forbidden
```

#### 2.3 CloudFrontアクセステスト

```bash
# CloudFront URLアクセス
curl https://your-cloudfront-domain.cloudfront.net/

# 許可されたIP: 200 OK
# 許可されていないIP: 403 Forbidden
```

#### 2.4 WAFメトリクス確認

```bash
# ブロックされたリクエスト数確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=WebACL,Value=FaceAuth-API-WebACL \
  --start-time 2026-02-05T00:00:00Z \
  --end-time 2026-02-05T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

---

## 📝 デプロイ手順

### 1. 変更内容の確認

```bash
# Git差分確認
git diff infrastructure/face_auth_stack.py

# 変更ファイル一覧
git status
```

### 2. CDK差分確認

```bash
# CDK差分確認
cdk diff

# 期待される出力:
# [-] AWS::EC2::NetworkAclEntry (IP制限ルール削除)
# [-] AWS::ApiGateway::RestApi.Policy (Resource Policy削除)
# [~] AWS::WAF::WebACL (変更なし)
```

### 3. デプロイ実行

```bash
# IP制限ありでデプロイ
cdk deploy --context allowed_ips="210.128.54.64/27"

# または開発環境（IP制限なし）
cdk deploy
```

### 4. 動作確認

```bash
# API Gatewayエンドポイント確認
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
  --output text

# WAF Web ACL確認
aws wafv2 list-web-acls --scope REGIONAL --region ap-northeast-1
```

---

## 🔄 ロールバック手順

万が一問題が発生した場合のロールバック手順：

### 1. 前のバージョンに戻す

```bash
# Gitで前のコミットに戻す
git revert HEAD

# 再デプロイ
cdk deploy
```

### 2. 手動でResource Policyを追加

```bash
# API Gateway Resource Policyを手動で追加
aws apigateway update-rest-api \
  --rest-api-id <api-id> \
  --patch-operations op=replace,path=/policy,value='<policy-json>'
```

---

## 📚 関連ドキュメント

### 更新されたドキュメント

1. [IP制限メカニズム比較](IP_RESTRICTION_COMPARISON.md) - 実装完了状態
2. [WAF IP制限ガイド](WAF_IP_RESTRICTION_GUIDE.md) - WAF専用版
3. [README.md](README.md) - IPアクセス制御セクション更新
4. [.env.sample](.env.sample) - 環境変数コメント更新

### 参考ドキュメント

1. [IPアクセス制御](docs/IP_ACCESS_CONTROL.md) - 全体的な概要
2. [インフラストラクチャアーキテクチャ](docs/INFRASTRUCTURE_ARCHITECTURE.md) - システム全体のアーキテクチャ
3. [AWS WAF Documentation](https://docs.aws.amazon.com/waf/) - AWS公式ドキュメント

---

## 🎉 実装完了

### 完了項目

- ✅ Network ACLのIP制限削除
- ✅ API Gateway Resource Policy削除
- ✅ WAFの維持
- ✅ ドキュメント更新（5ファイル）
- ✅ 環境変数コメント更新
- ✅ README更新

### 次のステップ

1. `cdk diff` でデプロイ前の差分確認
2. `cdk deploy` で本番環境にデプロイ
3. WAF設定の動作確認
4. IP制限のテスト実施
5. CloudWatchメトリクスの監視

---

## 📞 サポート

問題が発生した場合は、以下のドキュメントを参照してください：

- [WAF IP制限ガイド - トラブルシューティング](WAF_IP_RESTRICTION_GUIDE.md#トラブルシューティング)
- [IP制限メカニズム比較](IP_RESTRICTION_COMPARISON.md)

---

**実装日:** 2026-02-05  
**実装者:** Face-Auth Development Team  
**バージョン:** 2.0（WAF専用版）  
**ステータス:** ✅ 実装完了
