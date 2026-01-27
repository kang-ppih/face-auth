# Face-Auth IdP System - デプロイ後セットアップガイド

## ✅ デプロイ完了

**デプロイ日時:** 2024年
**スタック名:** FaceAuthIdPStack
**リージョン:** ap-northeast-1
**AWS Profile:** dev

---

## 📋 デプロイ済みリソース

### API Gateway
- **エンドポイント:** https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/
- **API Key ID:** s3jyk9dhm1
- **ステージ:** prod

### Cognito
- **User Pool ID:** ap-northeast-1_ikSWDeIew
- **User Pool Client ID:** 6u4blhui7p35ra4p882srvrpod

### S3
- **バケット名:** face-auth-images-979431736455-ap-northeast-1

### VPC
- **VPC ID:** vpc-0af2750e674368e60
- **許可IPレンジ:** 0.0.0.0/0 (全IPアドレス許可 - 本番環境では制限推奨)

### Lambda関数
- FaceAuth-Enrollment
- FaceAuth-FaceLogin
- FaceAuth-EmergencyAuth
- FaceAuth-ReEnrollment
- FaceAuth-Status

### DynamoDB テーブル
- FaceAuth-CardTemplates
- FaceAuth-EmployeeFaces
- FaceAuth-AuthSessions

---

## 🚀 必須セットアップ手順

### 1. Rekognitionコレクション作成

顔認識機能を使用するために、Rekognitionコレクションを作成します。

```bash
aws rekognition create-collection \
  --collection-id face-auth-employees \
  --region ap-northeast-1 \
  --profile dev
```

**確認:**
```bash
aws rekognition describe-collection \
  --collection-id face-auth-employees \
  --region ap-northeast-1 \
  --profile dev
```

**期待される出力:**
```json
{
    "FaceCount": 0,
    "FaceModelVersion": "7.0",
    "CollectionARN": "arn:aws:rekognition:ap-northeast-1:979431736455:collection/face-auth-employees",
    "CreationTimestamp": "2024-XX-XX..."
}
```

---

### 2. DynamoDBカードテンプレート初期化

社員証OCR用のテンプレートデータを登録します。

```bash
# 仮想環境がアクティブでない場合
venv\Scripts\activate

# スクリプト実行
python scripts/init_dynamodb.py
```

**確認:**
```bash
aws dynamodb scan \
  --table-name FaceAuth-CardTemplates \
  --region ap-northeast-1 \
  --profile dev
```

**期待される結果:**
- 3つのカードテンプレートが登録されている
- template_id: standard_card_v1, premium_card_v1, contractor_card_v1

---

### 3. API動作確認

#### 3.1 ステータスエンドポイント確認

```bash
curl -X GET https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
```

**期待される出力:**
```json
{
  "status": "healthy",
  "timestamp": "2024-XX-XXTXX:XX:XX.XXXXXXZ",
  "version": "1.0.0",
  "services": {
    "dynamodb": "available",
    "s3": "available",
    "rekognition": "available",
    "cognito": "available"
  }
}
```

#### 3.2 API Key取得

```bash
aws apigateway get-api-key \
  --api-key s3jyk9dhm1 \
  --include-value \
  --region ap-northeast-1 \
  --profile dev
```

**API Keyを使用したリクエスト例:**
```bash
curl -X GET \
  -H "x-api-key: YOUR_API_KEY_VALUE" \
  https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
```

---

## 🔧 オプション設定

### 4. IP制限の設定（本番環境推奨）

現在、すべてのIPアドレスからのアクセスが許可されています。本番環境では特定のIPレンジに制限することを推奨します。

#### 4.1 許可するIPレンジの確認

```bash
# 現在のオフィスIPを確認
curl https://api.ipify.org
```

#### 4.2 infrastructure/face_auth_stack.py を更新

```python
# 現在の設定
allowed_ips = ["0.0.0.0/0"]

# 本番環境での推奨設定
allowed_ips = [
    "203.0.113.0/24",  # オフィスネットワーク
    "198.51.100.0/24"  # VPNネットワーク
]
```

#### 4.3 再デプロイ

```bash
npx cdk deploy --profile dev
```

---

### 5. CORS設定の更新（本番環境推奨）

現在、すべてのオリジンからのアクセスが許可されています。

#### 5.1 infrastructure/face_auth_stack.py を更新

