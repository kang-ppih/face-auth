# Face-Auth IdP System - デプロイ済みリソース一覧

## 📅 デプロイ情報

- **デプロイ日時:** 2024年
- **スタック名:** FaceAuthIdPStack
- **リージョン:** ap-northeast-1 (東京)
- **AWS Account:** 979431736455
- **AWS Profile:** dev
- **デプロイ時間:** 280.92秒 (~4.7分)
- **リソース数:** 91個

---

## 🌐 API Gateway

### エンドポイント
```
https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/
```

### API Key
```
ID: s3jyk9dhm1
```

### 利用可能なエンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/auth/status` | システムステータス確認 |
| POST | `/auth/enrollment` | 社員登録（社員証+顔） |
| POST | `/auth/face-login` | 顔認証ログイン |
| POST | `/auth/emergency` | 緊急認証（社員証+パスワード） |
| POST | `/auth/re-enrollment` | 顔再登録 |

---

## 🔐 Amazon Cognito

### User Pool
```
User Pool ID: ap-northeast-1_ikSWDeIew
User Pool Client ID: 6u4blhui7p35ra4p882srvrpod
```

### 設定
- **パスワードポリシー:** 最小8文字、大文字・小文字・数字・記号必須
- **MFA:** オプション
- **セッション有効期限:** 8時間（設定可能）
- **トークンタイプ:** JWT (Access Token, ID Token, Refresh Token)

---

## 📦 Amazon S3

### バケット
```
face-auth-images-979431736455-ap-northeast-1
```

### 用途
- 社員証画像保存
- 顔画像保存
- サムネイル画像保存
- 認証失敗時の画像保存

### セキュリティ
- ✅ パブリックアクセスブロック有効
- ✅ 暗号化有効（AWS管理キー）
- ✅ バージョニング: 未設定（推奨: 有効化）
- ✅ ライフサイクルポリシー: 未設定

---

## 🗄️ Amazon DynamoDB

### テーブル一覧

#### 1. FaceAuth-EmployeeFaces
```
テーブル名: FaceAuth-EmployeeFaces
パーティションキー: employee_id (String)
```

**用途:** 社員情報と顔データの管理

**属性:**
- employee_id (PK)
- face_id
- name
- department
- email
- enrolled_at
- last_login
- card_template_id

**設定:**
- 暗号化: AWS管理キー
- ポイントインタイムリカバリ: 未設定（推奨: 有効化）
- オンデマンド課金

---

#### 2. FaceAuth-AuthSessions
```
テーブル名: FaceAuth-AuthSessions
パーティションキー: session_id (String)
```

**用途:** 認証セッション管理

**属性:**
- session_id (PK)
- employee_id
- created_at
- expires_at
- ttl (DynamoDB TTL用)
- auth_method
- ip_address

**設定:**
- 暗号化: AWS管理キー
- TTL有効: ttl属性
- ポイントインタイムリカバリ: 未設定（推奨: 有効化）
- オンデマンド課金

---

#### 3. FaceAuth-CardTemplates
```
テーブル名: FaceAuth-CardTemplates
パーティションキー: template_id (String)
```

**用途:** 社員証OCRテンプレート管理

**属性:**
- template_id (PK)
- template_name
- field_mappings
- created_at
- updated_at

**設定:**
- 暗号化: AWS管理キー
- ポイントインタイムリカバリ: 未設定（推奨: 有効化）
- オンデマンド課金

---

## 🤖 AWS Lambda

### Lambda関数一覧

#### 1. FaceAuth-Enrollment
```
関数名: FaceAuth-Enrollment
ランタイム: Python 3.9
メモリ: 512 MB
タイムアウト: 15秒
```

**用途:** 社員登録（社員証OCR + 顔登録）

**環境変数:**
- FACE_AUTH_BUCKET
- EMPLOYEE_FACES_TABLE
- CARD_TEMPLATES_TABLE
- REKOGNITION_COLLECTION_ID
- COGNITO_USER_POOL_ID

---

#### 2. FaceAuth-FaceLogin
```
関数名: FaceAuth-FaceLogin
ランタイム: Python 3.9
メモリ: 512 MB
タイムアウト: 15秒
```

**用途:** 顔認証ログイン（Liveness検出 + 1:N検索）

**環境変数:**
- FACE_AUTH_BUCKET
- EMPLOYEE_FACES_TABLE
- AUTH_SESSIONS_TABLE
- REKOGNITION_COLLECTION_ID
- COGNITO_USER_POOL_ID
- COGNITO_CLIENT_ID

