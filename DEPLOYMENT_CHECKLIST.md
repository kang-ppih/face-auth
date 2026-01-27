# デプロイメントチェックリスト

## 事前準備

### 1. 環境変数の設定

`.env` ファイルを作成し、以下の設定を行ってください：

```bash
# AWS設定
AWS_REGION=ap-northeast-1
CDK_DEFAULT_ACCOUNT=your-account-id
CDK_DEFAULT_REGION=ap-northeast-1

# IP制限（本番環境では必ず設定）
ALLOWED_IPS=210.128.54.64/27

# CORS設定（本番環境では必ず設定）
FRONTEND_ORIGINS=https://app.example.com

# その他の設定
REKOGNITION_COLLECTION_ID=face-auth-employees
SESSION_TIMEOUT_HOURS=8
```

### 2. AWS認証情報の確認

```bash
aws sts get-caller-identity --profile dev
```

### 3. 依存関係のインストール

```bash
# Python依存関係
pip install -r requirements.txt

# フロントエンド依存関係
cd frontend
npm install
cd ..
```

## バックエンドデプロイ

### Step 1: CDK Bootstrap（初回のみ）

```bash
npx cdk bootstrap --profile dev
```

### Step 2: CDK差分確認

```bash
npx cdk diff --profile dev
```

### Step 3: デプロイ実行

```bash
# 環境変数を使用
npx cdk deploy --profile dev

# または、コマンドラインで指定
npx cdk deploy \
  --context allowed_ips="210.128.54.64/27" \
  --context frontend_origins="https://app.example.com" \
  --profile dev
```

### Step 4: Rekognitionコレクション作成

```bash
aws rekognition create-collection \
  --collection-id face-auth-employees \
  --profile dev
```

### Step 5: デプロイ結果の確認

```bash
# API Endpoint
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`APIEndpoint`].OutputValue' \
  --output text \
  --profile dev

# Cognito User Pool ID
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text \
  --profile dev

# Cognito Client ID
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
  --output text \
  --profile dev
```

## フロントエンドデプロイ

### Step 1: 環境変数の更新

`frontend/.env` ファイルを更新：

```bash
REACT_APP_API_ENDPOINT=<API Endpoint from Step 5>
REACT_APP_AWS_REGION=ap-northeast-1
REACT_APP_COGNITO_USER_POOL_ID=<User Pool ID from Step 5>
REACT_APP_COGNITO_CLIENT_ID=<Client ID from Step 5>
```

### Step 2: ビルドとデプロイ

```powershell
# PowerShellスクリプトを使用
.\deploy-frontend.ps1 -Profile dev
```

または手動で：

```bash
# ビルド
cd frontend
npm run build

# S3にアップロード
aws s3 sync build/ s3://<frontend-bucket-name>/ --delete --profile dev

# CloudFrontキャッシュクリア
aws cloudfront create-invalidation \
  --distribution-id <distribution-id> \
  --paths "/*" \
  --profile dev
```

### Step 3: フロントエンドURL確認

```bash
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendURL`].OutputValue' \
  --output text \
  --profile dev
```

## デプロイ後の確認

### 1. API動作確認

```bash
# ステータスエンドポイント
curl https://<api-endpoint>/prod/auth/status

# 期待される結果: 200 OK
```

### 2. フロントエンドアクセス確認

ブラウザで `https://<cloudfront-domain>` にアクセス

### 3. IP制限の確認

```bash
# 許可されたIPから
curl https://<api-endpoint>/prod/auth/status
# → 200 OK

# 許可されていないIPから（VPNなどで確認）
curl https://<api-endpoint>/prod/auth/status
# → 403 Forbidden
```

### 4. CORS設定の確認

ブラウザのコンソールで：

```javascript
fetch('https://<api-endpoint>/prod/auth/status')
  .then(response => console.log(response.status))
```

### 5. セキュリティヘッダーの確認

```bash
curl -I https://<cloudfront-domain>
```

期待されるヘッダー：
- `x-content-type-options: nosniff`
- `x-frame-options: DENY`
- `strict-transport-security: max-age=31536000; includeSubdomains`
- `x-xss-protection: 1; mode=block`

## トラブルシューティング

### 問題: CDKデプロイが失敗する

**確認事項:**
- [ ] AWS認証情報が正しいか
- [ ] 必要な権限があるか
- [ ] リージョンが正しいか
- [ ] 環境変数が設定されているか

**解決策:**
```bash
# スタック状態確認
aws cloudformation describe-stacks --stack-name FaceAuthStack --profile dev

# エラーログ確認
aws cloudformation describe-stack-events --stack-name FaceAuthStack --profile dev
```

### 問題: フロントエンドが表示されない

**確認事項:**
- [ ] S3にファイルがアップロードされているか
- [ ] CloudFrontディストリビューションが有効か
- [ ] 環境変数が正しいか

**解決策:**
```bash
# S3バケット確認
aws s3 ls s3://<frontend-bucket-name>/ --profile dev

# CloudFrontキャッシュクリア
aws cloudfront create-invalidation \
  --distribution-id <distribution-id> \
  --paths "/*" \
  --profile dev
```

### 問題: API呼び出しが403エラー

**確認事項:**
- [ ] IPアドレスが許可リストに含まれているか
- [ ] CORSオリジンが許可リストに含まれているか

**解決策:**
```bash
# 現在のIPアドレス確認
curl https://api.ipify.org

# 設定確認
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AllowedIPRanges`].OutputValue' \
  --output text \
  --profile dev
```

## ロールバック手順

### バックエンドのロールバック

```bash
# スタック削除
npx cdk destroy --profile dev

# 再デプロイ
npx cdk deploy --profile dev
```

### フロントエンドのロールバック

```bash
# S3バケットのバージョニングを使用
aws s3api list-object-versions \
  --bucket <frontend-bucket-name> \
  --profile dev

# 特定バージョンに戻す
aws s3api copy-object \
  --bucket <frontend-bucket-name> \
  --copy-source <bucket>/<key>?versionId=<version-id> \
  --key <key> \
  --profile dev
```

## セキュリティチェックリスト

### デプロイ前
- [ ] ALLOWED_IPSが設定されている（本番環境）
- [ ] FRONTEND_ORIGINSが設定されている（本番環境）
- [ ] 機密情報がコードに含まれていない
- [ ] .envファイルが.gitignoreに含まれている

### デプロイ後
- [ ] IP制限が機能している
- [ ] CORS設定が機能している
- [ ] HTTPS接続が強制されている
- [ ] セキュリティヘッダーが設定されている
- [ ] パブリックアクセスがブロックされている

## 環境別設定

### 開発環境
```bash
ALLOWED_IPS=0.0.0.0/0
FRONTEND_ORIGINS=*
```

### ステージング環境
```bash
ALLOWED_IPS=210.128.54.64/27,192.168.1.0/24
FRONTEND_ORIGINS=https://staging.example.com
```

### 本番環境
```bash
ALLOWED_IPS=210.128.54.64/27
FRONTEND_ORIGINS=https://app.example.com
```

## 参考ドキュメント

- [デプロイメントガイド](DEPLOYMENT_GUIDE.md)
- [CORS・IP制限ガイド](CORS_AND_IP_RESTRICTION_GUIDE.md)
- [フロントエンドクイックスタート](FRONTEND_QUICK_START.md)
- [インフラストラクチャアーキテクチャ](docs/INFRASTRUCTURE_ARCHITECTURE.md)

---

**最終更新**: 2024年1月28日
**バージョン**: 1.0
