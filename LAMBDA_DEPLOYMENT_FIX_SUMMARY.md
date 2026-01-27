# Lambda Deployment Fix Summary

## 問題の経緯

### 問題1: ad_connector_mock.py が見つからない
**エラー:** `No module named 'shared.ad_connector_mock'`

**原因:** CDKは各Lambda関数ディレクトリを個別にバンドルするため、`lambda/shared/ad_connector_mock.py`が各関数の`shared/`ディレクトリにコピーされていなかった。

**解決策:** `ad_connector_mock.py`を各Lambda関数の`shared/`ディレクトリにコピー
```bash
copy lambda\shared\ad_connector_mock.py lambda\enrollment\shared\
copy lambda\shared\ad_connector_mock.py lambda\face_login\shared\
copy lambda\shared\ad_connector_mock.py lambda\emergency_auth\shared\
copy lambda\shared\ad_connector_mock.py lambda\re_enrollment\shared\
copy lambda\shared\ad_connector_mock.py lambda\status\shared\
```

**ステータス:** ✅ 解決済み

---

### 問題2: Pillow (PIL) が見つからない
**エラー:** `No module named 'PIL'`

**原因:** Lambda関数でPillowライブラリが利用できない。ThumbnailProcessorが画像処理にPillowを使用しているが、Lambda環境にインストールされていない。

**影響:**
- S3に画像が保存されない
- サムネイル生成ができない
- 画像処理が失敗する

**試行した解決策:**

#### 試行1: CDK Bundling with Docker ❌
```python
bundling=BundlingOptions(
    image=lambda_.Runtime.PYTHON_3_9.bundling_image,
    command=["bash", "-c", "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output"]
)
```
**結果:** Dockerが利用できないためエラー

#### 試行2: Lambda Layer作成 ❌
```bash
mkdir -p lambda-layer/python
pip install Pillow==10.1.0 -t lambda-layer/python
```
**結果:** Python 3.14環境でPillow 10.1.0のビルドに失敗

---

## 解決策: AWS公開のPillow Lambda Layer使用

### オプション1: Klayers (推奨)