---

#### 3. FaceAuth-EmergencyAuth
```
関数名: FaceAuth-EmergencyAuth
ランタイム: Python 3.9
メモリ: 512 MB
タイムアウト: 15秒
```

**用途:** 緊急認証（社員証OCR + ADパスワード検証）

**環境変数:**
- FACE_AUTH_BUCKET
- EMPLOYEE_FACES_TABLE
- AUTH_SESSIONS_TABLE
- CARD_TEMPLATES_TABLE
- COGNITO_USER_POOL_ID
- COGNITO_CLIENT_ID
- AD_TIMEOUT (10秒)

---

#### 4. FaceAuth-ReEnrollment
```
関数名: FaceAuth-ReEnrollment
ランタイム: Python 3.9
メモリ: 512 MB
タイムアウト: 15秒
```

**用途:** 顔再登録（本人確認 + 古い顔削除 + 新しい顔登録）

**環境変数:**
- FACE_AUTH_BUCKET
- EMPLOYEE_FACES_TABLE
- CARD_TEMPLATES_TABLE
- REKOGNITION_COLLECTION_ID

---

#### 5. FaceAuth-Status
```
関数名: FaceAuth-Status
ランタイム: Python 3.9
メモリ: 256 MB
タイムアウト: 10秒
```

**用途:** システムステータス確認

**環境変数:**
- EMPLOYEE_FACES_TABLE
- FACE_AUTH_BUCKET
- REKOGNITION_COLLECTION_ID
- COGNITO_USER_POOL_ID

---

## 👁️ Amazon Rekognition

### コレクション
```
Collection ID: face-auth-employees
```

**ステータス:** ⚠️ 作成必要

**作成コマンド:**
```bash
aws rekognition create-collection \
  --collection-id face-auth-employees \
  --region ap-northeast-1 \
  --profile dev
```

**用途:**
- 顔特徴量の保存
- 1:N 顔検索
- Liveness検出

---

## 🌐 Amazon VPC

### VPC
```
VPC ID: vpc-0af2750e674368e60
CIDR: 10.0.0.0/16
Allowed IP Ranges: 210.128.54.64/27
```

### サブネット

#### Private Subnet 1
```
Subnet ID: subnet-xxxxxxxxx
CIDR: 10.0.1.0/24
AZ: ap-northeast-1a
```

#### Private Subnet 2
```
Subnet ID: subnet-xxxxxxxxx
CIDR: 10.0.2.0/24
AZ: ap-northeast-1c
```

### セキュリティグループ

#### Lambda Security Group
```
Security Group ID: sg-xxxxxxxxx
```

**インバウンドルール:**
- なし（Lambda関数は外部からの直接アクセス不可）

**アウトバウンドルール:**
- すべてのトラフィック許可（AWS サービスへのアクセス用）

---

## 📊 Amazon CloudWatch

### ログ グループ

| ログ グループ | 保持期間 |
|-------------|---------|
| `/aws/lambda/FaceAuth-Enrollment` | 7日 |
| `/aws/lambda/FaceAuth-FaceLogin` | 7日 |
| `/aws/lambda/FaceAuth-EmergencyAuth` | 7日 |
| `/aws/lambda/FaceAuth-ReEnrollment` | 7日 |
| `/aws/lambda/FaceAuth-Status` | 7日 |

### メトリクス

**Lambda:**
- Invocations（実行回数）
- Errors（エラー数）
- Duration（実行時間）
- Throttles（スロットリング）

**API Gateway:**
- Count（リクエスト数）
- 4XXError（クライアントエラー）
- 5XXError（サーバーエラー）
- Latency（レイテンシ）

**DynamoDB:**
- ConsumedReadCapacityUnits
- ConsumedWriteCapacityUnits
- UserErrors
- SystemErrors

---

## 🔒 IAM ロール

### Lambda実行ロール

#### FaceAuth-Enrollment-Role
**許可されたアクション:**
- S3: PutObject, GetObject
- DynamoDB: PutItem, GetItem, Query
- Rekognition: IndexFaces, DetectFaces
- Cognito: AdminCreateUser
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents

#### FaceAuth-FaceLogin-Role
**許可されたアクション:**
- S3: PutObject, GetObject
- DynamoDB: GetItem, PutItem, UpdateItem
- Rekognition: SearchFacesByImage, DetectFaces
- Cognito: AdminInitiateAuth, AdminGetUser
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents

