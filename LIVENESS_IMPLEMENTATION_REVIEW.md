# Liveness実装レビュー

## 実行日時
2026-02-10 22:40 JST

## レビュー概要
Liveness検証機能の実装を詳細にレビューし、潜在的な問題点と改善提案をまとめました。

---

## 🔴 重大な問題

### 1. Lambda関数のハンドラー名の不一致
**ファイル:** `lambda/liveness/create_session_handler.py`, `get_result_handler.py`

**問題:**
```python
# ハンドラー関数名が "handler" だが、
# インフラコードでは "create_session_handler.handler" を指定
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
```

**現状:** 動作している（ファイル名.関数名の形式で正しい）

**推奨:** 問題なし

---

### 2. sys.path.insert()の使用
**ファイル:** `lambda/liveness/create_session_handler.py`, `get_result_handler.py`

**問題:**
```python
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
```

この行は`lambda/shared`を参照していますが、実際には`lambda/liveness`ディレクトリに直接コピーしたモジュールを使用しています。

**影響:**
- 現在は動作している（同じディレクトリのモジュールが優先される）
- 将来的に混乱を招く可能性がある

**推奨対応:**
```python
# sys.path.insert()の行を削除
# 同じディレクトリのモジュールを直接インポート
from liveness_service import LivenessService, LivenessServiceError
from error_handler import ErrorHandler
from models import ErrorResponse
from timeout_manager import TimeoutManager
```

---

## ⚠️ 警告レベルの問題

### 3. TimeoutManagerが使用されていない
**ファイル:** `lambda/liveness/create_session_handler.py`, `get_result_handler.py`

**問題:**
```python
timeout_manager = TimeoutManager(context)
# この後、timeout_managerが使用されていない
```

**影響:**
- タイムアウト管理が機能していない
- Lambda関数が15秒でタイムアウトする可能性がある

**推奨対応:**
```python
# TimeoutManagerを使用してタイムアウトをチェック
timeout_manager = TimeoutManager(context)

# 処理前にタイムアウトをチェック
if timeout_manager.is_timeout_approaching():
    logger.warning("Timeout approaching, aborting operation")
    return ErrorResponse.request_timeout("Operation timeout")

# または、TimeoutManagerを削除
# timeout_manager = TimeoutManager(context)  # 削除
```

---

### 4. CORS設定が全開放
**ファイル:** `lambda/liveness/create_session_handler.py`, `get_result_handler.py`

**問題:**
```python
'Access-Control-Allow-Origin': '*',  # すべてのオリジンを許可
```

**影響:**
- セキュリティリスク
- 任意のWebサイトからAPIを呼び出せる

**推奨対応:**
```python
# 環境変数から許可するオリジンを取得
allowed_origins = os.environ.get('ALLOWED_ORIGINS', '*')

'Access-Control-Allow-Origin': allowed_origins,
```

**インフラコード修正:**
```python
environment={
    "LIVENESS_SESSIONS_TABLE": self.liveness_sessions_table.table_name,
    "FACE_AUTH_BUCKET": self.face_auth_bucket.bucket_name,
    "LIVENESS_CONFIDENCE_THRESHOLD": "90.0",
    "ALLOWED_ORIGINS": "https://d2576ywp5ut1v8.cloudfront.net"  # 追加
}
```

---

### 5. employee_idのバリデーションが厳しすぎる
**ファイル:** `lambda/liveness/create_session_handler.py`

**問題:**
```python
# 英数字のみ、50文字以内
if not employee_id.isalnum() or len(employee_id) > 50:
```

**影響:**
- ハイフン、アンダースコアを含む社員IDが使用できない
- 例: "EMP-001", "EMP_001" が拒否される

**推奨対応:**
```python
import re

# 英数字、ハイフン、アンダースコアを許可
if not re.match(r'^[a-zA-Z0-9_-]{1,50}$', employee_id):
    logger.warning(f"Invalid employee_id format: {employee_id}")
    return ErrorResponse.bad_request(
        "employee_id must be alphanumeric (with - or _) and max 50 characters"
    )
```

---

### 6. DynamoDBのTTL設定がない
**ファイル:** `lambda/liveness/liveness_service.py`

**問題:**
```python
self.dynamodb.put_item(
    TableName=self.liveness_sessions_table,
    Item={
        'session_id': {'S': session_id},
        'employee_id': {'S': employee_id},
        'status': {'S': 'PENDING'},
        'created_at': {'S': datetime.now(timezone.utc).isoformat()},
        'expires_at': {'N': str(expires_at_unix)}
    }
)
```

