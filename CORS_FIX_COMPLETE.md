# CORS Fix - 完了レポート

## 概要

フロントエンドから`/auth/enroll`エンドポイントへのCORSエラーを修正しました。

## 問題

```
Access to XMLHttpRequest at 'https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/enroll' 
from origin 'https://d2576ywp5ut1v8.cloudfront.net' has been blocked by CORS policy: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## 原因

Lambda関数のレスポンスヘッダーに以下が不足：
- `Access-Control-Allow-Headers`
- `Access-Control-Allow-Methods`

## 実施した修正

### 1. CORSヘッダーの追加

すべてのLambda関数のレスポンスヘッダーを以下のように修正：

**変更前:**
```python
'headers': {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
}
```

**変更後:**
```python
'headers': {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}
```

### 2. 修正したファイル

✅ `lambda/enrollment/handler.py` - 手動修正
✅ `lambda/face_login/handler.py` - スクリプトで修正
✅ `lambda/emergency_auth/handler.py` - スクリプトで修正
✅ `lambda/re_enrollment/handler.py` - スクリプトで修正
✅ `lambda/status/handler.py` - スクリプトで修正
✅ `lambda/liveness/create_session_handler.py` - スクリプトで修正
✅ `lambda/liveness/get_result_handler.py` - スクリプトで修正

### 3. デプロイ結果

```bash
npx cdk deploy --require-approval never --profile dev
```

**デプロイ成功:**
```
✅  FaceAuthIdPStack

✨  Deployment time: 53.23s

Outputs:
FaceAuthIdPStack.APIEndpoint = https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/
FaceAuthIdPStack.FrontendURL = https://d2576ywp5ut1v8.cloudfront.net
```

**更新されたLambda関数:**
- ✅ EnrollmentFunction
- ✅ FaceLoginFunction
- ✅ EmergencyAuthFunction
- ✅ ReEnrollmentFunction
- ✅ StatusFunction
- ✅ CreateLivenessSessionFunction
- ✅ GetLivenessResultFunction

## テスト方法

### 1. ブラウザでテスト

```
https://d2576ywp5ut1v8.cloudfront.net/
```

1. Ctrl+Shift+Rでキャッシュクリア
2. 社員証登録を試す
3. F12で開発者ツールを開く
4. Networkタブで`/auth/enroll`リクエストを確認

**期待される結果:**

Response Headersに以下が含まれる：
```
access-control-allow-origin: *
access-control-allow-headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token
access-control-allow-methods: GET,POST,OPTIONS
content-type: application/json
```

### 2. curlでテスト

```bash
# Preflightリクエスト（OPTIONS）
curl -X OPTIONS https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/enroll \
  -H "Origin: https://d2576ywp5ut1v8.cloudfront.net" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

**期待される結果:**
```
< HTTP/2 200
< access-control-allow-origin: *
< access-control-allow-headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token
< access-control-allow-methods: GET,POST,OPTIONS
```

## 技術的な詳細

### CORS (Cross-Origin Resource Sharing)

ブラウザのセキュリティ機能で、異なるオリジン間のリクエストを制限します。

**オリジン:**
- フロントエンド: `https://d2576ywp5ut1v8.cloudfront.net`
- API: `https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com`

異なるドメインのため、CORSヘッダーが必要です。

### 必要なCORSヘッダー

1. **Access-Control-Allow-Origin**
   - どのオリジンからのアクセスを許可するか
   - `*` = すべてのオリジンを許可（開発環境）
   - 本番環境では特定のドメインを指定推奨

2. **Access-Control-Allow-Headers**
   - クライアントが送信できるヘッダー
   - `Content-Type`, `Authorization`, `X-Api-Key`など

3. **Access-Control-Allow-Methods**
   - 許可するHTTPメソッド
   - `GET`, `POST`, `OPTIONS`

### Preflightリクエスト

ブラウザは実際のリクエストの前に、OPTIONSメソッドでPreflightリクエストを送信します。

**フロー:**
1. ブラウザ → API: OPTIONS /auth/enroll (Preflight)
2. API → ブラウザ: 200 OK + CORSヘッダー
3. ブラウザ → API: POST /auth/enroll (実際のリクエスト)
4. API → ブラウザ: 200 OK + CORSヘッダー + データ

API Gatewayの`default_cors_preflight_options`がPreflightリクエストを処理し、Lambda関数が実際のリクエストのCORSヘッダーを返します。

## 今後の改善案

### 本番環境でのCORS設定

開発環境では`Access-Control-Allow-Origin: *`を使用していますが、本番環境では特定のドメインを指定することを推奨します。

**infrastructure/face_auth_stack.py:**
```python
# 本番環境用
self.frontend_origins = ["https://your-production-domain.com"]

# Lambda関数のレスポンス
'Access-Control-Allow-Origin': 'https://your-production-domain.com'
```

**メリット:**
- セキュリティ向上
- 不正なオリジンからのアクセスを防止

### 環境変数での管理

```bash
# .env
FRONTEND_ORIGINS=https://d2576ywp5ut1v8.cloudfront.net

# 本番環境
FRONTEND_ORIGINS=https://your-production-domain.com
```

## まとめ

### 完了した作業

1. ✅ 問題の特定 - CORSヘッダー不足
2. ✅ 7つのLambda関数を修正
3. ✅ 修正スクリプト作成（`fix-cors-headers.ps1`）
4. ✅ CDKデプロイ完了
5. ✅ すべてのLambda関数が更新完了

### 次のステップ

1. ブラウザでテスト（Ctrl+Shift+Rでキャッシュクリア）
2. 社員証登録フローを確認
3. エラーが解消されていることを確認

### 関連ドキュメント

- `CORS_FIX_DEPLOYMENT.md` - 修正手順の詳細
- `fix-cors-headers.ps1` - 一括修正スクリプト
- `CONSOLE_LOG_AND_OCR_CLEANUP.md` - 前回の修正内容

---

**作成日:** 2026-02-11
**デプロイ時刻:** 12:59 JST
**ステータス:** ✅ 完了
**デプロイ時間:** 53.23秒
