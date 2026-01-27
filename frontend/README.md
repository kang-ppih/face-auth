# Face-Auth IdP System - Frontend

React + TypeScript フロントエンドアプリケーション

## 概要

Face-Auth IdP System のフロントエンドは、顔認証による無パスワード認証システムのユーザーインターフェースを提供します。

## 機能

- **顔認証ログイン**: 1:N 顔マッチングによるパスワードレス認証
- **新規登録**: 社員証 OCR + 顔データ登録
- **緊急ログイン**: 社員証 + AD パスワード認証
- **再登録**: 既存社員の顔データ更新

## 技術スタック

- React 19.2.4
- TypeScript 4.9.5
- AWS Amplify 6.16.0
- Axios 1.13.4

## セットアップ

### 環境変数設定

`.env` ファイルを作成し、以下の環境変数を設定してください：

```bash
REACT_APP_API_ENDPOINT=https://your-api-gateway-url.amazonaws.com/prod
REACT_APP_AWS_REGION=ap-northeast-1
REACT_APP_COGNITO_USER_POOL_ID=your-user-pool-id
REACT_APP_COGNITO_CLIENT_ID=your-client-id
```

### 依存関係インストール

```bash
npm install
```

### 開発サーバー起動

```bash
npm start
```

ブラウザで http://localhost:3000 を開きます。

### ビルド

```bash
npm run build
```

本番用の最適化されたビルドを `build/` フォルダに生成します。

## プロジェクト構造

```
frontend/
├── public/              # 静的ファイル
├── src/
│   ├── components/      # React コンポーネント
│   │   ├── CameraCapture.tsx
│   │   ├── Enrollment.tsx
│   │   ├── Login.tsx
│   │   ├── EmergencyAuth.tsx
│   │   └── ReEnrollment.tsx
│   ├── config/          # 設定ファイル
│   │   └── api.ts
│   ├── services/        # API サービス
│   │   └── api.ts
│   ├── types/           # TypeScript 型定義
│   │   └── index.ts
│   ├── utils/           # ユーティリティ関数
│   │   └── imageUtils.ts
│   ├── App.tsx          # メインアプリケーション
│   └── index.tsx        # エントリーポイント
└── package.json
```

## コンポーネント

### CameraCapture
カメラストリームと画像キャプチャを処理します。

### Login
顔認証ログイン画面。1:N 顔マッチングを実行します。

### Enrollment
新規登録画面。社員証 OCR と顔データ登録を行います。

### EmergencyAuth
緊急ログイン画面。社員証 + AD パスワード認証を行います。

### ReEnrollment
再登録画面。既存社員の顔データを更新します。

## API エンドポイント

- `POST /auth/enroll` - 新規登録
- `POST /auth/login` - 顔認証ログイン
- `POST /auth/emergency` - 緊急認証
- `POST /auth/re-enroll` - 再登録
- `GET /auth/status/:sessionId` - ステータス確認

## ブラウザサポート

- Chrome (最新版)
- Firefox (最新版)
- Safari (最新版)
- Edge (最新版)

カメラアクセスには HTTPS が必要です（localhost を除く）。

## トラブルシューティング

### カメラアクセスエラー
- ブラウザのカメラ権限を確認してください
- HTTPS 接続を使用してください（localhost を除く）

### API 接続エラー
- `.env` ファイルの API エンドポイントを確認してください
- CORS 設定を確認してください

## ライセンス

Copyright © 2024 Face-Auth IdP System
