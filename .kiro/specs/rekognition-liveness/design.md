# Rekognition Liveness API 移行 - 設計書

**Feature:** Rekognition Liveness APIへの移行  
**Priority:** High  
**Status:** Draft  
**Created:** 2026-02-02  
**Last Updated:** 2026-02-02

---

## 概要

現在の簡易的なliveness検証（DetectFaces API）から、AWS Rekognition Liveness APIへ移行し、写真・動画を使ったなりすまし攻撃を防ぐ高度なセキュリティを実現する。

### 設計目標

1. **セキュリティ強化**: なりすまし攻撃（写真・動画）の防止
2. **ユーザー体験**: 30秒以内の検証完了
3. **既存システムとの統合**: 最小限の変更で既存フローに組み込み
4. **段階的移行**: 後方互換性を維持しながら移行
5. **コスト最適化**: 月間予算$500以内

---

## アーキテクチャ概要

### システム構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  AWS Amplify UI Liveness Component                       │   │
│  │  - FaceLivenessDetector                                  │   │
│  │  - Camera Access & Challenge UI                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (REST API)                      │
│  - POST /liveness/session/create                                 │
│  - GET  /liveness/session/{sessionId}/result                     │
│  - POST /enrollment (updated)                                    │
│  - POST /face-login (updated)                                    │
│  - POST /emergency-auth (updated)                                │
│  - POST /re-enrollment (updated)                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Lambda Functions                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  CreateLivenessSession                                   │   │
│  │  - CreateFaceLivenessSession API                         │   │
│  │  - Store session in DynamoDB                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  GetLivenessResult                                       │   │
│  │  - GetFaceLivenessSessionResults API                     │   │
│  │  - Evaluate confidence score                             │   │
│  │  - Store audit log                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Existing Handlers (Updated)                             │   │
│  │  - Enrollment, FaceLogin, EmergencyAuth, ReEnrollment    │   │
│  │  - Integrate liveness verification                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Rekognition Service                       │
│  - CreateFaceLivenessSession                                     │
│  - GetFaceLivenessSessionResults                                 │
│  - Face Liveness Detection (Client-side)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Data Storage                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  DynamoDB: FaceAuth-LivenessSessions                     │   │
│  │  - session_id (PK), employee_id, status, confidence      │   │
│  │  - created_at, expires_at (TTL: 10 min)                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  S3: face-auth-images/liveness-audit/                    │   │
│  │  - {session_id}/reference.jpg                            │   │
│  │  - {session_id}/audit-log.json                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## コンポーネント設計

### 1. Liveness Session Service

新規サービス: `lambda/shared/liveness_service.py`

#### 責務
- Livenessセッションの作成と管理
- セッション結果の取得と評価
- 監査ログの記録

#### クラス設計

```python
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import boto3
import logging

@dataclass
class LivenessSessionResult:
    """Liveness検証結果"""
    session_id: str
    is_live: bool
    confidence: float
    reference_image_s3_key: Optional[str]
    audit_image_s3_key: Optional[str]
    status: str  # SUCCESS, FAILED, TIMEOUT
    error_message: Optional[str] = None

class LivenessService:
    """AWS Rekognition Liveness API統合サービス"""
    
    def __init__(
        self,
        rekognition_client: Optional[boto3.client] = None,
        dynamodb_service: Optional[Any] = None,
        s3_client: Optional[boto3.client] = None,
        confidence_threshold: float = 90.0,
        session_timeout_minutes: int = 10
    ):
        """
        Args:
            rekognition_client: Rekognitionクライアント
            dynamodb_service: DynamoDBサービス
            s3_client: S3クライアント
            confidence_threshold: 信頼度閾値（デフォルト: 90%）
            session_timeout_minutes: セッションタイムアウト（デフォルト: 10分）
        """
        self.rekognition = rekognition_client or boto3.client('rekognition')
        self.dynamodb = dynamodb_service
        self.s3 = s3_client or boto3.client('s3')
        self.confidence_threshold = confidence_threshold
        self.session_timeout_minutes = session_timeout_minutes
        self.logger = logging.getLogger(__name__)
    
    def create_session(self, employee_id: str) -> Dict[str, str]:
        """
        Livenessセッションを作成
        
        Args:
            employee_id: 社員ID
            
        Returns:
            {
                'session_id': str,
                'expires_at': str (ISO 8601)
            }
            
        Raises:
            LivenessServiceError: セッション作成失敗
        """
        pass
    
    def get_session_result(
        self,
        session_id: str
    ) -> LivenessSessionResult:
        """
        Livenessセッション結果を取得・評価
        
        Args:
            session_id: セッションID
            
        Returns:
            LivenessSessionResult
            
        Raises:
            LivenessServiceError: 結果取得失敗
            SessionNotFoundError: セッションが存在しない
            SessionExpiredError: セッションが期限切れ
        """
        pass
    
    def store_audit_log(
        self,
        session_id: str,
        result: LivenessSessionResult,
        employee_id: str
    ) -> None:
        """
        監査ログをS3に保存
        
        Args:
            session_id: セッションID
            result: 検証結果
            employee_id: 社員ID
        """
        pass
```

