# Liveness Service - 技術ドキュメント

**作成日:** 2026-02-04  
**バージョン:** 1.0  
**ステータス:** 完成

---

## 概要

Liveness Serviceは、AWS Rekognition Face Liveness APIを統合し、写真や動画を使ったなりすまし攻撃を防ぐ高度な生体検証機能を提供します。

### 主な機能

- **Livenessセッション作成**: Rekognition APIを使用してセッションを作成
- **セッション結果取得**: 検証結果を取得し、信頼度スコアを評価
- **監査ログ保存**: S3に監査ログを保存（90日間保持）
- **CloudWatchメトリクス**: 成功率、信頼度、処理時間などを監視
- **信頼度閾値検証**: 90%以上の信頼度を要求

---

## アーキテクチャ

### システム構成図

```
┌─────────────┐
│  Frontend   │
│  (React)    │
└──────┬──────┘
       │
       │ 1. POST /liveness/session/create
       ▼
┌─────────────────────────────────────┐
│  API Gateway                        │
└──────┬──────────────────────────────┘
       │
       │ 2. Invoke Lambda
       ▼
┌─────────────────────────────────────┐
│  CreateLivenessSession Lambda       │
│  - LivenessService.create_session() │
└──────┬──────────────────────────────┘
       │
       │ 3. CreateFaceLivenessSession
       ▼
┌─────────────────────────────────────┐
│  AWS Rekognition                    │
└──────┬──────────────────────────────┘
       │
       │ 4. Return SessionId
       ▼
┌─────────────────────────────────────┐
│  DynamoDB (LivenessSessions)        │
│  - session_id (PK)                  │
│  - employee_id (GSI)                │
│  - status, expires_at               │
└─────────────────────────────────────┘
       │
       │ 5. Return SessionId to Frontend
       ▼
┌─────────────────────────────────────┐
│  Frontend - FaceLivenessDetector    │
│  (Amplify UI Component)             │
│  - User performs liveness check     │
└──────┬──────────────────────────────┘
       │
       │ 6. GET /liveness/session/{sessionId}/result
       ▼
┌─────────────────────────────────────┐
│  GetLivenessResult Lambda           │
│  - LivenessService.get_session_result() │
└──────┬──────────────────────────────┘
       │
       │ 7. GetFaceLivenessSessionResults
       ▼
┌─────────────────────────────────────┐
│  AWS Rekognition                    │
└──────┬──────────────────────────────┘
       │
       │ 8. Return Confidence, Status
       ▼
┌─────────────────────────────────────┐
│  S3 (liveness-audit/)               │
│  - Reference images                 │
│  - Audit images                     │
│  - Audit logs (JSON)                │
└─────────────────────────────────────┘
```

---

## API仕様

### 1. セッション作成

**エンドポイント:** `POST /liveness/session/create`

**リクエスト:**
```json
{
  "employee_id": "E123456"
}
```

**レスポンス (成功):**
```json
{
  "statusCode": 200,
  "body": {
    "session_id": "abc123-def456-ghi789",
    "expires_at": "2026-02-04T10:30:00Z"
  }
}
```

**レスポンス (エラー):**
```json
{
  "statusCode": 500,
  "body": {
    "error": "LIVENESS_SERVICE_ERROR",
    "message": "Failed to create liveness session: ..."
  }
}
```

---

### 2. セッション結果取得

**エンドポイント:** `GET /liveness/session/{sessionId}/result`

**パスパラメータ:**
- `sessionId`: セッションID

**レスポンス (成功 - Live):**
```json
{
  "statusCode": 200,
  "body": {
    "session_id": "abc123-def456-ghi789",
    "is_live": true,
    "confidence": 95.5,
    "status": "SUCCESS",
    "reference_image_s3_key": "liveness-audit/abc123.../reference.jpg",
    "audit_image_s3_key": "liveness-audit/abc123.../audit-0.jpg"
  }
}
```

**レスポンス (失敗 - Not Live):**
```json
{
  "statusCode": 200,
  "body": {
    "session_id": "abc123-def456-ghi789",
    "is_live": false,
    "confidence": 85.0,
    "status": "FAILED",
    "error_message": "Confidence 85.00% below threshold 90.00%"
  }
}
```

**レスポンス (エラー - Session Not Found):**
```json
{
  "statusCode": 404,
  "body": {
    "error": "SESSION_NOT_FOUND",
    "message": "Session not found: abc123-def456-ghi789"
  }
}
```

**レスポンス (エラー - Session Expired):**
```json
{
  "statusCode": 410,
  "body": {
    "error": "SESSION_EXPIRED",
    "message": "Session expired: abc123-def456-ghi789"
  }
}
```

---

## データモデル

### DynamoDB: LivenessSessions テーブル

