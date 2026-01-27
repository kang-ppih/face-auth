# Face-Auth ローカル実行ガイド

## 概要

このガイドは、Face-Auth IdP システムをローカル環境で実行する方法を説明します。

## 前提条件

### 1. Python環境
```bash
python --version  # Python 3.9以上が必要
```

### 2. 必須パッケージのインストール
```bash
pip install -r requirements.txt
```

### 3. AWSアカウントおよび認証情報
- AWSアカウントが必要
- IAMユーザー作成およびアクセスキー発行

---

## AWS認証情報設定

### 方法 1: AWS CLI使用 (推奨)

#### 1.1 AWS CLIインストール
```bash
# Windows (PowerShell)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# インストール確認
aws --version
```

#### 1.2 AWS認証情報構成
```bash
aws configure
```

入力情報:
```
AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
Default region name [None]: ap-northeast-1
Default output format [None]: json
```

#### 1.3 認証情報確認
```bash
aws sts get-caller-identity
```

成功時の出力:
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

### 方法 2: 環境変数設定

#### Windows (PowerShell)
```powershell
$env:AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY"
$env:AWS_DEFAULT_REGION="ap-northeast-1"
```

#### 永続設定 (システム環境変数)
1. システムのプロパティ → 環境変数
2. 新規作成:
   - `AWS_ACCESS_KEY_ID`: YOUR_ACCESS_KEY_ID
   - `AWS_SECRET_ACCESS_KEY`: YOUR_SECRET_ACCESS_KEY
   - `AWS_DEFAULT_REGION`: ap-northeast-1

---

## AWSリソース作成

### 1. S3バケット作成
```bash
aws s3 mb s3://face-auth-dev-bucket --region ap-northeast-1
```

### 2. DynamoDBテーブル作成
```bash
# CardTemplatesテーブル
aws dynamodb create-table \
    --table-name CardTemplates \
    --attribute-definitions AttributeName=pattern_id,AttributeType=S \
    --key-schema AttributeName=pattern_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region ap-northeast-1

# EmployeeFacesテーブル
aws dynamodb create-table \
    --table-name EmployeeFaces \
    --attribute-definitions AttributeName=employee_id,AttributeType=S \
    --key-schema AttributeName=employee_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region ap-northeast-1

# AuthSessionsテーブル (TTL含む)
aws dynamodb create-table \
    --table-name AuthSessions \
    --attribute-definitions AttributeName=session_id,AttributeType=S \
    --key-schema AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region ap-northeast-1

# TTL有効化
aws dynamodb update-time-to-live \
    --table-name AuthSessions \
    --time-to-live-specification "Enabled=true, AttributeName=expires_at" \
    --region ap-northeast-1
```

### 3. Cognito User Pool作成
```bash
# User Pool作成
aws cognito-idp create-user-pool \
    --pool-name face-auth-users \
    --policies "PasswordPolicy={MinimumLength=8,RequireUppercase=false,RequireLowercase=false,RequireNumbers=false,RequireSymbols=false}" \
    --region ap-northeast-1

# User Pool IDを保存 (出力から確認)
# 例: ap-northeast-1_XXXXXXXXX

# App Client作成
aws cognito-idp create-user-pool-client \
    --user-pool-id ap-northeast-1_XXXXXXXXX \
    --client-name face-auth-client \
    --explicit-auth-flows ADMIN_NO_SRP_AUTH \
    --region ap-northeast-1

# Client IDを保存 (出力から確認)
```

### 4. Rekognition Collection作成
```bash
aws rekognition create-collection \
    --collection-id face-auth-employees \
    --region ap-northeast-1
```

---

## 環境変数設定

### ローカル実行用環境変数ファイル作成

`.env` ファイル作成:
```bash
# AWS設定
AWS_REGION=ap-northeast-1
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY

# S3設定
FACE_AUTH_BUCKET=face-auth-dev-bucket

# DynamoDB設定
CARD_TEMPLATES_TABLE=CardTemplates
EMPLOYEE_FACES_TABLE=EmployeeFaces
AUTH_SESSIONS_TABLE=AuthSessions

# Cognito設定
COGNITO_USER_POOL_ID=ap-northeast-1_XXXXXXXXX
COGNITO_CLIENT_ID=your-client-id

# Rekognition設定
REKOGNITION_COLLECTION_ID=face-auth-employees

# セッション設定
SESSION_TIMEOUT_HOURS=8
```

### 環境変数ロード (PowerShell)
```powershell
# .envファイルから環境変数をロード
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}
```

---

## 初期データ設定

### 1. カードテンプレート初期化
```bash
python scripts/init_dynamodb.py
```

このスクリプトは基本カードテンプレートをDynamoDBに作成します。

### 2. データモデルデモ実行
```bash
python scripts/demo_data_models.py
```

---

## ローカルテスト実行

### 1. 単体テスト (AWS不要)
```bash
python -m pytest tests/ --ignore=tests/test_ad_connector.py -v
```

### 2. 統合テスト (AWS必要)
```bash
# 環境変数設定後
python -m pytest tests/test_backend_integration.py -v
```

---

## Lambdaハンドラーローカルテスト

### テストスクリプト作成