#### 設計判断

**判断1: 信頼度閾値を90%に設定**
- 理由: AWS推奨値（85-95%）の中間値
- トレードオフ: セキュリティと利便性のバランス
- 調整可能: 環境変数で設定可能

**判断2: セッションタイムアウトを10分に設定**
- 理由: AWS Rekognition Livenessの最大値
- ユーザー体験: 十分な時間を提供
- セキュリティ: TTLで自動削除

**判断3: 監査ログをS3に保存**
- 理由: 長期保存とコスト効率
- 保持期間: 90日（ライフサイクルポリシー）
- 暗号化: SSE-S3（AWS管理キー）

---

### 2. DynamoDB テーブル設計

#### FaceAuth-LivenessSessions

```python
{
    "TableName": "FaceAuth-LivenessSessions",
    "KeySchema": [
        {"AttributeName": "session_id", "KeyType": "HASH"}
    ],
    "AttributeDefinitions": [
        {"AttributeName": "session_id", "AttributeType": "S"},
        {"AttributeName": "employee_id", "AttributeType": "S"}
    ],
    "GlobalSecondaryIndexes": [
        {
            "IndexName": "EmployeeIdIndex",
            "KeySchema": [
                {"AttributeName": "employee_id", "KeyType": "HASH"}
            ],
            "Projection": {"ProjectionType": "ALL"}
        }
    ],
    "TimeToLiveSpecification": {
        "Enabled": True,
        "AttributeName": "expires_at"
    }
}
```


**アイテム構造:**

```python
{
    "session_id": "uuid-v4",
    "employee_id": "EMP001",
    "status": "PENDING|SUCCESS|FAILED",
    "confidence": 95.5,  # Optional, set after verification
    "reference_image_s3_key": "liveness-audit/session-id/reference.jpg",
    "created_at": "2026-02-02T10:00:00Z",
    "expires_at": 1738497600,  # Unix timestamp (TTL)
    "error_message": "Optional error description"
}
```

**設計判断:**
- TTL有効化: 10分後に自動削除（メモリとコスト削減）
- GSI追加: 社員IDでのクエリを可能に（監査・デバッグ用）
- ステータス管理: PENDING → SUCCESS/FAILED

---

### 3. S3 バケット構造

#### liveness-audit/ ディレクトリ

```
face-auth-images-{account}-{region}/
└── liveness-audit/
    └── {session_id}/
        ├── reference.jpg          # Rekognitionから取得したリファレンス画像
        ├── audit-log.json         # 検証結果の詳細ログ
        └── metadata.json          # セッションメタデータ
```

**audit-log.json 構造:**

```json
{
  "session_id": "uuid-v4",
  "employee_id": "EMP001",
  "timestamp": "2026-02-02T10:00:00Z",
  "result": {
    "is_live": true,
    "confidence": 95.5,
    "status": "SUCCESS"
  },
  "rekognition_response": {
    "Status": "SUCCEEDED",
    "Confidence": 95.5,
    "AuditImages": [...]
  },
  "client_info": {
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.1"
  }
}
```

**設計判断:**
- ライフサイクルポリシー: 90日後に自動削除
- 暗号化: SSE-S3（デフォルト）
- アクセス制御: Lambda実行ロールのみ

---

### 4. Lambda関数設計

#### 4.1 CreateLivenessSession Lambda

**ファイル:** `lambda/liveness/create_session_handler.py`

```python
import json
import os
from typing import Dict, Any
from lambda.shared.liveness_service import LivenessService
from lambda.shared.error_handler import handle_errors, ErrorResponse
from lambda.shared.timeout_manager import TimeoutManager

@handle_errors
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Livenessセッション作成ハンドラー
    
    Request:
        POST /liveness/session/create
        {
            "employee_id": "EMP001"
        }
    
    Response:
        {
            "session_id": "uuid-v4",
            "expires_at": "2026-02-02T10:10:00Z"
        }
    """
    timeout_manager = TimeoutManager(context)
    
    # リクエストボディ解析
    body = json.loads(event.get('body', '{}'))
    employee_id = body.get('employee_id')
    
    if not employee_id:
        return ErrorResponse.bad_request("employee_id is required")
    
    # Livenessセッション作成
    liveness_service = LivenessService(
        confidence_threshold=float(os.environ.get('LIVENESS_CONFIDENCE_THRESHOLD', '90.0'))
    )
    
    with timeout_manager.operation("create_liveness_session", timeout_seconds=5):
        result = liveness_service.create_session(employee_id)
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }
```