```python
# 現在の設定
allow_origins=["*"]

# 本番環境での推奨設定
allow_origins=[
    "https://your-frontend-domain.com",
    "https://admin.your-domain.com"
]
```

#### 5.2 再デプロイ

```bash
npx cdk deploy --profile dev
```

---

### 6. CloudWatch アラーム設定

重要なメトリクスに対してアラームを設定します。

#### 6.1 Lambda エラー率アラーム

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name FaceAuth-Lambda-Errors \
  --alarm-description "Alert when Lambda error rate exceeds 5%" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --region ap-northeast-1 \
  --profile dev
```

#### 6.2 API Gateway 4xx/5xx エラーアラーム

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name FaceAuth-API-5xxErrors \
  --alarm-description "Alert when API 5xx errors exceed 10" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --region ap-northeast-1 \
  --profile dev
```

---

### 7. バックアップ設定

#### 7.1 DynamoDB ポイントインタイムリカバリ有効化

```bash
# EmployeeFaces テーブル
aws dynamodb update-continuous-backups \
  --table-name FaceAuth-EmployeeFaces \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
  --region ap-northeast-1 \
  --profile dev

# AuthSessions テーブル
aws dynamodb update-continuous-backups \
  --table-name FaceAuth-AuthSessions \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
  --region ap-northeast-1 \
  --profile dev

# CardTemplates テーブル
aws dynamodb update-continuous-backups \
  --table-name FaceAuth-CardTemplates \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
  --region ap-northeast-1 \
  --profile dev
```

#### 7.2 S3 バージョニング有効化

```bash
aws s3api put-bucket-versioning \
  --bucket face-auth-images-979431736455-ap-northeast-1 \
  --versioning-configuration Status=Enabled \
  --region ap-northeast-1 \
  --profile dev
```

---

## 🧪 エンドツーエンドテスト

### テストシナリオ1: 社員登録（Enrollment）

```bash
# 1. 社員証画像をBase64エンコード
# (実際の画像ファイルを使用)

# 2. Enrollmentエンドポイントにリクエスト
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "employee_id": "EMP001",
    "card_image": "BASE64_ENCODED_IMAGE",
    "face_image": "BASE64_ENCODED_FACE_IMAGE"
  }' \
  https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/enrollment
```

**期待される出力:**
```json
{
  "success": true,
  "employee_id": "EMP001",
  "face_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "message": "Enrollment successful"
}
```

---

### テストシナリオ2: 顔認証ログイン（Face Login）

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "face_image": "BASE64_ENCODED_FACE_IMAGE"
  }' \
  https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/face-login
```

**期待される出力:**
```json
{
  "success": true,
  "employee_id": "EMP001",
  "session_token": "eyJraWQiOiJ...",
  "access_token": "eyJraWQiOiJ...",
  "refresh_token": "eyJraWQiOiJ...",
  "expires_in": 3600
}
```

---

### テストシナリオ3: 緊急認証（Emergency Auth）

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{
    "card_image": "BASE64_ENCODED_CARD_IMAGE",
    "password": "user_ad_password"
  }' \
  https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/emergency
```

**期待される出力:**
```json
{
  "success": true,
  "employee_id": "EMP001",
  "session_token": "eyJraWQiOiJ...",
  "access_token": "eyJraWQiOiJ...",
  "refresh_token": "eyJraWQiOiJ...",
  "expires_in": 3600
}
```

---

## 🔐 セキュリティチェックリスト

### デプロイ直後

- [x] Rekognitionコレクション作成
- [x] DynamoDBテーブル初期化
- [x] API動作確認
- [ ] API Key取得・保管
- [ ] CloudWatch Logs確認

### 本番環境移行前

- [ ] IP制限設定（0.0.0.0/0 → 特定IPレンジ）
- [ ] CORS設定更新（* → 特定ドメイン）
- [ ] API Keyローテーション設定
- [ ] CloudWatch アラーム設定
- [ ] DynamoDB バックアップ有効化
- [ ] S3 バージョニング有効化
- [ ] AWS WAF設定
- [ ] AWS Secrets Manager移行（環境変数）
- [ ] Direct Connect設定（AD接続用）
- [ ] SSL証明書設定（カスタムドメイン）

---

## 📊 モニタリング

### CloudWatch Logs確認

