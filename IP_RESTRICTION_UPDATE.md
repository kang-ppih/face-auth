# Face-Auth IdP System - IP制限の更新方法

## 現在の設定

**許可されているIPレンジ:** `210.128.54.64/27`

このIPレンジからのみAPI Gatewayエンドポイントへのアクセスが許可されています。

---

## IP制限の仕組み

Face-Auth IdP SystemのIP制限は、API Gatewayのリソースポリシーで実装されています。

### 実装詳細

1. **環境変数 `ALLOWED_IPS`** から許可するIPレンジを読み取り
2. **API Gatewayリソースポリシー** に以下の2つのステートメントを追加：
   - **Allow**: 指定されたIPレンジからのアクセスを許可
   - **Deny**: 指定されたIPレンジ以外からのアクセスを拒否

### セキュリティ効果

- ✅ 指定されたIPレンジ外からのアクセスは **403 Forbidden** エラーになります
- ✅ API Keyが正しくても、IPレンジ外からはアクセスできません
- ✅ Lambda関数、DynamoDB、S3などのバックエンドリソースは保護されます

---

## IP制限の更新手順

### 方法1: 環境変数を使用（推奨）

#### 1. `.env` ファイルを編集

```bash
# .env ファイルを開く
notepad .env

# ALLOWED_IPS を更新（カンマ区切りで複数指定可能）
ALLOWED_IPS=210.128.54.64/27,203.0.113.0/24,198.51.100.0/24
```

#### 2. CDK差分を確認

```bash
# PowerShellの場合
$env:ALLOWED_IPS="210.128.54.64/27,203.0.113.0/24"; npx cdk diff --profile dev

# Bashの場合
ALLOWED_IPS="210.128.54.64/27,203.0.113.0/24" npx cdk diff --profile dev
```

#### 3. デプロイ実行

```bash
# PowerShellの場合
$env:ALLOWED_IPS="210.128.54.64/27,203.0.113.0/24"; npx cdk deploy --profile dev

# Bashの場合
ALLOWED_IPS="210.128.54.64/27,203.0.113.0/24" npx cdk deploy --profile dev
```

---

### 方法2: CDK Contextを使用

#### 1. `cdk.json` を編集

```json
{
  "app": "python app.py",
  "context": {
    "allowed_ips": "210.128.54.64/27,203.0.113.0/24,198.51.100.0/24"
  }
}
```

#### 2. デプロイ実行

```bash
npx cdk deploy --profile dev
```

---

## IPレンジの形式

### CIDR表記

IPレンジは **CIDR (Classless Inter-Domain Routing)** 形式で指定します。

**例:**

| CIDR | 説明 | IPアドレス範囲 |
|------|------|---------------|
| `210.128.54.64/27` | 32個のIPアドレス | 210.128.54.64 〜 210.128.54.95 |
| `203.0.113.0/24` | 256個のIPアドレス | 203.0.113.0 〜 203.0.113.255 |
| `198.51.100.0/24` | 256個のIPアドレス | 198.51.100.0 〜 198.51.100.255 |
| `192.0.2.10/32` | 1個のIPアドレス | 192.0.2.10 のみ |

### CIDR計算ツール

