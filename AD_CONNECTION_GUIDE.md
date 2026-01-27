# Active Directory 接続ガイド

## 📍 現在の接続状況

### ⚠️ 重要: AD接続は未設定

現在、Active Directory (AD) への接続は**設定されていません**。
ADConnectorのコードは実装済みですが、実際のオンプレミスADサーバーへの接続設定が必要です。

---

## 🔌 AD接続の仕組み

### 接続方式

Face-Auth IdP System は、以下の方式でオンプレミスActive Directoryに接続します：

```
AWS VPC (Private Subnet)
    ↓
Lambda関数 (ADConnector)
    ↓
Direct Connect または VPN
    ↓
オンプレミスネットワーク (10.0.0.0/8)
    ↓
Active Directory サーバー (LDAPS: 636)
```

### プロトコル

- **LDAPS (LDAP over SSL)** - ポート 636（推奨）
- **LDAP** - ポート 389（フォールバック）

---

## 🏗️ 現在のインフラ設定

### VPC構成

**VPC CIDR:** `10.0.0.0/16`

**サブネット:**
- Public Subnet: NAT Gateway配置
- Private Subnet: Lambda関数配置 ✅
- Isolated Subnet: 将来の拡張用

### セキュリティグループ

**ADSecurityGroup** がLambda関数にアタッチされています：

```python
# LDAPS (推奨)
Outbound Rule:
  Protocol: TCP
  Port: 636
  Destination: 10.0.0.0/8
  Description: LDAPS traffic to on-premises Active Directory

# LDAP (フォールバック)
Outbound Rule:
  Protocol: TCP
  Port: 389
  Destination: 10.0.0.0/8
  Description: LDAP traffic to on-premises Active Directory
```

### Customer Gateway（プレースホルダー）

現在、インフラコードには以下のプレースホルダーが設定されています：

```python
# infrastructure/face_auth_stack.py (コメントアウト済み)

# self.customer_gateway = ec2.CfnCustomerGateway(
#     self, "OnPremisesCustomerGateway",
#     bgp_asn=65000,  # Private ASN for on-premises
#     ip_address="YOUR_ACTUAL_IP_HERE",  # ⚠️ 実際のIPに変更必要
#     type="ipsec.1",
#     tags=[{
#         "key": "Name",
#         "value": "FaceAuth-OnPremises-Gateway"
#     }]
# )
```

---

## 🔧 AD接続の設定手順

### オプション1: AWS Direct Connect（推奨）

**メリット:**
- 専用線による安定した接続
- 低レイテンシー
- 高セキュリティ

**手順:**

#### 1. Direct Connect接続の確立

```bash
# 1. Direct Connect Locationの選択
# AWS Console > Direct Connect > Connections > Create Connection

# 2. 接続タイプの選択
# - Dedicated Connection (1Gbps, 10Gbps, 100Gbps)
# - Hosted Connection (50Mbps - 10Gbps)

# 3. ネットワークプロバイダーとの調整
# - LOA-CFA (Letter of Authorization and Connecting Facility Assignment) 取得
# - プロバイダーに物理接続を依頼
```

#### 2. Virtual Private Gateway作成

```bash
# Virtual Private Gateway作成
aws ec2 create-vpn-gateway \
  --type ipsec.1 \
  --amazon-side-asn 64512 \
  --tag-specifications 'ResourceType=vpn-gateway,Tags=[{Key=Name,Value=FaceAuth-VGW}]' \
  --profile dev

# VPCにアタッチ
aws ec2 attach-vpn-gateway \
  --vpn-gateway-id vgw-xxxxx \
  --vpc-id vpc-0af2750e674368e60 \
  --profile dev
```

#### 3. Customer Gateway作成

```bash
# Customer Gateway作成（オンプレミス側）
aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip <オンプレミスゲートウェイのパブリックIP> \
  --bgp-asn 65000 \
  --tag-specifications 'ResourceType=customer-gateway,Tags=[{Key=Name,Value=FaceAuth-CGW}]' \
  --profile dev
```

#### 4. Direct Connect Gateway作成

```bash
# Direct Connect Gateway作成
aws directconnect create-direct-connect-gateway \
  --direct-connect-gateway-name FaceAuth-DXGW \
  --amazon-side-asn 64512 \
  --profile dev

# Virtual Private Gatewayと関連付け
aws directconnect create-direct-connect-gateway-association \
  --direct-connect-gateway-id <dxgw-id> \
  --virtual-gateway-id <vgw-id> \
  --profile dev
```

