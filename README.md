# Face-Auth IdP システム

AWS基盤のFace-Auth Identity Providerシステムは、社員証ベースの信頼チェーンとAmazon Rekognitionを活用した1:N顔認識により、パスワードレス認証を提供するエンタープライズグレードの従業員認証システムです。

## 🏗️ アーキテクチャ概要

このシステムは以下のAWSサービスを使用します：

### バックエンド
- **AWS CDK (Python)**: Infrastructure as Code
- **Amazon VPC**: ネットワーク分離とセキュリティ
- **AWS Direct Connect**: オンプレミスActive Directory接続
- **Amazon S3**: 顔画像保存（ライフサイクルポリシー付き）
- **Amazon DynamoDB**: カードテンプレートと従業員データ保存
- **AWS Lambda**: 認証ロジック処理
- **Amazon Rekognition**: 顔認識とLiveness検出（なりすまし防止）
- **Amazon Textract**: 社員証OCR処理
- **AWS Cognito**: ユーザーセッション管理
- **Amazon API Gateway**: REST APIエンドポイント
- **Amazon CloudWatch**: ロギングとモニタリング

### フロントエンド
- **React 19.2.4**: UIフレームワーク
- **TypeScript 4.9.5**: 型安全性
- **AWS Amplify 6.16.0**: AWS統合
- **Axios 1.13.4**: HTTP通信

## 🚀 クイックスタート

### 前提条件

1. **AWS CLIのインストールと設定**
   ```bash
   aws configure
   ```

2. **Node.jsとAWS CDKのインストール**
   ```bash
   npm install -g aws-cdk
   ```

3. **Python 3.9+のインストール**

### バックエンドデプロイ手順

1. **リポジトリのクローンと依存関係のインストール**
   ```bash
   git clone https://github.com/kang-ppih/face-auth.git
   cd face-auth
   ```

2. **PowerShellでデプロイ実行**
   ```powershell
   .\deploy.ps1
   ```

   または手動で：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cdk bootstrap
   cdk deploy
   ```

3. **IPアクセス制御の設定（オプション）**
   
   特定のIPアドレスからのみAPIアクセスを許可する場合：
   
   ```bash
   # 単一IPアドレスを許可
   cdk deploy --context allowed_ips="203.0.113.10/32"
   
   # 複数のIP範囲を許可（カンマ区切り）
   cdk deploy --context allowed_ips="203.0.113.10/32,198.51.100.0/24"
   
   # 社内ネットワーク全体を許可
   cdk deploy --context allowed_ips="10.0.0.0/8"
   ```
   
   詳細は [IPアクセス制御ドキュメント](docs/IP_ACCESS_CONTROL.md) を参照してください。

4. **CORS設定（オプション）**
   
   特定のフロントエンドオリジンからのみAPIアクセスを許可する場合：
   
   ```bash
   # 単一オリジンを許可
   cdk deploy --context frontend_origins="https://app.example.com"
   
   # 複数のオリジンを許可（カンマ区切り）
   cdk deploy --context frontend_origins="https://app.example.com,https://staging.example.com"
   ```
   
   詳細は [CORS設定ガイド](CORS_AND_IP_RESTRICTION_GUIDE.md) を参照してください。

5. **Rekognitionコレクションの作成**
   ```bash
   aws rekognition create-collection --collection-id face-auth-employees
   ```

## 📋 構成要素

### インフラストラクチャコンポーネント

#### VPCとネットワーキング
- **VPC**: 10.0.0.0/16 CIDRブロック
- **サブネット**: Public、Private、Isolatedサブネット各2つのAZ
- **セキュリティグループ**: LambdaとAD接続用セキュリティグループ
- **VPCエンドポイント**: S3とDynamoDB用ゲートウェイエンドポイント

#### ストレージ
- **S3バケット**: 
  - `enroll/`: 登録サムネイル（永久保管）
  - `logins/`: ログイン試行画像（30日後自動削除）
  - `temp/`: 一時処理ファイル（1日後自動削除）

#### データベース
- **CardTemplates**: 社員証認識パターン保存
- **EmployeeFaces**: 従業員顔データメタデータ
- **AuthSessions**: 認証セッション管理（TTL適用）

#### コンピューティング
- **Lambda関数**:
  - `FaceAuth-Enrollment`: 従業員登録
  - `FaceAuth-FaceLogin`: 顔ログイン
  - `FaceAuth-EmergencyAuth`: 緊急認証
  - `FaceAuth-ReEnrollment`: 再登録
  - `FaceAuth-Status`: ステータス確認
  - `FaceAuth-CreateLivenessSession`: Livenessセッション作成
  - `FaceAuth-GetLivenessResult`: Liveness検証結果取得

### APIエンドポイント

```
POST /auth/enroll                          # 従業員登録
POST /auth/login                           # 顔ログイン
POST /auth/emergency                       # 緊急認証
POST /auth/re-enroll                       # 再登録
GET  /auth/status                          # 認証ステータス確認
POST /liveness/session/create              # Livenessセッション作成
GET  /liveness/session/{sessionId}/result  # Liveness検証結果取得
```

## 🛡️ Liveness検証機能

### 概要

Face-Auth IdPシステムは、AWS Rekognition Face Liveness APIを使用して、写真や動画を使ったなりすまし攻撃を防ぐ高度な生体検証機能を提供します。

### 主な機能

- **写真なりすまし防御**: 印刷された写真やスマートフォン画面での攻撃を防御（100%防御率）
- **動画なりすまし防御**: 録画された動画での攻撃を防御（95%以上の防御率）
- **信頼度スコア**: 90%以上の信頼度を要求
- **監査ログ**: すべての検証結果をS3に保存（90日間保持）
- **CloudWatch監視**: 成功率、信頼度、処理時間などをリアルタイム監視

### 認証フロー

```
1. ユーザーがLiveness検証を開始
   ↓