**環境変数:**
- `LIVENESS_CONFIDENCE_THRESHOLD`: 信頼度閾値（デフォルト: 90.0）
- `LIVENESS_SESSIONS_TABLE`: DynamoDBテーブル名
- `FACE_AUTH_BUCKET`: S3バケット名

**タイムアウト:** 10秒
**メモリ:** 256MB

---

#### 4.2 GetLivenessResult Lambda

**ファイル:** `lambda/liveness/get_result_handler.py`

```python
import json
import os
from typing import Dict, Any
from lambda.shared.liveness_service import LivenessService
from lambda.shared.error_handler import handle_errors, ErrorResponse
from lambda.shared.timeout_manager import TimeoutManager

@handle_errors
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Livenessセッション結果取得ハンドラー
    
    Request:
        GET /liveness/session/{sessionId}/result
    
    Response:
        {
            "session_id": "uuid-v4",
            "is_live": true,
            "confidence": 95.5,
            "status": "SUCCESS"
        }
    """
    timeout_manager = TimeoutManager(context)
    
    # パスパラメータ取得
    session_id = event.get('pathParameters', {}).get('sessionId')
    
    if not session_id:
        return ErrorResponse.bad_request("sessionId is required")
    
    # Liveness結果取得
    liveness_service = LivenessService()
    
    with timeout_manager.operation("get_liveness_result", timeout_seconds=8):
        result = liveness_service.get_session_result(session_id)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'session_id': result.session_id,
            'is_live': result.is_live,
            'confidence': result.confidence,
            'status': result.status
        })
    }
```

**タイムアウト:** 15秒
**メモリ:** 256MB

---

### 5. 既存Lambda関数の更新

#### 5.1 Enrollment Handler 更新

**変更点:**
1. Liveness検証ステップを追加
2. 検証成功後に顔データ登録

```python
# lambda/enrollment/handler.py (更新部分)

@handle_errors
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """登録ハンドラー（Liveness統合版）"""
    
    body = json.loads(event.get('body', '{}'))
    employee_id = body.get('employee_id')
    liveness_session_id = body.get('liveness_session_id')  # 新規追加
    face_image_base64 = body.get('face_image')
    
    # 1. Liveness検証（新規）
    liveness_service = LivenessService()
    liveness_result = liveness_service.get_session_result(liveness_session_id)
    
    if not liveness_result.is_live:
        return ErrorResponse.unauthorized(
            "Liveness verification failed",
            details={"confidence": liveness_result.confidence}
        )
    
    # 2. 既存の登録処理
    # ... (既存コード)
```

**設計判断:**
- Liveness検証を最初に実行（早期失敗）
- セッションIDをリクエストに含める（フロントエンドで管理）
- 検証失敗時は詳細なエラーメッセージを返す

---

#### 5.2 Face Login Handler 更新

```python
# lambda/face_login/handler.py (更新部分)

@handle_errors
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """顔ログインハンドラー（Liveness統合版）"""
    
    body = json.loads(event.get('body', '{}'))
    liveness_session_id = body.get('liveness_session_id')  # 新規追加
    face_image_base64 = body.get('face_image')
    
    # 1. Liveness検証（新規）
    liveness_service = LivenessService()
    liveness_result = liveness_service.get_session_result(liveness_session_id)
    
    if not liveness_result.is_live:
        # 失敗試行をS3に記録
        store_failed_login_attempt(liveness_session_id, liveness_result)
        return ErrorResponse.unauthorized("Liveness verification failed")
    
    # 2. 既存の1:N顔マッチング
    # ... (既存コード)
```

---

#### 5.3 Emergency Auth Handler 更新

```python
# lambda/emergency_auth/handler.py (更新部分)

@handle_errors
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """緊急認証ハンドラー（Liveness統合版）"""
    
    body = json.loads(event.get('body', '{}'))
    card_image_base64 = body.get('card_image')
    password = body.get('password')
    liveness_session_id = body.get('liveness_session_id')  # 新規追加
    face_image_base64 = body.get('face_image')
    
    # 1. 社員証OCR
    # ... (既存コード)
    
    # 2. AD認証
    # ... (既存コード)
    
    # 3. Liveness検証（新規）
    liveness_service = LivenessService()
    liveness_result = liveness_service.get_session_result(liveness_session_id)
    
    if not liveness_result.is_live:
        return ErrorResponse.unauthorized("Liveness verification failed")
    
    # 4. セッション作成
    # ... (既存コード)
```