#### 5. ルートテーブル更新

```bash
# Private Subnetのルートテーブルに追加
aws ec2 create-route \
  --route-table-id <rtb-id> \
  --destination-cidr-block 10.0.0.0/8 \
  --gateway-id <vgw-id> \
  --profile dev
```

#### 6. CDKコードの更新

`infrastructure/face_auth_stack.py` を編集：

```python
# Customer Gatewayのコメントアウトを解除
self.customer_gateway = ec2.CfnCustomerGateway(
    self, "OnPremisesCustomerGateway",
    bgp_asn=65000,  # 実際のASNに変更
    ip_address="203.0.113.1",  # 実際のIPに変更
    type="ipsec.1",
    tags=[{
        "key": "Name",
        "value": "FaceAuth-OnPremises-Gateway"
    }]
)

# Virtual Private Gateway追加
self.vpn_gateway = ec2.CfnVPNGateway(
    self, "FaceAuthVPNGateway",
    type="ipsec.1",
    amazon_side_asn=64512,
    tags=[{
        "key": "Name",
        "value": "FaceAuth-VPN-Gateway"
    }]
)

# VPCにアタッチ
ec2.CfnVPCGatewayAttachment(
    self, "VPNGatewayAttachment",
    vpc_id=self.vpc.vpc_id,
    vpn_gateway_id=self.vpn_gateway.ref
)
```

---

### オプション2: Site-to-Site VPN（低コスト）

**メリット:**
- 低コスト
- 迅速なセットアップ
- インターネット経由（暗号化）

**デメリット:**
- レイテンシーが高い
- 帯域幅が限られる

**手順:**

#### 1. Customer Gateway作成

```bash
aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip <オンプレミスゲートウェイのパブリックIP> \
  --bgp-asn 65000 \
  --tag-specifications 'ResourceType=customer-gateway,Tags=[{Key=Name,Value=FaceAuth-CGW}]' \
  --profile dev
```

#### 2. Virtual Private Gateway作成

```bash
aws ec2 create-vpn-gateway \
  --type ipsec.1 \
  --amazon-side-asn 64512 \
  --tag-specifications 'ResourceType=vpn-gateway,Tags=[{Key=Name,Value=FaceAuth-VGW}]' \
  --profile dev

aws ec2 attach-vpn-gateway \
  --vpn-gateway-id vgw-xxxxx \
  --vpc-id vpc-0af2750e674368e60 \
  --profile dev
```

#### 3. VPN Connection作成

```bash
aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id cgw-xxxxx \
  --vpn-gateway-id vgw-xxxxx \
  --options TunnelOptions=[{TunnelInsideCidr=169.254.10.0/30},{TunnelInsideCidr=169.254.11.0/30}] \
  --tag-specifications 'ResourceType=vpn-connection,Tags=[{Key=Name,Value=FaceAuth-VPN}]' \
  --profile dev
```

#### 4. オンプレミス側の設定

VPN Connection作成後、設定ファイルをダウンロード：

```bash
aws ec2 describe-vpn-connections \
  --vpn-connection-ids vpn-xxxxx \
  --profile dev
```

設定ファイルをオンプレミスのVPNデバイスに適用。

---

### オプション3: AWS Client VPN（テスト用）

**用途:** 開発・テスト環境のみ

**メリット:**
- 個人のPCから直接接続可能
- セットアップが簡単

**デメリット:**
- 本番環境には不適切
- コストが高い

---

## 🔐 ADConnectorの設定

### 環境変数

Lambda関数に以下の環境変数を追加する必要があります：

```bash
# ADサーバー設定
AD_SERVER_URL=ldaps://ad.company.com:636
AD_BASE_DN=DC=company,DC=com
AD_TIMEOUT=10

# オプション: サービスアカウント（匿名バインドを使用しない場合）
AD_SERVICE_USER=CN=ServiceAccount,OU=ServiceAccounts,DC=company,DC=com
AD_SERVICE_PASSWORD=<Secrets Managerから取得>
```

### CDKコードの更新

`infrastructure/face_auth_stack.py` を編集：

```python
# Lambda環境変数に追加
"environment": {
    # 既存の環境変数...
    "AD_SERVER_URL": os.getenv("AD_SERVER_URL", "ldaps://ad.company.com:636"),
    "AD_BASE_DN": os.getenv("AD_BASE_DN", "DC=company,DC=com"),
    "AD_TIMEOUT": "10",
    # オプション: サービスアカウント
    "AD_SERVICE_USER": os.getenv("AD_SERVICE_USER", ""),
    "AD_SERVICE_PASSWORD": f"{{{{resolve:secretsmanager:{ad_secret_arn}:SecretString:password}}}}"
}
```

