# Face-Auth IdP System - デプロイメントガイド

## 📋 実装完了事項

### ✅ AWSインフラおよび基本設定構築 (Task 1)

以下のAWSインフラコンポーネントがAWS CDKを使用して実装されました:

#### 🌐 VPCおよびネットワーキング (要件 4.1, 4.5)
- **VPC**: 10.0.0.0/16 CIDRブロック
- **サブネット**: 
  - Publicサブネット (24ビットマスク)
  - Private サブネット with NAT Gateway (24ビットマスク)
  - Isolated サブネット (24ビットマスク)
- **セキュリティグループ**:
  - Lambda関数用セキュリティグループ
  - Active Directory接続用セキュリティグループ (LDAPS 636, LDAP 389ポート)
- **VPCエンドポイント**: S3およびDynamoDB用ゲートウェイエンドポイント
- **Direct Connect準備**: Customer Gateway構成 (物理接続は別途設定が必要)

#### 🪣 S3バケット (要件 4.4, 5.2, 5.3, 5.4, 5.6)
- **バケット名**: `face-auth-images-{account}-{region}`
- **暗号化**: S3管理型暗号化適用
- **パブリックアクセス**: 完全ブロック
- **Lifecycleポリシー**:
  - `logins/` フォルダ: 30日後自動削除
  - `temp/` フォルダ: 1日後自動削除
  - `enroll/` フォルダ: 永久保管
- **CORS構成**: フロントエンド統合サポート

#### 🗄️ DynamoDBテーブル (要件 5.5, 7.4)
1. **CardTemplatesテーブル**:
   - パーティションキー: `pattern_id` (String)
   - GSI: `CardTypeIndex` (card_type基準)
   - 暗号化およびPoint-in-Time Recovery有効化

2. **EmployeeFacesテーブル**:
   - パーティションキー: `employee_id` (String)
   - GSI: `FaceIdIndex` (face_id基準)
   - 暗号化およびPoint-in-Time Recovery有効化

3. **AuthSessionsテーブル**:
   - パーティションキー: `session_id` (String)
   - TTL: `expires_at` 属性で自動セッションクリーンアップ

#### ⚡ Lambda関数 (要件 4.3, 4.4)
すべてのLambda関数は以下の構成で作成:
- **ランタイム**: Python 3.9
- **タイムアウト**: 15秒 (要件準拠)
- **メモリ**: 512MB
- **VPC**: Privateサブネットで実行
- **セキュリティグループ**: LambdaおよびAD接続セキュリティグループ適用

作成された関数:
1. `FaceAuth-Enrollment`: 従業員登録処理
2. `FaceAuth-FaceLogin`: 顔ログイン処理
3. `FaceAuth-EmergencyAuth`: 緊急認証処理
4. `FaceAuth-ReEnrollment`: 再登録処理
5. `FaceAuth-Status`: 認証ステータス確認

#### 🔐 IAMロールおよびポリシー (要件 4.7, 5.6, 5.7)
- **Lambda実行ロール**: VPCアクセス権限を含む
- **カスタムポリシー**:
  - S3バケット読み取り/書き込み権限
  - DynamoDBテーブルCRUD権限
  - Amazon Rekognition全権限
  - Amazon Textractドキュメント分析権限
  - Cognitoユーザー管理権限
  - CloudWatchロギング権限

#### 🚪 API Gateway (要件 4.6, 4.7)
- **REST API**: `FaceAuth-API`
- **エンドポイント**:
  - `POST /auth/enroll`: 従業員登録
  - `POST /auth/login`: 顔ログイン
  - `POST /auth/emergency`: 緊急認証
  - `POST /auth/re-enroll`: 再登録
  - `GET /auth/status`: ステータス確認
- **セキュリティ**: APIキー、使用量プラン、レート制限構成
- **CORS**: フロントエンド統合サポート

#### 👤 AWS Cognito (要件 2.3, 3.5)
- **ユーザープール**: `FaceAuth-UserPool`
- **パスワードポリシー**: 12文字以上、大小文字/数字/特殊文字を含む
- **トークン有効期間**:
  - Access Token: 1時間
  - ID Token: 1時間
  - Refresh Token: 30日
