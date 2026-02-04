# Liveness Operations Manual - 運用手順書

**作成日:** 2026-02-04  
**バージョン:** 1.0  
**対象:** 運用チーム、SRE

---

## 概要

このドキュメントは、Rekognition Liveness APIの日常運用、監視、アラート対応、トラブルシューティングの手順を説明します。

---

## 日常運用

### 毎日の確認事項

#### 1. CloudWatchダッシュボード確認

**URL:** `https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=FaceAuth-Liveness`

**確認項目:**
- [ ] セッション作成数（正常範囲内か）
- [ ] 成功率（> 95%）
- [ ] 平均信頼度（> 90%）
- [ ] 平均検証時間（< 30秒）
- [ ] エラー数（< 1%）

#### 2. CloudWatchアラーム確認

```bash
# アラーム状態確認
aws cloudwatch describe-alarms \
  --alarm-name-prefix "FaceAuth-Liveness" \
  --state-value ALARM

# アラームがある場合は対応
```

#### 3. Lambda関数ヘルスチェック

```bash
# Lambda関数のエラー率確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=FaceAuth-CreateLivenessSession \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

---

### 週次の確認事項

#### 1. コスト分析

```bash
# Rekognition Liveness APIコスト確認
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '7 days ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter file://cost-filter.json

# cost-filter.json:
# {
#   "Dimensions": {
#     "Key": "SERVICE",
#     "Values": ["Amazon Rekognition"]
#   }
# }
```

**目標コスト:** $400-$450/月

#### 2. S3ストレージ使用量確認

```bash
# liveness-audit/ ディレクトリのサイズ確認
aws s3 ls s3://face-auth-images-123456789012-us-east-1/liveness-audit/ \
  --recursive --summarize | grep "Total Size"
```

#### 3. DynamoDBテーブル確認

```bash
# LivenessSessionsテーブルのアイテム数確認
aws dynamodb describe-table \
  --table-name FaceAuth-LivenessSessions \
  --query 'Table.ItemCount'
```

---

### 月次の確認事項

#### 1. パフォーマンスレポート作成

**含める内容:**
- 総セッション数
- 成功率の推移
- 平均信頼度の推移
- 平均検証時間の推移
- エラー率の推移
- コスト分析

#### 2. セキュリティ監査

```bash
# IAM権限レビュー
aws iam get-role-policy \
  --role-name FaceAuthLambdaExecutionRole \
  --policy-name FaceAuthLambdaPolicy

# S3バケットポリシー確認
aws s3api get-bucket-policy \
  --bucket face-auth-images-123456789012-us-east-1
```

#### 3. バックアップ確認

```bash
# DynamoDBバックアップ確認
aws dynamodb list-backups \
  --table-name FaceAuth-LivenessSessions

# S3バージョニング確認
aws s3api get-bucket-versioning \
  --bucket face-auth-images-123456789012-us-east-1
```

---

## 監視

### CloudWatchメトリクス

#### カスタムメトリクス

**Namespace:** `FaceAuth/Liveness`

| メトリクス | 正常範囲 | アラート閾値 |
|-----------|---------|-------------|
| SessionCreated | 100-1000/日 | - |
| SuccessCount | > 95% | < 95% |
| ConfidenceScore | > 90% | < 92% |
| VerificationTime | < 30秒 | > 30秒 |
| VerificationError | < 1% | > 1% |

#### Lambda メトリクス

| メトリクス | 正常範囲 | アラート閾値 |
|-----------|---------|-------------|
| Invocations | 100-1000/日 | - |
| Errors | < 1% | > 5 errors/5min |
| Duration | < 10秒（Create）<br>< 15秒（GetResult） | > 9秒<br>> 14秒 |
| Throttles | 0 | > 0 |

---

### CloudWatchアラーム一覧

| アラーム名 | 条件 | 重要度 | 対応時間 |
|-----------|------|--------|---------|
| FaceAuth-Liveness-LowSuccessRate | 成功率 < 95% | 高 | 30分以内 |
| FaceAuth-Liveness-LowConfidence | 平均信頼度 < 92% | 中 | 1時間以内 |
| FaceAuth-Liveness-SlowVerification | 検証時間 > 30秒 | 中 | 1時間以内 |
| FaceAuth-Liveness-HighErrorRate | エラー率 > 1% | 高 | 30分以内 |
| FaceAuth-CreateLivenessSession-Errors | エラー > 5 | 高 | 30分以内 |
| FaceAuth-GetLivenessResult-Errors | エラー > 5 | 高 | 30分以内 |
| FaceAuth-CreateLivenessSession-Timeouts | 実行時間 > 9秒 | 中 | 1時間以内 |
| FaceAuth-GetLivenessResult-Timeouts | 実行時間 > 14秒 | 中 | 1時間以内 |

---

## アラート対応手順

### アラート1: 成功率低下

**アラーム:** `FaceAuth-Liveness-LowSuccessRate`  
**重要度:** 高  
**対応時間:** 30分以内

#### 対応手順

**1. 現状確認**

```bash
# 直近1時間の成功率確認
aws cloudwatch get-metric-statistics \
  --namespace FaceAuth/Liveness \
  --metric-name SuccessCount \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