---

#### 5.4 Re-enrollment Handler 更新

```python
# lambda/re_enrollment/handler.py (更新部分)

@handle_errors
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """再登録ハンドラー（Liveness統合版）"""
    
    body = json.loads(event.get('body', '{}'))
    card_image_base64 = body.get('card_image')
    password = body.get('password')
    liveness_session_id = body.get('liveness_session_id')  # 新規追加
    new_face_image_base64 = body.get('new_face_image')
    
    # 1. 本人確認（OCR + AD）
    # ... (既存コード)
    
    # 2. Liveness検証（新規）
    liveness_service = LivenessService()
    liveness_result = liveness_service.get_session_result(liveness_session_id)
    
    if not liveness_result.is_live:
        return ErrorResponse.unauthorized("Liveness verification failed")
    
    # 3. 古い顔データ削除 + 新しい顔データ登録
    # ... (既存コード)
```

---

### 6. フロントエンド設計

#### 6.1 Liveness Component

**ファイル:** `frontend/src/components/LivenessDetector.tsx`

```typescript
import React, { useState } from 'react';
import { FaceLivenessDetector } from '@aws-amplify/ui-react-liveness';
import { Loader } from '@aws-amplify/ui-react';

interface LivenessDetectorProps {
  onSuccess: (sessionId: string) => void;
  onError: (error: Error) => void;
}

export const LivenessDetector: React.FC<LivenessDetectorProps> = ({
  onSuccess,
  onError
}) => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // セッション作成
  const createLivenessSession = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/liveness/session/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          employee_id: localStorage.getItem('employee_id')
        })
      });
      
      const data = await response.json();
      setSessionId(data.session_id);
    } catch (error) {
      onError(error as Error);
    } finally {
      setLoading(false);
    }
  };

  // Liveness検証完了
  const handleAnalysisComplete = async () => {
    if (!sessionId) return;
    
    try {
      // 結果取得（バックエンドで検証）
      const response = await fetch(`/api/liveness/session/${sessionId}/result`);
      const result = await response.json();
      
      if (result.is_live) {
        onSuccess(sessionId);
      } else {
        onError(new Error('Liveness verification failed'));
      }
    } catch (error) {
      onError(error as Error);
    }
  };

  if (loading) {
    return <Loader />;
  }

  if (!sessionId) {
    return (
      <button onClick={createLivenessSession}>
        本人確認を開始
      </button>
    );
  }

  return (
    <FaceLivenessDetector
      sessionId={sessionId}
      region="ap-northeast-1"
      onAnalysisComplete={handleAnalysisComplete}
      onError={onError}
    />
  );
};
```


#### 6.2 既存コンポーネントの更新

**Enrollment.tsx 更新:**

```typescript
// frontend/src/components/Enrollment.tsx (更新部分)

const Enrollment: React.FC = () => {
  const [step, setStep] = useState<'liveness' | 'capture' | 'submit'>('liveness');
  const [livenessSessionId, setLivenessSessionId] = useState<string | null>(null);
  const [faceImage, setFaceImage] = useState<string | null>(null);

  const handleLivenessSuccess = (sessionId: string) => {
    setLivenessSessionId(sessionId);
    setStep('capture');
  };

  const handleSubmit = async () => {
    const response = await fetch('/api/enrollment', {
      method: 'POST',
      body: JSON.stringify({
        employee_id: employeeId,
        liveness_session_id: livenessSessionId,  // 追加
        face_image: faceImage
      })
    });
    // ... 処理
  };

  return (
    <div>
      {step === 'liveness' && (
        <LivenessDetector
          onSuccess={handleLivenessSuccess}
          onError={handleError}
        />
      )}
      {step === 'capture' && (
        <CameraCapture onCapture={setFaceImage} />
      )}
      {/* ... */}
    </div>
  );
};
```

**設計判断:**
- ステップ分離: Liveness → 顔キャプチャ → 送信
- セッションID管理: フロントエンドで保持
- エラーハンドリング: 各ステップで適切なメッセージ表示

---

## API設計

### 新規エンドポイント

#### POST /liveness/session/create

**リクエスト:**
```json
{
  "employee_id": "EMP001"
}
```

**レスポンス (200):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "expires_at": "2026-02-02T10:10:00Z"
}
```

**エラー (400):**
```json
{
  "error": "BAD_REQUEST",
  "message": "employee_id is required"
}
```

---

#### GET /liveness/session/{sessionId}/result

**レスポンス (200):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "is_live": true,
  "confidence": 95.5,
  "status": "SUCCESS"
}
```

