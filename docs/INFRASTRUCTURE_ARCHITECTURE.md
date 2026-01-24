# Face-Auth IdP System - Infrastructure Architecture

## 概要

このドキュメントは、Face-Auth IdP システムのAWSインフラストラクチャアーキテクチャを説明します。VPC構成、ネットワーク配置、セキュリティ設定、およびパブリックアクセス可能性について詳述します。

---

## 🏗️ VPC とネットワーク構成

### VPC 基本設定

```
VPC CIDR: 10.0.0.0/16
Availability Zones: 2
NAT Gateways: 1
```

### サブネット構成

#### 1. Public Subnet (CIDR: /24)
**用途:**
- NAT Gateway配置
- インターネットゲートウェイ経由でインターネットアクセス

**配置リソース:**
- NAT Gateway
- (将来的に) Bastion Host

#### 2. Private Subnet with Egress (CIDR: /24)
**用途:**
- Lambda関数の配置 ✅
- NAT Gateway経由でインターネットアクセス可能
- 外部からの直接アクセス不可

**配置リソース:**
- 全Lambda関数（enrollment, face_login, emergency_auth, re_enrollment, status）

**特徴:**
- NAT Gateway経由でAWSサービスにアクセス
- VPC Endpoint経由でS3/DynamoDBにアクセス（より安全・高速）
- Direct Connect経由でオンプレミスADにアクセス

#### 3. Isolated Subnet (CIDR: /24)
**用途:**
- 完全に隔離されたリソース用
- インターネットアクセスなし

**配置リソース:**
- (現在未使用、将来の拡張用)

---

## 🔐 セキュリティグループ

### 1. LambdaSecurityGroup
**適用対象:** 全Lambda関数

**ルール:**
- **Outbound:** すべて許可
  - AWS サービス（Rekognition, Textract, Cognito）へのアクセス
  - VPC Endpoint経由でS3/DynamoDBへのアクセス

### 2. ADSecurityGroup
**適用対象:** AD接続が必要なLambda関数

**ルール:**
- **Outbound (LDAPS):** 
  - Protocol: TCP
  - Port: 636
  - Destination: 10.0.0.0/8 (オンプレミスネットワーク)
  - Description: LDAPS traffic to on-premises Active Directory

- **Outbound (LDAP - Fallback):**
  - Protocol: TCP
  - Port: 389
  - Destination: 10.0.0.0/8
  - Description: LDAP traffic to on-premises Active Directory

---

## 🌐 VPC Endpoints

### S3 VPC Endpoint (Gateway型)
**目的:** Lambda関数からS3への安全で高速なアクセス

**メリット:**
- インターネット経由不要
- NAT Gateway料金削減
- レイテンシ削減
- セキュリティ向上

### DynamoDB VPC Endpoint (Gateway型)
**目的:** Lambda関数からDynamoDBへの安全で高速なアクセス

**メリット:**
- インターネット経由不要
- NAT Gateway料金削減
- レイテンシ削減
- セキュリティ向上

---

## 🔌 Direct Connect 構成

### Customer Gateway
**設定:**
```python
BGP ASN: 65000 (Private ASN)
IP Address: 203.0.113.1 (プレースホルダー)
Type: ipsec.1
```

**⚠️ 注意:**
- 実際のデプロイ時には実際のオンプレミスIPとASNに変更が必要
- Direct Connectの物理接続は別途AWS Console/CLIで設定
- ネットワークプロバイダーとの調整が必要

**用途:**
- オンプレミスActive Directoryへの安全な接続
- 10秒タイムアウト制限付き

---

## 🌐 Public アクセス可能性

### ✅ Public アクセス可能なコンポーネント

#### 1. API Gateway
**エンドポイント形式:**
```
https://{api-id}.execute-api.{region}.amazonaws.com/prod
```

**利用可能なエンドポイント:**
- `POST /auth/enroll` - 直員登録
- `POST /auth/login` - 顔認証ログイン
- `POST /auth/emergency` - 緊急認証
- `POST /auth/re-enroll` - 再登録
- `GET /auth/status` - 認証状態確認

**アクセス制御:**
- CORS設定: `allow_origins=["*"]` ⚠️ **本番環境では制限必要**
- API Key: オプション（使用プラン付き）
- レート制限: 100 req/sec
- バースト制限: 200 req/sec
- 日次クォータ: 10,000 requests

**セキュリティ設定:**
```python
throttle=apigateway.ThrottleSettings(
    rate_limit=100,
    burst_limit=200
)
quota=apigateway.QuotaSettings(
    limit=10000,
    period=apigateway.Period.DAY
)
```

#### 2. Cognito User Pool
**アクセス:**
- Public エンドポイント（AWS管理）
- フロントエンドから直接アクセス可能
- JWT トークン発行・検証