aws cloudwatch get-metric-statistics \
  --namespace FaceAuth/Liveness \
  --metric-name FailureCount \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**2. 失敗理由分析**

```bash
# 失敗ログ確認
aws logs filter-log-events \
  --log-group-name /aws/lambda/FaceAuth-GetLivenessResult \
  --filter-pattern "is_live=False" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --limit 50
```

**3. 原因特定**

**よくある原因:**
- ユーザー環境の問題（照明不足、カメラ品質低下）
- Rekognition APIの問題
- 信頼度閾値が高すぎる

**4. 対応**

**ユーザー環境の問題:**
- フロントエンドでガイダンス強化
- サポートチームに連絡してユーザー教育

**Rekognition APIの問題:**
- AWS Service Health Dashboard確認
- AWS Supportに問い合わせ

**信頼度閾値の問題:**
- 一時的に閾値を下げる（85%）
- 開発チームに相談

**5. エスカレーション**

30分以内に解決しない場合:
- 開発チームリーダーに連絡
- インシデント管理システムに登録

---

### アラート2: エラー率上昇

**アラーム:** `FaceAuth-Liveness-HighErrorRate`  
**重要度:** 高  
**対応時間:** 30分以内

#### 対応手順

**1. エラーログ確認**

```bash
# エラーログ取得
aws logs filter-log-events \
  --log-group-name /aws/lambda/FaceAuth-CreateLivenessSession \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --limit 50

aws logs filter-log-events \
  --log-group-name /aws/lambda/FaceAuth-GetLivenessResult \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000 \
  --limit 50
```

**2. エラー種別分析**

**よくあるエラー:**
- `SessionNotFoundError`: セッションが存在しない
- `SessionExpiredError`: セッション期限切れ
- `ClientError`: AWS API呼び出しエラー
- `LivenessServiceError`: 一般的なサービスエラー

**3. 対応**

**SessionNotFoundError/SessionExpiredError:**
- 正常な動作（ユーザーがタイムアウト）
- 頻度が高い場合はセッション有効期限延長検討

**ClientError:**
- IAM権限確認
- Rekognition APIクォータ確認
- AWS Service Health Dashboard確認

**LivenessServiceError:**
- CloudWatch Logsで詳細確認
- 必要に応じてロールバック

**4. 緊急対応**

エラー率が5%を超える場合:
```bash
# Liveness APIを無効化（DetectFaces APIに戻す）
aws lambda update-function-configuration \
  --function-name FaceAuth-Enrollment \
  --environment Variables={LIVENESS_ROLLOUT_PERCENTAGE=0}
```

---

### アラート3: 検証時間超過

**アラーム:** `FaceAuth-Liveness-SlowVerification`  
**重要度:** 中  
**対応時間:** 1時間以内

#### 対応手順

**1. 実行時間確認**

```bash
# Lambda実行時間分析
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=FaceAuth-GetLivenessResult \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum,Minimum
```

**2. 原因特定**

**よくある原因:**
- Rekognition API応答遅延
- DynamoDB書き込み遅延
- Lambda コールドスタート

