# Phase 8: 段階的展開 - デプロイチェックリスト

**作成日:** 2026-02-04  
**ステータス:** 準備完了  
**対象:** Task 28-33

---

## 📋 Phase 8 概要

Phase 8は、Liveness API機能を実際の環境にデプロイし、段階的に展開するフェーズです。

### タスク一覧

- [ ] Task 28: 開発環境デプロイ
- [ ] Task 29: オプトイン機能実装
- [ ] Task 30: パイロットユーザーテスト
- [ ] Task 31: 段階的展開（50%）
- [ ] Task 32: 完全展開（100%）
- [ ] Task 33: レガシーコード削除

---

## Task 28: 開発環境デプロイ

### 前提条件チェック

#### 環境準備

- [ ] AWS CLI設定済み（`aws configure`）
- [ ] AWS CDK v2インストール済み（`npm install -g aws-cdk`）
- [ ] Python 3.9以上インストール済み
- [ ] Node.js 18以上インストール済み
- [ ] Git最新版にプル済み（`git pull origin main`）

#### 認証情報確認

```bash
# AWS認証情報確認
aws sts get-caller-identity

# 出力例:
# {
#     "UserId": "AIDAXXXXXXXXXXXXXXXXX",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-user"
# }
```

#### 環境変数設定

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

# 機能フラグ（初期値）
ENABLE_LIVENESS_API=true
LIVENESS_ROLLOUT_PERCENTAGE=0  # 0%から開始
```

---

### デプロイ前テスト

#### 1. すべてのテスト実行

```bash
# 単体テスト
py -m pytest tests/test_liveness_service.py -v
py -m pytest tests/test_create_liveness_session.py -v
py -m pytest tests/test_get_liveness_result.py -v

# 統合テスト
py -m pytest tests/test_liveness_integration.py -v

# E2Eテスト
py -m pytest tests/test_liveness_e2e.py -v

# すべてのテスト（AD Connector除く）
py -m pytest tests/ --ignore=tests/test_ad_connector.py -v
```

**期待結果:** すべてのテストが通過（45/45）

#### 2. コード品質チェック

```bash
# Type hints確認（オプション）
# mypy lambda/shared/liveness_service.py

# Linting（オプション）
# pylint lambda/shared/liveness_service.py
```

---

### CDKデプロイ

#### 1. CDK差分確認

```bash
# スタック差分確認
cdk diff

# 確認項目:
# - LivenessSessionsテーブル作成
# - CreateLivenessSession Lambda作成
# - GetLivenessResult Lambda作成
# - CloudWatchアラーム作成（9個）
# - API Gatewayエンドポイント追加（2個）
```

**重要な変更:**
- 新規DynamoDBテーブル: `FaceAuth-LivenessSessions`
- 新規Lambda関数: `FaceAuth-CreateLivenessSession`, `FaceAuth-GetLivenessResult`
- 新規APIエンドポイント: `/liveness/session/create`, `/liveness/session/{sessionId}/result`
- 新規CloudWatchアラーム: 9個

#### 2. デプロイ実行

```bash
# デプロイ実行
cdk deploy

# または、承認なしで実行
cdk deploy --require-approval never
```

**デプロイ時間:** 約5-10分

#### 3. デプロイ結果確認

デプロイ完了後、以下の出力を確認：

```
Outputs:
FaceAuthStack.APIEndpoint = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/
FaceAuthStack.UserPoolId = us-east-1_XXXXXXXXX
FaceAuthStack.S3BucketName = face-auth-images-123456789012-us-east-1
...
```

---

### デプロイ後検証

#### 1. DynamoDBテーブル確認

```bash
# LivenessSessionsテーブル確認
aws dynamodb describe-table --table-name FaceAuth-LivenessSessions

# 確認項目:
# - TableStatus: ACTIVE
# - KeySchema: session_id (HASH)
# - GlobalSecondaryIndexes: EmployeeIdIndex
# - TimeToLiveDescription: Enabled (expires_at)
```

#### 2. Lambda関数確認

```bash
# CreateLivenessSession Lambda確認
aws lambda get-function --function-name FaceAuth-CreateLivenessSession

# GetLivenessResult Lambda確認
aws lambda get-function --function-name FaceAuth-GetLivenessResult

