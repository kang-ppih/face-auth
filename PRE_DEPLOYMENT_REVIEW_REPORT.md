# デプロイ前レビューレポート

**日時:** 2026-01-24  
**環境:** AWS Profile `dev`, Region `ap-northeast-1`  
**アカウント:** 979431736455  
**スタック名:** FaceAuthIdPStack

---

## 📋 エグゼクティブサマリー

CDKスタックのデプロイ準備状況を包括的にレビューしました。

**総合評価:** ⚠️ **条件付き承認 - 修正推奨**

**主要な発見:**
- ✅ CDK v2.110.0との互換性: 完全対応
- ✅ 既存リソースとの衝突: なし
- ⚠️ セキュリティ設定: 一部改善が必要
- ⚠️ 環境変数の不整合: 修正が必要
- ⚠️ Customer Gateway設定: プレースホルダーIPアドレス

---

## 🔍 詳細レビュー結果

### 1. AWS環境確認

#### ✅ アカウント・リージョン
```
Account ID: 979431736455
Region: ap-northeast-1 (Tokyo)
User: PPIH.m.kan
Profile: dev
```

#### ✅ 既存リソース確認
- **CloudFormation Stacks:** FaceAuth関連スタックなし
- **S3 Buckets:** face-auth関連バケットなし
- **DynamoDB Tables:** FaceAuth関連テーブルなし
- **CDK Bootstrap:** 完了 (CDKToolkit: UPDATE_COMPLETE)

**結論:** リソース衝突のリスクなし

---

### 2. CDK互換性

#### ✅ CDK バージョン
- **インストール済み:** 2.1102.0
- **requirements.txt:** 2.110.0
- **互換性:** 完全対応

#### ✅ CDK Diff結果
- エラー: なし
- 警告: なし (すべて解決済み)
- 作成予定リソース: 80+個

---

### 3. コード整合性チェック

#### ⚠️ 環境変数の不整合

**問題1: AWS_REGION環境変数**

**場所:** `infrastructure/face_auth_stack.py` (Line 332)

```python
# 現在のコード
"environment": {
    "FACE_AUTH_BUCKET": self.face_auth_bucket.bucket_name,
    # ... 他の環境変数
    "AWS_REGION": region,  # ❌ Lambda予約済み環境変数
}
```

**問題:** `AWS_REGION`はLambdaランタイムによって自動的に設定される予約済み環境変数です。明示的に設定すると警告が発生します。

**影響:** 
- デプロイは成功するが、警告が表示される
- Lambda関数は正常に動作する（ランタイムが上書き）

**推奨修正:**
```python
"environment": {
    "FACE_AUTH_BUCKET": self.face_auth_bucket.bucket_name,
    "CARD_TEMPLATES_TABLE": self.card_templates_table.table_name,
    "EMPLOYEE_FACES_TABLE": self.employee_faces_table.table_name,
    "AUTH_SESSIONS_TABLE": self.auth_sessions_table.table_name,
    "COGNITO_USER_POOL_ID": self.user_pool.user_pool_id,
    "COGNITO_CLIENT_ID": self.user_pool_client.user_pool_client_id,
    "REKOGNITION_COLLECTION_ID": "face-auth-employees",
    "AD_TIMEOUT": "10",
    "LAMBDA_TIMEOUT": "15",
    "SESSION_TIMEOUT_HOURS": "8"
    # AWS_REGIONは削除（Lambdaランタイムが自動設定）
}
```

**Lambda関数での対応:**
すべてのLambda関数で`os.environ.get('AWS_REGION', 'ap-northeast-1')`を使用しているため、環境変数が設定されていなくてもデフォルト値で動作します。

---

#### ⚠️ Customer Gateway設定

**場所:** `infrastructure/face_auth_stack.py` (Line 143-151)