**エラー (404):**
```json
{
  "error": "NOT_FOUND",
  "message": "Session not found or expired"
}
```

**エラー (401):**
```json
{
  "error": "UNAUTHORIZED",
  "message": "Liveness verification failed",
  "details": {
    "confidence": 75.2,
    "threshold": 90.0
  }
}
```

---

### 既存エンドポイントの更新

#### POST /enrollment (更新)

**リクエスト変更:**
```json
{
  "employee_id": "EMP001",
  "liveness_session_id": "550e8400-e29b-41d4-a716-446655440000",  // 追加
  "face_image": "base64-encoded-image"
}
```

#### POST /face-login (更新)

**リクエスト変更:**
```json
{
  "liveness_session_id": "550e8400-e29b-41d4-a716-446655440000",  // 追加
  "face_image": "base64-encoded-image"
}
```

#### POST /emergency-auth (更新)

**リクエスト変更:**
```json
{
  "card_image": "base64-encoded-image",
  "password": "password123",
  "liveness_session_id": "550e8400-e29b-41d4-a716-446655440000",  // 追加
  "face_image": "base64-encoded-image"
}
```

#### POST /re-enrollment (更新)

**リクエスト変更:**
```json
{
  "card_image": "base64-encoded-image",
  "password": "password123",
  "liveness_session_id": "550e8400-e29b-41d4-a716-446655440000",  // 追加
  "new_face_image": "base64-encoded-image"
}
```

---

## セキュリティ設計

### 1. IAM権限

#### Lambda実行ロール

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:CreateFaceLivenessSession",
        "rekognition:GetFaceLivenessSessionResults"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/FaceAuth-LivenessSessions",
        "arn:aws:dynamodb:*:*:table/FaceAuth-LivenessSessions/index/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::face-auth-images-*/liveness-audit/*"
    }
  ]
}
```

**設計判断:**
- 最小権限の原則: 必要なアクションのみ許可
- リソース制限: 特定のテーブル・バケットのみ
- Rekognition: リージョン制限なし（API仕様）

---

### 2. データ暗号化

#### 転送中
- HTTPS/TLS 1.2以上
- API Gateway + CloudFront

#### 保存時
- DynamoDB: AWS管理キー（デフォルト）
- S3: SSE-S3（AWS管理キー）
- 将来的にKMS対応可能

---

### 3. セッション管理

#### セキュリティ対策
1. **セッションID**: UUID v4（暗号学的に安全）
2. **有効期限**: 10分（TTL自動削除）
3. **再利用防止**: 1回限りの使用
4. **レート制限**: 社員IDごとに制限（DynamoDB GSI）

---

## エラーハンドリング

### エラー分類

#### 1. Liveness検証エラー

| エラーコード | 説明 | HTTPステータス | 対応 |
|------------|------|---------------|------|
| LIVENESS_FAILED | 信頼度不足 | 401 | ユーザーに再試行を促す |
| SESSION_NOT_FOUND | セッション不存在 | 404 | 新規セッション作成 |
| SESSION_EXPIRED | セッション期限切れ | 410 | 新規セッション作成 |
| TIMEOUT | タイムアウト | 408 | 再試行 |

#### 2. API呼び出しエラー

| エラー | 原因 | 対応 |
|-------|------|------|
| ThrottlingException | レート制限 | 指数バックオフで再試行 |
| ServiceUnavailableException | AWS障害 | フォールバック（DetectFaces） |
| ValidationException | 不正なパラメータ | エラーメッセージ表示 |

---

### エラーメッセージ設計

#### ユーザー向けメッセージ（日本語）

```python
ERROR_MESSAGES = {
    'LIVENESS_FAILED': '本人確認に失敗しました。もう一度お試しください。',
    'SESSION_EXPIRED': 'セッションの有効期限が切れました。最初からやり直してください。',
    'TIMEOUT': 'タイムアウトしました。もう一度お試しください。',
    'CAMERA_ACCESS_DENIED': 'カメラへのアクセスが拒否されました。ブラウザの設定を確認してください。',
    'NETWORK_ERROR': 'ネットワークエラーが発生しました。接続を確認してください。'
}
```

---

## パフォーマンス設計

### タイムアウト設定

| 処理 | タイムアウト | 理由 |
|------|------------|------|
| セッション作成 | 5秒 | Rekognition API呼び出し |
| 結果取得 | 8秒 | Rekognition API + S3保存 |
| Liveness検証（クライアント） | 30秒 | ユーザー操作時間 |
| 全体フロー | 45秒 | 要件（NFR-1.1） |

### 最適化戦略

1. **並列処理**: 可能な処理を並列実行
2. **キャッシング**: セッション情報をDynamoDBにキャッシュ
3. **早期失敗**: Liveness検証を最初に実行
4. **非同期処理**: 監査ログ保存を非同期化（オプション）

---

## 監視とロギング

### CloudWatch メトリクス

#### カスタムメトリクス

```python
# 成功率
cloudwatch.put_metric_data(
    Namespace='FaceAuth/Liveness',
    MetricData=[{
        'MetricName': 'LivenessSuccessRate',
        'Value': success_count / total_count * 100,
        'Unit': 'Percent'
    }]
)