| 属性名 | 型 | 説明 |
|--------|-----|------|
| `session_id` | String (PK) | セッションID（UUID） |
| `employee_id` | String (GSI) | 社員ID |
| `status` | String | ステータス（PENDING, SUCCESS, FAILED） |
| `confidence` | Number | 信頼度スコア（0-100） |
| `reference_image_s3_key` | String | リファレンス画像のS3キー |
| `created_at` | String | 作成日時（ISO 8601） |
| `expires_at` | Number (TTL) | 有効期限（Unix timestamp） |

**GSI: EmployeeIdIndex**
- Partition Key: `employee_id`
- 用途: 社員IDでセッションを検索（監査・デバッグ用）

---

### S3: liveness-audit/ ディレクトリ

```
liveness-audit/
├── {session_id}/
│   ├── reference.jpg          # リファレンス画像
│   ├── audit-0.jpg            # 監査画像1
│   ├── audit-1.jpg            # 監査画像2
│   └── audit-log.json         # 監査ログ
```

**audit-log.json 形式:**
```json
{
  "session_id": "abc123-def456-ghi789",
  "employee_id": "E123456",
  "timestamp": "2026-02-04T10:25:00Z",
  "result": {
    "session_id": "abc123-def456-ghi789",
    "is_live": true,
    "confidence": 95.5,
    "status": "SUCCESS"
  },
  "client_info": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}
```

---

## LivenessService クラス

### 初期化

```python
from lambda.shared.liveness_service import LivenessService

service = LivenessService(
    rekognition_client=boto3.client('rekognition'),
    dynamodb_client=boto3.client('dynamodb'),
    s3_client=boto3.client('s3'),
    cloudwatch_client=boto3.client('cloudwatch'),
    confidence_threshold=90.0,
    session_timeout_minutes=10,
    liveness_sessions_table='FaceAuth-LivenessSessions',
    face_auth_bucket='face-auth-images-123456789012-us-east-1'
)
```

### メソッド

#### create_session(employee_id: str) -> Dict[str, str]

Livenessセッションを作成します。

**引数:**
- `employee_id`: 社員ID

**戻り値:**
```python
{
    'session_id': 'abc123-def456-ghi789',
    'expires_at': '2026-02-04T10:30:00Z'
}
```

**例外:**
- `LivenessServiceError`: セッション作成失敗

**使用例:**
```python
try:
    result = service.create_session('E123456')
    session_id = result['session_id']
    print(f"Session created: {session_id}")
except LivenessServiceError as e:
    print(f"Error: {e}")
```

---

#### get_session_result(session_id: str) -> LivenessSessionResult

セッション結果を取得・評価します。

**引数:**
- `session_id`: セッションID

**戻り値:**
```python
LivenessSessionResult(
    session_id='abc123-def456-ghi789',
    is_live=True,
    confidence=95.5,
    reference_image_s3_key='liveness-audit/abc123.../reference.jpg',
    audit_image_s3_key='liveness-audit/abc123.../audit-0.jpg',
    status='SUCCESS',
    error_message=None
)
```

**例外:**
- `SessionNotFoundError`: セッションが存在しない
- `SessionExpiredError`: セッションが期限切れ
- `LivenessServiceError`: 結果取得失敗

**使用例:**
```python
try:
    result = service.get_session_result(session_id)
    if result.is_live:
        print(f"Liveness verified: {result.confidence}%")
    else:
        print(f"Liveness failed: {result.error_message}")
except SessionNotFoundError:
    print("Session not found")
except SessionExpiredError:
    print("Session expired")
```

---

#### store_audit_log(session_id, result, employee_id, client_info)

監査ログをS3に保存します。

**引数:**
- `session_id`: セッションID
- `result`: LivenessSessionResult
- `employee_id`: 社員ID
- `client_info`: クライアント情報（オプション）

**使用例:**
```python
service.store_audit_log(
    session_id=session_id,
    result=result,
    employee_id='E123456',
    client_info={
        'ip_address': '192.168.1.100',
        'user_agent': 'Mozilla/5.0...'
    }
)
```

---

## CloudWatch メトリクス

### カスタムメトリクス

**Namespace:** `FaceAuth/Liveness`

| メトリクス名 | 単位 | 説明 |
|-------------|------|------|
| `SessionCreated` | Count | セッション作成数 |
| `SessionCreationTime` | Seconds | セッション作成時間 |
| `SessionCreationError` | Count | セッション作成エラー数 |
| `SessionCount` | Count | セッション数（Status別） |
| `SuccessCount` | Count | 成功数 |
| `FailureCount` | Count | 失敗数 |
| `ConfidenceScore` | Percent | 信頼度スコア |
| `VerificationTime` | Seconds | 検証時間 |
| `VerificationError` | Count | 検証エラー数 |
| `SessionNotFound` | Count | セッション未検出数 |
| `SessionExpired` | Count | セッション期限切れ数 |

### ディメンション

- `Status`: SUCCESS, FAILED

---

## CloudWatch アラーム

### 1. 成功率低下アラーム

**アラーム名:** `FaceAuth-Liveness-LowSuccessRate`  
**条件:** 成功率 < 95%  
**評価期間:** 5分間 × 2回  
**アクション:** SNS通知（設定時）

