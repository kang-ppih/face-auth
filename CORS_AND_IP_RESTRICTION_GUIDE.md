# CORS と IP 制限設定ガイド

## 概要

Face-Auth IdP System では、セキュリティ強化のために以下の2つの制限を実装しています：

1. **IP制限**: 特定のIPアドレスからのみAPIアクセスを許可
2. **CORS制限**: 特定のフロントエンドオリジンからのみAPIアクセスを許可

## 設定方法

### 1. 環境変数での設定

`.env` ファイルまたは環境変数で設定します：

```bash
# IP制限（CIDR形式、カンマ区切り）
ALLOWED_IPS=210.128.54.64/27,192.168.1.0/24

# CORS制限（オリジン、カンマ区切り）
FRONTEND_ORIGINS=https://app.example.com,https://staging.example.com
```

### 2. CDKコンテキストでの設定

デプロイ時にコマンドラインで指定することもできます：

```bash
# IP制限を指定してデプロイ
npx cdk deploy --context allowed_ips="210.128.54.64/27,192.168.1.0/24"

# CORS制限を指定してデプロイ
npx cdk deploy --context frontend_origins="https://app.example.com"

# 両方を指定
npx cdk deploy \
  --context allowed_ips="210.128.54.64/27" \
  --context frontend_origins="https://app.example.com"
```

## IP制限の詳細

### 実装レイヤー

IP制限は以下の3つのレイヤーで実装されています：

#### Layer 1: VPC Network ACL
- VPCレベルでのトラフィック制御
- パブリックサブネットへのアクセスを制限
- 最も外側の防御層

#### Layer 2: API Gateway Resource Policy
- API Gatewayレベルでのアクセス制御
- 許可されたIPアドレスからのみAPIリクエストを受け付ける
- IAMポリシーベースの制御

#### Layer 3: CloudFront (フロントエンド)
- フロントエンドへのアクセス制御
- WAF Web ACLでIP制限を実装（オプション）

### IP制限の設定例

#### 単一IPアドレス
```bash
ALLOWED_IPS=203.0.113.10/32
```

#### 複数のIPアドレス
```bash
ALLOWED_IPS=203.0.113.10/32,198.51.100.20/32
```

#### IPレンジ
```bash
ALLOWED_IPS=210.128.54.64/27
```
- これは 210.128.54.64 から 210.128.54.95 までの32個のIPアドレスを許可

#### 複数のIPレンジ
```bash
ALLOWED_IPS=210.128.54.64/27,192.168.1.0/24,10.0.0.0/8
```

#### 開発環境（すべてのIPを許可）
```bash
ALLOWED_IPS=0.0.0.0/0
# または
ALLOWED_IPS=
```

### IP制限の確認

デプロイ後、CloudFormation出力で設定を確認できます：

```bash
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AllowedIPRanges`].OutputValue' \
  --output text \
  --profile dev
```

## CORS制限の詳細

### CORS設定の実装

API Gatewayで以下のCORS設定が適用されます：

```python
default_cors_preflight_options=apigateway.CorsOptions(
    allow_origins=self.frontend_origins,  # 許可するオリジン
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-Amz-Date",
        "Authorization",
        "X-Api-Key",
        "X-Amz-Security-Token"
    ],
    allow_credentials=True,
    max_age=Duration.hours(1)
)
```

### CORS設定の例

#### 単一オリジン（本番環境推奨）
```bash
FRONTEND_ORIGINS=https://app.example.com
```

#### 複数のオリジン
```bash
FRONTEND_ORIGINS=https://app.example.com,https://staging.example.com
```

#### 開発環境（すべてのオリジンを許可）
```bash
FRONTEND_ORIGINS=*
# または
FRONTEND_ORIGINS=
```

### CORS設定の確認

デプロイ後、CloudFormation出力で設定を確認できます：

```bash
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendOrigins`].OutputValue' \
  --output text \
  --profile dev
```

## フロントエンドホスティング

### S3 + CloudFront構成

フロントエンドは以下の構成でホスティングされます：

1. **S3バケット**: 静的ファイルの保存
   - パブリックアクセスブロック有効
   - バージョニング有効
   - 暗号化有効

2. **CloudFront**: CDN配信
   - HTTPS強制
   - Origin Access Identity (OAI) でS3アクセス制御
   - セキュリティヘッダー自動付与
   - エラーページ設定（SPA対応）

### フロントエンドのデプロイ

#### 1. インフラストラクチャのデプロイ

