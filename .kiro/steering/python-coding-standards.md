---
inclusion: fileMatch
fileMatchPattern: "**/*.py"
---

# Python Coding Standards - Face-Auth IdP System

このドキュメントは、Face-Auth IdP システムのPythonコーディング標準を定義します。
すべてのPythonコードはこれらの標準に従う必要があります。

## Python バージョン

**必須:** Python 3.9 以上

**理由:**
- Type hints の完全サポート
- AWS Lambda Python 3.9 ランタイム
- 最新の標準ライブラリ機能

---

## コーディングスタイル

### PEP 8 準拠

基本的に[PEP 8](https://pep8.org/)に従う。

**主要ルール:**
- インデント: 4スペース
- 行の最大長: 100文字（docstringは79文字）
- 空行: クラス間2行、メソッド間1行
- インポート: 標準ライブラリ → サードパーティ → ローカル

### インポート順序

```python
# 1. 標準ライブラリ
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

# 2. サードパーティライブラリ
import boto3
from botocore.exceptions import ClientError

# 3. ローカルモジュール
from .models import EmployeeInfo, FaceData
from .error_handler import ErrorHandler
```

---

## Type Hints

### 必須使用

すべての関数・メソッドにtype hintsを付ける。

**Good:**
```python
def verify_employee(
    self, 
    employee_id: str, 
    extracted_info: EmployeeInfo
) -> ADVerificationResult:
    """Verify employee information against Active Directory."""
    pass
```

**Bad:**
```python
def verify_employee(self, employee_id, extracted_info):
    """Verify employee information against Active Directory."""
    pass
```

### 複雑な型

```python
from typing import Dict, List, Optional, Tuple, Any, Union

# Dict型
def get_config() -> Dict[str, Any]:
    return {"key": "value"}

# Optional型
def find_employee(employee_id: str) -> Optional[EmployeeInfo]:
    return None

# Union型
def process_result(result: Union[str, int, None]) -> bool:
    return True

# Tuple型
def get_coordinates() -> Tuple[float, float]:
    return (0.0, 0.0)

# List型
def get_employees() -> List[EmployeeInfo]:
    return []
```

### dataclass使用

データクラスには`@dataclass`デコレータを使用。

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ADVerificationResult:
    """Result of Active Directory verification operation"""
    success: bool
    reason: Optional[str] = None
    employee_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    elapsed_time: float = 0.0
```

---

## Docstrings

### Google形式を使用

```python
def handle_enrollment(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle employee enrollment with ID card OCR and face registration.
    
    This function orchestrates the complete enrollment workflow:
    1. Extract employee info from ID card using OCR
    2. Verify employee against Active Directory
    3. Capture and validate face with liveness detection
    4. Register face in Rekognition collection
    5. Store employee record in DynamoDB
    
    Args:
        event: Lambda event containing id_card_image and face_image
        context: Lambda context object
        
    Returns:
        API Gateway response with enrollment result
        
    Raises:
        ValueError: If required fields are missing
        ClientError: If AWS service call fails
        
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """
    pass
```

### クラスDocstring

```python
class FaceRecognitionService:
    """
    Amazon Rekognition service for face detection and matching.
    
    This service provides:
    - Liveness detection with >90% confidence threshold
    - 1:N face search in Rekognition collection
    - Face indexing and deletion
    - Collection management
    
    Attributes:
        rekognition_client: boto3 Rekognition client
        collection_id: Rekognition collection identifier
        confidence_threshold: Minimum confidence for face matching (default: 90.0)
        
    Requirements: 2.1, 2.2, 6.1, 6.2, 6.4
    """
    
    def __init__(self, collection_id: str, confidence_threshold: float = 90.0):
        """
        Initialize Face Recognition Service.
        
        Args:
            collection_id: Rekognition collection ID
            confidence_threshold: Minimum confidence threshold (default: 90.0)
        """
        pass
```

---

## エラーハンドリング

### 具体的な例外をキャッチ

**Good:**
```python
try:
    response = s3_client.get_object(Bucket=bucket, Key=key)
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'NoSuchKey':
        logger.error(f"Object not found: {key}")
        raise FileNotFoundError(f"S3 object not found: {key}")
    else:
        logger.error(f"S3 error: {e}")
        raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

**Bad:**
```python
try:
    response = s3_client.get_object(Bucket=bucket, Key=key)
except:  # Bare except
    pass
```

### カスタム例外

```python
class FaceAuthException(Exception):
    """Base exception for Face-Auth system."""
    pass

class LivenessDetectionFailedException(FaceAuthException):
    """Raised when liveness detection fails."""
    pass

class FaceNotFoundError(FaceAuthException):
    """Raised when no face is found in 1:N search."""
    pass
```

### エラーログ

```python
import logging

logger = logging.getLogger(__name__)

try:
    result = risky_operation()
except Exception as e:
    logger.error(
        f"Operation failed: {str(e)}",
        exc_info=True,  # スタックトレース含む
        extra={
            "employee_id": employee_id,
            "operation": "enrollment"
        }
    )
    raise
```

---

## ログ出力

### ログレベル

```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: 詳細なデバッグ情報
logger.debug(f"Processing employee: {employee_id}")

# INFO: 一般的な情報
logger.info(f"Employee enrollment successful: {employee_id}")

# WARNING: 警告（処理は継続）
logger.warning(f"AD connection slow: {elapsed_time:.2f}s")

# ERROR: エラー（処理失敗）
logger.error(f"Face recognition failed: {error_message}")

# CRITICAL: 重大なエラー
logger.critical(f"System failure: {error_message}")
```

### 構造化ログ

```python
logger.info(
    "Enrollment completed",
    extra={
        "employee_id": employee_id,
        "face_id": face_id,
        "confidence": confidence,
        "elapsed_time": elapsed_time,
        "request_id": context.aws_request_id
    }
)
```

---

## 関数設計

### 単一責任の原則

各関数は1つの責任のみを持つ。

**Good:**
```python
def extract_employee_info(image_bytes: bytes) -> EmployeeInfo:
    """Extract employee info from ID card image."""
    pass

def verify_against_ad(employee_info: EmployeeInfo) -> bool:
    """Verify employee info against Active Directory."""
    pass

def register_face(face_image: bytes, employee_id: str) -> str:
    """Register face in Rekognition collection."""
    pass
```

**Bad:**
```python
def process_enrollment(id_card: bytes, face: bytes) -> Dict:
    """Do everything: OCR, AD verify, face register, DB save."""
    # Too many responsibilities
    pass
```

### 関数の長さ

- 1関数は50行以内を目標
- 100行を超える場合は分割を検討

### 引数の数

- 引数は5個以内を推奨
- 多い場合はdataclassやDictを使用

**Good:**
```python
@dataclass
class EnrollmentRequest:
    id_card_image: bytes
    face_image: bytes
    employee_id: str
    metadata: Dict[str, Any]

def handle_enrollment(request: EnrollmentRequest) -> EnrollmentResult:
    pass
```

---

## クラス設計

### クラス構造

```python
class ServiceName:
    """Class docstring."""
    
    # クラス変数
    DEFAULT_TIMEOUT = 10
    
    def __init__(self, param1: str, param2: int):
        """Initialize service."""
        # インスタンス変数
        self.param1 = param1
        self.param2 = param2
        self._private_var = None  # プライベート変数は_で始める
        
    # パブリックメソッド
    def public_method(self) -> str:
        """Public method."""
        return self._private_method()
    
    # プライベートメソッド
    def _private_method(self) -> str:
        """Private method."""
        return "result"
    
    # プロパティ
    @property
    def computed_value(self) -> int:
        """Computed property."""
        return self.param2 * 2
```

### 継承

```python
from abc import ABC, abstractmethod

class BaseService(ABC):
    """Abstract base service."""
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process data - must be implemented by subclasses."""
        pass

class ConcreteService(BaseService):
    """Concrete implementation."""
    
    def process(self, data: Any) -> Any:
        """Process data implementation."""
        return data
```

---

## AWS SDK使用

### boto3クライアント

```python
import boto3
from botocore.exceptions import ClientError

class S3Service:
    """S3 service wrapper."""
    
    def __init__(self, bucket_name: str):
        """Initialize S3 service."""
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name
    
    def upload_file(self, key: str, data: bytes) -> bool:
        """
        Upload file to S3.
        
        Args:
            key: S3 object key
            data: File data as bytes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ServerSideEncryption='AES256'
            )
            logger.info(f"File uploaded successfully: {key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            return False
```

### リソース vs クライアント

- **クライアント:** 低レベルAPI、すべての操作をサポート（推奨）
- **リソース:** 高レベルAPI、オブジェクト指向

```python
# クライアント（推奨）
s3_client = boto3.client('s3')
response = s3_client.get_object(Bucket='bucket', Key='key')

# リソース
s3_resource = boto3.resource('s3')
obj = s3_resource.Object('bucket', 'key')
```

---

## テストコード

### テスト構造

```python
import pytest
from unittest.mock import Mock, patch, MagicMock

class TestFaceRecognitionService:
    """Test suite for FaceRecognitionService."""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return FaceRecognitionService(
            collection_id="test-collection",
            confidence_threshold=90.0
        )
    
    def test_detect_liveness_success(self, service):
        """Test successful liveness detection."""
        # Arrange
        mock_response = {
            'FaceDetails': [{
                'Confidence': 95.5
            }]
        }
        
        with patch.object(service.rekognition_client, 'detect_faces', return_value=mock_response):
            # Act
            result = service.detect_liveness(b'fake_image_data')
            
            # Assert
            assert result.success is True
            assert result.confidence > 90.0
    
    def test_detect_liveness_low_confidence(self, service):
        """Test liveness detection with low confidence."""
        # Arrange
        mock_response = {
            'FaceDetails': [{
                'Confidence': 85.0
            }]
        }
        
        with patch.object(service.rekognition_client, 'detect_faces', return_value=mock_response):
            # Act
            result = service.detect_liveness(b'fake_image_data')
            
            # Assert
            assert result.success is False
            assert result.reason == ErrorCodes.LIVENESS_FAILED
```

### モック使用

```python
from unittest.mock import Mock, patch, MagicMock

# 関数のモック
with patch('module.function_name') as mock_func:
    mock_func.return_value = "mocked_value"
    result = function_under_test()

# クラスメソッドのモック
with patch.object(MyClass, 'method_name') as mock_method:
    mock_method.return_value = "mocked_value"
    result = instance.method_name()

# boto3クライアントのモック
@patch('boto3.client')
def test_s3_operation(mock_boto_client):
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3
    mock_s3.get_object.return_value = {'Body': b'data'}
    
    # Test code here
```

---

## パフォーマンス

### リスト内包表記

**Good:**
```python
# リスト内包表記
employee_ids = [emp.employee_id for emp in employees if emp.is_active]

# ジェネレータ式（大量データ）
employee_ids = (emp.employee_id for emp in employees if emp.is_active)
```

**Bad:**
```python
# 非効率なループ
employee_ids = []
for emp in employees:
    if emp.is_active:
        employee_ids.append(emp.employee_id)
```

### 早期リターン

**Good:**
```python
def process_employee(employee: Optional[EmployeeInfo]) -> bool:
    if employee is None:
        return False
    
    if not employee.is_active:
        return False
    
    # メイン処理
    return True
```

**Bad:**
```python
def process_employee(employee: Optional[EmployeeInfo]) -> bool:
    if employee is not None:
        if employee.is_active:
            # メイン処理
            return True
    return False
```

---

## セキュリティ

### 機密情報の扱い

**Good:**
```python
import os

# 環境変数から取得
api_key = os.environ.get('API_KEY')
db_password = os.environ.get('DB_PASSWORD')
```

**Bad:**
```python
# ハードコード（絶対NG）
api_key = "sk-1234567890abcdef"
db_password = "MyPassword123"
```

### SQL インジェクション対策

DynamoDBではパラメータ化されたクエリを使用。

```python
# Good: パラメータ化
response = table.query(
    KeyConditionExpression=Key('employee_id').eq(employee_id)
)

# Bad: 文字列結合（使用しない）
# query = f"SELECT * FROM table WHERE id = '{employee_id}'"
```

---

## コード例

### 完全な例

```python
"""
Face-Auth IdP System - Face Recognition Service

This module provides Amazon Rekognition integration for face detection and matching.
"""

import logging
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class LivenessResult:
    """Result of liveness detection operation."""
    success: bool
    confidence: float
    reason: Optional[str] = None


class FaceRecognitionService:
    """
    Amazon Rekognition service for face detection and matching.
    
    This service provides:
    - Liveness detection with >90% confidence threshold
    - 1:N face search in Rekognition collection
    - Face indexing and deletion
    
    Attributes:
        rekognition_client: boto3 Rekognition client
        collection_id: Rekognition collection identifier
        confidence_threshold: Minimum confidence for face matching
        
    Requirements: 2.1, 2.2, 6.1, 6.2, 6.4
    """
    
    DEFAULT_CONFIDENCE_THRESHOLD = 90.0
    
    def __init__(
        self, 
        collection_id: str, 
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    ):
        """
        Initialize Face Recognition Service.
        
        Args:
            collection_id: Rekognition collection ID
            confidence_threshold: Minimum confidence threshold (default: 90.0)
        """
        self.rekognition_client = boto3.client('rekognition')
        self.collection_id = collection_id
        self.confidence_threshold = confidence_threshold
        
        logger.info(
            f"FaceRecognitionService initialized: "
            f"collection={collection_id}, threshold={confidence_threshold}"
        )
    
    def detect_liveness(self, image_bytes: bytes) -> LivenessResult:
        """
        Detect face liveness with confidence threshold.
        
        Args:
            image_bytes: Face image as bytes
            
        Returns:
            LivenessResult with success status and confidence
            
        Raises:
            ClientError: If Rekognition API call fails
            
        Requirements: 2.1, 6.1, 6.2
        """
        try:
            response = self.rekognition_client.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )
            
            if not response.get('FaceDetails'):
                logger.warning("No face detected in image")
                return LivenessResult(
                    success=False,
                    confidence=0.0,
                    reason="NO_FACE_DETECTED"
                )
            
            face_detail = response['FaceDetails'][0]
            confidence = face_detail.get('Confidence', 0.0)
            
            if confidence < self.confidence_threshold:
                logger.warning(
                    f"Liveness confidence too low: {confidence:.2f}% "
                    f"(threshold: {self.confidence_threshold}%)"
                )
                return LivenessResult(
                    success=False,
                    confidence=confidence,
                    reason="LOW_CONFIDENCE"
                )
            
            logger.info(f"Liveness detection successful: {confidence:.2f}%")
            return LivenessResult(success=True, confidence=confidence)
            
        except ClientError as e:
            logger.error(f"Rekognition API error: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error in liveness detection: {e}", exc_info=True)
            raise
```

---

## 参考資料

- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [PEP 484 - Type Hints](https://www.python.org/dev/peps/pep-0484/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [pytest Documentation](https://docs.pytest.org/)

---

**最終更新:** 2024
**バージョン:** 1.0