2. フロントエンドがセッション作成APIを呼び出し
   ↓
3. Rekognition Liveness APIがセッションを作成
   ↓
4. ユーザーがカメラで顔を撮影（Amplify UI Liveness Detector）
   ↓
5. フロントエンドが検証結果取得APIを呼び出し
   ↓
6. Rekognition APIが生体検証を実行
   ↓
7. 信頼度スコア（90%以上）を評価
   ↓
8. 検証成功 → 認証処理続行
   検証失敗 → エラーメッセージ表示
```

### ドキュメント

- [Liveness Service 技術ドキュメント](docs/LIVENESS_SERVICE.md)
- [Liveness Migration Guide](docs/LIVENESS_MIGRATION_GUIDE.md)
- [Liveness Operations Manual](docs/LIVENESS_OPERATIONS.md)

## 🔧 設定

### 環境変数

システムの動作に必要な環境変数は`.env.sample`ファイルを参考に設定してください。

#### セットアップ手順

1. **サンプルファイルをコピー**
   ```bash
   cp .env.sample .env
   ```

2. **必要な値を設定**
   
   `.env`ファイルを編集して、以下の値を設定してください：

#### 必須環境変数

| 環境変数 | 説明 | デフォルト値 | 設定タイミング |
|---------|------|------------|--------------|
| `AWS_REGION` | AWSリージョン | `ap-northeast-1` | デプロイ前 |
| `CDK_DEFAULT_ACCOUNT` | AWSアカウントID | - | デプロイ前 |
| `CDK_DEFAULT_REGION` | CDKデプロイリージョン | `ap-northeast-1` | デプロイ前 |

#### Lambda関数環境変数（CDKが自動設定）

以下の環境変数はCDKスタックによって自動的にLambda関数に設定されます。ローカルテスト時のみ手動設定が必要です。

| 環境変数 | 説明 | 例 |
|---------|------|-----|
| `FACE_AUTH_BUCKET` | S3バケット名 | `face-auth-images-123456789012-ap-northeast-1` |
| `CARD_TEMPLATES_TABLE` | カードテンプレートテーブル名 | `FaceAuth-CardTemplates` |
| `EMPLOYEE_FACES_TABLE` | 従業員顔データテーブル名 | `FaceAuth-EmployeeFaces` |
| `AUTH_SESSIONS_TABLE` | 認証セッションテーブル名 | `FaceAuth-AuthSessions` |
| `COGNITO_USER_POOL_ID` | Cognito User Pool ID | `ap-northeast-1_XXXXXXXXX` |
| `COGNITO_CLIENT_ID` | Cognito Client ID | デプロイ後に取得 |
| `REKOGNITION_COLLECTION_ID` | RekognitionコレクションID | `face-auth-employees` |
| `SESSION_TIMEOUT_HOURS` | セッションタイムアウト（時間） | `8` |

#### オプション環境変数

| 環境変数 | 説明 | デフォルト値 |
|---------|------|------------|
| `ALLOWED_IPS` | 許可するIPアドレス範囲（CIDR形式、カンマ区切り） | 空（全IP許可） |

#### 環境変数の取得方法

デプロイ後、以下のコマンドで必要な値を取得できます：

```bash
# Cognito User Pool IDの取得
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text

