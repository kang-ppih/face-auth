# Liveness API 移行ガイド

**作成日:** 2026-02-04  
**バージョン:** 1.0  
**対象:** 開発者、運用チーム

---

## 概要

このドキュメントは、DetectFaces APIからRekognition Liveness APIへの移行手順、ロールバック手順、トラブルシューティングを説明します。

---

## 移行の背景

### なぜ移行するのか？

**現状の課題（DetectFaces API）:**
- 写真なりすまし攻撃に脆弱
- 動画なりすままし攻撃に脆弱
- 単純な顔検出のみ（生体検証なし）

**Liveness APIの利点:**
- 高度な生体検証（写真・動画なりすまし防御）
- 95%以上の防御率
- AWS管理のMLモデル（継続的改善）
- 監査ログの自動保存

---

## 移行戦略

### 段階的展開

```
Phase 1: 開発環境デプロイ
  ↓
Phase 2: オプトイン機能実装
  ↓
Phase 3: パイロットユーザーテスト（10-20人）
  ↓
Phase 4: 段階的展開（50%）
  ↓
Phase 5: 完全展開（100%）
  ↓
Phase 6: レガシーコード削除
```

---

## Phase 1: 開発環境デプロイ

### 前提条件

- [ ] AWS CDK v2インストール済み
- [ ] Python 3.9以上
- [ ] Node.js 18以上（フロントエンド）
- [ ] AWS認証情報設定済み

### デプロイ手順

#### 1. コードの最新化

```bash
# リポジトリを最新化
git pull origin main

# 依存関係インストール
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

#### 2. 環境変数設定

`.env`ファイルを作成：

```bash
# AWS設定
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# S3
FACE_AUTH_BUCKET=face-auth-images-123456789012-us-east-1

# DynamoDB
LIVENESS_SESSIONS_TABLE=FaceAuth-LivenessSessions

# Liveness設定
LIVENESS_CONFIDENCE_THRESHOLD=90.0
```

#### 3. CDKデプロイ

```bash
# CDK差分確認
cdk diff

# デプロイ実行
cdk deploy

# 出力確認
# - APIEndpoint
# - UserPoolId
# - S3BucketName
```

#### 4. 動作確認

```bash
# テスト実行
py -m pytest tests/test_liveness_service.py -v
py -m pytest tests/test_liveness_integration.py -v
py -m pytest tests/test_liveness_e2e.py -v

# すべてのテストが通過することを確認
```

#### 5. API動作確認

```bash
# セッション作成テスト
curl -X POST https://your-api-endpoint/liveness/session/create \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "E123456"}'

# レスポンス例:
# {
#   "session_id": "abc123-def456-ghi789",
#   "expires_at": "2026-02-04T10:30:00Z"
# }
```

---

## Phase 2: オプトイン機能実装

### 機能フラグ設定

環境変数で機能フラグを管理：

```python
# Lambda環境変数
ENABLE_LIVENESS_API=true  # Liveness API有効化
LIVENESS_ROLLOUT_PERCENTAGE=0  # 0-100（段階的展開用）
```

### コード例

```python
import os

def should_use_liveness_api(employee_id: str) -> bool:
    """
    Liveness APIを使用するか判定
    
    Args:
        employee_id: 社員ID
        
    Returns:
        True: Liveness API使用
        False: DetectFaces API使用（レガシー）
    """
    # 機能フラグ確認
    if os.getenv('ENABLE_LIVENESS_API', 'false').lower() != 'true':
        return False
    
    # ロールアウト割合確認
    rollout_percentage = int(os.getenv('LIVENESS_ROLLOUT_PERCENTAGE', '0'))
    if rollout_percentage == 0:
        return False
    
    # 社員IDのハッシュ値でロールアウト判定
    import hashlib
    hash_value = int(hashlib.md5(employee_id.encode()).hexdigest(), 16)
    return (hash_value % 100) < rollout_percentage
```

---

## Phase 3: パイロットユーザーテスト

### テストユーザー選定

**基準:**
- 10-20人
- 技術的知識がある
- フィードバックを提供できる
- 多様なデバイス・環境

### テスト手順

#### 1. テストユーザーに機能有効化

```python
# 特定ユーザーのみLiveness API使用
LIVENESS_PILOT_USERS=E123456,E234567,E345678
```

#### 2. メトリクス監視

```bash
# CloudWatch Logsで監視
aws logs tail /aws/lambda/FaceAuth-CreateLivenessSession --follow

