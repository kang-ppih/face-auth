# タグ付け確認レポート

**日時:** 2026-01-27  
**ステータス:** ✅ **完了**

---

## 📋 タグ設定概要

すべてのAWSリソースに以下のタグが適用されています。

### 適用されたタグ

| キー | 値 | 目的 |
|------|-----|------|
| **Name** | Face-auth | リソース識別 |
| **Cost Center** | Face-auth | コスト追跡・配分 |
| **Development** | dm-dev | 開発環境識別 |
| **Project** | FaceAuth-IdP | プロジェクト分類 |
| **ManagedBy** | CDK | 管理方法識別 |

---

## ✅ タグ適用確認

### 実装箇所

**ファイル:** `infrastructure/face_auth_stack.py`

**コード:**
```python
def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    # Apply tags to all resources in this stack for cost tracking
    Tags.of(self).add("Name", "Face-auth")
    Tags.of(self).add("Cost Center", "Face-auth")
    Tags.of(self).add("Development", "dm-dev")
    Tags.of(self).add("Project", "FaceAuth-IdP")
    Tags.of(self).add("ManagedBy", "CDK")
```

### CloudFormationテンプレート確認

生成されたCloudFormationテンプレート (`cdk.out/FaceAuthIdPStack.template.json`) を確認した結果、すべてのリソースに正しくタグが適用されています。

**確認したリソース例:**
- ✅ VPC
- ✅ Subnets (Public, Private, Isolated)
- ✅ Route Tables
- ✅ Internet Gateway
- ✅ NAT Gateway
- ✅ Security Groups
- ✅ Lambda Functions
- ✅ DynamoDB Tables
- ✅ S3 Buckets
- ✅ API Gateway
- ✅ Cognito User Pool
- ✅ IAM Roles
- ✅ CloudWatch Log Groups

---

## 📊 タグ適用されるリソース一覧

### ネットワーク (VPC)
- **FaceAuthVPC** - VPC本体
- **PublicSubnetSubnet1/2** - パブリックサブネット
- **PrivateSubnetSubnet1/2** - プライベートサブネット
- **IsolatedSubnetSubnet1/2** - 分離サブネット
- **InternetGateway** - インターネットゲートウェイ
- **NATGateway** - NATゲートウェイ
- **RouteTable** - ルートテーブル（各サブネット用）
- **VPCEndpoint** - S3/DynamoDB用VPCエンドポイント

### セキュリティ
- **LambdaSecurityGroup** - Lambda用セキュリティグループ
- **ADSecurityGroup** - AD接続用セキュリティグループ

### コンピューティング (Lambda)
- **EnrollmentFunction** - 社員登録Lambda
- **FaceLoginFunction** - 顔認証ログインLambda
- **EmergencyAuthFunction** - 緊急認証Lambda
- **ReEnrollmentFunction** - 再登録Lambda
- **StatusFunction** - ステータス確認Lambda
- **FaceAuthLambdaExecutionRole** - Lambda実行ロール

### ストレージ (S3)
- **FaceAuthImageBucket** - 顔画像保存バケット

### データベース (DynamoDB)
- **CardTemplatesTable** - 社員証テンプレートテーブル
- **EmployeeFacesTable** - 社員顔データテーブル
- **AuthSessionsTable** - 認証セッションテーブル

### API (API Gateway)
- **FaceAuthAPI** - REST API
- **FaceAuthAPIKey** - APIキー
- **FaceAuthUsagePlan** - 使用量プラン

### 認証 (Cognito)
- **FaceAuthUserPool** - ユーザープール
- **FaceAuthUserPoolClient** - ユーザープールクライアント

### モニタリング (CloudWatch)
- **EnrollmentLogGroup** - 登録Lambda用ログ
- **FaceLoginLogGroup** - ログインLambda用ログ
- **EmergencyAuthLogGroup** - 緊急認証Lambda用ログ
- **ReEnrollmentLogGroup** - 再登録Lambda用ログ
- **StatusLogGroup** - ステータスLambda用ログ
- **APIAccessLogGroup** - API Gateway用ログ

---

## 💰 コスト追跡の利用方法

### AWS Cost Explorerでの確認

1. **Cost Explorerにアクセス**
   ```
   AWS Console > Billing > Cost Explorer
   ```

2. **タグでフィルタリング**
   - **Cost Center = Face-auth** でフィルタ
   - **Development = dm-dev** でフィルタ
   - **Project = FaceAuth-IdP** でフィルタ

3. **コストレポート作成**
   - グループ化: Tag: Cost Center
   - 期間: 月次/日次
   - サービス別内訳表示

### AWS CLIでの確認

```bash
# Cost Centerタグでコスト取得
aws ce get-cost-and-usage \
  --time-period Start=2026-01-01,End=2026-01-31 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=Cost\ Center \
  --filter file://filter.json \
  --profile dev \
  --region ap-northeast-1

# filter.json
{
  "Tags": {
    "Key": "Cost Center",
    "Values": ["Face-auth"]
  }
}
```