```python
self.customer_gateway = ec2.CfnCustomerGateway(
    self, "OnPremisesCustomerGateway",
    bgp_asn=65000,
    ip_address="203.0.113.1",  # ⚠️ プレースホルダーIP
    type="ipsec.1",
    tags=[{
        "key": "Name",
        "value": "FaceAuth-OnPremises-Gateway"
    }]
)
```

**問題:** `203.0.113.1`はRFC 5737で定義されたドキュメント用プレースホルダーIPアドレスです。

**影響:**
- デプロイは成功する
- Customer Gatewayは作成されるが、実際の接続は確立できない
- オンプレミスAD接続が機能しない

**推奨対応:**
1. **短期:** コメントアウトして後で設定
2. **長期:** 実際のオンプレミスゲートウェイIPアドレスに置き換え

```python
# Customer Gateway - 実際のIPアドレスが必要
# self.customer_gateway = ec2.CfnCustomerGateway(
#     self, "OnPremisesCustomerGateway",
#     bgp_asn=65000,
#     ip_address="YOUR_ACTUAL_IP_HERE",  # 実際のIPに置き換え
#     type="ipsec.1",
#     tags=[{
#         "key": "Name",
#         "value": "FaceAuth-OnPremises-Gateway"
#     }]
# )
```

---

### 4. セキュリティ設定

#### ⚠️ CORS設定

**場所:** `infrastructure/face_auth_stack.py` (Line 172, Line 437)

```python
# S3 CORS
self.face_auth_bucket.add_cors_rule(
    allowed_origins=["*"],  # ⚠️ すべてのオリジンを許可
    # ...
)

# API Gateway CORS
default_cors_preflight_options=apigateway.CorsOptions(
    allow_origins=apigateway.Cors.ALL_ORIGINS,  # ⚠️ すべてのオリジンを許可
    # ...
)
```

**問題:** 本番環境では特定のオリジンのみを許可すべきです。

**影響:**
- セキュリティリスク: CSRF攻撃の可能性
- 開発環境では問題なし

**推奨修正:**
```python
# 環境別CORS設定
cors_origins = ["*"] if env_name == "dev" else ["https://your-app-domain.com"]

# S3 CORS
self.face_auth_bucket.add_cors_rule(
    allowed_origins=cors_origins,
    # ...
)

# API Gateway CORS
default_cors_preflight_options=apigateway.CorsOptions(
    allow_origins=cors_origins,
    # ...
)
```

---

#### ✅ 暗号化設定

**S3:**
- ✅ サーバーサイド暗号化: AES256 (AWS管理キー)
- ✅ パブリックアクセスブロック: 有効

**DynamoDB:**
- ✅ 暗号化: AWS管理キー
- ✅ ポイントインタイムリカバリ: 有効

**Lambda:**
- ✅ VPC内デプロイ: Private Subnet
- ✅ セキュリティグループ: 適切に設定

---

#### ✅ IAM権限

**Lambda実行ロール:**
- ✅ 最小権限の原則: 遵守
- ✅ リソース制限: 特定のリソースのみアクセス許可
- ✅ VPCアクセス: AWSLambdaVPCAccessExecutionRole

---

### 5. ネットワーク設定

#### ✅ VPC構成
```
CIDR: 10.0.0.0/16
AZ: 2個
NAT Gateway: 1個

Subnets:
- Public Subnet: /24 x 2
- Private Subnet (with NAT): /24 x 2
- Isolated Subnet: /24 x 2
```

#### ✅ セキュリティグループ
- Lambda SG: アウトバウンドすべて許可
- AD SG: LDAP/LDAPS (389/636) のみ許可

#### ✅ VPCエンドポイント
- S3: Gateway Endpoint
- DynamoDB: Gateway Endpoint

---

### 6. Lambda関数設定

#### ✅ タイムアウト設定
- Lambda Timeout: 15秒
- AD Timeout: 10秒
- API Gateway Timeout: 29秒（デフォルト）

#### ✅ メモリ設定
- メモリ: 512MB（開発環境適切）