```bash
# Lambda関数のログ確認
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev
aws logs tail /aws/lambda/FaceAuth-FaceLogin --follow --profile dev
aws logs tail /aws/lambda/FaceAuth-EmergencyAuth --follow --profile dev
```

### メトリクス確認

```bash
# Lambda実行回数
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=FaceAuth-Enrollment \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-12-31T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --region ap-northeast-1 \
  --profile dev
```

---

## 🔄 Direct Connect設定（オプション）

Active Directory接続のために、オンプレミスネットワークとAWS VPCを接続します。

### 前提条件
- Direct Connect物理接続が確立済み
- Virtual Private Gateway (VGW) 作成済み
- BGP設定完了

### 設定手順

1. **Virtual Private Gateway作成**
```bash
aws ec2 create-vpn-gateway \
  --type ipsec.1 \
  --amazon-side-asn 64512 \
  --region ap-northeast-1 \
  --profile dev
```

2. **VPCにアタッチ**
```bash
aws ec2 attach-vpn-gateway \
  --vpn-gateway-id vgw-xxxxxxxxx \
  --vpc-id vpc-0af2750e674368e60 \
  --region ap-northeast-1 \
  --profile dev
```

3. **ルートテーブル更新**
```bash
# オンプレミスネットワークへのルート追加
aws ec2 create-route \
  --route-table-id rtb-xxxxxxxxx \
  --destination-cidr-block 10.0.0.0/8 \
  --gateway-id vgw-xxxxxxxxx \
  --region ap-northeast-1 \
  --profile dev
```

4. **セキュリティグループ更新**
```bash
# AD接続用ポート開放（LDAP: 389, LDAPS: 636）
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxx \
  --protocol tcp \
  --port 389 \
  --cidr 10.0.0.0/8 \
  --region ap-northeast-1 \
  --profile dev
```

---

## 🐛 トラブルシューティング

### 問題1: API Gateway 403 Forbidden

**原因:** API Keyが設定されていない、または無効

**解決策:**
```bash
# API Key取得
aws apigateway get-api-key \
  --api-key s3jyk9dhm1 \
  --include-value \
  --region ap-northeast-1 \
  --profile dev

# リクエストヘッダーに追加
curl -H "x-api-key: YOUR_API_KEY" ...
```

---

### 問題2: Lambda タイムアウト

**原因:** AD接続に時間がかかりすぎる

**解決策:**
1. TimeoutManagerが正しく動作しているか確認
2. AD_TIMEOUT環境変数を調整（デフォルト: 10秒）
3. Direct Connect接続を確認

---

### 問題3: Rekognition FaceNotFound

**原因:** コレクションが作成されていない、または顔が登録されていない

**解決策:**
```bash
# コレクション確認
aws rekognition describe-collection \
  --collection-id face-auth-employees \
  --region ap-northeast-1 \
  --profile dev

# 登録済み顔の数を確認
# FaceCount が 0 の場合、Enrollmentを実行
```

---

### 問題4: DynamoDB テーブルが見つからない

**原因:** テーブル名が環境変数と一致していない

**解決策:**
```bash
# テーブル一覧確認
aws dynamodb list-tables --region ap-northeast-1 --profile dev

# Lambda環境変数確認
aws lambda get-function-configuration \
  --function-name FaceAuth-Enrollment \
  --region ap-northeast-1 \
  --profile dev
```

---

## 📞 サポート

### ドキュメント
- [README.md](README.md) - プロジェクト概要
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - デプロイ手順
- [LOCAL_EXECUTION_GUIDE.md](LOCAL_EXECUTION_GUIDE.md) - ローカル開発
- [docs/](docs/) - 技術ドキュメント

### AWS リソース
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Amazon Rekognition Documentation](https://docs.aws.amazon.com/rekognition/)
- [Amazon Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)

---

## 📝 次のステップ

1. ✅ Rekognitionコレクション作成
2. ✅ DynamoDBテーブル初期化
3. ✅ API動作確認
4. ⏳ テストユーザーで登録・ログインテスト
5. ⏳ IP制限・CORS設定更新
6. ⏳ CloudWatch アラーム設定
7. ⏳ バックアップ設定
8. ⏳ Direct Connect設定（必要に応じて）
9. ⏳ 本番環境デプロイ

---

**作成日:** 2024年
**最終更新:** 2024年
**バージョン:** 1.0
**プロジェクト:** Face-Auth IdP System