### Secrets Managerの設定（推奨）

ADパスワードはSecrets Managerに保存：

```bash
# Secret作成
aws secretsmanager create-secret \
  --name FaceAuth/AD/ServiceAccount \
  --description "AD Service Account Credentials" \
  --secret-string '{"username":"ServiceAccount","password":"YourPassword"}' \
  --profile dev

# Lambda実行ロールに権限追加
aws iam attach-role-policy \
  --role-name FaceAuthLambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite \
  --profile dev
```

---

## 🧪 接続テスト

### 1. ネットワーク接続テスト

Lambda関数から以下のコマンドでテスト：

```python
import socket

def test_ad_connection():
    try:
        # LDAPS接続テスト
        sock = socket.create_connection(("ad.company.com", 636), timeout=10)
        sock.close()
        print("✅ LDAPS connection successful")
        return True
    except Exception as e:
        print(f"❌ LDAPS connection failed: {e}")
        return False
```

### 2. LDAP接続テスト

ADConnectorの`test_connection()`メソッドを使用：

```python
from lambda.shared.ad_connector import ADConnector

ad_connector = ADConnector(
    server_url="ldaps://ad.company.com:636",
    base_dn="DC=company,DC=com",
    timeout=10
)

success, message = ad_connector.test_connection()
print(f"Connection test: {message}")
```

### 3. 社員検証テスト

```python
from lambda.shared.models import EmployeeInfo

employee_info = EmployeeInfo(
    employee_id="123456",
    name="山田太郎",
    department="開発部"
)

result = ad_connector.verify_employee("123456", employee_info)

if result.success:
    print(f"✅ Employee verified: {result.employee_data}")
else:
    print(f"❌ Verification failed: {result.error}")
```

### 4. パスワード認証テスト

```python
result = ad_connector.authenticate_password("123456", "password123")

if result.success:
    print(f"✅ Authentication successful")
else:
    print(f"❌ Authentication failed: {result.error}")
```

---

## 📊 ADConnectorの動作

### 社員検証フロー

```
1. Lambda関数 (handle_enrollment)
   ↓
2. ADConnector.verify_employee()
   ↓
3. LDAPS接続 (ldaps://ad.company.com:636)
   ↓
4. LDAP検索 (employeeID={employee_id})
   ↓
5. アカウント状態確認 (userAccountControl)
   ↓
6. 社員情報比較
   ↓
7. 結果返却 (ADVerificationResult)
```

### パスワード認証フロー

```
1. Lambda関数 (handle_emergency_auth)
   ↓
2. ADConnector.authenticate_password()
   ↓
3. LDAPS接続
   ↓
4. 社員DN検索
   ↓
5. アカウント状態確認
   ↓
6. LDAP Bind試行（パスワード検証）
   ↓
7. 結果返却 (ADVerificationResult)
```

### タイムアウト管理

- **AD接続タイムアウト:** 10秒
- **Lambda全体タイムアウト:** 15秒
- **タイムアウト超過時:** エラーコード `AD_CONNECTION_ERROR` を返却

---

## 🔒 セキュリティ考慮事項

### 1. LDAPS使用（推奨）

```python
# Good: LDAPS (暗号化)
server_url = "ldaps://ad.company.com:636"

# Bad: LDAP (平文)
server_url = "ldap://ad.company.com:389"
```

### 2. サービスアカウントの最小権限

ADサービスアカウントには以下の権限のみ付与：

- ✅ 社員情報の読み取り
- ✅ パスワード検証（Bind操作）
- ❌ 書き込み権限は不要
- ❌ 管理者権限は不要

### 3. Secrets Manager使用

パスワードはコードにハードコードせず、Secrets Managerに保存：

```python
import boto3
import json

def get_ad_credentials():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='FaceAuth/AD/ServiceAccount')
    secret = json.loads(response['SecretString'])
    return secret['username'], secret['password']
```

### 4. ネットワーク分離

- ✅ Lambda関数はPrivate Subnetに配置
- ✅ セキュリティグループで通信制限
- ✅ Direct Connect経由で安全な接続

---

## 🐛 トラブルシューティング

### 問題1: 接続タイムアウト

**症状:**
```
AD connection timeout exceeded: 10.00s
```