# 平均信頼度
cloudwatch.put_metric_data(
    Namespace='FaceAuth/Liveness',
    MetricData=[{
        'MetricName': 'AverageConfidence',
        'Value': average_confidence,
        'Unit': 'None'
    }]
)

# セッション数
cloudwatch.put_metric_data(
    Namespace='FaceAuth/Liveness',
    MetricData=[{
        'MetricName': 'SessionCount',
        'Value': 1,
        'Unit': 'Count'
    }]
)
```


### CloudWatch アラーム

```python
# 成功率低下アラーム
alarm = cloudwatch.Alarm(
    self, "LivenessSuccessRateAlarm",
    metric=liveness_success_rate_metric,
    threshold=95,
    evaluation_periods=2,
    comparison_operator=cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
    alarm_description="Liveness success rate below 95%"
)

# コスト超過アラーム
alarm = cloudwatch.Alarm(
    self, "LivenessCostAlarm",
    metric=session_count_metric,
    threshold=20000,  # $500 / $0.025
    evaluation_periods=1,
    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
    alarm_description="Monthly liveness session count exceeds budget"
)
```

### ログ出力

```python
# 構造化ログ
logger.info("Liveness session created", extra={
    "session_id": session_id,
    "employee_id": employee_id,
    "expires_at": expires_at
})

logger.info("Liveness verification completed", extra={
    "session_id": session_id,
    "is_live": is_live,
    "confidence": confidence,
    "duration_ms": duration
})

logger.error("Liveness verification failed", extra={
    "session_id": session_id,
    "error": error_message,
    "confidence": confidence
})
```

---

## テスト戦略

### 1. 単体テスト

**ファイル:** `tests/test_liveness_service.py`

```python
import pytest
from unittest.mock import Mock, patch
from lambda.shared.liveness_service import LivenessService, LivenessSessionResult

class TestLivenessService:
    """LivenessService単体テスト"""
    
    def test_create_session_success(self):
        """セッション作成成功"""
        # Arrange
        mock_rekognition = Mock()
        mock_rekognition.create_face_liveness_session.return_value = {
            'SessionId': 'test-session-id'
        }
        service = LivenessService(rekognition_client=mock_rekognition)
        
        # Act
        result = service.create_session('EMP001')
        
        # Assert
        assert result['session_id'] == 'test-session-id'
        assert 'expires_at' in result
    
    def test_get_session_result_live(self):
        """Liveness検証成功（生体検出）"""
        # Arrange
        mock_rekognition = Mock()
        mock_rekognition.get_face_liveness_session_results.return_value = {
            'Status': 'SUCCEEDED',
            'Confidence': 95.5,
            'ReferenceImage': {'Bytes': b'image-data'}
        }
        service = LivenessService(
            rekognition_client=mock_rekognition,
            confidence_threshold=90.0
        )
        
        # Act
        result = service.get_session_result('test-session-id')
        
        # Assert
        assert result.is_live is True
        assert result.confidence == 95.5
        assert result.status == 'SUCCESS'
    
    def test_get_session_result_not_live(self):
        """Liveness検証失敗（信頼度不足）"""
        # Arrange
        mock_rekognition = Mock()
        mock_rekognition.get_face_liveness_session_results.return_value = {
            'Status': 'SUCCEEDED',
            'Confidence': 75.0
        }
        service = LivenessService(
            rekognition_client=mock_rekognition,
            confidence_threshold=90.0
        )
        
        # Act
        result = service.get_session_result('test-session-id')
        
        # Assert
        assert result.is_live is False
        assert result.confidence == 75.0
        assert result.status == 'FAILED'
```

---

### 2. 統合テスト

**ファイル:** `tests/test_liveness_integration.py`

```python
import pytest
import boto3
from lambda.shared.liveness_service import LivenessService