```bash
# IP制限とCORS設定を含めてデプロイ
npx cdk deploy \
  --context allowed_ips="210.128.54.64/27" \
  --context frontend_origins="https://app.example.com" \
  --profile dev
```

#### 2. フロントエンドのビルドとデプロイ

```powershell
# PowerShellスクリプトを使用
.\deploy-frontend.ps1 -Profile dev

# または手動で
cd frontend
npm run build
aws s3 sync build/ s3://face-auth-frontend-{account}-{region}/ --delete --profile dev
aws cloudfront create-invalidation --distribution-id {distribution-id} --paths "/*" --profile dev
```

### フロントエンドURL取得

```bash
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendURL`].OutputValue' \
  --output text \
  --profile dev
```

## セキュリティベストプラクティス

### 本番環境

```bash
# 本番環境の推奨設定
ALLOWED_IPS=210.128.54.64/27  # 社内ネットワークのみ
FRONTEND_ORIGINS=https://app.example.com  # 本番ドメインのみ
```

### ステージング環境

```bash
# ステージング環境の推奨設定
ALLOWED_IPS=210.128.54.64/27,192.168.1.0/24  # 社内 + テストネットワーク
FRONTEND_ORIGINS=https://staging.example.com,https://test.example.com
```

### 開発環境

```bash
# 開発環境の設定（制限なし）
ALLOWED_IPS=0.0.0.0/0  # すべてのIPを許可
FRONTEND_ORIGINS=*  # すべてのオリジンを許可
```

## トラブルシューティング

### 問題: API呼び出しが403エラーになる

**原因1: IP制限**
- 現在のIPアドレスが許可リストに含まれていない

**解決策:**
```bash
# 現在のIPアドレスを確認
curl https://api.ipify.org

# ALLOWED_IPSに追加して再デプロイ
ALLOWED_IPS=210.128.54.64/27,{your-ip}/32
npx cdk deploy --profile dev
```

**原因2: CORS制限**
- フロントエンドのオリジンが許可リストに含まれていない

**解決策:**
```bash
# フロントエンドのオリジンを追加
FRONTEND_ORIGINS=https://app.example.com,https://{cloudfront-domain}
npx cdk deploy --profile dev
```

### 問題: フロントエンドが表示されない

**確認事項:**
1. CloudFrontディストリビューションが有効か
2. S3バケットにファイルがアップロードされているか
3. CloudFrontキャッシュが更新されているか

**解決策:**
```bash
# S3バケットの内容を確認
aws s3 ls s3://face-auth-frontend-{account}-{region}/ --profile dev

# CloudFrontキャッシュをクリア
aws cloudfront create-invalidation \
  --distribution-id {distribution-id} \
  --paths "/*" \
  --profile dev
```

### 問題: CORS エラーが発生する

**エラーメッセージ例:**
```
Access to fetch at 'https://api.example.com/auth/login' from origin 'https://app.example.com' 
has been blocked by CORS policy
```

**解決策:**
```bash
# フロントエンドのオリジンをFRONTEND_ORIGINSに追加
FRONTEND_ORIGINS=https://app.example.com
npx cdk deploy --profile dev

# API Gatewayの設定を確認
aws apigateway get-rest-api \
  --rest-api-id {api-id} \
  --profile dev
```

## 設定変更の手順

### 1. IP制限の変更

```bash
# 1. .envファイルを編集
ALLOWED_IPS=新しいIPレンジ

# 2. 再デプロイ
npx cdk deploy --profile dev

# 3. 設定を確認
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AllowedIPRanges`].OutputValue' \
  --output text \
  --profile dev
```

### 2. CORS設定の変更

```bash
# 1. .envファイルを編集
FRONTEND_ORIGINS=新しいオリジン

# 2. 再デプロイ
npx cdk deploy --profile dev

# 3. 設定を確認
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendOrigins`].OutputValue' \
  --output text \
  --profile dev
```

### 3. フロントエンドの再デプロイ

```powershell
# ビルドとデプロイ
.\deploy-frontend.ps1 -Profile dev

# ビルドをスキップしてデプロイのみ
.\deploy-frontend.ps1 -Profile dev -SkipBuild
```

## 参考資料

- [API Gateway Resource Policies](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-resource-policies.html)
- [CORS Configuration](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-cors.html)
- [VPC Network ACLs](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html)
- [CloudFront Security](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/SecurityAndPrivateContent.html)

---

**最終更新**: 2024年1月28日
**バージョン**: 1.0
