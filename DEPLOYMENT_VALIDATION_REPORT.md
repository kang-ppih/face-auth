# デプロイ検証レポート - Face-Auth IdP System

**日付:** 2026-01-24  
**環境:** AWS Profile `dev`  
**アカウント:** 979431736455  
**リージョン:** ap-northeast-1 (東京)

## 実行した検証

### 1. AWS 認証情報確認
✅ **成功** - AWS profile `dev` で認証済み
- User: PPIH.m.kan
- Account: 979431736455
- ARN: arn:aws:iam::979431736455:user/PPIH.m.kan

### 2. Python 構文チェック
✅ **成功** - app.py および infrastructure/face_auth_stack.py の構文エラーなし

### 3. CDK スタック構造分析

#### 検出された潜在的な問題

## 🔴 重大な問題

### 1. 環境変数の未設定
**問題:** `app.py` が環境変数 `CDK_DEFAULT_ACCOUNT` と `CDK_DEFAULT_REGION` に依存
```python
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region=os.getenv('CDK_DEFAULT_REGION', 'ap-northeast-1')
)
```

**影響:** これらの環境変数が設定されていない場合、デプロイが失敗する可能性

**解決策:**
```bash
# デプロイ前に環境変数を設定
export CDK_DEFAULT_ACCOUNT=979431736455
export CDK_DEFAULT_REGION=ap-northeast-1

# または PowerShell の場合
$env:CDK_DEFAULT_ACCOUNT="979431736455"
$env:CDK_DEFAULT_REGION="ap-northeast-1"
```

### 2. 環境識別子の欠如
**問題:** スタックに環境識別子（dev/staging/prod）が含まれていない
- 現在のスタック名: `FaceAuthIdPStack`
- 推奨: `FaceAuthIdPStack-Dev`

**影響:** 
- 複数環境のデプロイ時にリソース名が衝突
- タグに環境情報が含まれない
- コスト追跡が困難

**解決策:** `app.py` を修正して環境パラメータを追加

### 3. Customer Gateway の IP アドレス
**問題:** プレースホルダーIPアドレスが使用されている
```python
ip_address="203.0.113.1",  # Placeholder public IP - replace with actual
```

**影響:** Direct Connect 接続が機能しない

**解決策:** 実際のオンプレミスゲートウェイのパブリックIPに置き換え

## ⚠️ 警告レベルの問題

### 4. CORS 設定が開放的
**問題:** すべてのオリジンを許可
```python
allow_origins=apigateway.Cors.ALL_ORIGINS,  # Restrict in production
```

**影響:** セキュリティリスク（開発環境では許容可能）

**推奨:** 開発環境でも特定のオリジンに制限

### 5. Lambda 関数のコードパス
**問題:** Lambda 関数のコードが `lambda/` ディレクトリから読み込まれる
```python
code=lambda_.Code.from_asset("lambda/enrollment"),
```

**確認必要:** 
- `lambda/enrollment/handler.py` に `handle_enrollment` 関数が存在するか
- `lambda/shared/` モジュールが正しくパッケージングされるか

### 6. Rekognition コレクションの事前作成
**問題:** コレクション `face-auth-employees` が存在することを前提
```python
"REKOGNITION_COLLECTION_ID": "face-auth-employees",
```

**影響:** 初回デプロイ時にコレクションが存在しない場合、Lambda 実行時エラー

**解決策:** Lambda 関数内でコレクションの存在確認と自動作成を実装

### 7. Python 依存関係
**問題:** Python 3.14 環境で一部のパッケージがインストール失敗
- `Pillow==10.1.0` のビルドエラー
- `python-ldap==3.4.3` も同様の問題の可能性

**影響:** Lambda レイヤーまたはデプロイパッケージの作成失敗

**解決策:** 
- Python 3.9 環境を使用（Lambda ランタイムと一致）
- または Docker を使用してパッケージをビルド

## 📋 デプロイ前チェックリスト

### 必須対応項目
- [ ] 環境変数 `CDK_DEFAULT_ACCOUNT` を設定
- [ ] 環境変数 `CDK_DEFAULT_REGION` を設定
- [ ] Customer Gateway の IP アドレスを実際の値に変更
- [ ] Lambda 関数コードが存在することを確認
- [ ] Python 3.9 環境で依存関係をビルド

