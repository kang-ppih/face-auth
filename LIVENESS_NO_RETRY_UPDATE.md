# Liveness検証 - リトライ防止対応

## 実行日時
2026-02-10 22:37 JST

## 変更概要
APIエラー発生時に自動リトライしないように、LivenessDetectorコンポーネントを修正しました。

## 変更内容

### 1. useEffectの依存配列を空に変更
**変更前:**
```typescript
useEffect(() => {
  createSession();
}, [employeeId, onError]); // employeeIdやonErrorが変わるたびに再実行
```

**変更後:**
```typescript
useEffect(() => {
  createSession();
  return () => {
    isMounted = false;
  };
}, []); // マウント時に1回のみ実行
```

**効果:**
- コンポーネントのマウント時に1回だけセッション作成を実行
- `employeeId`や`onError`が変更されても再実行されない
- 自動リトライが発生しない

### 2. デバッグログの追加
APIリクエスト/レスポンスの詳細をコンソールに出力するようにしました：

```typescript
console.log('Creating liveness session for employee:', employeeId);
console.log('API URL:', apiUrl);
console.log('Response status:', response.status);
console.log('Response headers:', response.headers);
console.log('Session created:', data);
console.error('API error:', errorData);
console.error('Session creation error:', err);
```

**効果:**
- ブラウザの開発者ツール（F12 > Console）で詳細なエラー情報を確認可能
- APIエラーの原因を特定しやすくなる

### 3. エラーメッセージの改善
**変更前:**
```typescript
<p className="error-message">{error}</p>
```

**変更後:**
```typescript
<p className="error-message">{error}</p>
<p className="error-details">
  エラーが発生しました。画面を閉じて最初からやり直してください。
</p>
```

**効果:**
- ユーザーに明確な対処方法を提示
- 自動リトライがないことを明示

### 4. HTTPステータスコードの表示
エラーメッセージにHTTPステータスコードを含めるようにしました：

```typescript
throw new Error(errorData.message || `セッション作成に失敗しました (${response.status})`);
```

**効果:**
- 400, 401, 403, 500などのステータスコードが表示される
- エラーの種類を判別しやすくなる

### 5. メモリリーク対策
コンポーネントがアンマウントされた後に状態更新が発生しないように、`isMounted`フラグを追加：

```typescript
let isMounted = true;

// ...

if (isMounted) {
  setSessionData(data);
  setError(errorMessage);
  setLoading(false);
}

return () => {
  isMounted = false;
};
```

## デプロイ状況

### ✅ ビルド
- ステータス: 成功
- ファイルサイズ: 383.97 kB (前回比 +216 B)

### ✅ S3デプロイ
- バケット: `face-auth-frontend-979431736455-ap-northeast-1`
- ステータス: 完了

### ✅ CloudFrontキャッシュ無効化
- Distribution ID: `EE7F2PTRFZ6WV`
- Invalidation ID: `IA5Y13HX1YL34HSR4JMJXDUXZ7`
- ステータス: InProgress

## テスト方法

### 1. ブラウザのキャッシュをクリア
```
Ctrl+Shift+R (Windows/Linux)
Cmd+Shift+R (Mac)
```

### 2. CloudFront URLにアクセス
```
https://d2576ywp5ut1v8.cloudfront.net
```

### 3. 開発者ツールを開く
```
F12キー
```

### 4. Consoleタブを確認
以下のようなログが表示されます：

**成功時:**
```
Creating liveness session for employee: test123
API URL: https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod
Response status: 200
Session created: {session_id: "...", expires_at: "..."}
```

**エラー時:**
```
Creating liveness session for employee: test123
API URL: https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod
Response status: 500
API error: {message: "Internal Server Error"}
Session creation error: Error: Internal Server Error
```

### 5. Networkタブを確認
`/liveness/session/create`リクエストの詳細を確認：
- Request Headers
- Request Payload
- Response Headers
- Response Body
- Status Code

## エラー診断ガイド

### ステータスコード別の対処方法

#### 400 Bad Request
**原因:** リクエストパラメータが不正
**確認:** 
- `employee_id`が正しく送信されているか
- リクエストボディのJSON形式が正しいか

#### 401 Unauthorized
**原因:** 認証エラー
**確認:**
- API Keyが必要な場合、正しく送信されているか
- Cognitoトークンが必要な場合、有効なトークンか

#### 403 Forbidden
**原因:** アクセス権限エラー
**確認:**
- IPアドレス制限に引っかかっていないか
- WAFルールでブロックされていないか

#### 500 Internal Server Error
**原因:** サーバー側のエラー
**確認:**
- Lambda関数のログを確認
- Lambda実行ロールの権限を確認
- Rekognition APIの呼び出しが成功しているか

#### 502 Bad Gateway
**原因:** API GatewayとLambda間の通信エラー
**確認:**
- Lambda関数がタイムアウトしていないか
- Lambda関数がVPC内で正しく動作しているか

#### 504 Gateway Timeout
**原因:** Lambda関数のタイムアウト
**確認:**
- Lambda関数のタイムアウト設定（現在10秒）
- Rekognition APIの応答時間

### CORS エラー
**症状:** 
```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**確認:**
- API GatewayのCORS設定
- レスポンスヘッダーに`Access-Control-Allow-Origin`が含まれているか

### Network エラー
**症状:**
```
Failed to fetch
TypeError: Failed to fetch
```

**原因:**
- ネットワーク接続の問題
- API URLが間違っている
- CORSエラー
- SSL証明書の問題

## 期待される動作

### 正常時
1. コンポーネントがマウントされる
2. セッション作成APIを1回だけ呼び出す
3. セッションIDを取得
4. FaceLivenessDetectorコンポーネントを表示
5. ライブネス検証を実行

### エラー時
1. コンポーネントがマウントされる
2. セッション作成APIを1回だけ呼び出す
3. エラーが発生
4. エラーメッセージを表示
5. **自動リトライしない**
6. ユーザーが画面を閉じて最初からやり直す

## 注意事項

- **自動リトライは実装されていません**
- エラーが発生した場合、ユーザーは画面を閉じて最初からやり直す必要があります
- リトライが必要な場合は、親コンポーネントで実装してください

## 関連ファイル

- `frontend/src/components/LivenessDetector.tsx` - 修正済み
- `LIVENESS_API_DIAGNOSIS.md` - API診断レポート

---

**作成者:** Kiro AI Assistant
**最終更新:** 2026-02-10 22:37 JST
