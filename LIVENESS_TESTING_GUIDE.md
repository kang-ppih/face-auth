# Liveness Detection Testing Guide

## テスト環境

- **フロントエンド URL:** https://d2576ywp5ut1v8.cloudfront.net
- **API エンドポイント:** https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/
- **Identity Pool ID:** ap-northeast-1:3c402eb3-35f0-4068-927f-4ef969195361
- **リージョン:** ap-northeast-1

## テスト手順

### 1. ブラウザでフロントエンドにアクセス

```
https://d2576ywp5ut1v8.cloudfront.net
```

### 2. ブラウザコンソールを開く

- Windows/Linux: `F12` または `Ctrl+Shift+I`
- Mac: `Cmd+Option+I`
- Console タブを選択

### 3. Amplify 設定を確認

コンソールに以下のログが表示されることを確認：

```
Amplify configured:
- Region: ap-northeast-1
- User Pool ID: ap-northeast-1_Mg04RQ15H
- User Pool Client ID: 1hgfirru3r4jrasg9g8s1j0kme
- Identity Pool ID: ap-northeast-1:3c402eb3-35f0-4068-927f-4ef969195361
```

### 4. ライブネス検証を開始

1. **社員IDを入力**
   - 例: `TEST001`
   - 「顔認証でログイン」ボタンをクリック

2. **セッション作成を確認**
   - コンソールに以下のログが表示されることを確認：
     ```
     Creating liveness session for employee: TEST001
     API URL: https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod
     Response status: 200
     Session created: {session_id: "...", expires_at: "..."}
     ```

3. **カメラ許可を承認**
   - ブラウザがカメラアクセスを要求
   - 「許可」をクリック

4. **FaceLivenessDetector の起動を確認**
   - カメラプレビューが表示される
   - 顔検出の指示が表示される
   - **以前のエラー「SERVER_ERROR」が発生しないことを確認**

### 5. ライブネス検証を実行

1. **顔を中央に配置**
   - 画面の指示に従って顔を動かす
   - 明るい場所で実施

2. **検証完了を確認**
   - 検証が完了すると、結果取得 API が呼び出される
   - コンソールに結果が表示される

## 期待される動作

### ✅ 正常な動作

1. **セッション作成成功**
   ```
   Creating liveness session for employee: TEST001
   Response status: 200
   Session created: {session_id: "abc123...", expires_at: "2026-02-11T02:00:00Z"}
   ```

2. **カメラ許可後、FaceLivenessDetector が起動**
   - カメラプレビューが表示される
   - 顔検出の指示が日本語で表示される
   - エラーが発生しない

3. **ライブネス検証実行**
   - Rekognition API が呼び出される
   - 検証結果が返される

### ❌ エラーが発生した場合

#### エラー 1: "No credentials provided"

**原因:**
- Identity Pool ID が設定されていない
- Amplify 設定が正しくない

**確認方法:**
```bash
# フロントエンド .env ファイルを確認
cat frontend/.env | grep IDENTITY_POOL_ID
```

**解決方法:**
```bash
# .env ファイルに Identity Pool ID を追加
echo "REACT_APP_IDENTITY_POOL_ID=ap-northeast-1:3c402eb3-35f0-4068-927f-4ef969195361" >> frontend/.env

# 再ビルド & デプロイ
cd frontend
npm run build
aws s3 sync build/ s3://face-auth-frontend-979431736455-ap-northeast-1 --delete --profile dev
aws cloudfront create-invalidation --distribution-id EE7F2PTRFZ6WV --paths "/*" --profile dev
```

#### エラー 2: "SERVER_ERROR"

**原因:**
- Identity Pool の IAM ロールに権限がない
- Rekognition API へのアクセスが拒否されている

**確認方法:**
```bash
# IAM ロールの権限を確認
aws iam get-role-policy \
  --role-name FaceAuthIdPStack-CognitoUnauthenticatedRoleCF6AD730-gowvkwEJ99A0 \
  --policy-name CognitoUnauthenticatedRoleDefaultPolicyA3267F02 \
  --profile dev
```

**期待される出力:**
```json
{
  "Statement": [
    {
      "Action": "rekognition:StartFaceLivenessSession",
      "Resource": "*",
      "Effect": "Allow"
    }
  ]
}
```

#### エラー 3: "セッション作成に失敗しました"