# 確認項目:
# - State: Active
# - Runtime: python3.9
# - Timeout: 10秒（Create）、15秒（GetResult）
# - Environment Variables: LIVENESS_SESSIONS_TABLE, FACE_AUTH_BUCKET
```

#### 3. S3バケット確認

```bash
# liveness-audit/ ディレクトリ確認
aws s3 ls s3://face-auth-images-123456789012-us-east-1/liveness-audit/

# ライフサイクルポリシー確認
aws s3api get-bucket-lifecycle-configuration \
  --bucket face-auth-images-123456789012-us-east-1
```

#### 4. API Gatewayエンドポイント確認

```bash
# API確認
aws apigateway get-rest-apis

# エンドポイント確認
curl -X POST https://your-api-endpoint/liveness/session/create \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "E123456"}'

# 期待レスポンス:
# {
#   "session_id": "abc123-def456-ghi789",
#   "expires_at": "2026-02-04T10:30:00Z"
# }
```

#### 5. CloudWatchアラーム確認

```bash
# アラーム一覧確認
aws cloudwatch describe-alarms --alarm-name-prefix "FaceAuth-Liveness"

# 確認項目:
# - 9個のアラームが作成されている
# - StateValue: OK（初期状態）
```

#### 6. CloudWatchメトリクス確認

```bash
# メトリクス確認（デプロイ後、数分待つ）
aws cloudwatch list-metrics --namespace FaceAuth/Liveness

# 期待結果:
# - SessionCreated
# - SuccessCount
# - FailureCount
# - ConfidenceScore
# - VerificationTime
# など
```

---

### 統合テスト実行

#### 1. セッション作成テスト

```bash
# セッション作成
curl -X POST https://your-api-endpoint/liveness/session/create \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "E123456"}'

# レスポンス保存
# session_id: abc123-def456-ghi789
```

#### 2. セッション結果取得テスト

```bash
# 結果取得（セッション作成後、ユーザーがLiveness検証を完了した後）
curl -X GET https://your-api-endpoint/liveness/session/abc123-def456-ghi789/result

# 期待レスポンス:
# {
#   "session_id": "abc123-def456-ghi789",
#   "is_live": true,
#   "confidence": 95.5,
#   "status": "SUCCESS"
# }
```

#### 3. フロントエンド統合テスト

```bash
# フロントエンドビルド
cd frontend
npm install
npm run build

# 環境変数設定
# .env.production:
# REACT_APP_API_ENDPOINT=https://your-api-endpoint/prod
# REACT_APP_USER_POOL_ID=us-east-1_XXXXXXXXX
# REACT_APP_USER_POOL_CLIENT_ID=your-client-id

# ローカルテスト
npm start
```

---

### トラブルシューティング

#### 問題1: CDKデプロイ失敗

**症状:**
```
Error: Stack FaceAuthStack failed to deploy
```

**対応:**
```bash
# スタック状態確認
aws cloudformation describe-stacks --stack-name FaceAuthStack

# スタックイベント確認
aws cloudformation describe-stack-events --stack-name FaceAuthStack

# ロールバック
cdk destroy
cdk deploy
```

#### 問題2: Lambda関数エラー

**症状:**
```
Internal Server Error
```

**対応:**
```bash
# CloudWatch Logsで詳細確認
aws logs tail /aws/lambda/FaceAuth-CreateLivenessSession --follow

# 環境変数確認
aws lambda get-function-configuration \
  --function-name FaceAuth-CreateLivenessSession \
  --query 'Environment.Variables'
```

#### 問題3: API Gatewayアクセスエラー

**症状:**
```
403 Forbidden
```

**対応:**
```bash
# CORS設定確認
# API Gatewayコンソールで確認

# IP制限確認
# allowed_ips設定を確認
```

---

## Task 29: オプトイン機能実装

### 機能フラグ設定

#### 1. Lambda環境変数更新

```bash
# すべてのLambda関数に機能フラグを追加
aws lambda update-function-configuration \
  --function-name FaceAuth-Enrollment \
  --environment Variables={ENABLE_LIVENESS_API=true,LIVENESS_ROLLOUT_PERCENTAGE=0}

aws lambda update-function-configuration \
  --function-name FaceAuth-FaceLogin \
  --environment Variables={ENABLE_LIVENESS_API=true,LIVENESS_ROLLOUT_PERCENTAGE=0}

