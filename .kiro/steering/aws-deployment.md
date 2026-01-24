---
inclusion: fileMatch
fileMatchPattern: "**/infrastructure/**/*.py"
---

# AWS Deployment Standards - Face-Auth IdP System

このドキュメントは、Face-Auth IdP システムのAWSデプロイメント標準を定義します。

## AWS リソース命名規則

### 基本パターン

```
FaceAuth-<ResourceType>-<Purpose>-<Environment>
```

**例:**
- `FaceAuth-Enrollment-Lambda-Dev`
- `FaceAuth-CardTemplates-Table-Prod`
- `FaceAuth-Images-Bucket-Staging`

### 環境識別子

| 環境 | 識別子 | 説明 |
|------|--------|------|
| 開発 | `Dev` | 開発環境 |
| ステージング | `Staging` | 本番前検証環境 |
| 本番 | `Prod` | 本番環境 |

### リソース別命名規則

#### Lambda 関数
```
FaceAuth-<FunctionName>-<Environment>
```

**例:**
- `FaceAuth-Enrollment-Dev`
- `FaceAuth-FaceLogin-Prod`
- `FaceAuth-EmergencyAuth-Staging`

#### DynamoDB テーブル
```
FaceAuth-<TableName>-<Environment>
```

**例:**
- `FaceAuth-CardTemplates-Dev`
- `FaceAuth-EmployeeFaces-Prod`
- `FaceAuth-AuthSessions-Staging`

#### S3 バケット
```
face-auth-<purpose>-<account>-<region>-<environment>
```

**例:**
- `face-auth-images-123456789012-us-east-1-dev`
- `face-auth-images-123456789012-us-east-1-prod`

**理由:** S3バケット名はグローバルに一意である必要があるため、アカウントIDとリージョンを含める

#### API Gateway
```
FaceAuth-API-<Environment>
```

**例:**
- `FaceAuth-API-Dev`
- `FaceAuth-API-Prod`

#### Cognito User Pool
```
FaceAuth-UserPool-<Environment>
```

**例:**
- `FaceAuth-UserPool-Dev`
- `FaceAuth-UserPool-Prod`

#### VPC
```
FaceAuth-VPC-<Environment>
```

**例:**
- `FaceAuth-VPC-Dev`
- `FaceAuth-VPC-Prod`

#### Security Group
```
FaceAuth-<Purpose>-SG-<Environment>
```

**例:**
- `FaceAuth-Lambda-SG-Dev`
- `FaceAuth-AD-SG-Prod`

---

## タグ付けルール

### 必須タグ

すべてのAWSリソースに以下のタグを付ける：

```python
tags = {
    "Project": "FaceAuth",
    "Environment": "dev|staging|prod",
    "ManagedBy": "CDK",
    "Owner": "team-name",
    "CostCenter": "cost-center-id",
    "Application": "FaceAuth-IdP"
}
```

### CDKでのタグ実装

```python
from aws_cdk import Tags

class FaceAuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, env_name: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # スタック全体にタグを適用
        Tags.of(self).add("Project", "FaceAuth")
        Tags.of(self).add("Environment", env_name)
        Tags.of(self).add("ManagedBy", "CDK")
        Tags.of(self).add("Owner", "face-auth-team")
        Tags.of(self).add("CostCenter", "engineering-001")
        Tags.of(self).add("Application", "FaceAuth-IdP")
```

### リソース固有のタグ

```python
# Lambda関数
lambda_function = lambda_.Function(
    self, "EnrollmentFunction",
    function_name=f"FaceAuth-Enrollment-{env_name}",
    # ... other properties
)
Tags.of(lambda_function).add("Component", "Lambda")
Tags.of(lambda_function).add("Function", "Enrollment")

# DynamoDB テーブル
table = dynamodb.Table(
    self, "EmployeeFacesTable",
    table_name=f"FaceAuth-EmployeeFaces-{env_name}",
    # ... other properties
)
Tags.of(table).add("Component", "DynamoDB")
Tags.of(table).add("DataType", "EmployeeFaces")
```

---

## 環境別設定

### 環境変数管理