# メトリクス確認
aws cloudwatch get-metric-statistics \
  --namespace FaceAuth/Liveness \
  --metric-name SuccessCount \
  --start-time 2026-02-04T00:00:00Z \
  --end-time 2026-02-04T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

#### 3. フィードバック収集

**質問項目:**
- Liveness検証は完了しましたか？
- 所要時間は許容範囲でしたか？
- エラーは発生しましたか？
- 改善点はありますか？

#### 4. 問題点の特定と修正

**よくある問題:**
- 照明不足 → フロントエンドでガイダンス改善
- カメラ品質 → 最小要件を明示
- タイムアウト → セッション有効期限延長検討

---

## Phase 4: 段階的展開（50%）

### 展開手順

#### 1. ロールアウト割合を50%に設定

```bash
# Lambda環境変数更新
aws lambda update-function-configuration \
  --function-name FaceAuth-Enrollment \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=50}
```

#### 2. 24時間監視

**監視項目:**
- 成功率 > 95%
- 平均信頼度 > 90%
- 平均検証時間 < 30秒
- エラー率 < 1%

#### 3. CloudWatchダッシュボード確認

```bash
# ダッシュボードURL
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=FaceAuth-Liveness
```

**確認項目:**
- SessionCount（SUCCESS vs FAILED）
- ConfidenceScore（平均値）
- VerificationTime（平均値）
- ErrorRate

#### 4. 問題発生時の対応

**問題:** 成功率 < 95%

**対応:**
1. CloudWatch Logsで詳細確認
2. 失敗理由を分析
3. 必要に応じてロールバック

---

## Phase 5: 完全展開（100%）

### 展開手順

#### 1. ロールアウト割合を100%に設定

```bash
aws lambda update-function-configuration \
  --function-name FaceAuth-Enrollment \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=100}
```

#### 2. 1週間監視

**成功基準:**
- 成功率 > 95%
- 平均検証時間 < 20秒
- エラー率 < 1%
- ユーザー満足度 > 80%

#### 3. 最終報告書作成

**含める内容:**
- 移行前後の比較
- メトリクス分析
- ユーザーフィードバック
- 問題点と対応
- 今後の改善点

---

## Phase 6: レガシーコード削除

### 削除対象

#### 1. DetectFaces API呼び出し

**削除ファイル:**
- `lambda/shared/face_recognition_service.py` の `detect_liveness()` メソッド（旧実装）

#### 2. 不要な環境変数

```bash
# 削除する環境変数
FACE_DETECTION_CONFIDENCE_THRESHOLD  # 旧設定
```

#### 3. 不要なテスト

```bash
# 削除するテストファイル
tests/test_legacy_face_detection.py
```

### 削除手順

```bash
# 1. ブランチ作成
git checkout -b cleanup/remove-legacy-liveness

# 2. コード削除
# （手動で削除）

# 3. テスト実行
py -m pytest tests/ -v

# 4. コミット
git add .
git commit -m "chore: Remove legacy DetectFaces API code"

# 5. プッシュとPR作成
git push origin cleanup/remove-legacy-liveness
```

---

## ロールバック手順

### 緊急ロールバック（即座に実行）

#### 1. ロールアウト割合を0%に設定

```bash
# すべてのユーザーをDetectFaces APIに戻す
aws lambda update-function-configuration \
  --function-name FaceAuth-Enrollment \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=0}

# 他のLambda関数も同様に更新
aws lambda update-function-configuration \
  --function-name FaceAuth-FaceLogin \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=0}

aws lambda update-function-configuration \
  --function-name FaceAuth-EmergencyAuth \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=0}

aws lambda update-function-configuration \
  --function-name FaceAuth-ReEnrollment \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=0}
```

#### 2. 動作確認

```bash
# API動作確認
curl -X POST https://your-api-endpoint/auth/enroll \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "E123456", ...}'

# レスポンスが正常であることを確認
```

#### 3. ログ確認

```bash
# エラーが解消されたことを確認
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow
```

---

### 完全ロールバック（CDKスタック削除）

**注意:** Liveness関連リソースをすべて削除します。

```bash
# 1. バックアップ確認
aws dynamodb describe-table --table-name FaceAuth-LivenessSessions
aws s3 ls s3://face-auth-images-123456789012-us-east-1/liveness-audit/

# 2. CDKスタック更新（Liveness関連リソース削除）
# infrastructure/face_auth_stack.py を編集してLiveness関連コードをコメントアウト

# 3. デプロイ
cdk deploy

# 4. 動作確認
py -m pytest tests/ --ignore=tests/test_liveness* -v
```