**3. 対応**

**Rekognition API遅延:**
- AWS Service Health Dashboard確認
- AWS Supportに問い合わせ

**DynamoDB遅延:**
- DynamoDBスロットリング確認
- 必要に応じてキャパシティ増加

**Lambda コールドスタート:**
```bash
# プロビジョニング済み同時実行数設定
aws lambda put-provisioned-concurrency-config \
  --function-name FaceAuth-GetLivenessResult \
  --provisioned-concurrent-executions 5
```

---

### アラート4: Lambda エラー

**アラーム:** `FaceAuth-CreateLivenessSession-Errors`  
**重要度:** 高  
**対応時間:** 30分以内

#### 対応手順

**1. エラー詳細確認**

```bash
# 最新のエラーログ取得
aws logs tail /aws/lambda/FaceAuth-CreateLivenessSession \
  --follow \
  --filter-pattern "ERROR"
```

**2. Lambda関数状態確認**

```bash
# Lambda関数設定確認
aws lambda get-function-configuration \
  --function-name FaceAuth-CreateLivenessSession

# 環境変数確認
aws lambda get-function-configuration \
  --function-name FaceAuth-CreateLivenessSession \
  --query 'Environment.Variables'
```

**3. 対応**

**IAM権限エラー:**
```bash
# IAM権限確認
aws iam get-role-policy \
  --role-name FaceAuthLambdaExecutionRole \
  --policy-name FaceAuthLambdaPolicy
```

**環境変数エラー:**
```bash
# 環境変数修正
aws lambda update-function-configuration \
  --function-name FaceAuth-CreateLivenessSession \
  --environment Variables={LIVENESS_SESSIONS_TABLE=FaceAuth-LivenessSessions,...}
```

**コードエラー:**
- 開発チームに連絡
- 必要に応じてロールバック

---

## トラブルシューティング

### 問題: セッション作成が遅い

**症状:**
- セッション作成に5秒以上かかる

**診断:**
```bash
# Lambda実行時間確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=FaceAuth-CreateLivenessSession \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

**解決策:**
1. Lambda メモリ増加（256MB → 512MB）
2. プロビジョニング済み同時実行数設定
3. VPC設定確認（NAT Gateway遅延）

---

### 問題: DynamoDB書き込みエラー

**症状:**
```
ClientError: ProvisionedThroughputExceededException
```

**診断:**
```bash
# DynamoDBスロットリング確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name UserErrors \
  --dimensions Name=TableName,Value=FaceAuth-LivenessSessions \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**解決策:**
```bash
# オンデマンドモードに変更
aws dynamodb update-table \
  --table-name FaceAuth-LivenessSessions \
  --billing-mode PAY_PER_REQUEST
```

---

### 問題: S3アクセスエラー

**症状:**
```
ClientError: AccessDenied
```

**診断:**
```bash
# S3バケットポリシー確認
aws s3api get-bucket-policy \
  --bucket face-auth-images-123456789012-us-east-1

# IAM権限確認
aws iam get-role-policy \
  --role-name FaceAuthLambdaExecutionRole \
  --policy-name FaceAuthLambdaPolicy
```

**解決策:**
- IAMポリシーにS3権限追加
- S3バケットポリシー更新

---

## コスト管理

### コスト監視

#### 日次コスト確認

```bash
# 昨日のRekognitionコスト
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -d '1 day ago' +%Y-%m-%d),End=$(date -u +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter file://cost-filter.json
```

#### 月次コスト予測

```bash
# 今月のコスト予測
aws ce get-cost-forecast \
  --time-period Start=$(date -u +%Y-%m-%d),End=$(date -u -d '+1 month' +%Y-%m-%d) \
  --metric BLENDED_COST \
  --granularity MONTHLY
```

### コスト最適化

#### 1. セッション数削減

**不要なセッション作成を防ぐ:**
- フロントエンドでバリデーション強化
- 重複セッション作成防止

#### 2. S3ライフサイクルポリシー確認

```bash
# ライフサイクルポリシー確認
aws s3api get-bucket-lifecycle-configuration \
  --bucket face-auth-images-123456789012-us-east-1
```