#### 開発環境 (Dev)
```python
dev_config = {
    "environment": "dev",
    "vpc_cidr": "10.0.0.0/16",
    "lambda_memory": 512,
    "lambda_timeout": 15,
    "dynamodb_billing": "PAY_PER_REQUEST",
    "log_retention_days": 7,
    "enable_xray": False,
    "cors_origins": ["*"],  # 開発用
}
```

#### ステージング環境 (Staging)
```python
staging_config = {
    "environment": "staging",
    "vpc_cidr": "10.1.0.0/16",
    "lambda_memory": 512,
    "lambda_timeout": 15,
    "dynamodb_billing": "PAY_PER_REQUEST",
    "log_retention_days": 30,
    "enable_xray": True,
    "cors_origins": ["https://staging.example.com"],
}
```

#### 本番環境 (Prod)
```python
prod_config = {
    "environment": "prod",
    "vpc_cidr": "10.2.0.0/16",
    "lambda_memory": 1024,  # 本番は大きめ
    "lambda_timeout": 15,
    "dynamodb_billing": "PROVISIONED",  # 本番はプロビジョニング
    "log_retention_days": 90,
    "enable_xray": True,
    "cors_origins": ["https://app.example.com"],
    "enable_waf": True,
    "enable_backup": True,
}
```

### 設定ファイルの構造

```python
# config.py
from typing import Dict, Any

class EnvironmentConfig:
    """Environment-specific configuration."""
    
    def __init__(self, env_name: str):
        self.env_name = env_name
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration based on environment."""
        configs = {
            "dev": self._dev_config(),
            "staging": self._staging_config(),
            "prod": self._prod_config(),
        }
        return configs.get(self.env_name, self._dev_config())
    
    def _dev_config(self) -> Dict[str, Any]:
        return {
            "environment": "dev",
            "vpc_cidr": "10.0.0.0/16",
            "lambda_memory": 512,
            "lambda_timeout": 15,
            "log_retention_days": 7,
        }
    
    def _staging_config(self) -> Dict[str, Any]:
        return {
            "environment": "staging",
            "vpc_cidr": "10.1.0.0/16",
            "lambda_memory": 512,
            "lambda_timeout": 15,
            "log_retention_days": 30,
        }
    
    def _prod_config(self) -> Dict[str, Any]:
        return {
            "environment": "prod",
            "vpc_cidr": "10.2.0.0/16",
            "lambda_memory": 1024,
            "lambda_timeout": 15,
            "log_retention_days": 90,
        }
```

---

## セキュリティ設定

### 暗号化

#### S3 バケット
```python
bucket = s3.Bucket(
    self, "FaceAuthImageBucket",
    bucket_name=f"face-auth-images-{self.account}-{self.region}-{env_name}",
    encryption=s3.BucketEncryption.S3_MANAGED,  # 最低限
    # または
    encryption=s3.BucketEncryption.KMS,  # より強固（本番推奨）
    encryption_key=kms_key,
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
    versioning=True if env_name == "prod" else False,
)
```

#### DynamoDB テーブル
```python
table = dynamodb.Table(
    self, "EmployeeFacesTable",
    table_name=f"FaceAuth-EmployeeFaces-{env_name}",
    encryption=dynamodb.TableEncryption.AWS_MANAGED,  # 最低限
    # または
    encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,  # より強固
    encryption_key=kms_key,
    point_in_time_recovery=True if env_name == "prod" else False,
)
```

#### Lambda 環境変数
```python
lambda_function = lambda_.Function(
    self, "EnrollmentFunction",
    environment={
        "FACE_AUTH_BUCKET": bucket.bucket_name,
        # 機密情報はSecrets Managerから取得
        "AD_SERVER_URL": f"{{{{resolve:secretsmanager:{secret_arn}:SecretString:ad_server_url}}}}",
    },
    environment_encryption=kms_key,  # 環境変数の暗号化
)
```

### IAM 最小権限の原則

```python
# Lambda実行ロール
lambda_role = iam.Role(
    self, "LambdaExecutionRole",
    assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    description="Execution role for Face-Auth Lambda functions",
)

# 必要最小限の権限のみ付与
lambda_role.add_to_policy(iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=[
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
    ],
    resources=[
        f"{bucket.bucket_arn}/*"
    ]
))

# 特定のテーブルのみアクセス許可
lambda_role.add_to_policy(iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=[
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query",
    ],
    resources=[
        table.table_arn,
        f"{table.table_arn}/index/*"
    ]
))
```

