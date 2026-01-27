# フロントエンド クイックスタートガイド

## 前提条件

- Node.js 16.x 以上
- npm 8.x 以上
- モダンブラウザ（Chrome, Firefox, Safari, Edge）

## セットアップ手順

### 1. 依存関係のインストール

```bash
cd frontend
npm install
```

### 2. 環境変数の確認

`.env` ファイルが既に設定されています：

```bash
REACT_APP_API_ENDPOINT=https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod
REACT_APP_AWS_REGION=ap-northeast-1
REACT_APP_COGNITO_USER_POOL_ID=ap-northeast-1_ikSWDeIew
REACT_APP_COGNITO_CLIENT_ID=6u4blhui7p35ra4p882srvrpod
```

### 3. 開発サーバーの起動

```bash
npm start
```

ブラウザで自動的に http://localhost:3000 が開きます。

### 4. ビルド（本番用）

```bash
npm run build
```

最適化されたビルドが `build/` フォルダに生成されます。

## 使用方法

### ログイン
1. トップページで「ログイン」タブを選択
2. カメラ権限を許可
3. 顔をカメラに向けて「撮影」ボタンをクリック
4. 認証処理が実行されます

### 新規登録
1. 「新規登録」タブを選択
2. 社員証をカメラに向けて撮影
3. 次に顔をカメラに向けて撮影
4. 登録処理が実行されます

### 緊急ログイン
1. ログイン画面で2回失敗すると「緊急ログイン」ボタンが表示
2. または直接「緊急ログイン」モードに切り替え
3. 社員証を撮影
4. ADパスワードを入力
5. 認証処理が実行されます

### 再登録
1. 「再登録」タブを選択
2. 社員証を撮影（本人確認）
3. 新しい顔データを撮影
4. 更新処理が実行されます

## トラブルシューティング

### カメラが起動しない
- ブラウザのカメラ権限を確認
- HTTPS接続を使用（localhost除く）
- 他のアプリケーションがカメラを使用していないか確認

### API接続エラー
- `.env` ファイルのAPI_ENDPOINTを確認
- ネットワーク接続を確認
- API Gatewayが正しくデプロイされているか確認

### ビルドエラー
```bash
# node_modulesを削除して再インストール
rm -rf node_modules
npm install
```

## 開発時のヒント

### ホットリロード
ファイルを保存すると自動的にブラウザがリロードされます。

### デバッグ
ブラウザの開発者ツール（F12）でコンソールログを確認できます。

### コンポーネント編集
- `src/components/` 内のファイルを編集
- 保存すると自動的に反映されます

## デプロイ

### S3 + CloudFront へのデプロイ

```bash
# ビルド
npm run build

# S3にアップロード
aws s3 sync build/ s3://your-bucket-name/ --profile dev

# CloudFront キャッシュクリア
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*" --profile dev
```

## 次のステップ

1. ローカルでの動作確認
2. バックエンドAPI連携テスト
3. 各認証フローのテスト
4. 本番環境へのデプロイ

## サポート

問題が発生した場合は、以下を確認してください：
- `frontend/README.md` - 詳細なドキュメント
- `FRONTEND_IMPLEMENTATION_SUMMARY.md` - 実装詳細
- ブラウザのコンソールログ
- ネットワークタブでAPI通信を確認

---

**作成日**: 2024年1月28日
