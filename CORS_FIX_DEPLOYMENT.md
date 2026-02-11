# CORS Error Fix - Deployment Guide

## 問題

フロントエンドから`/auth/enroll`エンドポイントへのリクエストがCORSエラーで失敗：

```
Access to XMLHttpRequest at 'https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/enroll' 
from origin 'https://d2576ywp5ut1v8.cloudfront.net' has been blocked by CORS policy: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

## 原因

Lambda関数のレスポンスヘッダーに`Access-Control-Allow-Headers`と`Access-Control-Allow-Methods`が不足していました。

## 修正内容

### 修正ファイル

`lambda/enrollment/handler.py` - CORSヘッダーを追加

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

### 他のLambda関数も同様に修正が必要

以下のファイルも同じ修正が必要です：

- `lambda/face_login/handler.py`
- `lambda/emergency_auth/handler.py`
- `lambda/re_enrollment/handler.py`
- `lambda/status/handler.py`
- `lambda/liveness/create_session_handler.py`
- `lambda/liveness/get_result_handler.py`

## デプロイ手順

### 1. すべてのLambda関数のCORSヘッダーを更新

以下のコマンドを実行して、すべてのLambda関数を一括更新します：

```bash
# PowerShellスクリプトを実行
.\fix-cors-headers.ps1
```

または手動で各ファイルを編集してください。

### 2. CDKデプロイ

```bash
cdk deploy --require-approval never
```

### 3. 動作確認

ブラウザでキャッシュクリアしてアクセス：

```
Ctrl + Shift + R
```

社員証登録を試してください。

## 一括修正スクリプト

以下のPowerShellスクリプトを`fix-cors-headers.ps1`として保存して実行してください：

```powershell
# fix-cors-headers.ps1
# すべてのLambda関数のCORSヘッダーを一括修正

$files = @(
    "lambda/face_login/handler.py",
    "lambda/emergency_auth/handler.py",
    "lambda/re_enrollment/handler.py",
    "lambda/status/handler.py"
)

$oldPattern = "'Access-Control-Allow-Origin': '\*'"
$newHeaders = @"
'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
"@

foreach ($file in $files) {
    Write-Host "Updating $file..."
    $content = Get-Content $file -Raw
    $content = $content -replace $oldPattern, $newHeaders
    Set-Content $file $content -NoNewline
    Write-Host "✓ $file updated"
}

Write-Host "`nAll files updated successfully!"
Write-Host "Next step: Run 'cdk deploy --require-approval never'"
```

## 手動修正方法

各Lambda関数の`handler.py`ファイルで、すべてのレスポンスヘッダーを以下のように修正：

### 検索パターン

```python
'headers': {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*'
}
```

### 置換パターン

```python
'headers': {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
}
```

## 確認方法

### ブラウザ開発者ツールで確認

1. ブラウザでF12を押して開発者ツールを開く
2. Networkタブを選択
3. 社員証登録を実行
4. `/auth/enroll`リクエストを選択
5. Response Headersを確認

**期待される結果:**
```
access-control-allow-origin: *
access-control-allow-headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token
access-control-allow-methods: GET,POST,OPTIONS
content-type: application/json
```

### curlコマンドで確認

```bash
curl -X OPTIONS https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/enroll \
  -H "Origin: https://d2576ywp5ut1v8.cloudfront.net" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v
```

## トラブルシューティング

### CORSエラーが継続する場合

1. **Lambda関数が更新されているか確認**
   ```bash
   aws lambda get-function --function-name FaceAuth-Enrollment --profile dev
   ```

2. **API Gatewayのデプロイ確認**
   ```bash
   aws apigateway get-deployments --rest-api-id ivgbc7glnl --profile dev
   ```

3. **ブラウザキャッシュクリア**
   ```
   Ctrl + Shift + R (Windows)
   Cmd + Shift + R (Mac)
   ```

4. **CloudFrontキャッシュ無効化**
   ```bash
   aws cloudfront create-invalidation --distribution-id EE7F2PTRFZ6WV --paths "/*" --profile dev
   ```

### Preflightリクエストが失敗する場合

API GatewayのOPTIONSメソッドが正しく設定されているか確認：

```bash
aws apigateway get-method --rest-api-id ivgbc7glnl --resource-id <resource-id> --http-method OPTIONS --profile dev
```

## まとめ

### 修正内容

- ✅ `lambda/enrollment/handler.py` - CORSヘッダー追加完了
- ⏳ 他のLambda関数 - 修正が必要

### 次のステップ

1. 上記のスクリプトを実行してすべてのLambda関数を修正
2. `cdk deploy`を実行
3. ブラウザでテスト

---

**作成日:** 2026-02-11
**ステータス:** 修正中