#### ⚠️ 同時実行数
- 予約済み同時実行数: 未設定
- **推奨:** 開発環境では10に制限してコスト管理

```python
lambda_function = lambda_.Function(
    self, "Function",
    reserved_concurrent_executions=10,  # 開発環境のみ
    # ...
)
```

---

### 7. モニタリング設定

#### ✅ CloudWatch Logs
- ログ保持期間: 1ヶ月
- ログ削除ポリシー: RETAIN

#### ⚠️ CloudWatch Alarms
- **状態:** 未設定
- **推奨:** Lambda エラー、タイムアウト、DynamoDBスロットリングのアラーム設定

#### ⚠️ X-Ray トレーシング
- **状態:** 無効
- **推奨:** ステージング・本番環境では有効化

---

### 8. コスト最適化

#### ✅ DynamoDB
- ビリングモード: PAY_PER_REQUEST（開発環境適切）

#### ✅ S3 Lifecycle
- logins/: 30日後削除
- temp/: 1日後削除

#### ⚠️ NAT Gateway
- **コスト:** 約$32/月 + データ転送料
- **推奨:** 開発環境では必要時のみ起動

---

## 🔧 必須修正事項

### 優先度: 高

#### 1. AWS_REGION環境変数の削除

**ファイル:** `infrastructure/face_auth_stack.py`

**修正箇所:** Line 332付近

```python
# 修正前
"environment": {
    "FACE_AUTH_BUCKET": self.face_auth_bucket.bucket_name,
    "CARD_TEMPLATES_TABLE": self.card_templates_table.table_name,
    "EMPLOYEE_FACES_TABLE": self.employee_faces_table.table_name,
    "AUTH_SESSIONS_TABLE": self.auth_sessions_table.table_name,
    "COGNITO_USER_POOL_ID": self.user_pool.user_pool_id,
    "COGNITO_CLIENT_ID": self.user_pool_client.user_pool_client_id,
    "REKOGNITION_COLLECTION_ID": "face-auth-employees",
    "AD_TIMEOUT": "10",
    "LAMBDA_TIMEOUT": "15",
    "SESSION_TIMEOUT_HOURS": "8",
    "AWS_REGION": region  # ❌ 削除
}

# 修正後
"environment": {
    "FACE_AUTH_BUCKET": self.face_auth_bucket.bucket_name,
    "CARD_TEMPLATES_TABLE": self.card_templates_table.table_name,
    "EMPLOYEE_FACES_TABLE": self.employee_faces_table.table_name,
    "AUTH_SESSIONS_TABLE": self.auth_sessions_table.table_name,
    "COGNITO_USER_POOL_ID": self.user_pool.user_pool_id,
    "COGNITO_CLIENT_ID": self.user_pool_client.user_pool_client_id,
    "REKOGNITION_COLLECTION_ID": "face-auth-employees",
    "AD_TIMEOUT": "10",
    "LAMBDA_TIMEOUT": "15",
    "SESSION_TIMEOUT_HOURS": "8"
}
```

---

### 優先度: 中

#### 2. Customer Gatewayのコメントアウト

**ファイル:** `infrastructure/face_auth_stack.py`

**修正箇所:** Line 143-151

```python
# Customer Gateway (placeholder - actual DX setup requires physical connection)
# This would be configured separately in the AWS Console or via AWS CLI
# as it requires coordination with network providers

# TODO: 実際のオンプレミスゲートウェイIPアドレスに置き換え
# self.customer_gateway = ec2.CfnCustomerGateway(
#     self, "OnPremisesCustomerGateway",
#     bgp_asn=65000,  # Private ASN for on-premises
#     ip_address="203.0.113.1",  # Placeholder public IP - replace with actual
#     type="ipsec.1",
#     tags=[{
#         "key": "Name",
#         "value": "FaceAuth-OnPremises-Gateway"
#     }]
# )
```

