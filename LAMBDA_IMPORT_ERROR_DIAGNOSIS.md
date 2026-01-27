# Lambda Import Error - 診断レポート

## 🔴 問題の概要

**エラーメッセージ:**
```
Unable to import module 'handler': No module named 'cognito_service'
```

**エラータイプ:** `Runtime.ImportModuleError`

**HTTPステータス:** 502 Bad Gateway

---

## 📊 ログ分析結果

### アクセス元IP

ログから確認されたアクセス元IP：
- **210.128.54.73** (許可されたIPレンジ `210.128.54.64/27` 内)
- **CloudFront-Viewer-Country:** JP (日本)
- **CloudFront-Viewer-ASN:** 2497

### IP制限の動作状況

✅ **IP制限は正常に機能しています**

- 許可されたIPレンジからのアクセスは正常にAPI Gatewayを通過
- Lambda関数まで到達している
- リソースポリシーによる403エラーは発生していない

### 実際のエラー

❌ **Lambda関数のモジュールインポートエラー**

```json
{
  "errorMessage": "Unable to import module 'handler': No module named 'cognito_service'",
  "errorType": "Runtime.ImportModuleError",
  "requestId": "",
  "stackTrace": []
}
```

---

## 🔍 根本原因

### 1. Lambda Layer の構造問題

**現在の構造（推測）:**
```
lambda/shared/
├── cognito_service.py
├── dynamodb_service.py
├── error_handler.py
├── face_recognition_service.py
├── models.py
├── ocr_service.py
├── timeout_manager.py
└── __init__.py
```

**Lambda Layerの要求構造:**
```
lambda/shared/
└── python/
    └── (モジュールファイル)
```

または

```
lambda/shared/
└── python/
    └── lib/
        └── python3.9/
            └── site-packages/
                └── (モジュールファイル)
```

### 2. インポートパスの問題

Lambda関数のハンドラーコードで以下のようにインポートしている可能性：

```python
from cognito_service import CognitoService  # ❌ 失敗
```

Lambda Layerを使用する場合、正しいインポート方法：

```python
from shared.cognito_service import CognitoService  # ✅ 正しい（Layerが正しく構造化されている場合）
```

---

## 🛠️ 解決方法

### 方法1: Lambda Layerの構造を修正（推奨）

#### 1.1 ディレクトリ構造を変更

```bash
# 新しい構造を作成
mkdir -p lambda/shared_layer/python
cp -r lambda/shared/* lambda/shared_layer/python/
```

#### 1.2 CDKコードを更新

```python
shared_layer = lambda_.LayerVersion(
    self, "SharedLayer",
    code=lambda_.Code.from_asset("lambda/shared_layer"),  # 変更
    compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
    description="Shared utilities and services for Face-Auth Lambda functions"
)
```

---

### 方法2: Lambda関数に直接バンドル（簡単）

Lambda Layerを使用せず、各Lambda関数のディレクトリに `shared` をコピーする。

#### 2.1 デプロイ前スクリプト作成

```bash
# deploy_prepare.sh
#!/bin/bash

# Copy shared modules to each Lambda function
for func in enrollment face_login emergency_auth re_enrollment status; do
    cp -r lambda/shared lambda/$func/
done
```

#### 2.2 CDKコードを更新

```python
# Lambda Layerを削除
# "layers": [shared_layer],  # この行を削除

# 各Lambda関数の定義から layers を削除
self.enrollment_lambda = lambda_.Function(
    self, "EnrollmentFunction",
    function_name="FaceAuth-Enrollment",
    description="Handle employee enrollment with ID card OCR and face registration",
    code=lambda_.Code.from_asset("lambda/enrollment"),
    handler="handler.handle_enrollment",
    runtime=lambda_.Runtime.PYTHON_3_9,
    timeout=Duration.seconds(15),
    memory_size=512,
    role=self.lambda_execution_role,
    # layers は削除
    environment={...}
)
```

---

### 方法3: requirements.txt を使用

各Lambda関数ディレクトリに `requirements.txt` を作成し、依存関係を管理する。