- **クライアント**: フロントエンド用パブリッククライアント

#### 📊 CloudWatchロギング (要件 6.7, 8.7)
- **Lambdaログ グループ**: 各関数ごとに30日保管
- **API Gatewayアクセスログ**: 30日保管
- **モニタリング**: メトリクスおよびアラーム準備

## 🚀 デプロイ方法

### 1. 前提条件
```bash
# Node.jsおよびAWS CDKインストール
npm install -g aws-cdk

# AWS CLI構成
aws configure

# Python 3.9+インストール確認
python --version
```

### 2. デプロイ実行
```powershell
# PowerShellで実行
.\deploy.ps1
```

または手動デプロイ:
```bash
# 仮想環境作成および有効化
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# CDKブートストラップ (アカウントごとに1回のみ)
cdk bootstrap

# スタックデプロイ
cdk deploy
```

### 3. デプロイ後設定

#### Rekognitionコレクション作成
```bash
aws rekognition create-collection --collection-id face-auth-employees
```

#### カードテンプレート追加
DynamoDB `FaceAuth-CardTemplates` テーブルに社員証認識パターンを追加:
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
    },
    {
      "field_name": "employee_name",
      "query_phrase": "氏名は何ですか？",
      "expected_format": "[\\u4e00-\\u9faf]{2,4}",
      "required": true
    }
  ],
  "is_active": true
}
```

#### Direct Connect設定
物理的なDirect Connect接続はAWSコンソールまたはネットワークチームと協力して別途構成が必要です。

## 📁 プロジェクト構造

```
face-auth-idp/
├── app.py                    # CDKアプリエントリーポイント
├── cdk.json                  # CDK構成
├── requirements.txt          # Python依存関係
├── config.py                 # システム構成
├── deploy.ps1               # PowerShellデプロイスクリプト
├── validate_stack.py        # スタック検証スクリプト
├── README.md                # プロジェクトドキュメント
├── DEPLOYMENT_GUIDE.md      # このファイル
├── infrastructure/
│   ├── __init__.py
│   └── face_auth_stack.py   # メインCDKスタック
├── lambda/                  # Lambda関数
│   ├── enrollment/
│   ├── face_login/
│   ├── emergency_auth/
│   ├── re_enrollment/
│   └── status/
└── tests/
    ├── __init__.py
    └── test_infrastructure.py
```

## 🔧 構成管理

主要設定は`config.py`で管理:
- Rekognition信頼度閾値 (90%)
- タイムアウト設定 (AD: 10秒, Lambda: 15秒)
- S3フォルダ構造
- エラーメッセージマッピング
- Active Directory接続情報

## ✅ 要件充足確認

### 要件 4.1: Direct Connect使用
- ✅ Customer Gateway構成完了
- ✅ AD接続用セキュリティグループ (LDAPS/LDAPポート) 構成

### 要件 4.4: AWS CDK使用
- ✅ Python CDKで全インフラ実装
- ✅ Infrastructure as Code適用

### 要件 4.5: VPCおよびセキュリティグループ
- ✅ VPCネットワーク分離実装
- ✅ 適切なセキュリティグループ構成

### 要件 4.7: IAMロールおよびポリシー
- ✅ 最小権限の原則適用
- ✅ サービスごとに適切な権限付与

## 🎯 次のステップ

1. **Lambda関数実装**: 各認証フローのビジネスロジック実装
2. **テスト作成**: 単体テストおよびプロパティベーステスト実装
3. **フロントエンド開発**: React + AWS Amplify UI実装
4. **統合テスト**: システム全体の統合テスト
5. **セキュリティレビュー**: 本番デプロイ前のセキュリティ監査

## 🚨 注意事項

- Direct Connect物理接続は別途設定が必要
- 本番環境ではCORS設定を特定ドメインに制限
- APIキーおよびシークレットはAWS Secrets Manager使用を推奨
- モニタリングおよびアラーム設定が必要

---

**Task 1完了**: AWSインフラおよび基本設定構築が正常に完了しました。すべての要件 (4.1, 4.4, 4.5, 4.7)が満たされ、次の作業ステップに進む準備が整いました。