**設定:**
- liveness-audit/: 90日後削除

#### 3. DynamoDB TTL確認

```bash
# TTL設定確認
aws dynamodb describe-time-to-live \
  --table-name FaceAuth-LivenessSessions
```

**設定:**
- expires_at: 10分後自動削除

---

## バックアップとリカバリ

### DynamoDBバックアップ

#### オンデマンドバックアップ作成

```bash
# バックアップ作成
aws dynamodb create-backup \
  --table-name FaceAuth-LivenessSessions \
  --backup-name FaceAuth-LivenessSessions-$(date +%Y%m%d)
```

#### バックアップからリストア

```bash
# バックアップ一覧確認
aws dynamodb list-backups \
  --table-name FaceAuth-LivenessSessions

# リストア実行
aws dynamodb restore-table-from-backup \
  --target-table-name FaceAuth-LivenessSessions-Restored \
  --backup-arn arn:aws:dynamodb:us-east-1:123456789012:table/FaceAuth-LivenessSessions/backup/01234567890123-abcdefgh
```

### S3バックアップ

#### S3バージョニング有効化

```bash
# バージョニング有効化
aws s3api put-bucket-versioning \
  --bucket face-auth-images-123456789012-us-east-1 \
  --versioning-configuration Status=Enabled
```

#### 削除されたオブジェクトの復元

```bash
# バージョン一覧確認
aws s3api list-object-versions \
  --bucket face-auth-images-123456789012-us-east-1 \
  --prefix liveness-audit/

# 特定バージョンを復元
aws s3api copy-object \
  --bucket face-auth-images-123456789012-us-east-1 \
  --copy-source face-auth-images-123456789012-us-east-1/liveness-audit/abc123/audit-log.json?versionId=VERSION_ID \
  --key liveness-audit/abc123/audit-log.json
```

---

## セキュリティ

### セキュリティ監査

#### IAM権限レビュー

```bash
# Lambda実行ロール確認
aws iam get-role \
  --role-name FaceAuthLambdaExecutionRole

# アタッチされたポリシー確認
aws iam list-attached-role-policies \
  --role-name FaceAuthLambdaExecutionRole

# インラインポリシー確認
aws iam list-role-policies \
  --role-name FaceAuthLambdaExecutionRole
```

#### S3バケットセキュリティ

```bash
# パブリックアクセスブロック確認
aws s3api get-public-access-block \
  --bucket face-auth-images-123456789012-us-east-1

# 暗号化設定確認
aws s3api get-bucket-encryption \
  --bucket face-auth-images-123456789012-us-east-1
```

#### DynamoDBセキュリティ

```bash
# 暗号化設定確認
aws dynamodb describe-table \
  --table-name FaceAuth-LivenessSessions \
  --query 'Table.SSEDescription'

# ポイントインタイムリカバリ確認
aws dynamodb describe-continuous-backups \
  --table-name FaceAuth-LivenessSessions
```

---

## エスカレーション

### エスカレーションフロー

```
Level 1: 運用チーム（初動対応）
  ↓ 30分以内に解決しない
Level 2: 開発チームリーダー
  ↓ 1時間以内に解決しない
Level 3: システムアーキテクト
  ↓ 2時間以内に解決しない
Level 4: CTO / AWS Support
```

### 連絡先

| レベル | 担当 | 連絡先 |
|--------|------|--------|
| Level 1 | 運用チーム | ops@company.com<br>Slack: #ops |
| Level 2 | 開発リーダー | dev-lead@company.com<br>Slack: #face-auth-dev |
| Level 3 | アーキテクト | architect@company.com<br>Phone: XXX-XXXX-XXXX |
| Level 4 | CTO | cto@company.com<br>AWS Support: Premium |

---

## 参考資料

- [Liveness Service 技術ドキュメント](./LIVENESS_SERVICE.md)
- [Liveness Migration Guide](./LIVENESS_MIGRATION_GUIDE.md)
- [AWS Rekognition Documentation](https://docs.aws.amazon.com/rekognition/)
- [CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)

---

**最終更新:** 2026-02-04  
**作成者:** Face-Auth Operations Team  
**バージョン:** 1.0