### セキュリティグループ

```python
# Lambda用セキュリティグループ
lambda_sg = ec2.SecurityGroup(
    self, "LambdaSecurityGroup",
    vpc=vpc,
    description="Security group for Face-Auth Lambda functions",
    allow_all_outbound=True,  # 開発環境
    # 本番環境では特定の宛先のみ許可
)

# AD接続用セキュリティグループ
ad_sg = ec2.SecurityGroup(
    self, "ADSecurityGroup",
    vpc=vpc,
    description="Security group for AD connection",
    allow_all_outbound=False,  # 明示的に許可
)

# LDAPS (port 636) のみ許可
ad_sg.add_egress_rule(
    peer=ec2.Peer.ipv4("10.0.0.0/8"),  # オンプレミスネットワーク
    port=ec2.Port.tcp(636),
    description="LDAPS to on-premises AD"
)
```

---

## モニタリングとログ

### CloudWatch Logs

```python
# Lambda関数のログ
log_group = logs.LogGroup(
    self, "LambdaLogGroup",
    log_group_name=f"/aws/lambda/FaceAuth-{function_name}-{env_name}",
    retention=logs.RetentionDays.ONE_WEEK if env_name == "dev" else logs.RetentionDays.ONE_MONTH,
    removal_policy=RemovalPolicy.RETAIN if env_name == "prod" else RemovalPolicy.DESTROY,
)
```

### CloudWatch Alarms

```python
# Lambda エラーアラーム
error_alarm = cloudwatch.Alarm(
    self, "LambdaErrorAlarm",
    alarm_name=f"FaceAuth-{function_name}-Errors-{env_name}",
    metric=lambda_function.metric_errors(),
    threshold=10,
    evaluation_periods=1,
    datapoints_to_alarm=1,
    treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
)

# Lambda タイムアウトアラーム
timeout_alarm = cloudwatch.Alarm(
    self, "LambdaTimeoutAlarm",
    alarm_name=f"FaceAuth-{function_name}-Timeouts-{env_name}",
    metric=lambda_function.metric_duration(),
    threshold=14000,  # 14秒（15秒タイムアウトの直前）
    evaluation_periods=2,
    comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
)

# DynamoDB スロットリングアラーム
throttle_alarm = cloudwatch.Alarm(
    self, "DynamoDBThrottleAlarm",
    alarm_name=f"FaceAuth-DynamoDB-Throttles-{env_name}",
    metric=table.metric_user_errors(),
    threshold=5,
    evaluation_periods=1,
)
```

### X-Ray トレーシング

```python
# Lambda関数でX-Rayを有効化
lambda_function = lambda_.Function(
    self, "EnrollmentFunction",
    tracing=lambda_.Tracing.ACTIVE if env_name in ["staging", "prod"] else lambda_.Tracing.DISABLED,
    # ... other properties
)

# API GatewayでX-Rayを有効化
api = apigateway.RestApi(
    self, "FaceAuthAPI",
    deploy_options=apigateway.StageOptions(
        tracing_enabled=True if env_name in ["staging", "prod"] else False,
    )
)
```

---

## デプロイメント

### CDK デプロイコマンド

```bash
# 開発環境
cdk deploy FaceAuthStack-Dev --context env=dev

# ステージング環境
cdk deploy FaceAuthStack-Staging --context env=staging

# 本番環境
cdk deploy FaceAuthStack-Prod --context env=prod --require-approval broadening
```

### デプロイ前チェックリスト

#### 開発環境
- [ ] コードがコミットされている
- [ ] 単体テストが通過
- [ ] CDK diff確認

#### ステージング環境
- [ ] 開発環境で動作確認済み
- [ ] 統合テストが通過
- [ ] CDK diff確認
- [ ] セキュリティ設定確認

#### 本番環境
- [ ] ステージング環境で動作確認済み
- [ ] すべてのテストが通過
- [ ] セキュリティレビュー完了
- [ ] CDK diff確認
- [ ] CORS設定が本番用に制限されている
- [ ] ログ保持期間が適切
- [ ] バックアップ設定が有効
- [ ] アラーム設定が有効
- [ ] ロールバック手順確認

### デプロイスクリプト