@pytest.mark.integration
class TestLivenessIntegration:
    """Liveness統合テスト（実際のAWS API使用）"""
    
    def test_full_liveness_flow(self):
        """完全なLivenessフロー"""
        # 1. セッション作成
        service = LivenessService()
        session = service.create_session('TEST001')
        
        assert 'session_id' in session
        session_id = session['session_id']
        
        # 2. クライアント側検証（手動またはシミュレーション）
        # ... (実際のテストでは手動実行が必要)
        
        # 3. 結果取得
        result = service.get_session_result(session_id)
        
        assert result.session_id == session_id
        assert result.status in ['SUCCESS', 'FAILED', 'PENDING']
```

---

### 3. E2Eテスト

**ファイル:** `tests/test_liveness_e2e.py`

```python
import pytest
import requests
from frontend.src.utils.testUtils import simulateLivenessDetection

@pytest.mark.e2e
class TestLivenessE2E:
    """Liveness E2Eテスト"""
    
    def test_enrollment_with_liveness(self):
        """Liveness統合登録フロー"""
        base_url = "https://api.example.com"
        
        # 1. Livenessセッション作成
        response = requests.post(
            f"{base_url}/liveness/session/create",
            json={"employee_id": "TEST001"}
        )
        assert response.status_code == 200
        session_id = response.json()['session_id']
        
        # 2. Liveness検証（シミュレーション）
        simulateLivenessDetection(session_id)
        
        # 3. 登録
        response = requests.post(
            f"{base_url}/enrollment",
            json={
                "employee_id": "TEST001",
                "liveness_session_id": session_id,
                "face_image": "base64-image"
            }
        )
        assert response.status_code == 200
```

---

## 移行戦略

### フェーズ1: 準備（Week 1）

**目標:** インフラとサービス実装

**タスク:**
1. DynamoDBテーブル作成
2. S3バケット構造準備
3. LivenessService実装
4. Lambda関数実装
5. 単体テスト作成

**成功基準:**
- すべての単体テストが通過
- インフラがデプロイ可能

---

### フェーズ2: 統合（Week 2）

**目標:** 既存システムとの統合

**タスク:**
1. 既存Lambda関数更新
2. API Gateway更新
3. フロントエンド実装
4. 統合テスト実施

**成功基準:**
- 統合テストが通過
- E2Eテストが通過

---

### フェーズ3: 段階的展開（Week 3-4）

**目標:** 本番環境への段階的展開

**戦略:**
1. **オプトイン方式**: 一部ユーザーのみLiveness有効化
2. **A/Bテスト**: 成功率とユーザー体験を比較
3. **監視強化**: メトリクスとアラームを監視
4. **フィードバック収集**: ユーザーからのフィードバック

**ロールバック計画:**
- 環境変数で機能無効化
- 既存フロー（DetectFaces）に戻す
- データは保持（監査用）

---

### フェーズ4: 完全移行（Week 5-6）

**目標:** 全ユーザーへの展開

**タスク:**
1. すべてのユーザーでLiveness有効化
2. DetectFaces APIコード削除
3. ドキュメント更新
4. 運用手順書作成

**成功基準:**
- 成功率 > 95%
- 平均検証時間 < 20秒
- ユーザー満足度 > 4.0/5.0

---

## コスト分析

### 月間コスト見積もり

**前提条件:**
- 社員数: 1,000人
- 1日あたりログイン: 2回/人
- 月間営業日: 20日
- 月間セッション数: 1,000 × 2 × 20 = 40,000セッション

**コスト内訳:**

| サービス | 使用量 | 単価 | 月額 |
|---------|-------|------|------|
| Rekognition Liveness | 40,000セッション | $0.025/セッション | $1,000 |
| DynamoDB (LivenessSessions) | 40,000 write + 40,000 read | $0.25/million | $0.02 |
| S3 (監査ログ) | 40,000 × 100KB = 4GB | $0.023/GB | $0.09 |
| Lambda (新規2関数) | 40,000 × 2 × 0.5秒 | $0.20/million | $0.01 |
| **合計** | | | **$1,000.12** |

**⚠️ 注意:** 予算$500を超過

### コスト最適化戦略

#### 戦略1: セッション数削減

**方法:**
- 登録時のみLiveness必須
- ログイン時は週1回のみ
- 信頼済みデバイスは免除

**効果:**
- セッション数: 40,000 → 10,000
- 月額: $1,000 → $250

#### 戦略2: 段階的適用

**方法:**
- 高リスク操作のみLiveness必須
- 通常ログインはDetectFaces継続

**効果:**
- セッション数: 40,000 → 5,000
- 月額: $1,000 → $125

#### 戦略3: ハイブリッドアプローチ（推奨）

**方法:**
- 登録・再登録: Liveness必須
- 初回ログイン: Liveness必須
- 2回目以降: DetectFaces（信頼済み）
- 緊急認証: Liveness必須

**効果:**
- セッション数: 40,000 → 8,000
- 月額: $1,000 → $200
- **予算内達成** ✅

---

## 運用設計

### 監視項目

| 項目 | 閾値 | アクション |
|------|------|----------|
| 成功率 | < 95% | アラート送信 |
| 平均検証時間 | > 30秒 | パフォーマンス調査 |
| エラー率 | > 1% | ログ確認 |
| 月間セッション数 | > 20,000 | コスト確認 |

### トラブルシューティング

#### 問題1: 成功率低下

**原因:**
- カメラ品質不足
- 照明条件不良
- ユーザー操作ミス

**対応:**
- ユーザーガイド改善
- 環境チェック機能追加
- 信頼度閾値調整

#### 問題2: タイムアウト頻発

**原因:**
- ネットワーク遅延
- Rekognition API遅延

**対応:**
- タイムアウト値調整
- リトライロジック追加
- フォールバック機能

---

## セキュリティ考慮事項

### 脅威モデル

| 脅威 | 対策 | 優先度 |
|------|------|--------|
| 写真なりすまし | Liveness検証 | High |
| 動画なりすまし | Liveness検証 | High |
| セッションハイジャック | 1回限り使用 | Medium |
| リプレイ攻撃 | TTL + ステータス管理 | Medium |
| DDoS | レート制限 | Low |

### コンプライアンス

- **GDPR**: 顔データは90日後削除
- **個人情報保護法**: 暗号化保存
- **監査要件**: すべての検証を記録

---

## 参考資料

### AWS ドキュメント
- [Rekognition Liveness API](https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness.html)
- [Amplify UI Liveness](https://ui.docs.amplify.aws/react/connected-components/liveness)
- [Best Practices](https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness-best-practices.html)

### 内部ドキュメント
- `docs/INFRASTRUCTURE_ARCHITECTURE.md`
- `docs/COGNITO_SERVICE.md`
- `lambda/shared/error_handler.py`
- `lambda/shared/timeout_manager.py`

---

## 付録

### A. 環境変数一覧

```bash
# Liveness設定
LIVENESS_CONFIDENCE_THRESHOLD=90.0
LIVENESS_SESSION_TIMEOUT_MINUTES=10
LIVENESS_SESSIONS_TABLE=FaceAuth-LivenessSessions