**影響:**
- 期限切れセッションがDynamoDBに残り続ける
- ストレージコストが増加

**推奨対応:**
```python
self.dynamodb.put_item(
    TableName=self.liveness_sessions_table,
    Item={
        'session_id': {'S': session_id},
        'employee_id': {'S': employee_id},
        'status': {'S': 'PENDING'},
        'created_at': {'S': datetime.now(timezone.utc).isoformat()},
        'expires_at': {'N': str(expires_at_unix)},
        'ttl': {'N': str(expires_at_unix + 86400)}  # 24時間後に自動削除
    }
)
```

**インフラコード修正:**
DynamoDBテーブルにTTL属性を設定する必要があります。

---

### 7. CloudWatchメトリクスの権限エラー
**ログ出力:**
```
Failed to send metric SessionCreationTime: An error occurred (AccessDenied) 
when calling the PutMetricData operation
```

**問題:**
Lambda実行ロールに`cloudwatch:PutMetricData`権限がない

**影響:**
- メトリクスが送信されない
- モニタリングができない

**推奨対応:**
インフラコードでIAMポリシーを追加：
```python
lambda_role.add_to_policy(iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=["cloudwatch:PutMetricData"],
    resources=["*"]
))
```

---

## 💡 改善提案

### 8. エラーハンドリングの改善
**ファイル:** `lambda/liveness/liveness_service.py`

**現状:**
```python
except Exception as e:
    logger.error(f"Failed to create liveness session: {str(e)}")
    raise LivenessServiceError(f"Failed to create liveness session: {str(e)}")
```

**推奨:**
```python
except ClientError as e:
    error_code = e.response['Error']['Code']
    error_message = e.response['Error']['Message']
    logger.error(
        f"AWS API error: {error_code} - {error_message}",
        extra={'error_code': error_code}
    )
    raise LivenessServiceError(f"AWS API error: {error_code}")
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}", exc_info=True)
    raise LivenessServiceError(f"Unexpected error: {str(e)}")
```

---

### 9. セッションIDの検証
**ファイル:** `lambda/liveness/get_result_handler.py`

**現状:**
```python
session_id = path_parameters.get('sessionId')

if not session_id:
    return ErrorResponse.bad_request("sessionId is required")
```

**推奨:**
```python
import re

session_id = path_parameters.get('sessionId')

if not session_id:
    return ErrorResponse.bad_request("sessionId is required")

# UUIDフォーマットを検証
if not re.match(r'^[a-f0-9-]{36}$', session_id):
    logger.warning(f"Invalid sessionId format: {session_id}")
    return ErrorResponse.bad_request("Invalid sessionId format")
```

---

### 10. リトライロジックの追加
**ファイル:** `lambda/liveness/liveness_service.py`

**現状:**
Rekognition APIの一時的なエラーでリトライしない

**推奨:**
```python
from botocore.config import Config
from botocore.exceptions import ClientError

# Rekognitionクライアントにリトライ設定を追加
config = Config(
    retries={
        'max_attempts': 3,
        'mode': 'adaptive'
    }
)

self.rekognition = rekognition_client or boto3.client('rekognition', config=config)
```

---

### 11. ログ出力の構造化
**ファイル:** すべてのLambda関数

**現状:**
```python
logger.info(
    "CreateLivenessSession invoked",
    extra={
        'request_id': context.aws_request_id,
        'function_name': context.function_name
    }
)
```

**推奨:**
すべてのログに共通フィールドを追加：
```python
import json

def structured_log(level, message, **kwargs):
    """構造化ログ出力"""
    log_data = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'level': level,
        'message': message,
        **kwargs
    }
    getattr(logger, level.lower())(json.dumps(log_data))

structured_log(
    'INFO',
    'CreateLivenessSession invoked',
    request_id=context.aws_request_id,
    function_name=context.function_name
)
```

---

### 12. S3バケット名の検証
**ファイル:** `lambda/liveness/liveness_service.py`

**現状:**
```python
self.face_auth_bucket = face_auth_bucket or os.environ.get('FACE_AUTH_BUCKET')
```

**問題:**
環境変数が設定されていない場合、`None`になる

**推奨:**
```python
self.face_auth_bucket = face_auth_bucket or os.environ.get('FACE_AUTH_BUCKET')

if not self.face_auth_bucket:
    raise ValueError("FACE_AUTH_BUCKET environment variable is required")
```