### タグベースのコスト配分レポート

```bash
# Developmentタグでグループ化
aws ce get-cost-and-usage \
  --time-period Start=2026-01-01,End=2026-01-31 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --group-by Type=TAG,Key=Development \
  --profile dev \
  --region ap-northeast-1
```

---

## 🔍 タグ確認コマンド

### デプロイ後のタグ確認

#### VPCのタグ確認
```bash
aws ec2 describe-vpcs \
  --filters "Name=tag:Name,Values=Face-auth" \
  --query "Vpcs[*].Tags" \
  --profile dev \
  --region ap-northeast-1
```

#### Lambda関数のタグ確認
```bash
aws lambda list-tags \
  --resource arn:aws:lambda:ap-northeast-1:979431736455:function:FaceAuth-Enrollment \
  --profile dev \
  --region ap-northeast-1
```

#### DynamoDBテーブルのタグ確認
```bash
aws dynamodb list-tags-of-resource \
  --resource-arn arn:aws:dynamodb:ap-northeast-1:979431736455:table/FaceAuth-EmployeeFaces \
  --profile dev \
  --region ap-northeast-1
```

#### S3バケットのタグ確認
```bash
aws s3api get-bucket-tagging \
  --bucket face-auth-images-979431736455-ap-northeast-1 \
  --profile dev \
  --region ap-northeast-1
```

#### すべてのリソースのタグ確認
```bash
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Cost\ Center,Values=Face-auth \
  --profile dev \
  --region ap-northeast-1
```

---

## 📈 コスト追跡のベストプラクティス

### 1. Cost Allocation Tagsの有効化

AWS Billing Consoleで以下のタグをCost Allocation Tagsとして有効化：

1. AWS Console > Billing > Cost Allocation Tags
2. 以下のタグを有効化：
   - Cost Center
   - Development
   - Project
   - Name

**注意:** タグの有効化後、コストデータに反映されるまで最大24時間かかります。

### 2. 定期的なコストレビュー

- **日次:** Development環境のコスト確認
- **週次:** サービス別コスト分析
- **月次:** Cost Centerごとの予算対比

### 3. コストアラートの設定

```bash
# 月額予算アラート設定（例: $100）
aws budgets create-budget \
  --account-id 979431736455 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json \
  --profile dev
```

**budget.json:**
```json
{
  "BudgetName": "FaceAuth-Monthly-Budget",
  "BudgetLimit": {
    "Amount": "100",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST",
  "CostFilters": {
    "TagKeyValue": ["user:Cost Center$Face-auth"]
  }
}
```

---

## 🎯 タグ管理のベストプラクティス

### DO（推奨）

✅ **一貫性のあるタグ付け**
- すべてのリソースに同じタグセットを適用
- タグの値は統一された命名規則に従う

✅ **自動タグ付け**
- CDKの`Tags.of(this).add()`を使用
- スタックレベルでタグを適用

✅ **タグの文書化**
- タグの目的と使用方法を文書化
- チーム全体でタグ規則を共有

✅ **定期的なタグ監査**
- タグが正しく適用されているか確認
- 未タグリソースを特定して修正

### DON'T（非推奨）

❌ **手動タグ付け**
- コンソールでの手動タグ付けは避ける
- IaCで管理する

❌ **不一致なタグ値**
- 環境ごとに異なるタグ値を使用しない
- 標準化されたタグ値を使用

❌ **タグの過剰使用**
- 必要最小限のタグに絞る
- 管理が複雑になるタグは避ける

---

## 📝 タグ変更手順

タグの値を変更する必要がある場合：

### 1. コードを修正

**ファイル:** `infrastructure/face_auth_stack.py`

```python
# 変更前
Tags.of(self).add("Cost Center", "Face-auth")

# 変更後
Tags.of(self).add("Cost Center", "新しい値")
```

### 2. 変更を確認

```bash
npx cdk diff --profile dev
```

### 3. デプロイ

```bash
npx cdk deploy --profile dev
```

**注意:** タグの変更は既存リソースに自動的に適用されます。リソースの再作成は不要です。

---

## ✅ 結論

**タグ付けステータス:** ✅ **完了**

すべてのAWSリソースに以下のタグが正しく適用されています：

- ✅ Name: Face-auth
- ✅ Cost Center: Face-auth
- ✅ Development: dm-dev
- ✅ Project: FaceAuth-IdP
- ✅ ManagedBy: CDK

これにより、以下が可能になります：

1. **コスト追跡:** Cost Centerタグでプロジェクトコストを追跡
2. **環境識別:** Developmentタグで開発環境を識別
3. **リソース管理:** Nameタグでリソースを簡単に識別
4. **プロジェクト分類:** Projectタグでプロジェクト全体を管理
5. **管理方法識別:** ManagedByタグでCDK管理リソースを識別

デプロイ後、AWS Cost ExplorerまたはCLIでコストを確認できます。

---

**確認日時:** 2026-01-27  
**確認者:** Kiro AI Assistant  
**次のアクション:** デプロイ実行