**設定:**
- ユーザー名ログインのみ（メール/電話番号なし）
- パスワードポリシー: 12文字以上、大小英数字+記号
- トークン有効期限:
  - Access Token: 1時間
  - ID Token: 1時間
  - Refresh Token: 30日

---

### ❌ Public アクセス不可なコンポーネント

#### 1. Lambda 関数
**配置:** Private Subnet with Egress

**アクセス方法:**
- API Gateway経由でのみアクセス可能
- 直接呼び出し不可

**Lambda関数一覧:**
- `FaceAuth-Enrollment`
- `FaceAuth-FaceLogin`
- `FaceAuth-EmergencyAuth`
- `FaceAuth-ReEnrollment`
- `FaceAuth-Status`

**設定:**
```python
timeout=Duration.seconds(15)  # 15秒タイムアウト
memory_size=512  # 512MB メモリ
vpc_subnets=ec2.SubnetSelection(
    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
)
```

#### 2. S3 Bucket
**セキュリティ設定:**
```python
block_public_access=s3.BlockPublicAccess.BLOCK_ALL
encryption=s3.BucketEncryption.S3_MANAGED
```

**アクセス方法:**
- Lambda関数からIAMロール経由
- 署名付きURL経由（必要に応じて）

**CORS設定:**
```python
allowed_origins=["*"]  # ⚠️ 本番環境では制限必要
allowed_methods=[GET, POST, PUT]
```

**フォルダ構造:**
- `enroll/` - 登録時の顔画像（永久保管）
- `logins/` - ログイン試行画像（30日後自動削除）
- `temp/` - 一時処理ファイル（1日後自動削除）

#### 3. DynamoDB テーブル
**アクセス方法:**
- VPC内からのみアクセス
- IAMロール経由でのみアクセス

**テーブル一覧:**
- `FaceAuth-CardTemplates` - カードテンプレート
- `FaceAuth-EmployeeFaces` - 従業員顔データ
- `FaceAuth-AuthSessions` - 認証セッション（TTL有効）

**セキュリティ:**
```python
encryption=dynamodb.TableEncryption.AWS_MANAGED
point_in_time_recovery=True
```

#### 4. VPC リソース
**アクセス:**
- Private/Isolated Subnet内
- セキュリティグループで保護
- 外部から直接アクセス不可

---

## 📊 アクセスフロー図

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │   API Gateway (Public) │ ✅ Public アクセス可能
              │  - CORS設定           │
              │  - レート制限         │
              │  - API Key (Optional) │
              └──────────┬───────────┘
                         │
                         ↓
              ┌──────────────────────┐
              │  Lambda Functions     │ ❌ 直接アクセス不可
              │  (Private Subnet)     │
              │  - Enrollment         │
              │  - Face Login         │
              │  - Emergency Auth     │
              │  - Re-enrollment      │
              │  - Status             │
              └──────────┬───────────┘
                         │
         ┌───────────────┼───────────────┬──────────────┐
         │               │               │              │
         ↓               ↓               ↓              ↓
    ┌────────┐    ┌──────────┐    ┌──────────┐   ┌─────────┐
    │   S3   │    │ DynamoDB │    │Rekognition│   │Textract │
    │(Private)│    │(Private) │    │  (AWS)   │   │  (AWS)  │
    └────────┘    └──────────┘    └──────────┘   └─────────┘
         ↑               ↑               ↑              ↑
         │               │               │              │
    VPC Endpoint    VPC Endpoint    NAT Gateway   NAT Gateway
         
         
         ↓ (Direct Connect)
    ┌──────────────────┐
    │  On-Premises AD  │
    │  (LDAPS: 636)    │
    └──────────────────┘
```

---

## 🔐 セキュリティ評価

### ✅ 実装済みのセキュリティ対策

#### 1. ネットワークセキュリティ
- ✅ Lambda関数をPrivate Subnetに配置
- ✅ セキュリティグループで通信制限
- ✅ VPC Endpoint使用（S3/DynamoDB）
- ✅ NAT Gateway経由でインターネットアクセス制御

#### 2. データ保護
- ✅ S3バケットのパブリックアクセスブロック
- ✅ S3暗号化（AWS管理キー）
- ✅ DynamoDB暗号化（AWS管理キー）
- ✅ ポイントインタイムリカバリ有効

#### 3. アクセス制御
- ✅ IAM最小権限の原則
- ✅ Lambda実行ロールの分離
- ✅ API Gatewayレート制限
- ✅ Cognito認証統合

#### 4. 監視とログ
- ✅ CloudWatch Logs統合
- ✅ API Gatewayアクセスログ
- ✅ Lambda関数ログ（1ヶ月保持）
- ✅ メトリクス有効化

#### 5. タイムアウト管理
- ✅ Lambda 15秒タイムアウト
- ✅ AD 10秒タイムアウト
- ✅ API Gateway 29秒タイムアウト

---

### ⚠️ 本番環境で修正が必要な設定

#### 1. CORS設定の制限
**現在の設定:**
```python
# API Gateway
allow_origins=apigateway.Cors.ALL_ORIGINS  # ["*"]

