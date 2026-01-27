# Face-Auth IdP System - クイックスタート テストガイド

## 🚀 すぐに始める

システムのデプロイが完了しました。このガイドに従って、各機能をテストしてください。

---

## 📍 アクセス情報

### フロントエンド
```
https://d3ecve2syriq5q.cloudfront.net
```

### API エンドポイント
```
https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/
```

### Cognito 情報
- **User Pool ID:** `ap-northeast-1_ikSWDeIew`
- **Client ID:** `6u4blhui7p35ra4p882srvrpod`

---

## ⚠️ 重要な注意事項

### IP制限について

現在、以下のIP範囲からのみアクセス可能です：
```
210.128.54.64/27
```

**許可されていないIPからアクセスすると403エラーが発生します。**

別のIPアドレスからアクセスする必要がある場合：

1. `.env`ファイルを編集
```bash
ALLOWED_IPS=210.128.54.64/27,<新しいIP>/32
```

2. CDK再デプロイ
```bash
npx cdk deploy --profile dev --context allowed_ips="210.128.54.64/27,<新しいIP>/32"
```

---

## 🧪 テストシナリオ

### シナリオ1: 社員登録フロー

**目的:** 新規社員の顔データを登録する

**手順:**

1. **フロントエンドにアクセス**
   ```
   https://d3ecve2syriq5q.cloudfront.net
   ```

2. **「社員登録」ボタンをクリック**

3. **社員証画像をアップロード**
   - 社員証の写真を撮影またはアップロード
   - OCRで社員ID、氏名、部署を自動抽出

4. **AD認証**
   - 抽出された情報でActive Directoryに照会
   - 社員情報の正当性を確認

5. **顔画像キャプチャ**
   - カメラで顔を撮影
   - Liveness検出（>90%信頼度）

6. **登録完了**
   - Rekognitionに顔データを登録
   - DynamoDBに社員情報を保存

**期待される結果:**
- ✅ 登録成功メッセージが表示される
- ✅ DynamoDB `FaceAuth-EmployeeFaces` テーブルにレコードが追加される
- ✅ Rekognition Collection `face-auth-employees` に顔データが登録される

**確認方法:**
```bash
# DynamoDBテーブル確認
aws dynamodb scan --table-name FaceAuth-EmployeeFaces --profile dev

# Rekognition Collection確認
aws rekognition list-faces --collection-id face-auth-employees --profile dev
```

---

### シナリオ2: 顔認証ログインフロー

**目的:** 登録済み社員が顔認証でログインする

**前提条件:** シナリオ1で社員登録が完了していること

**手順:**

1. **フロントエンドにアクセス**
   ```
   https://d3ecve2syriq5q.cloudfront.net
   ```

2. **「顔認証ログイン」ボタンをクリック**

3. **顔画像キャプチャ**
   - カメラで顔を撮影
   - Liveness検出（>90%信頼度）

4. **1:N 顔検索**
   - Rekognition Collectionで顔を検索
   - 類似度>90%の顔を特定

5. **セッション作成**
   - Cognitoでセッションを作成
   - JWTトークンを発行

6. **ログイン完了**
   - ダッシュボードまたはホーム画面に遷移

**期待される結果:**
- ✅ ログイン成功メッセージが表示される
- ✅ DynamoDB `FaceAuth-AuthSessions` テーブルにセッションが作成される
- ✅ `last_login` タイムスタンプが更新される

**確認方法:**
```bash
# セッションテーブル確認
aws dynamodb scan --table-name FaceAuth-AuthSessions --profile dev

# 社員テーブルのlast_login確認
aws dynamodb get-item \
  --table-name FaceAuth-EmployeeFaces \
  --key '{"employee_id": {"S": "<社員ID>"}}' \
  --profile dev
```

---

### シナリオ3: 緊急認証フロー

**目的:** 顔認証が使えない場合に社員証+ADパスワードでログインする

**手順:**

1. **フロントエンドにアクセス**
   ```
   https://d3ecve2syriq5q.cloudfront.net
   ```

2. **「緊急認証」ボタンをクリック**

3. **社員証画像をアップロード**
   - 社員証の写真を撮影またはアップロード
   - OCRで社員ID、氏名を抽出

4. **ADパスワード入力**
   - Active Directoryのパスワードを入力

