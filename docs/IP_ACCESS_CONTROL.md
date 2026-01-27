# API Gateway IPアクセス制御

Face-Auth IdP SystemのAPI GatewayにIPベースのアクセス制御を実装しています。

## 概要

API Gatewayリソースポリシーを使用して、特定のIPアドレス範囲からのみAPIへのアクセスを許可します。

### セキュリティレベル

1. **開発環境:** すべてのIPアドレスを許可（デフォルト）
2. **ステージング/本番環境:** 特定のIPアドレス範囲のみ許可

---

## 設定方法

### 方法1: CDK Context（推奨）

デプロイ時にコマンドラインで指定：

```bash
# 単一IPアドレスを許可
npx cdk deploy --profile dev --context allowed_ips="203.0.113.10/32"

# 複数のIPアドレス範囲を許可（カンマ区切り）
npx cdk deploy --profile dev --context allowed_ips="203.0.113.10/32,198.51.100.0/24"

# 社内ネットワーク全体を許可
npx cdk deploy --profile dev --context allowed_ips="10.0.0.0/8,172.16.0.0/12"
```

### 方法2: 環境変数

環境変数を設定してからデプロイ：

```bash
# Windows (PowerShell)
$env:ALLOWED_IPS="203.0.113.10/32,198.51.100.0/24"
npx cdk deploy --profile dev

# Linux/Mac
export ALLOWED_IPS="203.0.113.10/32,198.51.100.0/24"
npx cdk deploy --profile dev
```

### 方法3: cdk.json設定

`cdk.json`ファイルに永続的に設定：

```json
{
  "app": "python3 app.py",
  "context": {
    "allowed_ips": "203.0.113.10/32,198.51.100.0/24"
  }
}
```

---

## IPアドレス形式

### CIDR表記

IPアドレスはCIDR表記で指定します：

| 表記 | 説明 | 許可されるIP数 |
|------|------|---------------|
| `203.0.113.10/32` | 単一IPアドレス | 1個 |
| `203.0.113.0/24` | クラスC（/24） | 256個 |
| `203.0.113.0/16` | クラスB（/16） | 65,536個 |
| `10.0.0.0/8` | クラスA（/8） | 16,777,216個 |
| `0.0.0.0/0` | すべてのIP | すべて |

### 複数のIP範囲

カンマ区切りで複数指定可能：

```
203.0.113.10/32,198.51.100.0/24,192.0.2.0/24
```

---

## 使用例

### 例1: 開発環境（すべてのIPを許可）

```bash
# allowed_ipsを指定しない場合、デフォルトで0.0.0.0/0（すべて許可）
npx cdk deploy --profile dev
```

### 例2: 社内ネットワークのみ許可

```bash
# 社内ネットワーク 10.0.0.0/8 のみ許可
npx cdk deploy --profile prod --context allowed_ips="10.0.0.0/8"
```

### 例3: 特定のオフィスIPのみ許可

```bash
# 東京オフィス、大阪オフィス、リモートVPNのIPを許可
npx cdk deploy --profile prod \
  --context allowed_ips="203.0.113.10/32,198.51.100.20/32,192.0.2.0/24"
```

### 例4: 本番環境（複数拠点）

```bash
# 本社、支社、データセンターのIPを許可
npx cdk deploy --profile prod \
  --context allowed_ips="203.0.113.0/24,198.51.100.0/24,192.0.2.0/24,10.0.0.0/8"
```

---

## 動作確認

### 1. デプロイ後の確認

```bash
# CloudFormation Outputsから許可IPを確認
aws cloudformation describe-stacks \
  --stack-name FaceAuthIdPStack \
  --profile dev \
  --region ap-northeast-1 \
  --query "Stacks[0].Outputs[?OutputKey=='AllowedIPRanges'].OutputValue" \
  --output text
```

### 2. API Gatewayリソースポリシーの確認

```bash
# API IDを取得
API_ID=$(aws cloudformation describe-stacks \
  --stack-name FaceAuthIdPStack \
  --profile dev \
  --region ap-northeast-1 \
  --query "Stacks[0].Outputs[?OutputKey=='APIEndpoint'].OutputValue" \
  --output text | cut -d'/' -f3 | cut -d'.' -f1)

# リソースポリシーを確認
aws apigateway get-rest-api \
  --rest-api-id $API_ID \
  --profile dev \
  --region ap-northeast-1 \
  --query "policy" \
  --output text | jq .
```

### 3. アクセステスト

#### 許可されたIPからのアクセス

```bash
# ステータスエンドポイントにアクセス
curl -X GET "https://your-api-id.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status"

# 期待される結果: 200 OK
```

#### 許可されていないIPからのアクセス

```bash
# 別のIPアドレスからアクセス
curl -X GET "https://your-api-id.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status"

# 期待される結果: 403 Forbidden
{
  "Message": "User is not authorized to access this resource"
}
```