#### FaceAuth-EmergencyAuth-Role
**許可されたアクション:**
- S3: PutObject, GetObject
- DynamoDB: GetItem, PutItem, UpdateItem
- Textract: AnalyzeDocument
- Cognito: AdminInitiateAuth
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents
- VPC: CreateNetworkInterface, DescribeNetworkInterfaces, DeleteNetworkInterface

---

## 💰 コスト見積もり

### 月間コスト（想定: 1000ユーザー、1日10回ログイン）

| サービス | 使用量 | 月額コスト（USD） |
|---------|--------|-----------------|
| Lambda | 300,000実行/月 | $0.60 |
| API Gateway | 300,000リクエスト/月 | $1.05 |
| DynamoDB | オンデマンド | $2.50 |
| S3 | 10GB保存 + 転送 | $0.30 |
| Rekognition | 300,000検索/月 | $300.00 |
| Cognito | 1000 MAU | $0.00（無料枠） |
| CloudWatch Logs | 5GB/月 | $2.50 |
| VPC | NAT Gateway | $32.40 |
| **合計** | | **約 $339/月** |

**注意:** Rekognitionが最大のコスト要因です。使用量に応じて変動します。

---

## 🔧 環境変数一覧

### 共通環境変数

```bash
AWS_REGION=ap-northeast-1
CDK_DEFAULT_ACCOUNT=979431736455
CDK_DEFAULT_REGION=ap-northeast-1
```

### Lambda環境変数

```bash
# S3
FACE_AUTH_BUCKET=face-auth-images-979431736455-ap-northeast-1

# DynamoDB
CARD_TEMPLATES_TABLE=FaceAuth-CardTemplates
EMPLOYEE_FACES_TABLE=FaceAuth-EmployeeFaces
AUTH_SESSIONS_TABLE=FaceAuth-AuthSessions

# Cognito
COGNITO_USER_POOL_ID=ap-northeast-1_ikSWDeIew
COGNITO_CLIENT_ID=6u4blhui7p35ra4p882srvrpod

# Rekognition
REKOGNITION_COLLECTION_ID=face-auth-employees

# タイムアウト
AD_TIMEOUT=10
SESSION_TIMEOUT_HOURS=8
```

---

## 📋 クイックリファレンス

### API呼び出し例

```bash
# ステータス確認
curl https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status

# 社員登録
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"employee_id":"EMP001","card_image":"BASE64","face_image":"BASE64"}' \
  https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/enrollment

# 顔認証ログイン
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-api-key: YOUR_API_KEY" \
  -d '{"face_image":"BASE64"}' \
  https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/face-login
```

### AWS CLI コマンド

```bash
# Rekognitionコレクション作成
aws rekognition create-collection --collection-id face-auth-employees --region ap-northeast-1 --profile dev

# DynamoDB初期化
python scripts/init_dynamodb.py

# Lambda ログ確認
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev

# API Key取得
aws apigateway get-api-key --api-key s3jyk9dhm1 --include-value --region ap-northeast-1 --profile dev
```

---

## ⚠️ セキュリティ注意事項

### 現在の設定（開発環境）

- ✅ すべてのリソースが暗号化済み
- ✅ Lambda関数はPrivate Subnetに配置
- ✅ IAM最小権限の原則適用
- ⚠️ **IP制限: 0.0.0.0/0（全IP許可）**
- ⚠️ **CORS: *（全オリジン許可）**
- ⚠️ **API Key: 固定値**

### 本番環境への移行前に必須

1. **IP制限を特定レンジに変更**
2. **CORS設定を特定ドメインに制限**
3. **API Keyローテーション設定**
4. **CloudWatch アラーム設定**
5. **バックアップ有効化**
6. **WAF設定**
7. **Secrets Manager使用**

---

## 📞 次のアクション

### 即座に実行

1. ✅ Rekognitionコレクション作成
   ```bash
   aws rekognition create-collection --collection-id face-auth-employees --region ap-northeast-1 --profile dev
   ```

2. ✅ DynamoDBテーブル初期化
   ```bash
   python scripts/init_dynamodb.py
   ```

3. ✅ API動作確認
   ```bash
   curl https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
   ```

### 本番環境移行前

4. ⏳ セキュリティ設定強化
5. ⏳ モニタリング・アラート設定
6. ⏳ バックアップ設定
7. ⏳ Direct Connect設定（AD接続用）

---

**作成日:** 2024年
**最終更新:** 2024年
**バージョン:** 1.0