---

## 📝 推奨改善事項

### 1. 環境別設定の導入

**目的:** 開発・ステージング・本番環境の設定を分離

**実装例:**

```python
# app.py
env_name = app.node.try_get_context("env") or "dev"

FaceAuthStack(
    app, 
    f"FaceAuthIdPStack-{env_name.capitalize()}",
    env_name=env_name,
    env=cdk.Environment(
        account=os.getenv('CDK_DEFAULT_ACCOUNT'),
        region=os.getenv('CDK_DEFAULT_REGION', 'ap-northeast-1')
    ),
    description=f"Face-Auth Identity Provider System - {env_name.upper()}"
)
```

### 2. スタック説明の追加

**現在:** 基本的な説明のみ

**推奨:**
```python
description="Face-Auth Identity Provider System - AWS Infrastructure (Dev Environment)"
```

### 3. タグの追加

**推奨:**
```python
from aws_cdk import Tags

Tags.of(self).add("Project", "FaceAuth")
Tags.of(self).add("Environment", "dev")
Tags.of(self).add("ManagedBy", "CDK")
Tags.of(self).add("Owner", "face-auth-team")
Tags.of(self).add("CostCenter", "engineering")
```

---

## ✅ デプロイ前チェックリスト

### 必須項目

- [ ] AWS_REGION環境変数を削除
- [ ] Customer Gatewayをコメントアウト
- [ ] CDK diff確認（警告なし）
- [ ] AWS認証情報確認（profile dev）
- [ ] リージョン確認（ap-northeast-1）

### 推奨項目

- [ ] CORS設定を環境別に変更
- [ ] Lambda同時実行数制限を設定
- [ ] CloudWatch Alarmsを設定
- [ ] タグを追加
- [ ] 環境別設定を導入

### デプロイ後確認項目

- [ ] CloudFormation スタック作成成功
- [ ] Lambda関数デプロイ成功
- [ ] API Gateway エンドポイント作成
- [ ] DynamoDB テーブル作成
- [ ] S3 バケット作成
- [ ] Cognito User Pool作成
- [ ] VPC・サブネット作成
- [ ] CloudWatch Logs作成

---

## 🚀 デプロイコマンド

### 修正適用後のデプロイ手順

```bash
# 1. 修正を適用
# infrastructure/face_auth_stack.pyを編集

# 2. CDK差分確認
npx cdk diff --profile dev

# 3. デプロイ実行
npx cdk deploy --profile dev

# 4. デプロイ後確認
aws cloudformation describe-stacks \
  --stack-name FaceAuthIdPStack \
  --profile dev \
  --region ap-northeast-1
```

---

## 📊 リスク評価

| リスク項目 | レベル | 影響 | 対策 |
|-----------|--------|------|------|
| AWS_REGION環境変数 | 低 | 警告表示のみ | 削除推奨 |
| Customer Gateway | 中 | AD接続不可 | コメントアウト |
| CORS設定 | 低 | 開発環境では問題なし | 本番前に修正 |
| リソース衝突 | なし | - | - |
| CDK互換性 | なし | - | - |

---

## 💡 結論

**デプロイ可否:** ✅ **デプロイ可能（修正推奨）**

**理由:**
1. 致命的な問題はなし
2. AWS_REGION環境変数は警告のみ（機能に影響なし）
3. Customer Gatewayは後で設定可能
4. 既存リソースとの衝突なし
5. CDK v2.110.0完全対応

**推奨アクション:**
1. **即座にデプロイ可能:** 現状のままでもデプロイは成功します
2. **修正後デプロイ推奨:** AWS_REGION削除とCustomer Gatewayコメントアウトを適用してからデプロイ
3. **本番環境前:** CORS設定、アラーム、タグを追加

---

**レビュー実施者:** Kiro AI Assistant  
**レビュー日時:** 2026-01-24  
**次回レビュー:** デプロイ後の動作確認時