5. **AD認証**
   - LDAPS経由でAD認証（10秒タイムアウト）
   - 認証成功後、セッション作成

6. **ログイン完了**
   - ダッシュボードまたはホーム画面に遷移

**期待される結果:**
- ✅ ログイン成功メッセージが表示される
- ✅ DynamoDB `FaceAuth-AuthSessions` テーブルにセッションが作成される
- ✅ 失敗した場合、S3 `logins/` に試行ログが保存される

**確認方法:**
```bash
# セッションテーブル確認
aws dynamodb scan --table-name FaceAuth-AuthSessions --profile dev

# 失敗ログ確認（失敗した場合）
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/logins/ --profile dev
```

---

### シナリオ4: 再登録フロー

**目的:** 既存社員の顔データを更新する

**前提条件:** シナリオ1で社員登録が完了していること

**手順:**

1. **フロントエンドにアクセス**
   ```
   https://d3ecve2syriq5q.cloudfront.net
   ```

2. **「再登録」ボタンをクリック**

3. **社員証画像をアップロード**
   - 社員証の写真を撮影またはアップロード
   - OCRで社員ID、氏名を抽出

4. **AD認証**
   - Active Directoryで本人確認

5. **古い顔データ削除**
   - Rekognition Collectionから古い顔データを削除

6. **新しい顔画像キャプチャ**
   - カメラで顔を撮影
   - Liveness検出（>90%信頼度）

7. **再登録完了**
   - Rekognitionに新しい顔データを登録
   - DynamoDBの`face_id`を更新

**期待される結果:**
- ✅ 再登録成功メッセージが表示される
- ✅ DynamoDB `FaceAuth-EmployeeFaces` テーブルの`face_id`が更新される
- ✅ Rekognition Collectionの顔データが更新される

**確認方法:**
```bash
# 社員テーブルのface_id確認
aws dynamodb get-item \
  --table-name FaceAuth-EmployeeFaces \
  --key '{"employee_id": {"S": "<社員ID>"}}' \
  --profile dev

# Rekognition Collection確認
aws rekognition list-faces --collection-id face-auth-employees --profile dev
```

---

### シナリオ5: ステータス確認

**目的:** 現在のセッション状態を確認する

**手順:**

1. **APIエンドポイントに直接リクエスト**
   ```bash
   curl -X GET https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
   ```

2. **レスポンス確認**
   ```json
   {
     "statusCode": 200,
     "body": {
       "status": "healthy",
       "timestamp": "2026-01-28T12:00:00Z"
     }
   }
   ```

**期待される結果:**
- ✅ 200 OK レスポンス
- ✅ システムステータスが返される

---

## 🔍 デバッグとログ確認

### Lambda関数のログ確認

```bash
# Enrollment Lambda
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev

# Face Login Lambda
aws logs tail /aws/lambda/FaceAuth-FaceLogin --follow --profile dev

# Emergency Auth Lambda
aws logs tail /aws/lambda/FaceAuth-EmergencyAuth --follow --profile dev

# Re-enrollment Lambda
aws logs tail /aws/lambda/FaceAuth-ReEnrollment --follow --profile dev

# Status Lambda
aws logs tail /aws/lambda/FaceAuth-Status --follow --profile dev
```

### API Gatewayのアクセスログ

```bash
aws logs tail /aws/apigateway/face-auth-access-logs --follow --profile dev
```

### エラーログのフィルタリング

```bash
# ERRORレベルのログのみ表示
aws logs filter-log-events \
  --log-group-name /aws/lambda/FaceAuth-Enrollment \
  --filter-pattern "ERROR" \
  --profile dev
```

---

## 🐛 よくある問題と解決策

### 問題1: フロントエンドにアクセスできない

**症状:** `https://d3ecve2syriq5q.cloudfront.net` にアクセスすると403エラー

**解決策:**
```bash
# CloudFrontキャッシュ無効化
aws cloudfront create-invalidation \
  --distribution-id E2G99Q4A3UQ8PU \
  --paths "/*" \
  --profile dev

# 5-10分待つ
```

### 問題2: API呼び出しで403エラー

**症状:** API呼び出しで403 Forbiddenエラー

**原因:** IP制限により、許可されていないIPアドレスからアクセスしている

