---
inclusion: always
---

# Face-Auth IdP System - Project Standards

このドキュメントは、Face-Auth IdP システムのプロジェクト全体の標準とルールを定義します。
すべてのコード、ドキュメント、インフラストラクチャはこれらの標準に従う必要があります。

## プロジェクト概要

**プロジェクト名:** Face-Auth IdP System
**目的:** 社員証ベースの信頼チェーンと顔認識による無パスワード認証システム
**技術スタック:** Python 3.9+, AWS CDK, React, AWS Services (Lambda, S3, DynamoDB, Rekognition, Textract, Cognito)

---

## 命名規則

### ファイル・ディレクトリ命名

#### Python ファイル
- **モジュール:** `snake_case.py`
  - 例: `face_recognition_service.py`, `error_handler.py`
- **テストファイル:** `test_<module_name>.py`
  - 例: `test_face_recognition_service.py`

#### ドキュメント
- **大文字スネークケース:** `UPPERCASE_SNAKE_CASE.md`
  - 例: `README.md`, `DEPLOYMENT_GUIDE.md`, `LOCAL_EXECUTION_GUIDE.md`
- **技術ドキュメント:** `TITLE_CASE.md` (docs/フォルダ内)
  - 例: `docs/COGNITO_SERVICE.md`, `docs/SESSION_MANAGEMENT.md`

#### ディレクトリ
- **小文字スネークケース:** `lowercase_snake_case/`
  - 例: `lambda/`, `infrastructure/`, `tests/`, `lambda/shared/`

### コード命名

#### Python
- **クラス:** `PascalCase`
  - 例: `FaceRecognitionService`, `ErrorHandler`, `TimeoutManager`
- **関数・メソッド:** `snake_case`
  - 例: `handle_enrollment()`, `verify_employee()`, `create_session()`
- **定数:** `UPPER_SNAKE_CASE`
  - 例: `MAX_TIMEOUT`, `DEFAULT_CONFIDENCE_THRESHOLD`
- **変数:** `snake_case`
  - 例: `employee_id`, `face_data`, `session_token`

#### AWS リソース
- **命名パターン:** `FaceAuth-<ResourceType>-<Purpose>`
  - Lambda: `FaceAuth-Enrollment`, `FaceAuth-FaceLogin`
  - DynamoDB: `FaceAuth-CardTemplates`, `FaceAuth-EmployeeFaces`
  - S3: `face-auth-images-{account}-{region}`
  - API Gateway: `FaceAuth-API`
  - Cognito: `FaceAuth-UserPool`

---

## ディレクトリ構造

```
face-auth/
├── .kiro/
│   ├── specs/face-auth/          # Spec files (requirements, design, tasks)
│   ├── steering/                 # Project standards and guidelines
│   └── hooks/                    # Kiro automation hooks
├── infrastructure/               # AWS CDK infrastructure code
│   ├── __init__.py
│   └── face_auth_stack.py
├── lambda/                       # Lambda function handlers
│   ├── enrollment/
│   ├── face_login/
│   ├── emergency_auth/
│   ├── re_enrollment/
│   ├── status/
│   └── shared/                   # Shared services and utilities
│       ├── models.py
│       ├── dynamodb_service.py
│       ├── ocr_service.py
│       ├── face_recognition_service.py
│       ├── ad_connector.py
│       ├── cognito_service.py
│       ├── error_handler.py
│       ├── timeout_manager.py
│       └── thumbnail_processor.py
├── tests/                        # Unit and integration tests
│   ├── test_*.py
│   └── __init__.py
├── scripts/                      # Utility scripts
│   ├── init_dynamodb.py
│   └── demo_data_models.py
├── docs/                         # Technical documentation
│   ├── COGNITO_SERVICE.md
│   ├── SESSION_MANAGEMENT.md
│   ├── TIMEOUT_MANAGER.md
│   └── INFRASTRUCTURE_ARCHITECTURE.md
├── requirements.txt              # Python dependencies
├── cdk.json                      # CDK configuration
├── app.py                        # CDK app entry point
├── README.md                     # Project overview
├── DEPLOYMENT_GUIDE.md           # Deployment instructions
└── LOCAL_EXECUTION_GUIDE.md      # Local development guide
```