**原因:**
- Lambda 関数がエラーを返している
- API Gateway の設定が正しくない

**確認方法:**
```bash
# Lambda ログを確認
aws logs tail /aws/lambda/FaceAuth-CreateLivenessSession --since 5m --profile dev --follow
```

**解決方法:**
- Lambda ログでエラーメッセージを確認
- DynamoDB テーブルの存在を確認
- Lambda 関数の環境変数を確認

## デバッグ方法

### 1. ブラウザコンソールでエラーを確認

```javascript
// コンソールに表示されるエラーメッセージを確認
// 例:
// Error: No credentials provided at credentialProvider
// Error: SERVER_ERROR
// Error: Invalid session
```

### 2. Network タブで API 呼び出しを確認

1. **ブラウザの Network タブを開く**
2. **API 呼び出しを確認**
   - `/liveness/session/create` - セッション作成
   - Rekognition API 呼び出し（`rekognition.ap-northeast-1.amazonaws.com`）
3. **レスポンスを確認**
   - ステータスコード
   - レスポンスボディ
   - エラーメッセージ

### 3. Lambda ログを確認

```bash
# CreateLivenessSession Lambda のログ
aws logs tail /aws/lambda/FaceAuth-CreateLivenessSession --since 5m --profile dev --follow

# GetLivenessResult Lambda のログ
aws logs tail /aws/lambda/FaceAuth-GetLivenessResult --since 5m --profile dev --follow
```

### 4. CloudWatch Insights でエラーを検索

```bash
# CloudWatch Insights クエリ
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 20
```

## トラブルシューティング

### 問題: カメラが起動しない

**原因:**
- ブラウザがカメラアクセスをブロックしている
- HTTPS 接続が必要

**解決方法:**
1. ブラウザのアドレスバーのカメラアイコンをクリック
2. 「カメラを許可」を選択
3. ページをリロード

### 問題: "Waiting for you to allow camera permission" が表示され続ける

**原因:**
- セッション作成が失敗している
- API エンドポイントが正しくない

**解決方法:**
1. ブラウザコンソールでエラーを確認
2. Network タブで API 呼び出しを確認
3. Lambda ログを確認

### 問題: ライブネス検証が失敗する

**原因:**
- 顔が検出されない
- 照明が暗すぎる/明るすぎる
- 複数の顔が検出されている

**解決方法:**
1. 明るい場所で実施
2. 顔を中央に配置
3. 一人で実施
4. カメラに近づきすぎない/遠すぎない

## 成功時のログ例

```
Amplify configured:
- Region: ap-northeast-1
- User Pool ID: ap-northeast-1_Mg04RQ15H
- User Pool Client ID: 1hgfirru3r4jrasg9g8s1j0kme
- Identity Pool ID: ap-northeast-1:3c402eb3-35f0-4068-927f-4ef969195361

Creating liveness session for employee: TEST001
API URL: https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod
Response status: 200
Response headers: Headers { ... }
Session created: {
  session_id: "abc123-def456-ghi789",
  expires_at: "2026-02-11T02:00:00Z"
}

[FaceLivenessDetector] Starting liveness check...
[FaceLivenessDetector] Face detected
[FaceLivenessDetector] Liveness check complete
[FaceLivenessDetector] Confidence: 95.5%

Liveness verification successful!
```

## 参考情報

### AWS リソース

- **Identity Pool ID:** ap-northeast-1:3c402eb3-35f0-4068-927f-4ef969195361
- **User Pool ID:** ap-northeast-1_Mg04RQ15H
- **User Pool Client ID:** 1hgfirru3r4jrasg9g8s1j0kme
- **API Gateway:** https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/
- **CloudFront Distribution:** EE7F2PTRFZ6WV
- **S3 Bucket:** face-auth-frontend-979431736455-ap-northeast-1

### IAM ロール

- **未認証ユーザー:** FaceAuthIdPStack-CognitoUnauthenticatedRoleCF6AD730-gowvkwEJ99A0
- **認証済みユーザー:** FaceAuthIdPStack-CognitoAuthenticatedRole5CA1BC89-edbwMzJDS2G3

### 権限

- `rekognition:StartFaceLivenessSession` - 未認証ユーザーに許可

---

**作成日:** 2026-02-11
**最終更新:** 2026-02-11