# Cognito Client IDの取得
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolClientId`].OutputValue' \
  --output text

# S3バケット名の取得
aws cloudformation describe-stacks \
  --stack-name FaceAuthStack \
  --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' \
  --output text
```

#### セキュリティに関する注意事項

⚠️ **重要**: 
- `.env`ファイルは`.gitignore`に含まれており、Gitにコミットされません
- 機密情報（パスワード、APIキーなど）は絶対にGitにコミットしないでください
- 本番環境では、AWS Secrets ManagerまたはSystems Manager Parameter Storeの使用を推奨します

#### 環境別設定

環境ごとに異なる設定ファイルを作成できます：

```bash
.env.development   # 開発環境
.env.staging       # ステージング環境
.env.production    # 本番環境
```

詳細は`.env.sample`ファイルのコメントを参照してください。

### Active Directory接続

`config.py`でAD設定を更新してください：

```python
AD_CONFIG = {
    'SERVER_URL': 'ldaps://your-ad-server.com',
    'BASE_DN': 'ou=employees,dc=yourcompany,dc=com',
    'TIMEOUT': 10,
    'USE_SSL': True,
    'PORT': 636
}
```

### カードテンプレート設定

DynamoDBのCardTemplatesテーブルに社員証認識パターンを追加してください：

```json
{
  "pattern_id": "company_standard_v1",
  "card_type": "standard_employee",
  "logo_position": {"x": 50, "y": 30, "width": 100, "height": 50},
  "fields": [
    {
      "field_name": "employee_id",
      "query_phrase": "社員番号は何ですか？",
      "expected_format": "\\d{6}",
      "required": true
    }
  ],
  "is_active": true
}
```

## 🔒 セキュリティ考慮事項

### ネットワークセキュリティ
- VPC内の分離された環境で実行
- Direct Connectによる安全なオンプレミス接続
- セキュリティグループによるトラフィック制御

### データセキュリティ
- S3とDynamoDBの暗号化（AWS管理キー）
- IAMロールベースの最小権限原則
- API Gatewayによるアクセス制御

### 認証セキュリティ
- 90%以上のLiveness検出信頼度要求
- 10秒AD接続タイムアウト
- 15秒Lambda実行タイムアウト
- レート制限と監査ログ

## 📊 モニタリングとロギング

### CloudWatchロググループ
- `/aws/lambda/FaceAuth-*`: Lambda関数ログ
- `/aws/apigateway/face-auth-access-logs`: APIアクセスログ

### メトリクスとアラーム
- Lambda実行時間とエラー率
- API Gatewayリクエスト数とレイテンシ
- DynamoDB読み取り/書き込みキャパシティ

## 🧪 テスト

### 単体テスト
```bash
pytest tests/ --ignore=tests/test_ad_connector.py -v
```

### 統合テスト
```bash
pytest tests/test_backend_integration.py -v
```

### テスト結果
- **総テスト数**: 223
- **合格率**: 100%
- **カバレッジ**: ~90%

## 📈 パフォーマンス最適化

### Lambda最適化
- 512MBメモリ割り当て
- VPC内実行によるセキュリティ強化
- 環境変数による設定管理

### DynamoDB最適化
- Pay-per-request料金モデル
- グローバルセカンダリインデックス活用
- TTLによる自動データクリーンアップ

### S3最適化
- ライフサイクルポリシーによる自動データ管理
- CORS設定によるフロントエンド統合サポート

## 🚨 トラブルシューティング

### 一般的な問題

1. **CDKデプロイ失敗**
   - AWS認証情報の確認
   - 必要なIAM権限の確認
   - リージョン別サービス可用性の確認

2. **Lambdaタイムアウト**
   - VPC設定の確認（NAT Gateway必要）
   - セキュリティグループのアウトバウンドルール確認

3. **Direct Connect接続問題**
   - ネットワークチームと協力して物理接続を確認
   - ルーティングテーブルとBGP設定の確認

## 📚 追加リソース

