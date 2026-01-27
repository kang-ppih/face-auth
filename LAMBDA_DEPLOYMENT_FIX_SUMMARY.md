# Lambda デプロイ修正サマリー

## 実施した対策

### ✅ 完了した作業

1. **shared モジュールのコピー**
   - `lambda/shared` を各Lambda関数ディレクトリにコピー
   - `lambda/enrollment/shared/`
   - `lambda/face_login/shared/`
   - `lambda/emergency_auth/shared/`
   - `lambda/re_enrollment/shared/`
   - `lambda/status/shared/`

2. **CDKコードの修正**
   - Lambda Layerの定義を削除
   - `lambda_config` から `layers` パラメータを削除

3. **インポート文の修正**
   - すべてのLambda関数ハンドラーで `from shared.xxx import` に変更
   - `sys.path.insert` の削除

4. **デプロイ実行**
   - 2回のデプロイを実行
   - すべてのLambda関数のコードが更新された

---

## 🔴 残っている問題

### 問題: 外部ライブラリの欠如

**エラーメッセージ:**
```
Runtime.ImportModuleError: Unable to import module 'handler': No module named 'jwt'
```

**原因:**
- `cognito_service.py` が `PyJWT` ライブラリを使用
- Lambda関数に外部ライブラリがバンドルされていない

**影響を受けるモジュール:**
- `cognito_service.py` - `jwt`, `PyJWKClient`
- その他の外部ライブラリ（`Pillow`, `ldap3` など）も同様の問題がある可能性

---

## 🛠️ 解決方法

### 方法1: requirements.txt + Docker bundling（推奨）

各Lambda関数ディレクトリに `requirements.txt` を作成し、CDKでDocker bundlingを使用する。

#### ステップ1: requirements.txt 作成

```bash
# lambda/status/requirements.txt
boto3>=1.26.0
botocore>=1.29.0
PyJWT>=2.8.0
cryptography>=41.0.0
```

#### ステップ2: CDKコードを更新

```python
from aws_cdk.aws_lambda_python_alpha import PythonFunction

self.status_lambda = PythonFunction(
    self, "StatusFunction",
    entry="lambda/status",
    runtime=lambda_.Runtime.PYTHON_3_9,
    index="handler.py",
    handler="handle_status",
    timeout=Duration.seconds(15),
    memory_size=512,
    # 自動的に requirements.txt をインストール
)
```

**注意:** `aws-cdk.aws-lambda-python-alpha` モジュールが必要

---

### 方法2: Lambda Layer with dependencies（代替案）

外部ライブラリを含むLambda Layerを作成する。

#### ステップ1: Lambda Layer用ディレクトリ作成

```bash
mkdir -p lambda_layer/python
cd lambda_layer
```

#### ステップ2: requirements.txt 作成

```bash
# lambda_layer/requirements.txt
PyJWT>=2.8.0
cryptography>=41.0.0
Pillow>=10.0.0
```

#### ステップ3: ライブラリをインストール

```bash
pip install -r requirements.txt -t python/
```

#### ステップ4: CDKでLambda Layer作成

```python
dependencies_layer = lambda_.LayerVersion(
    self, "DependenciesLayer",
    code=lambda_.Code.from_asset("lambda_layer"),
    compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
    description="External dependencies for Face-Auth Lambda functions"
)

# Lambda関数に追加
lambda_config = {
    ...
    "layers": [dependencies_layer],
    ...
}
```

---

### 方法3: 外部ライブラリを手動でバンドル（簡易）

各Lambda関数ディレクトリに外部ライブラリを直接インストールする。

```bash
# 各Lambda関数ディレクトリで実行
cd lambda/status
pip install PyJWT cryptography -t .
cd ../..

cd lambda/enrollment
pip install PyJWT cryptography Pillow -t .
cd ../..

# 他のLambda関数も同様
```

**デメリット:**
- デプロイパッケージが大きくなる
- 管理が煩雑

---

## 📋 必要な外部ライブラリ一覧

### すべてのLambda関数

```
boto3>=1.26.0
botocore>=1.29.0
```

### Cognito使用（status, face_login, emergency_auth）

```
PyJWT>=2.8.0
cryptography>=41.0.0
```

### 画像処理使用（enrollment, face_login, re_enrollment）

```
Pillow>=10.0.0
```

### AD接続使用（enrollment, emergency_auth, re_enrollment）

```
ldap3>=2.9.0
```

---

## 🚀 推奨される即時対応

### 最も簡単な方法: 方法3（手動バンドル）

```powershell
# PowerShellで実行

# 1. 仮想環境を作成（まだの場合）
python -m venv venv
venv\Scripts\activate

# 2. 各Lambda関数に必要なライブラリをインストール

# Status Lambda
cd lambda\status
pip install PyJWT cryptography -t .
cd ..\..

# Face Login Lambda
cd lambda\face_login
pip install PyJWT cryptography Pillow -t .
cd ..\..

# Enrollment Lambda
cd lambda\enrollment
pip install PyJWT cryptography Pillow ldap3 -t .
cd ..\..

# Emergency Auth Lambda
cd lambda\emergency_auth
pip install PyJWT cryptography ldap3 -t .
cd ..\..

# Re-enrollment Lambda
cd lambda\re_enrollment
pip install PyJWT cryptography Pillow ldap3 -t .
cd ..\..

# 3. 再デプロイ
$env:ALLOWED_IPS="210.128.54.64/27"; npx cdk deploy --profile dev
```

---

## ⚠️ 注意事項

### .gitignore の更新

外部ライブラリをLambda関数ディレクトリにインストールする場合、`.gitignore` を更新してライブラリファイルを除外する必要があります。

```gitignore
# Lambda function dependencies
lambda/*/jwt/
lambda/*/cryptography/
lambda/*/PIL/
lambda/*/ldap3/
lambda/*/*.dist-info/
lambda/*/*.egg-info/
```

ただし、デプロイには必要なので、完全に除外しないように注意してください。

---

## 📊 現在の状況

### デプロイ状況

- ✅ インフラストラクチャ: デプロイ済み
- ✅ Lambda関数コード: デプロイ済み
- ✅ shared モジュール: バンドル済み
- ❌ 外部ライブラリ: 未バンドル

### API動作状況

- ❌ `/auth/status`: 502 Bad Gateway (ImportModuleError: jwt)
- ❓ `/auth/enrollment`: 未テスト
- ❓ `/auth/face-login`: 未テスト
- ❓ `/auth/emergency`: 未テスト
- ❓ `/auth/re-enrollment`: 未テスト

---

## 🎯 次のステップ

### 即座に実行

1. ✅ 各Lambda関数に外部ライブラリをインストール（方法3）
2. ✅ 再デプロイ
3. ✅ API動作確認

### 長期的な対応

1. ⏳ Lambda Layerを正しく実装（方法2）
2. ⏳ CI/CDパイプラインに組み込む
3. ⏳ requirements.txt を使用した自動管理（方法1）

---

**作成日:** 2024年
**最終更新:** 2024年
**ステータス:** 🔴 対応必要 - 外部ライブラリのバンドルが必要