---

## トラブルシューティング

### 問題1: セッション作成エラー急増

**症状:**
```
CloudWatch Alarm: FaceAuth-Liveness-SessionCreationErrors
```

**原因:**
- Rekognition APIクォータ超過
- IAM権限不足
- S3バケットアクセス権限不足

**対応:**
```bash
# 1. CloudWatch Logsで詳細確認
aws logs filter-log-events \
  --log-group-name /aws/lambda/FaceAuth-CreateLivenessSession \
  --filter-pattern "ERROR"

# 2. Rekognitionクォータ確認
aws service-quotas get-service-quota \
  --service-code rekognition \
  --quota-code L-XXXXXXXX

# 3. 必要に応じてクォータ引き上げリクエスト
aws service-quotas request-service-quota-increase \
  --service-code rekognition \
  --quota-code L-XXXXXXXX \
  --desired-value 10000
```

---

### 問題2: 成功率低下

**症状:**
```
CloudWatch Alarm: FaceAuth-Liveness-LowSuccessRate
```

**原因:**
- ユーザー環境の問題（照明、カメラ品質）
- 信頼度閾値が高すぎる
- フロントエンドのガイダンス不足

**対応:**
```bash
# 1. 失敗理由を分析
aws logs filter-log-events \
  --log-group-name /aws/lambda/FaceAuth-GetLivenessResult \
  --filter-pattern "is_live=False"

# 2. 信頼度分布を確認
aws cloudwatch get-metric-statistics \
  --namespace FaceAuth/Liveness \
  --metric-name ConfidenceScore \
  --start-time 2026-02-04T00:00:00Z \
  --end-time 2026-02-04T23:59:59Z \
  --period 3600 \
  --statistics Average,Minimum,Maximum

# 3. 必要に応じて閾値調整（慎重に）
# LIVENESS_CONFIDENCE_THRESHOLD=85.0  # 90.0 → 85.0
```

---

### 問題3: 検証時間超過

**症状:**
```
CloudWatch Alarm: FaceAuth-Liveness-SlowVerification
```

**原因:**
- Rekognition API応答遅延
- DynamoDB書き込み遅延
- Lambda関数のコールドスタート

**対応:**
```bash
# 1. Lambda実行時間を確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=FaceAuth-GetLivenessResult \
  --start-time 2026-02-04T00:00:00Z \
  --end-time 2026-02-04T23:59:59Z \
  --period 300 \
  --statistics Average,Maximum

# 2. プロビジョニング済み同時実行数を設定（コールドスタート削減）
aws lambda put-provisioned-concurrency-config \
  --function-name FaceAuth-GetLivenessResult \
  --provisioned-concurrent-executions 5

# 3. Lambda メモリ増加（処理速度向上）
aws lambda update-function-configuration \
  --function-name FaceAuth-GetLivenessResult \
  --memory-size 512  # 256 → 512
```

---

## チェックリスト

### デプロイ前

- [ ] すべてのテストが通過
- [ ] CDK差分確認
- [ ] 環境変数設定確認
- [ ] IAM権限確認
- [ ] ロールバック手順確認

### デプロイ後

- [ ] API動作確認
- [ ] CloudWatchメトリクス確認
- [ ] CloudWatchアラーム設定確認
- [ ] ログ出力確認
- [ ] フロントエンド動作確認

### パイロットテスト前

- [ ] テストユーザー選定
- [ ] フィードバックフォーム準備
- [ ] 監視ダッシュボード準備
- [ ] エスカレーション手順確認

### 完全展開前

- [ ] パイロットテスト完了
- [ ] すべての問題解決
- [ ] ステークホルダー承認
- [ ] ロールバック手順再確認

---

## 参考資料

- [Liveness Service 技術ドキュメント](./LIVENESS_SERVICE.md)
- [Liveness Operations Manual](./LIVENESS_OPERATIONS.md)
- [AWS Rekognition Face Liveness](https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness.html)
- [CDK Deployment Guide](../DEPLOYMENT_GUIDE.md)

---

## サポート

**問題が発生した場合:**
1. CloudWatch Logsで詳細確認
2. このドキュメントのトラブルシューティングセクション参照
3. 開発チームに連絡

**連絡先:**
- Email: face-auth-dev@company.com
- Slack: #face-auth-support

---

**最終更新:** 2026-02-04  
**作成者:** Face-Auth Development Team  
**バージョン:** 1.0