```bash
#!/bin/bash
# deploy.sh

set -e

ENV=$1

if [ -z "$ENV" ]; then
    echo "Usage: ./deploy.sh <dev|staging|prod>"
    exit 1
fi

echo "Deploying to $ENV environment..."

# テスト実行
echo "Running tests..."
python -m pytest tests/ --ignore=tests/test_ad_connector.py -v

# CDK差分確認
echo "Checking CDK diff..."
cdk diff FaceAuthStack-${ENV^} --context env=$ENV

# デプロイ確認
read -p "Continue with deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 1
fi

# デプロイ実行
echo "Deploying..."
cdk deploy FaceAuthStack-${ENV^} --context env=$ENV --require-approval never

echo "Deployment completed successfully!"
```

---

## コスト最適化

### Lambda

```python
# 開発環境: 小さめのメモリ
lambda_function = lambda_.Function(
    self, "Function",
    memory_size=512 if env_name == "dev" else 1024,
    timeout=Duration.seconds(15),
    reserved_concurrent_executions=10 if env_name == "dev" else None,
)
```

### DynamoDB

```python
# 開発環境: オンデマンド
# 本番環境: プロビジョニング（予測可能なトラフィック）
table = dynamodb.Table(
    self, "Table",
    billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST if env_name != "prod" 
                  else dynamodb.BillingMode.PROVISIONED,
    read_capacity=100 if env_name == "prod" else None,
    write_capacity=50 if env_name == "prod" else None,
)
```

### S3 Lifecycle

```python
bucket = s3.Bucket(
    self, "Bucket",
    lifecycle_rules=[
        # 開発環境: 短い保持期間
        s3.LifecycleRule(
            id="TempFilesCleanup",
            prefix="temp/",
            expiration=Duration.days(1 if env_name == "dev" else 7),
        ),
        # 本番環境: Glacier移行
        s3.LifecycleRule(
            id="ArchiveOldFiles",
            prefix="enroll/",
            transitions=[
                s3.Transition(
                    storage_class=s3.StorageClass.GLACIER,
                    transition_after=Duration.days(90)
                )
            ] if env_name == "prod" else [],
        ),
    ]
)
```

---

## バックアップとディザスタリカバリ

### DynamoDB バックアップ

```python
# 本番環境のみポイントインタイムリカバリ有効
table = dynamodb.Table(
    self, "Table",
    point_in_time_recovery=True if env_name == "prod" else False,
)

# バックアッププラン（本番環境）
if env_name == "prod":
    backup_plan = backup.BackupPlan(
        self, "BackupPlan",
        backup_plan_name=f"FaceAuth-DynamoDB-Backup-{env_name}",
    )
    
    backup_plan.add_rule(backup.BackupPlanRule(
        backup_vault=backup_vault,
        rule_name="DailyBackup",
        schedule_expression=events.Schedule.cron(
            hour="2",
            minute="0"
        ),
        delete_after=Duration.days(30),
    ))
    
    backup_plan.add_selection(
        "Selection",
        resources=[
            backup.BackupResource.from_dynamo_db_table(table)
        ]
    )
```

### S3 バージョニング

```python
# 本番環境のみバージョニング有効
bucket = s3.Bucket(
    self, "Bucket",
    versioning=True if env_name == "prod" else False,
)
```

---

## トラブルシューティング

### デプロイ失敗時

```bash
# スタック状態確認
aws cloudformation describe-stacks --stack-name FaceAuthStack-Dev

# スタックイベント確認
aws cloudformation describe-stack-events --stack-name FaceAuthStack-Dev

# ロールバック
cdk destroy FaceAuthStack-Dev --context env=dev
cdk deploy FaceAuthStack-Dev --context env=dev
```

### Lambda エラー確認

```bash
# ログ確認
aws logs tail /aws/lambda/FaceAuth-Enrollment-Dev --follow

# 最新のエラーログ
aws logs filter-log-events \
    --log-group-name /aws/lambda/FaceAuth-Enrollment-Dev \
    --filter-pattern "ERROR"
```

---

## 参考資料

- [AWS CDK Best Practices](https://docs.aws.amazon.com/cdk/latest/guide/best-practices.html)
- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)

---

**最終更新:** 2024
**バージョン:** 1.0