---

### 13. セッション結果のキャッシング
**ファイル:** `lambda/liveness/liveness_service.py`

**現状:**
同じセッションIDで複数回呼び出された場合、毎回Rekognition APIを呼び出す

**推奨:**
DynamoDBに結果をキャッシュして、2回目以降はキャッシュから返す：
```python
def get_session_result(self, session_id: str) -> LivenessSessionResult:
    # Check cache in DynamoDB first
    db_response = self.dynamodb.get_item(
        TableName=self.liveness_sessions_table,
        Key={'session_id': {'S': session_id}}
    )
    
    if 'Item' in db_response:
        item = db_response['Item']
        
        # If result is already cached, return it
        if item.get('status', {}).get('S') in ['SUCCESS', 'FAILED']:
            logger.info(f"Returning cached result for session: {session_id}")
            return LivenessSessionResult(
                session_id=session_id,
                is_live=item.get('status', {}).get('S') == 'SUCCESS',
                confidence=float(item.get('confidence', {}).get('N', 0)),
                # ... other fields
            )
    
    # Otherwise, fetch from Rekognition
    # ...
```

---

## 📊 パフォーマンス最適化

### 14. Lambda関数のメモリサイズ
**現状:** 256 MB

**推奨:**
- CreateLivenessSession: 256 MB（適切）
- GetLivenessResult: 512 MB（画像処理があるため）

### 15. Lambda関数のタイムアウト
**現状:**
- CreateLivenessSession: 10秒
- GetLivenessResult: 15秒

**推奨:**
- CreateLivenessSession: 15秒（Rekognition APIの応答時間を考慮）
- GetLivenessResult: 20秒（画像取得と処理を考慮）

---

## 🔒 セキュリティ強化

### 16. 入力サニタイゼーション
すべてのユーザー入力をサニタイズ：
```python
import html

def sanitize_input(value: str) -> str:
    """入力値をサニタイズ"""
    return html.escape(value.strip())

employee_id = sanitize_input(body.get('employee_id', ''))
```

### 17. レート制限
同じemployee_idからの連続リクエストを制限：
```python
# DynamoDBで最後のリクエスト時刻をチェック
# 1分以内に複数回リクエストされた場合は拒否
```

### 18. 監査ログの暗号化
S3に保存する監査ログをKMSで暗号化：
```python
self.s3.put_object(
    Bucket=self.face_auth_bucket,
    Key=s3_key,
    Body=json.dumps(audit_log, indent=2),
    ContentType='application/json',
    ServerSideEncryption='aws:kms',  # KMS暗号化
    SSEKMSKeyId='arn:aws:kms:...'    # KMSキーARN
)
```

---

## 優先度別対応リスト

### 🔴 高優先度（すぐに対応）
1. ✅ sys.path.insert()の削除（混乱を防ぐ）
2. ⚠️ CORS設定の制限（セキュリティ）
3. ⚠️ CloudWatchメトリクス権限の追加（モニタリング）
4. ⚠️ S3バケット名の検証（エラー防止）

### 🟡 中優先度（近日中に対応）
5. employee_idバリデーションの改善（ユーザビリティ）
6. DynamoDB TTL設定（コスト削減）
7. セッションIDの検証（セキュリティ）
8. エラーハンドリングの改善（デバッグ性）

### 🟢 低優先度（余裕があれば対応）
9. TimeoutManagerの使用または削除（コード整理）
10. リトライロジックの追加（信頼性）
11. ログ出力の構造化（運用性）
12. セッション結果のキャッシング（パフォーマンス）
13. Lambda関数のメモリ/タイムアウト調整（最適化）

---

## 総合評価

### ✅ 良い点
- Lambda関数は正常に動作している
- エラーハンドリングの基本構造は適切
- ログ出力が充実している
- Rekognition Liveness APIの統合が正しい
- DynamoDBでセッション管理ができている

### ⚠️ 改善が必要な点
- CORS設定が全開放（セキュリティリスク）
- CloudWatchメトリクスの権限がない
- DynamoDB TTL設定がない（コスト増加）
- employee_idバリデーションが厳しすぎる

### 🎯 推奨される次のアクション
1. CORS設定を環境変数で制御
2. CloudWatchメトリクス権限を追加
3. DynamoDB TTL設定を追加
4. employee_idバリデーションを緩和

---

**作成者:** Kiro AI Assistant
**最終更新:** 2026-02-10 22:40 JST