# S3 Bucket
allowed_origins=["*"]
```

**本番環境での推奨設定:**
```python
# API Gateway
allow_origins=["https://your-frontend-domain.com"]

# S3 Bucket
allowed_origins=["https://your-frontend-domain.com"]
```

#### 2. API Key認証の強制
**現在:** オプション

**本番環境での推奨:**
- API Key必須化
- 使用プランの厳格化
- クライアント別のAPI Key発行

#### 3. Direct Connect設定
**現在の設定（プレースホルダー）:**
```python
ip_address="203.0.113.1"  # プレースホルダー
bgp_asn=65000  # Private ASN
```

**本番環境での必要作業:**
- 実際のオンプレミスIPアドレスに変更
- 実際のBGP ASNに変更
- Direct Connect物理接続の設定
- ネットワークプロバイダーとの調整

#### 4. ログ保持期間の延長
**現在:** 1ヶ月

**本番環境での推奨:**
- セキュリティログ: 6ヶ月〜1年
- 監査ログ: 法規制に応じて設定
- S3へのアーカイブ検討

#### 5. WAF (Web Application Firewall) の追加
**推奨:**
- API GatewayにAWS WAF統合
- SQLインジェクション対策
- XSS対策
- レート制限の強化

---

## 💰 コスト最適化

### VPC Endpoint使用によるコスト削減
**削減項目:**
- NAT Gateway データ転送料金
- インターネット転送料金

**推定削減額:**
- S3/DynamoDBトラフィックが多い場合、月$50-100程度の削減可能

### Lambda配置の最適化
**現在:** Private Subnet with NAT Gateway

**代替案（コスト削減）:**
- Lambda関数をVPC外に配置
- VPC Endpointのみ使用
- Direct Connect不要な場合に検討

**トレードオフ:**
- コスト削減 vs セキュリティ
- Direct Connect接続が不要な場合のみ推奨

---

## 📋 デプロイ後の確認事項

### 1. VPC設定確認
```bash
# VPC ID確認
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=FaceAuthVPC"

# サブネット確認
aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc-id>"

# セキュリティグループ確認
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=<vpc-id>"
```

### 2. Lambda設定確認
```bash
# Lambda関数一覧
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `FaceAuth`)].FunctionName'

# VPC設定確認
aws lambda get-function-configuration --function-name FaceAuth-Enrollment
```

### 3. API Gateway確認
```bash
# API一覧
aws apigateway get-rest-apis --query 'items[?name==`FaceAuth-API`]'

# エンドポイントURL確認
# CloudFormation Outputsから取得
```

### 4. S3バケット確認
```bash
# バケット一覧
aws s3 ls | grep face-auth

# パブリックアクセス設定確認
aws s3api get-public-access-block --bucket <bucket-name>

# ライフサイクルポリシー確認
aws s3api get-bucket-lifecycle-configuration --bucket <bucket-name>
```

### 5. DynamoDB確認
```bash
# テーブル一覧
aws dynamodb list-tables --query 'TableNames[?starts_with(@, `FaceAuth`)]'

# TTL設定確認
aws dynamodb describe-time-to-live --table-name FaceAuth-AuthSessions
```

---

## 🚀 次のステップ

### デプロイ前の準備
1. ✅ AWS CLI設定
2. ✅ AWS CDK インストール
3. ✅ 環境変数設定
4. ⚠️ Direct Connect設定（オンプレミスAD接続が必要な場合）

### デプロイ手順
```bash
# 1. 依存関係インストール
npm install -g aws-cdk
pip install -r requirements.txt

# 2. CDK Bootstrap（初回のみ）
cdk bootstrap

# 3. スタック確認
cdk synth

# 4. デプロイ
cdk deploy

# 5. 出力確認
cdk deploy --outputs-file outputs.json
```

### デプロイ後の作業
1. API Gateway URLの取得
2. Cognito User Pool ID/Client IDの取得
3. フロントエンド環境変数設定
4. 初期データ投入（カードテンプレート）
5. 統合テスト実行

---

## 📚 関連ドキュメント

- [DEPLOYMENT_GUIDE.md](../DEPLOYMENT_GUIDE.md) - デプロイ手順
- [LOCAL_EXECUTION_GUIDE.md](../LOCAL_EXECUTION_GUIDE.md) - ローカル実行ガイド
- [CHECKPOINT_11_VERIFICATION_REPORT.md](../CHECKPOINT_11_VERIFICATION_REPORT.md) - バックエンド検証レポート

---

**作成日:** 2024
**バージョン:** 1.0
**最終更新:** 2024