[Klayers](https://github.com/keithrozario/Klayers)は、AWS Lambda用のプリビルド済みPythonパッケージLayerを提供しています。

**Pillow Layer ARN (Python 3.9, ap-northeast-1):**
```
arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p39-pillow:1
```

**CDKでの実装:**
```python
from aws_cdk import aws_lambda as lambda_

# Pillow Lambda Layer
pillow_layer = lambda_.LayerVersion.from_layer_version_arn(
    self, "PillowLayer",
    layer_version_arn="arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p39-pillow:1"
)

# Lambda関数にLayerを追加
enrollment_function = lambda_.Function(
    self, "EnrollmentFunction",
    layers=[pillow_layer],
    # ... other properties
)
```

### オプション2: 自前でLambda Layer作成

Python 3.9環境でPillowをビルドしてLayerを作成する方法。

**手順:**
```bash
# 1. Python 3.9環境を用意（Docker使用）
docker run -v "$PWD":/var/task "public.ecr.aws/sam/build-python3.9" /bin/sh -c "pip install Pillow==10.1.0 -t python/lib/python3.9/site-packages/; exit"

# 2. Layerをzipに圧縮
cd python
zip -r ../pillow-layer.zip .
cd ..

# 3. Layerを公開
aws lambda publish-layer-version \
    --layer-name pillow-python39 \
    --description "Pillow 10.1.0 for Python 3.9" \
    --zip-file fileb://pillow-layer.zip \
    --compatible-runtimes python3.9 \
    --profile dev

# 4. Layer ARNを取得
# 出力: arn:aws:lambda:ap-northeast-1:979431736455:layer:pillow-python39:1
```

### オプション3: Pillowを使わない実装に変更

ThumbnailProcessorを修正して、Pillowを使わずにboto3のみで実装する。

**メリット:**
- 外部依存なし
- デプロイが簡単

**デメリット:**
- サムネイル生成機能が制限される
- 画像リサイズができない

---

## 推奨される実装手順

### ステップ1: Klayers Pillow Layerを使用

```python
# infrastructure/face_auth_stack.py

from aws_cdk import (
    aws_lambda as lambda_,
    # ... other imports
)

class FaceAuthIdPStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Pillow Lambda Layer (Klayers)
        pillow_layer = lambda_.LayerVersion.from_layer_version_arn(
            self, "PillowLayer",
            layer_version_arn="arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-p39-pillow:1"
        )
        
        # Enrollment Lambda
        self.enrollment_function = lambda_.Function(
            self, "EnrollmentFunction",
            function_name="FaceAuth-Enrollment",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="handler.handle_enrollment",
            code=lambda_.Code.from_asset("lambda/enrollment"),
            layers=[pillow_layer],  # Pillow Layerを追加
            # ... other properties
        )
        
        # Face Login Lambda
        self.face_login_function = lambda_.Function(
            self, "FaceLoginFunction",
            function_name="FaceAuth-FaceLogin",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="handler.handle_face_login",
            code=lambda_.Code.from_asset("lambda/face_login"),
            layers=[pillow_layer],  # Pillow Layerを追加
            # ... other properties
        )
        
        # Re-enrollment Lambda
        self.re_enrollment_function = lambda_.Function(
            self, "ReEnrollmentFunction",
            function_name="FaceAuth-ReEnrollment",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="handler.handle_re_enrollment",
            code=lambda_.Code.from_asset("lambda/re_enrollment"),
            layers=[pillow_layer],  # Pillow Layerを追加
            # ... other properties
        )
```

### ステップ2: デプロイ

```bash
# CDK差分確認
npx cdk diff --profile dev

# デプロイ
npx cdk deploy --profile dev --require-approval never
```

### ステップ3: 動作確認

```bash
# テストリクエスト送信
python test_enrollment_api.py

# Lambda ログ確認
aws logs tail /aws/lambda/FaceAuth-Enrollment --since 1m --profile dev
```

**期待される結果:**
- ✅ `No module named 'PIL'` エラーが解消
- ✅ ThumbnailProcessorが正常に動作
- ✅ S3に画像が保存される

---

## 代替案: Pillowなしの実装

もしLayerの使用が難しい場合、ThumbnailProcessorを修正してPillowを使わない実装に変更できます。

```python
# lambda/shared/thumbnail_processor.py

import base64
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class ThumbnailProcessor:
    """
    Process images without Pillow dependency.
    Simply validates and passes through the original image.
    """
    
    def __init__(self, max_size_kb: int = 500):
        self.max_size_kb = max_size_kb
        logger.info(f"ThumbnailProcessor initialized (no Pillow, max_size={max_size_kb}KB)")
    
    def process_image(
        self, 
        image_data: bytes, 
        employee_id: str
    ) -> Tuple[bytes, bytes]:
        """
        Process image without resizing (Pillow not available).
        
        Args:
            image_data: Original image bytes
            employee_id: Employee ID for validation
            
        Returns:
            Tuple of (original_image, original_image)
        """
        # Validate employee ID format (7 digits)
        if not employee_id or len(employee_id) != 7 or not employee_id.isdigit():
            raise ValueError(f"Invalid employee ID format: {employee_id}")
        
        # Check image size
        size_kb = len(image_data) / 1024
        if size_kb > self.max_size_kb:
            logger.warning(
                f"Image size ({size_kb:.2f}KB) exceeds limit ({self.max_size_kb}KB), "
                f"but cannot resize without Pillow"
            )
        
        logger.info(f"Image processed (no resize): {size_kb:.2f}KB")
        
        # Return original image for both full and thumbnail
        return image_data, image_data
```

**注意:** この実装ではサムネイル生成ができないため、ストレージコストが増加する可能性があります。

---

## 次のステップ

1. ✅ `ad_connector_mock.py`を各Lambda関数にコピー（完了）
2. ⏳ Pillow Lambda Layerを追加（次のタスク）
3. ⏳ CDK再デプロイ
4. ⏳ 動作確認（S3に画像が保存されることを確認）

---

**作成日:** 2026年1月28日  
**ステータス:** 🔄 進行中（Pillow Layer追加待ち）