**解決策:**
```bash
# 現在のIPアドレス確認
curl https://checkip.amazonaws.com

# .envファイル更新
ALLOWED_IPS=210.128.54.64/27,<新しいIP>/32

# 再デプロイ
npx cdk deploy --profile dev \
  --context allowed_ips="210.128.54.64/27,<新しいIP>/32"
```

### 問題3: Lambda関数でImportError

**症状:** `ModuleNotFoundError: No module named 'jwt'`

**原因:** 外部ライブラリがバンドルされていない

**解決策:** Lambda Layerを作成（詳細は`DEPLOYMENT_STATUS_REPORT.md`参照）

### 問題4: CORSエラー

**症状:** ブラウザコンソールに`CORS policy: No 'Access-Control-Allow-Origin' header`

**解決策:**
```bash
# .envファイル確認
cat .env | grep FRONTEND_ORIGINS

# 正しいオリジンを設定
FRONTEND_ORIGINS=https://d3ecve2syriq5q.cloudfront.net

# 再デプロイ
npx cdk deploy --profile dev \
  --context frontend_origins="https://d3ecve2syriq5q.cloudfront.net"
```

### 問題5: Rekognition Collection not found

**症状:** `ResourceNotFoundException: Collection face-auth-employees not found`

**解決策:**
```bash
# Collection作成
aws rekognition create-collection \
  --collection-id face-auth-employees \
  --profile dev
```

---

## 📊 パフォーマンステスト

### Lambda関数のレスポンスタイム測定

```bash
# 10回実行して平均レスポンスタイムを測定
for i in {1..10}; do
  time curl -X GET https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
done
```

### 同時実行テスト

```bash
# Apache Bench（要インストール）
ab -n 100 -c 10 https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
```

---

## 🔐 セキュリティチェック

### 1. S3バケットのパブリックアクセス確認

```bash
# パブリックアクセスがブロックされていることを確認
aws s3api get-public-access-block \
  --bucket face-auth-images-979431736455-ap-northeast-1 \
  --profile dev

aws s3api get-public-access-block \
  --bucket face-auth-frontend-979431736455-ap-northeast-1 \
  --profile dev
```

**期待される結果:**
```json
{
  "PublicAccessBlockConfiguration": {
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  }
}
```

### 2. Lambda実行ロールの権限確認

```bash
# Lambda実行ロールのポリシー確認
aws iam list-attached-role-policies \
  --role-name FaceAuthIdPStack-FaceAuthLambdaExecutionRole* \
  --profile dev
```

### 3. API Gateway IP制限確認

```bash
# API Gateway Resource Policy確認
aws apigateway get-rest-api \
  --rest-api-id zao7evz9jk \
  --profile dev \
  --query "policy"
```

---

## 📈 モニタリングダッシュボード

### CloudWatch メトリクス確認

```bash
# Lambda関数のエラー数
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=FaceAuth-Enrollment \
  --start-time 2026-01-28T00:00:00Z \
  --end-time 2026-01-28T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --profile dev

# API Gatewayのリクエスト数
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=FaceAuth-API \
  --start-time 2026-01-28T00:00:00Z \
  --end-time 2026-01-28T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --profile dev
```

---

## ✅ テスト完了チェックリスト

- [ ] フロントエンドにアクセスできる
- [ ] 社員登録フローが動作する
- [ ] 顔認証ログインフローが動作する
- [ ] 緊急認証フローが動作する
- [ ] 再登録フローが動作する
- [ ] ステータス確認APIが動作する
- [ ] CORS設定が正しく動作する
- [ ] IP制限が正しく動作する
- [ ] Lambda関数のログが確認できる
- [ ] DynamoDBにデータが保存される
- [ ] Rekognition Collectionに顔データが登録される
- [ ] セッション管理が正しく動作する

---

## 📞 サポート

問題が発生した場合は、以下のドキュメントを参照してください：

- `DEPLOYMENT_STATUS_REPORT.md` - デプロイ完了レポート
- `DEPLOYMENT_GUIDE.md` - デプロイ手順
- `CORS_AND_IP_RESTRICTION_GUIDE.md` - CORS・IP制限ガイド
- `docs/INFRASTRUCTURE_ARCHITECTURE.md` - インフラアーキテクチャ

---

**作成日:** 2026年1月28日  
**ステータス:** ✅ テスト準備完了

システムは稼働可能な状態です。上記のテストシナリオに従って、各機能の動作確認を実施してください。