### 推奨対応項目
- [ ] 環境識別子を追加（dev/staging/prod）
- [ ] CORS 設定を制限
- [ ] Rekognition コレクション自動作成ロジックを追加
- [ ] タグ設定を追加（Project, Environment, Owner など）

### 確認項目
- [ ] IAM ユーザーに必要な権限があるか
  - CloudFormation
  - Lambda
  - S3
  - DynamoDB
  - Rekognition
  - Textract
  - Cognito
  - VPC/EC2
  - IAM
  - API Gateway
  - CloudWatch Logs
- [ ] リージョン `ap-northeast-1` が正しいか
- [ ] アカウント制限（Lambda 同時実行数、VPC 制限など）

## 🔧 推奨される修正

### 1. app.py の改善

```python
#!/usr/bin/env python3
"""
Face-Auth IdP System - AWS CDK Application Entry Point
"""

import os
import aws_cdk as cdk
from infrastructure.face_auth_stack import FaceAuthStack

app = cdk.App()

# 環境名を取得（デフォルトは dev）
env_name = app.node.try_get_context("env") or os.getenv("ENVIRONMENT", "dev")

# AWS 環境設定
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT') or os.getenv('AWS_ACCOUNT_ID'),
    region=os.getenv('CDK_DEFAULT_REGION', 'ap-northeast-1')
)

# スタック名に環境を含める
stack_name = f"FaceAuthIdPStack-{env_name.capitalize()}"

# Deploy the Face-Auth IdP Stack
FaceAuthStack(
    app, 
    stack_name,
    env=env,
    env_name=env_name,
    description=f"Face-Auth Identity Provider System - {env_name.upper()} Environment"
)

app.synth()
```

### 2. デプロイコマンド

```bash
# 環境変数を設定してデプロイ
export CDK_DEFAULT_ACCOUNT=979431736455
export CDK_DEFAULT_REGION=ap-northeast-1

# または PowerShell
$env:CDK_DEFAULT_ACCOUNT="979431736455"
$env:CDK_DEFAULT_REGION="ap-northeast-1"

# CDK Bootstrap（初回のみ）
cdk bootstrap aws://979431736455/ap-northeast-1

# デプロイ（差分確認）
cdk diff --context env=dev

# デプロイ実行
cdk deploy --context env=dev
```

## 📊 リソース見積もり

### 作成されるリソース
- VPC: 1
- Subnets: 6 (Public x2, Private x2, Isolated x2)
- NAT Gateway: 1
- Security Groups: 2
- VPC Endpoints: 2 (S3, DynamoDB)
- S3 Buckets: 1
- DynamoDB Tables: 3
- Lambda Functions: 5
- API Gateway: 1
- Cognito User Pool: 1
- CloudWatch Log Groups: 6
- IAM Roles: 1
- IAM Policies: 1

### 推定コスト（月額、開発環境）
- VPC: 無料
- NAT Gateway: ~$32
- S3: ~$1-5（使用量による）
- DynamoDB: ~$1-10（オンデマンド）
- Lambda: ~$0-5（無料枠内）
- API Gateway: ~$3.50（100万リクエスト）
- Cognito: 無料（50,000 MAU まで）
- CloudWatch Logs: ~$0.50

**合計: 約 $40-60/月**

## ⚡ 次のステップ

1. **環境変数の設定**
   ```bash
   $env:CDK_DEFAULT_ACCOUNT="979431736455"
   $env:CDK_DEFAULT_REGION="ap-northeast-1"
   ```

2. **CDK Bootstrap（初回のみ）**
   ```bash
   cdk bootstrap aws://979431736455/ap-northeast-1 --profile dev
   ```

3. **差分確認**
   ```bash
   cdk diff --profile dev --context env=dev
   ```

4. **デプロイ実行**
   ```bash
   cdk deploy --profile dev --context env=dev
   ```

## 📝 注意事項

- Direct Connect の設定は別途 AWS Console または CLI で実施が必要
- オンプレミス AD への接続テストは物理接続後に実施
- Rekognition コレクションは初回 Lambda 実行時に自動作成されるよう実装推奨
- 本番環境デプロイ前に必ずステージング環境でテスト

---

**検証者:** Kiro AI Assistant  
**ステータス:** 修正推奨事項あり  
**次回アクション:** 環境変数設定後に CDK diff 実行