#### 3.1 requirements.txt 作成

```bash
# lambda/enrollment/requirements.txt
boto3>=1.26.0
botocore>=1.29.0
```

#### 3.2 CDKでDocker bundlingを使用

```python
from aws_cdk.aws_lambda_python_alpha import PythonFunction

self.enrollment_lambda = PythonFunction(
    self, "EnrollmentFunction",
    entry="lambda/enrollment",
    runtime=lambda_.Runtime.PYTHON_3_9,
    index="handler.py",
    handler="handle_enrollment",
    # 自動的に requirements.txt をインストール
)
```

---

## 🚀 推奨される即時対応

### ステップ1: Lambda関数のコードを確認

```bash
# Lambda関数のインポート文を確認
grep -r "from.*cognito_service" lambda/
grep -r "import.*cognito_service" lambda/
```

### ステップ2: 一時的な修正（方法2を使用）

```bash
# 各Lambda関数ディレクトリにsharedをコピー
cp -r lambda/shared lambda/enrollment/
cp -r lambda/shared lambda/face_login/
cp -r lambda/shared lambda/emergency_auth/
cp -r lambda/shared lambda/re_enrollment/
cp -r lambda/shared lambda/status/
```

### ステップ3: CDKコードを更新

```python
# infrastructure/face_auth_stack.py
# Lambda Layerの定義をコメントアウト
# shared_layer = lambda_.LayerVersion(...)

# lambda_configから layers を削除
lambda_config = {
    "runtime": lambda_.Runtime.PYTHON_3_9,
    "timeout": Duration.seconds(15),
    "memory_size": 512,
    "role": self.lambda_execution_role,
    "vpc": self.vpc,
    "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
    "security_groups": [self.lambda_security_group, self.ad_security_group],
    # "layers": [shared_layer],  # この行を削除
    "environment": {...}
}
```

### ステップ4: 再デプロイ

```bash
# 環境変数を設定してデプロイ
$env:ALLOWED_IPS="210.128.54.64/27"; npx cdk deploy --profile dev
```

---

## 📝 "Missing Authentication Token" について

### このエラーメッセージの原因

1. **存在しないパスへのアクセス**
   - `/prod/` (末尾のスラッシュのみ)
   - `/` (ルートパス)
   - `/auth` (末尾に `/status` がない)

2. **ブラウザキャッシュ**
   - 以前のエラーレスポンスがキャッシュされている

### 正しいパス

✅ **正しいパス:**
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/enrollment`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/face-login`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/emergency`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/re-enrollment`

❌ **間違ったパス:**
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/`

---

## 🔄 次のステップ

### 即座に実行

1. ✅ Lambda関数のインポート文を確認
2. ✅ `shared` ディレクトリを各Lambda関数にコピー
3. ✅ CDKコードからLambda Layerを削除
4. ✅ 再デプロイ

### 長期的な対応

1. ⏳ Lambda Layerの正しい構造を実装
2. ⏳ CI/CDパイプラインにデプロイ前スクリプトを追加
3. ⏳ 自動テストでインポートエラーを検出

---

## 📞 確認コマンド

### Lambda関数のログを確認

```bash
# 最新のエラーログを確認
aws logs tail /aws/lambda/FaceAuth-Status --since 10m --region ap-northeast-1 --profile dev

# 特定のエラーを検索
aws logs filter-log-events \
  --log-group-name /aws/lambda/FaceAuth-Status \
  --filter-pattern "ImportModuleError" \
  --region ap-northeast-1 \
  --profile dev
```

### Lambda関数の環境を確認

```bash
# Lambda関数の設定を確認
aws lambda get-function-configuration \
  --function-name FaceAuth-Status \
  --region ap-northeast-1 \
  --profile dev
```

### Lambda Layerの内容を確認

```bash
# Lambda Layerのバージョンを確認
aws lambda list-layer-versions \
  --layer-name SharedLayer \
  --region ap-northeast-1 \
  --profile dev
```

---

**作成日:** 2024年
**最終更新:** 2024年
**ステータス:** 🔴 対応必要