---

## ドキュメント規約

### ドキュメントの種類と配置

#### 1. プロジェクトルート
- `README.md` - プロジェクト概要、クイックスタート
- `DEPLOYMENT_GUIDE.md` - デプロイ手順
- `LOCAL_EXECUTION_GUIDE.md` - ローカル開発環境セットアップ
- `CONTRIBUTING.md` - 貢献ガイドライン（必要に応じて）

#### 2. docs/ フォルダ
- 技術的な詳細ドキュメント
- サービス別のドキュメント
- アーキテクチャドキュメント

#### 3. .kiro/specs/ フォルダ
- `requirements.md` - 要求仕様
- `design.md` - 設計書
- `tasks.md` - 実装タスク

#### 4. .kiro/steering/ フォルダ
- プロジェクト標準
- コーディング規約
- ワークフロールール

### ドキュメント作成ルール

1. **すべてのドキュメントはMarkdown形式**
2. **日本語または英語（一貫性を保つ）**
3. **コードブロックには言語指定を含める**
   ```python
   # Good
   def example():
       pass
   ```
4. **見出しは階層的に使用（H1 → H2 → H3）**
5. **重要な情報は太字または絵文字で強調**
   - ✅ 完了
   - ❌ 未完了
   - ⚠️ 注意
   - 🔴 重要

---

## コード品質基準

### 必須要件

1. **Type Hints使用**
   - すべての関数・メソッドにtype hintsを付ける
   - Python 3.9+ の型アノテーションを使用

2. **Docstrings**
   - すべてのクラス、関数、メソッドにdocstringを記述
   - Google形式またはNumPy形式を使用

3. **エラーハンドリング**
   - すべての外部API呼び出しにtry-exceptを使用
   - 適切なログ出力
   - ユーザーフレンドリーなエラーメッセージ

4. **テストカバレッジ**
   - 新規コードは必ずテストを含める
   - 単体テストは最低限必須
   - 統合テストは重要な機能に対して実施

5. **セキュリティ**
   - 機密情報をコードにハードコードしない
   - 環境変数を使用
   - IAM最小権限の原則

---

## Git ワークフロー

### ブランチ戦略

- `master` - 本番環境用（安定版）
- `develop` - 開発環境用（統合ブランチ）
- `feature/*` - 機能開発用
- `bugfix/*` - バグ修正用
- `hotfix/*` - 緊急修正用

### コミットメッセージ規約

**フォーマット:**
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type:**
- `feat` - 新機能
- `fix` - バグ修正
- `docs` - ドキュメント変更
- `style` - コードフォーマット（機能変更なし）
- `refactor` - リファクタリング
- `test` - テスト追加・修正
- `chore` - ビルド・設定変更

**例:**
```
feat(lambda): Add face login handler with 1:N matching

- Implement liveness detection (>90% confidence)
- Add 1:N face search in Rekognition
- Store failed login attempts in S3
- Update last_login in DynamoDB

Closes #123
```

### 自動コミット

- タスク完了時に自動コミット（Kiro Hook使用）
- コミットメッセージは明確で説明的に

---

## テスト戦略

### テストの種類

1. **単体テスト (Unit Tests)**
   - 各サービス・関数の個別テスト
   - モックを使用して外部依存を排除
   - 高速実行

2. **統合テスト (Integration Tests)**
   - 複数のサービス間の連携テスト
   - 実際のAWSサービスを使用（可能な場合）

3. **E2Eテスト (End-to-End Tests)**
   - 完全な認証フローのテスト
   - フロントエンド + バックエンド

### テスト実行

```bash
# すべてのテスト
python -m pytest tests/ -v

# AD Connectorを除外（ldap3依存）
python -m pytest tests/ --ignore=tests/test_ad_connector.py -v

# 特定のテストファイル
python -m pytest tests/test_lambda_handlers.py -v

# カバレッジ付き
python -m pytest tests/ --cov=lambda --cov-report=html
```