`test_local_handler.py` ファイル作成:
```python
import os
import sys
import json
import base64

# 環境変数設定
os.environ['FACE_AUTH_BUCKET'] = 'face-auth-dev-bucket'
os.environ['CARD_TEMPLATES_TABLE'] = 'CardTemplates'
os.environ['EMPLOYEE_FACES_TABLE'] = 'EmployeeFaces'
os.environ['AUTH_SESSIONS_TABLE'] = 'AuthSessions'
os.environ['COGNITO_USER_POOL_ID'] = 'ap-northeast-1_XXXXXXXXX'
os.environ['COGNITO_CLIENT_ID'] = 'your-client-id'
os.environ['REKOGNITION_COLLECTION_ID'] = 'face-auth-employees'
os.environ['AWS_REGION'] = 'ap-northeast-1'

# Lambdaパス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lambda'))

from enrollment.handler import handle_enrollment

# Mock context
class MockContext:
    aws_request_id = 'test-request-id'
    function_name = 'test-function'
    memory_limit_in_mb = 512
    invoked_function_arn = 'arn:aws:lambda:ap-northeast-1:123456789012:function:test'

# テスト画像 (1x1ピクセルPNG)
test_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01').decode()

# テストイベント
event = {
    'body': json.dumps({
        'id_card_image': test_image,
        'face_image': test_image
    }),
    'requestContext': {
        'identity': {
            'sourceIp': '127.0.0.1'
        }
    },
    'headers': {
        'User-Agent': 'Test/1.0'
    }
}

# ハンドラー実行
context = MockContext()
response = handle_enrollment(event, context)

print(json.dumps(json.loads(response['body']), indent=2, ensure_ascii=False))
```

### 実行
```bash
python test_local_handler.py
```

---

## IAM権限設定

ローカル実行のための最小IAM権限:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::face-auth-dev-bucket/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:ap-northeast-1:*:table/CardTemplates",
                "arn:aws:dynamodb:ap-northeast-1:*:table/EmployeeFaces",
                "arn:aws:dynamodb:ap-northeast-1:*:table/AuthSessions"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:AdminCreateUser",
                "cognito-idp:AdminGetUser",
                "cognito-idp:AdminInitiateAuth",
                "cognito-idp:AdminSetUserPassword",
                "cognito-idp:AdminEnableUser",
                "cognito-idp:AdminDisableUser",
                "cognito-idp:AdminUserGlobalSignOut"
            ],
            "Resource": "arn:aws:cognito-idp:ap-northeast-1:*:userpool/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "rekognition:CreateCollection",
                "rekognition:DeleteCollection",
                "rekognition:DetectFaces",
                "rekognition:IndexFaces",
                "rekognition:SearchFacesByImage",
                "rekognition:DeleteFaces",
                "rekognition:ListFaces"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "textract:AnalyzeDocument"
            ],
            "Resource": "*"
        }
    ]
}
```

---

## コスト管理

### 予想コスト (開発/テスト環境)

- **S3**: ほぼ無料 (GBあたり$0.023)
- **DynamoDB**: 無料枠 (25GB, 25読み取り/書き込みユニット)
- **Cognito**: 無料枠 (月間50,000 MAU)
- **Rekognition**: 
  - 顔検出: 1,000件あたり$1.00
  - 顔検索: 1,000件あたり$1.00
- **Textract**: 1,000ページあたり$1.50

### コスト削減のヒント

1. **テスト後リソース削除**
```bash
# S3バケットを空にして削除
aws s3 rm s3://face-auth-dev-bucket --recursive
aws s3 rb s3://face-auth-dev-bucket

# DynamoDBテーブル削除
aws dynamodb delete-table --table-name CardTemplates
aws dynamodb delete-table --table-name EmployeeFaces
aws dynamodb delete-table --table-name AuthSessions

# Rekognition Collection削除
aws rekognition delete-collection --collection-id face-auth-employees

# Cognito User Pool削除
aws cognito-idp delete-user-pool --user-pool-id ap-northeast-1_XXXXXXXXX
```

2. **開発時間制限**
   - 必要な時のみリソース作成
   - 使用後すぐに削除

3. **無料枠モニタリング**
   - AWS Billing Dashboardで使用量確認

---

## トラブルシューティング

### 1. 認証情報エラー
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**解決:**
```bash
aws configure
# または
$env:AWS_ACCESS_KEY_ID="YOUR_KEY"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET"
```

### 2. 権限エラー
```
botocore.exceptions.ClientError: An error occurred (AccessDenied)
```

**解決:**
- IAMユーザーに必要な権限を追加
- 上記のIAM権限ポリシーを参照

### 3. リージョンエラー
```
botocore.exceptions.ClientError: The specified bucket does not exist
```

**解決:**
```bash
$env:AWS_DEFAULT_REGION="ap-northeast-1"
```

### 4. Rekognition Collectionなし
```
InvalidParameterException: Collection face-auth-employees not found
```

**解決:**
```bash
aws rekognition create-collection --collection-id face-auth-employees
```

---

## 次のステップ

1. ✅ AWS認証情報設定
2. ✅ AWSリソース作成
3. ✅ 環境変数設定
4. ✅ 初期データ設定
5. ✅ ローカルテスト実行
6. 🔄 Lambdaハンドラーテスト
7. 🔄 フロントエンド開発
8. 🔄 AWSデプロイ

---

## 参考資料

- [AWS CLIインストールガイド](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [AWS認証情報構成](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [boto3認証情報](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)
- [AWS無料枠](https://aws.amazon.com/free/)

---

**作成日:** 2024
**バージョン:** 1.0