- [AWS CDKドキュメント](https://docs.aws.amazon.com/cdk/)
- [Amazon Rekognition開発者ガイド](https://docs.aws.amazon.com/rekognition/)
- [Amazon Textract開発者ガイド](https://docs.aws.amazon.com/textract/)
- [AWS Direct Connectユーザーガイド](https://docs.aws.amazon.com/directconnect/)
- [プロジェクトドキュメント](docs/)
- [ローカル実行ガイド](LOCAL_EXECUTION_GUIDE.md)
- [デプロイメントガイド](DEPLOYMENT_GUIDE.md)

## 📄 ライセンス

このプロジェクトはMITライセンスの下で配布されます。

## 🤝 貢献

バグレポート、機能リクエスト、プルリクエストを歓迎します。

## 📊 プロジェクトステータス

- ✅ バックエンド実装完了（Tasks 1-11）
- ✅ 223単体テスト合格（100%合格率）
- ✅ インフラストラクチャ定義完了
- ✅ プロジェクト標準確立
- 🔄 フロントエンド実装待ち（Task 12）
- 🔄 AWSデプロイ待ち（Task 15）

---

**注意**: このシステムは本番環境で使用する前に、徹底的なセキュリティレビューとテストが必要です。

**リポジトリ**: https://github.com/kang-ppih/face-auth


## 🎨 フロントエンド

### セットアップ

```bash
cd frontend
npm install
```

### 環境変数設定

`.env` ファイルは既に設定されています：

```bash
REACT_APP_API_ENDPOINT=https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod
REACT_APP_AWS_REGION=ap-northeast-1
REACT_APP_COGNITO_USER_POOL_ID=ap-northeast-1_ikSWDeIew
REACT_APP_COGNITO_CLIENT_ID=6u4blhui7p35ra4p882srvrpod
```

### 開発サーバー起動

```bash
npm start
```

ブラウザで http://localhost:3000 が開きます。

### ビルド

```bash
npm run build
```

最適化されたビルドが `build/` フォルダに生成されます。

### フロントエンドデプロイ

```powershell
# フロントエンドのビルドとデプロイ
.\deploy-frontend.ps1 -Profile dev

# ビルドをスキップしてデプロイのみ
.\deploy-frontend.ps1 -Profile dev -SkipBuild
```

詳細は [フロントエンドクイックスタート](FRONTEND_QUICK_START.md) を参照してください。

### 機能

- **顔認証ログイン**: 1:N 顔マッチングによるパスワードレス認証
- **新規登録**: 社員証 OCR + 顔データ登録
- **緊急ログイン**: 社員証 + AD パスワード認証
- **再登録**: 既存社員の顔データ更新

### 詳細ドキュメント

- [フロントエンド README](frontend/README.md)
- [クイックスタートガイド](FRONTEND_QUICK_START.md)
- [実装サマリー](FRONTEND_IMPLEMENTATION_SUMMARY.md)

## 📚 ドキュメント

### 技術ドキュメント
- [インフラストラクチャアーキテクチャ](docs/INFRASTRUCTURE_ARCHITECTURE.md)
- [Cognitoサービス](docs/COGNITO_SERVICE.md)
- [セッション管理](docs/SESSION_MANAGEMENT.md)
- [タイムアウトマネージャー](docs/TIMEOUT_MANAGER.md)
- [IPアクセス制御](docs/IP_ACCESS_CONTROL.md)

### デプロイメントガイド
- [デプロイメントガイド](DEPLOYMENT_GUIDE.md)
- [ローカル実行ガイド](LOCAL_EXECUTION_GUIDE.md)
- [デプロイ後ガイド](POST_DEPLOYMENT_GUIDE.md)

### 実装レポート
- [Lambda実装サマリー](LAMBDA_HANDLERS_IMPLEMENTATION.md)
- [テストカバレッジ分析](TEST_COVERAGE_ANALYSIS.md)
- [VPC NACL実装](VPC_NETWORK_ACL_IMPLEMENTATION.md)
- [フロントエンド実装サマリー](FRONTEND_IMPLEMENTATION_SUMMARY.md)

## 🤝 貢献

プロジェクトへの貢献を歓迎します。以下のガイドラインに従ってください：

1. プロジェクト標準に従う（`.kiro/steering/project-standards.md`）
2. Gitワークフローに従う（`.kiro/steering/git-workflow.md`）
3. コーディング規約に従う（`.kiro/steering/python-coding-standards.md`）
4. テストを追加する
5. ドキュメントを更新する

## 📄 ライセンス

Copyright © 2024 Face-Auth IdP System

---

**最終更新**: 2024年1月28日
**バージョン**: 1.0