**原因:**
- Direct Connect/VPN接続が確立されていない
- ルートテーブルが正しく設定されていない
- セキュリティグループでポート636/389が許可されていない

**解決策:**
```bash
# 1. VPN/Direct Connect状態確認
aws ec2 describe-vpn-connections --profile dev

# 2. ルートテーブル確認
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-0af2750e674368e60" --profile dev

# 3. セキュリティグループ確認
aws ec2 describe-security-groups --group-names ADSecurityGroup --profile dev
```

### 問題2: LDAP Bind失敗

**症状:**
```
LDAPBindError: invalid credentials
```

**原因:**
- サービスアカウントのパスワードが間違っている
- サービスアカウントが無効化されている

**解決策:**
```bash
# Secrets Manager確認
aws secretsmanager get-secret-value --secret-id FaceAuth/AD/ServiceAccount --profile dev

# パスワード更新
aws secretsmanager update-secret \
  --secret-id FaceAuth/AD/ServiceAccount \
  --secret-string '{"username":"ServiceAccount","password":"NewPassword"}' \
  --profile dev
```

### 問題3: 社員が見つからない

**症状:**
```
Employee not found in AD: 123456
```

**原因:**
- Base DNが間違っている
- 社員IDの属性名が異なる（`employeeID` vs `employeeNumber`）

**解決策:**

ADConnectorのコードを修正：

```python
# 属性名を確認
search_filter = f"(employeeNumber={employee_id})"  # employeeIDではなくemployeeNumber

# Base DNを確認
base_dn = "OU=Employees,DC=company,DC=com"  # より具体的なOUを指定
```

### 問題4: アカウント無効化エラー

**症状:**
```
AD account is disabled: 123456
```

**原因:**
- ADでアカウントが無効化されている

**解決策:**
- AD管理者にアカウントの有効化を依頼
- または、テスト用に別のアカウントを使用

---

## 📋 チェックリスト

### AD接続設定前

- [ ] オンプレミスADサーバーのIPアドレス確認
- [ ] LDAPS (ポート636) が有効か確認
- [ ] Base DN確認（例: `DC=company,DC=com`）
- [ ] サービスアカウント作成（読み取り権限のみ）
- [ ] ネットワークプロバイダーとの調整（Direct Connect使用時）

### AWS側設定

- [ ] Customer Gateway作成
- [ ] Virtual Private Gateway作成
- [ ] Direct Connect Gateway作成（Direct Connect使用時）
- [ ] VPN Connection作成（VPN使用時）
- [ ] ルートテーブル更新（10.0.0.0/8 → VGW）
- [ ] セキュリティグループ確認（ポート636/389許可）
- [ ] Secrets Manager設定（サービスアカウント）
- [ ] Lambda環境変数設定

### テスト

- [ ] ネットワーク接続テスト（ポート636）
- [ ] LDAP接続テスト（`test_connection()`）
- [ ] 社員検証テスト（`verify_employee()`）
- [ ] パスワード認証テスト（`authenticate_password()`）
- [ ] タイムアウトテスト（10秒制限）

---

## 📚 関連ドキュメント

- `lambda/shared/ad_connector.py` - ADConnectorの実装
- `docs/INFRASTRUCTURE_ARCHITECTURE.md` - インフラアーキテクチャ
- `DEPLOYMENT_STATUS_REPORT.md` - デプロイ状況

---

## 🎯 まとめ

### 現在の状況

- ✅ ADConnectorコード実装済み
- ✅ セキュリティグループ設定済み（ポート636/389許可）
- ✅ Lambda関数はPrivate Subnetに配置済み
- ⚠️ **Direct Connect/VPN接続は未設定**
- ⚠️ **AD環境変数は未設定**

### 次のステップ

1. **Direct ConnectまたはVPN接続の確立**
   - ネットワークプロバイダーとの調整
   - Customer Gateway/Virtual Private Gateway作成
   - ルートテーブル更新

2. **AD環境変数の設定**
   - `AD_SERVER_URL`
   - `AD_BASE_DN`
   - `AD_SERVICE_USER` (オプション)
   - `AD_SERVICE_PASSWORD` (Secrets Manager)

3. **接続テスト**
   - ネットワーク接続確認
   - LDAP接続確認
   - 社員検証テスト

4. **本番デプロイ**
   - CDKコード更新
   - 再デプロイ
   - E2Eテスト

---

**作成日:** 2026年1月28日  
**バージョン:** 1.0