- [CIDR Calculator](https://www.ipaddressguide.com/cidr)
- [Subnet Calculator](https://www.subnet-calculator.com/)

---

## 複数のIPレンジを許可する

### カンマ区切りで指定

```bash
ALLOWED_IPS=210.128.54.64/27,203.0.113.0/24,198.51.100.0/24
```

### 例: オフィスとVPNの両方を許可

```bash
# オフィスネットワーク: 210.128.54.64/27
# VPNネットワーク: 203.0.113.0/24
# 自宅ネットワーク: 198.51.100.0/24

ALLOWED_IPS=210.128.54.64/27,203.0.113.0/24,198.51.100.0/24
```

---

## 全IPアドレスを許可する（開発環境のみ）

### 設定方法

```bash
# 空文字列を設定
ALLOWED_IPS=

# または明示的に指定
ALLOWED_IPS=0.0.0.0/0
```

### ⚠️ 注意事項

- **開発環境でのみ使用してください**
- **本番環境では絶対に使用しないでください**
- セキュリティリスクが高まります

---

## 現在の設定を確認する

### CloudFormation出力から確認

```bash
aws cloudformation describe-stacks \
  --stack-name FaceAuthIdPStack \
  --region ap-northeast-1 \
  --profile dev \
  --query "Stacks[0].Outputs[?OutputKey=='AllowedIPRanges'].OutputValue" \
  --output text
```

**現在の出力:**
```
210.128.54.64/27
```

### API Gatewayリソースポリシーを確認

```bash
aws apigateway get-rest-api \
  --rest-api-id zao7evz9jk \
  --region ap-northeast-1 \
  --profile dev \
  --query "policy" \
  --output text
```

---

## トラブルシューティング

### 問題1: 403 Forbidden エラー

**症状:**
```json
{
  "message": "User is not authorized to access this resource"
}
```

**原因:** アクセス元のIPアドレスが許可されていない

**解決策:**

1. 現在のIPアドレスを確認
```bash
curl https://api.ipify.org
```

2. そのIPアドレスを許可リストに追加
```bash
ALLOWED_IPS=210.128.54.64/27,YOUR_IP_ADDRESS/32
```

3. 再デプロイ

---

### 問題2: デプロイ後も制限が反映されない

**原因:** 環境変数が正しく読み込まれていない

**解決策:**

1. 環境変数を確認
```bash
# PowerShell
echo $env:ALLOWED_IPS

# Bash
echo $ALLOWED_IPS
```

2. 環境変数を明示的に設定してデプロイ
```bash
$env:ALLOWED_IPS="210.128.54.64/27"; npx cdk deploy --profile dev
```

---

### 問題3: 複数のIPレンジが正しく設定されない

**原因:** カンマ区切りの形式が正しくない

**正しい形式:**
```bash
ALLOWED_IPS=210.128.54.64/27,203.0.113.0/24,198.51.100.0/24
```

**間違った形式:**
```bash
# スペースが含まれている（NG）
ALLOWED_IPS=210.128.54.64/27, 203.0.113.0/24, 198.51.100.0/24

# セミコロン区切り（NG）
ALLOWED_IPS=210.128.54.64/27;203.0.113.0/24;198.51.100.0/24
```

---

## セキュリティベストプラクティス

### ✅ 推奨

1. **最小限のIPレンジのみ許可**
   - 必要なオフィス、VPN、データセンターのみ

2. **定期的な見直し**
   - 不要になったIPレンジは削除

3. **/32 を使用して特定のIPのみ許可**
   - 管理者アクセスなど

4. **本番環境では必ず制限を設定**
   - `0.0.0.0/0` は使用しない

### ❌ 非推奨

1. **広すぎるIPレンジ**
   - `0.0.0.0/0` (全IP許可)
   - `10.0.0.0/8` (1600万個のIP)

2. **未使用のIPレンジを残す**
   - 古いオフィスのIPなど

3. **本番環境で全IP許可**
   - セキュリティリスク大

---

## 環境別の推奨設定

### 開発環境 (Dev)

```bash
# 開発者のIPアドレスのみ許可
ALLOWED_IPS=210.128.54.64/27,203.0.113.0/24
```

### ステージング環境 (Staging)

```bash
# オフィス + VPN + テスト環境
ALLOWED_IPS=210.128.54.64/27,203.0.113.0/24,198.51.100.0/24
```

### 本番環境 (Prod)

```bash
# 本番アプリケーションサーバーのみ
ALLOWED_IPS=203.0.113.0/24,198.51.100.0/24
```

---

## 参考資料

- [AWS API Gateway Resource Policies](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-resource-policies.html)
- [CIDR Notation](https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing)
- [AWS IP Address Ranges](https://docs.aws.amazon.com/general/latest/gr/aws-ip-ranges.html)

---

**作成日:** 2024年
**最終更新:** 2024年
**現在の設定:** 210.128.54.64/27