---

### 2. 信頼度低下アラーム

**アラーム名:** `FaceAuth-Liveness-LowConfidence`  
**条件:** 平均信頼度 < 92%  
**評価期間:** 5分間 × 2回  
**アクション:** SNS通知

---

### 3. 検証時間超過アラーム

**アラーム名:** `FaceAuth-Liveness-SlowVerification`  
**条件:** 平均検証時間 > 30秒  
**評価期間:** 5分間 × 2回  
**アクション:** SNS通知

---

### 4. エラー率アラーム

**アラーム名:** `FaceAuth-Liveness-HighErrorRate`  
**条件:** エラー数 > 10（5分間）  
**評価期間:** 5分間 × 1回  
**アクション:** SNS通知

---

### 5. Lambda エラーアラーム

**アラーム名:** 
- `FaceAuth-CreateLivenessSession-Errors`
- `FaceAuth-GetLivenessResult-Errors`

**条件:** エラー数 > 5  
**評価期間:** 5分間 × 1回  
**アクション:** SNS通知

---

### 6. Lambda タイムアウトアラーム

**アラーム名:**
- `FaceAuth-CreateLivenessSession-Timeouts`
- `FaceAuth-GetLivenessResult-Timeouts`

**条件:** 
- CreateSession: 実行時間 > 9秒（10秒タイムアウト）
- GetResult: 実行時間 > 14秒（15秒タイムアウト）

**評価期間:** 5分間 × 2回  
**アクション:** SNS通知

---

## セキュリティ

### 1. データ暗号化

- **転送中:** TLS/HTTPS
- **保存時:** 
  - DynamoDB: AWS管理キー
  - S3: SSE-S3（AES256）

### 2. アクセス制御

- **IAM権限:** Lambda実行ロールに最小権限
- **VPC:** Lambda関数はPrivate Subnetに配置
- **セキュリティグループ:** 必要な通信のみ許可

### 3. 監査ログ

- すべてのLiveness検証結果をS3に保存
- 90日間保持（ライフサイクルポリシー）
- CloudWatch Logsに構造化ログ出力

---

## パフォーマンス

### タイムアウト設定

| 処理 | タイムアウト | 説明 |
|------|-------------|------|
| セッション作成 | 10秒 | Rekognition API呼び出し |
| 結果取得 | 15秒 | Rekognition API + DynamoDB更新 |
| セッション有効期限 | 10分 | ユーザーがLiveness検証を完了する時間 |

### 目標パフォーマンス

| メトリクス | 目標値 |
|-----------|--------|
| セッション作成時間 | < 3秒 |
| 結果取得時間 | < 5秒 |
| 全体検証時間 | < 30秒 |
| 成功率 | > 95% |
| 信頼度スコア | > 90% |

---

## コスト

### Rekognition Liveness API

- **料金:** $0.04 per session（2026年2月時点）
- **月間予想:** 10,000セッション = $400

### S3 ストレージ

- **監査ログ:** 90日保持
- **月間予想:** ~$5

### DynamoDB

- **オンデマンド:** 読み取り・書き込みに応じて課金
- **月間予想:** ~$10

### 合計月間コスト

**約 $415 - $450**

---

## トラブルシューティング

### 問題: セッション作成失敗

**症状:**
```
LivenessServiceError: Failed to create liveness session
```

**原因:**
1. Rekognition API権限不足
2. S3バケットアクセス権限不足
3. DynamoDBテーブルアクセス権限不足

**解決策:**
```bash
# IAM権限確認
aws iam get-role-policy --role-name FaceAuthLambdaExecutionRole --policy-name FaceAuthLambdaPolicy

# CloudWatch Logsで詳細確認
aws logs tail /aws/lambda/FaceAuth-CreateLivenessSession --follow
```

---

### 問題: セッション期限切れ

**症状:**
```
SessionExpiredError: Session expired: abc123-def456-ghi789
```

**原因:**
- ユーザーが10分以内にLiveness検証を完了しなかった

**解決策:**
- 新しいセッションを作成
- フロントエンドでタイムアウト警告を表示

---

### 問題: 信頼度が低い

**症状:**
```
Confidence 85.00% below threshold 90.00%
```

**原因:**
1. 照明が不十分
2. カメラの品質が低い
3. ユーザーが指示に従っていない

**解決策:**
- フロントエンドで明るい場所での撮影を促す
- カメラ品質チェックを追加
- ユーザーガイダンスを改善

---

## 参考資料

- [AWS Rekognition Face Liveness API](https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness.html)
- [Amplify UI FaceLivenessDetector](https://ui.docs.amplify.aws/react/connected-components/liveness)
- [Face-Auth IdP System - Design Document](../design.md)
- [Liveness Migration Guide](./LIVENESS_MIGRATION_GUIDE.md)

---

**最終更新:** 2026-02-04  
**作成者:** Face-Auth Development Team  
**バージョン:** 1.0