---

## トラブルシューティング

### 問題1: 403 Forbiddenエラー

**症状:**
```json
{
  "Message": "User is not authorized to access this resource"
}
```

**原因:**
- アクセス元のIPアドレスが許可リストに含まれていない
- IPアドレス形式が間違っている

**解決方法:**

1. 現在のIPアドレスを確認：
```bash
curl https://checkip.amazonaws.com
```

2. 許可リストに追加してデプロイ：
```bash
npx cdk deploy --profile dev --context allowed_ips="YOUR_IP/32"
```

### 問題2: すべてのIPを許可したい

**解決方法:**

```bash
# allowed_ipsを指定しない（デフォルト）
npx cdk deploy --profile dev

# または明示的に指定
npx cdk deploy --profile dev --context allowed_ips="0.0.0.0/0"
```

### 問題3: 動的IPアドレスの対応

**問題:**
リモートワーカーなど、動的IPアドレスを使用している場合

**解決方法:**

1. **VPN経由でアクセス:** 固定IPのVPNサーバーを経由
2. **広い範囲を許可:** ISPのIP範囲全体を許可（セキュリティリスクあり）
3. **API Key認証を併用:** IPアクセス制御を緩和し、API Key認証を強化

---

## セキュリティベストプラクティス

### 1. 最小権限の原則

必要最小限のIP範囲のみを許可：

```bash
# Good: 特定のオフィスIPのみ
--context allowed_ips="203.0.113.10/32"

# Bad: 広すぎる範囲
--context allowed_ips="0.0.0.0/0"
```

### 2. 環境別の設定

環境ごとに異なるIP範囲を設定：

```bash
# 開発環境: すべて許可
npx cdk deploy FaceAuthStack-Dev --context env=dev

# 本番環境: 社内ネットワークのみ
npx cdk deploy FaceAuthStack-Prod \
  --context env=prod \
  --context allowed_ips="10.0.0.0/8"
```

### 3. 多層防御

IPアクセス制御に加えて：

- ✅ API Key認証
- ✅ Cognito認証
- ✅ Rate Limiting
- ✅ WAF（オプション）

### 4. 定期的な見直し

- 四半期ごとに許可IPリストを見直し
- 不要になったIPアドレスを削除
- アクセスログを監視

---

## API Gatewayリソースポリシーの詳細

### 生成されるポリシー例

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "execute-api:/*",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": [
            "203.0.113.10/32",
            "198.51.100.0/24"
          ]
        }
      }
    },
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "execute-api:/*",
      "Condition": {
        "NotIpAddress": {
          "aws:SourceIp": [
            "203.0.113.10/32",
            "198.51.100.0/24"
          ]
        }
      }
    }
  ]
}
```

### ポリシーの動作

1. **Allow Statement:** 許可されたIPからのアクセスを許可
2. **Deny Statement:** それ以外のIPからのアクセスを拒否

**注意:** Denyは常にAllowより優先されます。

---

## 更新手順

### 既存スタックのIP範囲を変更

```bash
# 1. 新しいIP範囲を指定してデプロイ
npx cdk deploy --profile dev \
  --context allowed_ips="NEW_IP_RANGE"

# 2. 変更を確認
aws cloudformation describe-stacks \
  --stack-name FaceAuthIdPStack \
  --profile dev \
  --region ap-northeast-1 \
  --query "Stacks[0].Outputs[?OutputKey=='AllowedIPRanges'].OutputValue"
```

### IP範囲の追加

既存のIP範囲に新しいIPを追加：

```bash
# 現在: 203.0.113.10/32
# 追加: 198.51.100.20/32

npx cdk deploy --profile dev \
  --context allowed_ips="203.0.113.10/32,198.51.100.20/32"
```

---

## よくある質問（FAQ）

### Q1: CloudFront経由でアクセスする場合は？

**A:** CloudFrontのIPアドレス範囲を許可する必要があります。ただし、CloudFrontのIPは頻繁に変更されるため、カスタムヘッダー認証を推奨します。

### Q2: Lambda関数からのアクセスは制限されますか？

**A:** いいえ。Lambda関数はVPC内からアクセスするため、API Gatewayのリソースポリシーの影響を受けません。

### Q3: IPアクセス制御を無効化できますか？

**A:** はい。`allowed_ips`を指定しないか、`0.0.0.0/0`を指定することで無効化できます。

### Q4: IPv6アドレスはサポートされていますか？

**A:** はい。IPv6 CIDR表記（例: `2001:db8::/32`）もサポートされています。

---

## 参考資料

- [AWS API Gateway Resource Policies](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-resource-policies.html)
- [AWS IP Address Ranges](https://docs.aws.amazon.com/general/latest/gr/aws-ip-ranges.html)
- [CIDR Notation](https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing)

---

**最終更新:** 2026-01-24  
**バージョン:** 1.0