# S3
FACE_AUTH_BUCKET=face-auth-images-{account}-{region}
LIVENESS_AUDIT_PREFIX=liveness-audit/

# AWS
AWS_REGION=ap-northeast-1
```

### B. CDK実装例

```python
# infrastructure/face_auth_stack.py (追加部分)

# DynamoDBテーブル
liveness_sessions_table = dynamodb.Table(
    self, "LivenessSessions",
    table_name="FaceAuth-LivenessSessions",
    partition_key=dynamodb.Attribute(
        name="session_id",
        type=dynamodb.AttributeType.STRING
    ),
    time_to_live_attribute="expires_at",
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
    removal_policy=RemovalPolicy.DESTROY
)

# GSI
liveness_sessions_table.add_global_secondary_index(
    index_name="EmployeeIdIndex",
    partition_key=dynamodb.Attribute(
        name="employee_id",
        type=dynamodb.AttributeType.STRING
    )
)

# Lambda関数
create_session_lambda = lambda_.Function(
    self, "CreateLivenessSession",
    function_name="FaceAuth-CreateLivenessSession",
    runtime=lambda_.Runtime.PYTHON_3_9,
    handler="create_session_handler.handler",
    code=lambda_.Code.from_asset("lambda/liveness"),
    timeout=Duration.seconds(10),
    memory_size=256,
    environment={
        "LIVENESS_CONFIDENCE_THRESHOLD": "90.0",
        "LIVENESS_SESSIONS_TABLE": liveness_sessions_table.table_name,
        "FACE_AUTH_BUCKET": face_auth_bucket.bucket_name
    }
)

# IAM権限
liveness_sessions_table.grant_read_write_data(create_session_lambda)
face_auth_bucket.grant_read_write(create_session_lambda)
create_session_lambda.add_to_role_policy(
    iam.PolicyStatement(
        actions=[
            "rekognition:CreateFaceLivenessSession",
            "rekognition:GetFaceLivenessSessionResults"
        ],
        resources=["*"]
    )
)
```

---

**Version:** 1.0  
**Last Updated:** 2026-02-02  
**Author:** Kiro AI Assistant  
**Status:** Ready for Review