aws lambda update-function-configuration \
  --function-name FaceAuth-EmergencyAuth \
  --environment Variables={ENABLE_LIVENESS_API=true,LIVENESS_ROLLOUT_PERCENTAGE=0}

aws lambda update-function-configuration \
  --function-name FaceAuth-ReEnrollment \
  --environment Variables={ENABLE_LIVENESS_API=true,LIVENESS_ROLLOUT_PERCENTAGE=0}
```

#### 2. 動作確認

```bash
# 環境変数確認
aws lambda get-function-configuration \
  --function-name FaceAuth-Enrollment \
  --query 'Environment.Variables'

# 期待結果:
# {
#   "ENABLE_LIVENESS_API": "true",
#   "LIVENESS_ROLLOUT_PERCENTAGE": "0"
# }
```

---

## Task 30: パイロットユーザーテスト

### テストユーザー選定

**基準:**
- 10-20人
- 技術的知識がある
- フィードバックを提供できる
- 多様なデバイス・環境

**選定リスト:**
```
E123456 - 山田太郎（開発チーム）
E234567 - 佐藤花子（QAチーム）
E345678 - 鈴木一郎（運用チーム）
...
```

### テスト手順

#### 1. パイロットユーザーに機能有効化

```bash
# 環境変数でパイロットユーザーを指定
aws lambda update-function-configuration \
  --function-name FaceAuth-Enrollment \
  --environment Variables={LIVENESS_PILOT_USERS="E123456,E234567,E345678"}
```

#### 2. テスト実施

- [ ] 各ユーザーがEnrollment実行
- [ ] Liveness検証完了確認
- [ ] ログイン成功確認
- [ ] フィードバック収集

#### 3. メトリクス監視

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

---

## Task 31-32: 段階的展開

### 50%展開（Task 31）

```bash
# ロールアウト割合を50%に設定
aws lambda update-function-configuration \
  --function-name FaceAuth-Enrollment \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=50}
```

**監視期間:** 24時間

### 100%展開（Task 32）

```bash
# ロールアウト割合を100%に設定
aws lambda update-function-configuration \
  --function-name FaceAuth-Enrollment \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=100}
```

**監視期間:** 1週間

---

## Task 33: レガシーコード削除

### 削除対象

- [ ] DetectFaces API呼び出しコード
- [ ] 不要な環境変数
- [ ] 不要なテスト

### 削除手順

```bash
# ブランチ作成
git checkout -b cleanup/remove-legacy-liveness

# コード削除（手動）

# テスト実行
py -m pytest tests/ -v

# コミット
git add .
git commit -m "chore: Remove legacy DetectFaces API code"

# プッシュ
git push origin cleanup/remove-legacy-liveness
```

---

## 📊 成功基準

### デプロイ成功基準

- [ ] すべてのテストが通過（45/45）
- [ ] CDKデプロイ成功
- [ ] すべてのリソースが作成されている
- [ ] API動作確認完了
- [ ] CloudWatchメトリクス収集開始

### パイロットテスト成功基準

- [ ] 成功率 > 95%
- [ ] 平均信頼度 > 90%
- [ ] 平均検証時間 < 30秒
- [ ] エラー率 < 1%
- [ ] ユーザーフィードバック良好

### 完全展開成功基準

- [ ] 成功率 > 95%（1週間）
- [ ] 平均検証時間 < 20秒
- [ ] エラー率 < 1%
- [ ] ユーザー満足度 > 80%
- [ ] コスト < $500/月

---

## 🚨 ロールバック手順

### 緊急ロールバック

```bash
# ロールアウト割合を0%に設定
aws lambda update-function-configuration \
  --function-name FaceAuth-Enrollment \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=0}
```

### 完全ロールバック

```bash
# CDKスタック削除
cdk destroy

# 再デプロイ（Liveness機能なし）
# infrastructure/face_auth_stack.py を編集
cdk deploy
```

---

## 📝 チェックリスト

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

## 📚 参考資料

- [Liveness Migration Guide](docs/LIVENESS_MIGRATION_GUIDE.md)
- [Liveness Operations Manual](docs/LIVENESS_OPERATIONS.md)
- [Liveness Service Documentation](docs/LIVENESS_SERVICE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)

---

**作成者:** Face-Auth Development Team  
**最終更新:** 2026-02-04  
**バージョン:** 1.0