### テスト要件

- ✅ 新規機能には必ずテストを追加
- ✅ バグ修正には再現テストを追加
- ✅ テストは独立して実行可能
- ✅ テストは決定的（ランダム性なし）

---

## AWS リソース管理

### タグ付けルール

すべてのAWSリソースに以下のタグを付ける：

```python
tags = {
    "Project": "FaceAuth",
    "Environment": "dev|staging|prod",
    "ManagedBy": "CDK",
    "Owner": "team-name",
    "CostCenter": "cost-center-id"
}
```

### リソース命名

- **一貫性:** すべてのリソースに`FaceAuth-`プレフィックス
- **環境識別:** 環境名を含める（dev, staging, prod）
- **目的明示:** リソースの目的が名前から分かる

### セキュリティ設定

1. **暗号化必須**
   - S3: AWS管理キーまたはKMS
   - DynamoDB: AWS管理キー
   - 転送中: TLS/HTTPS

2. **アクセス制御**
   - IAM最小権限の原則
   - セキュリティグループで通信制限
   - パブリックアクセスブロック

3. **ログとモニタリング**
   - CloudWatch Logs有効化
   - メトリクス収集
   - アラーム設定

---

## 環境変数管理

### 必須環境変数

```bash
# AWS設定
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# S3
FACE_AUTH_BUCKET=face-auth-images-{account}-{region}

# DynamoDB
CARD_TEMPLATES_TABLE=FaceAuth-CardTemplates
EMPLOYEE_FACES_TABLE=FaceAuth-EmployeeFaces
AUTH_SESSIONS_TABLE=FaceAuth-AuthSessions

# Cognito
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=your-client-id

# Rekognition
REKOGNITION_COLLECTION_ID=face-auth-employees

# タイムアウト
AD_TIMEOUT=10
LAMBDA_TIMEOUT=15
SESSION_TIMEOUT_HOURS=8
```

### 環境別設定

- **開発環境:** `.env.development`
- **ステージング:** `.env.staging`
- **本番環境:** `.env.production`

**注意:** `.env`ファイルは`.gitignore`に含める

---

## コードレビュー基準

### レビュー観点

1. **機能性**
   - 要件を満たしているか
   - エッジケースを考慮しているか

2. **コード品質**
   - 命名規則に従っているか
   - Type hintsとdocstringsがあるか
   - 適切なエラーハンドリングがあるか

3. **テスト**
   - テストが含まれているか
   - テストカバレッジは十分か

4. **セキュリティ**
   - 機密情報の漏洩がないか
   - 適切な権限設定か

5. **パフォーマンス**
   - タイムアウト制限を守っているか
   - 不要なAPI呼び出しがないか

---

## デプロイメント

### デプロイ前チェックリスト

- [ ] すべてのテストが通過
- [ ] ドキュメントが更新されている
- [ ] 環境変数が設定されている
- [ ] セキュリティ設定が確認されている
- [ ] CORS設定が適切（本番環境）
- [ ] ログ設定が有効

### デプロイ手順

```bash
# 1. テスト実行
python -m pytest tests/ --ignore=tests/test_ad_connector.py -v

# 2. CDK差分確認
cdk diff

# 3. デプロイ
cdk deploy

# 4. 動作確認
# API Gatewayエンドポイントにリクエスト送信
```

---

## トラブルシューティング

### よくある問題

1. **Lambda タイムアウト**
   - 15秒制限を確認
   - TimeoutManagerを使用

2. **AD接続エラー**
   - 10秒タイムアウトを確認
   - セキュリティグループ設定を確認
   - Direct Connect接続を確認

3. **テスト失敗**
   - AWS認証情報を確認
   - 環境変数を確認
   - モックが適切に設定されているか確認

---

## 参考資料

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [pytest Documentation](https://docs.pytest.org/)

---

**最終更新:** 2024
**バージョン:** 1.0
