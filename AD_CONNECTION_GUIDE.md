# Active Directory 謗･邯壹ぎ繧､繝・

## 桃 迴ｾ蝨ｨ縺ｮ謗･邯夂憾豕・

### 笞・・驥崎ｦ・ AD謗･邯壹・譛ｪ險ｭ螳・

迴ｾ蝨ｨ縲、ctive Directory (AD) 縺ｸ縺ｮ謗･邯壹・**險ｭ螳壹＆繧後※縺・∪縺帙ｓ**縲・
ADConnector縺ｮ繧ｳ繝ｼ繝峨・螳溯｣・ｸ医∩縺ｧ縺吶′縲∝ｮ滄圀縺ｮ繧ｪ繝ｳ繝励Ξ繝溘せAD繧ｵ繝ｼ繝舌・縺ｸ縺ｮ謗･邯夊ｨｭ螳壹′蠢・ｦ√〒縺吶・

---

## 伯 AD謗･邯壹・莉慕ｵ・∩

### 謗･邯壽婿蠑・

Face-Auth IdP System 縺ｯ縲∽ｻ･荳九・譁ｹ蠑上〒繧ｪ繝ｳ繝励Ξ繝溘せActive Directory縺ｫ謗･邯壹＠縺ｾ縺呻ｼ・

```
AWS VPC (Private Subnet)
    竊・
Lambda髢｢謨ｰ (ADConnector)
    竊・
Direct Connect 縺ｾ縺溘・ VPN
    竊・
繧ｪ繝ｳ繝励Ξ繝溘せ繝阪ャ繝医Ρ繝ｼ繧ｯ (10.0.0.0/8)
    竊・
Active Directory 繧ｵ繝ｼ繝舌・ (LDAPS: 636)
```

### 繝励Ο繝医さ繝ｫ

- **LDAPS (LDAP over SSL)** - 繝昴・繝・636・域耳螂ｨ・・
- **LDAP** - 繝昴・繝・389・医ヵ繧ｩ繝ｼ繝ｫ繝舌ャ繧ｯ・・

---

## 女・・迴ｾ蝨ｨ縺ｮ繧､繝ｳ繝輔Λ險ｭ螳・

### VPC讒区・

**VPC CIDR:** `10.0.0.0/16`

**繧ｵ繝悶ロ繝・ヨ:**
- Public Subnet: NAT Gateway驟咲ｽｮ
- Private Subnet: Lambda髢｢謨ｰ驟咲ｽｮ 笨・
- Isolated Subnet: 蟆・擂縺ｮ諡｡蠑ｵ逕ｨ

### 繧ｻ繧ｭ繝･繝ｪ繝・ぅ繧ｰ繝ｫ繝ｼ繝・

**ADSecurityGroup** 縺鍬ambda髢｢謨ｰ縺ｫ繧｢繧ｿ繝・メ縺輔ｌ縺ｦ縺・∪縺呻ｼ・

```python
# LDAPS (謗ｨ螂ｨ)
Outbound Rule:
  Protocol: TCP
  Port: 636
  Destination: 10.0.0.0/8
  Description: LDAPS traffic to on-premises Active Directory

# LDAP (繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ)
Outbound Rule:
  Protocol: TCP
  Port: 389
  Destination: 10.0.0.0/8
  Description: LDAP traffic to on-premises Active Directory
```

### Customer Gateway・医・繝ｬ繝ｼ繧ｹ繝帙Ν繝繝ｼ・・

迴ｾ蝨ｨ縲√う繝ｳ繝輔Λ繧ｳ繝ｼ繝峨↓縺ｯ莉･荳九・繝励Ξ繝ｼ繧ｹ繝帙Ν繝繝ｼ縺瑚ｨｭ螳壹＆繧後※縺・∪縺呻ｼ・

```python
# infrastructure/face_auth_stack.py (繧ｳ繝｡繝ｳ繝医い繧ｦ繝域ｸ医∩)

# self.customer_gateway = ec2.CfnCustomerGateway(
#     self, "OnPremisesCustomerGateway",
#     bgp_asn=65000,  # Private ASN for on-premises
#     ip_address="YOUR_ACTUAL_IP_HERE",  # 笞・・螳滄圀縺ｮIP縺ｫ螟画峩蠢・ｦ・
#     type="ipsec.1",
#     tags=[{
#         "key": "Name",
#         "value": "FaceAuth-OnPremises-Gateway"
#     }]
# )
```

---

## 肌 AD謗･邯壹・險ｭ螳壽焔鬆・

### 繧ｪ繝励す繝ｧ繝ｳ1: AWS Direct Connect・域耳螂ｨ・・

**繝｡繝ｪ繝・ヨ:**
- 蟆ら畑邱壹↓繧医ｋ螳牙ｮ壹＠縺滓磁邯・
- 菴弱Ξ繧､繝・Φ繧ｷ繝ｼ
- 鬮倥そ繧ｭ繝･繝ｪ繝・ぅ

**謇矩・**

#### 1. Direct Connect謗･邯壹・遒ｺ遶・

```bash
# 1. Direct Connect Location縺ｮ驕ｸ謚・
# AWS Console > Direct Connect > Connections > Create Connection

# 2. 謗･邯壹ち繧､繝励・驕ｸ謚・
# - Dedicated Connection (1Gbps, 10Gbps, 100Gbps)
# - Hosted Connection (50Mbps - 10Gbps)

# 3. 繝阪ャ繝医Ρ繝ｼ繧ｯ繝励Ο繝舌う繝繝ｼ縺ｨ縺ｮ隱ｿ謨ｴ
# - LOA-CFA (Letter of Authorization and Connecting Facility Assignment) 蜿門ｾ・
# - 繝励Ο繝舌う繝繝ｼ縺ｫ迚ｩ逅・磁邯壹ｒ萓晞ｼ
```

#### 2. Virtual Private Gateway菴懈・

```bash
# Virtual Private Gateway菴懈・
aws ec2 create-vpn-gateway \
  --type ipsec.1 \
  --amazon-side-asn 64512 \
  --tag-specifications 'ResourceType=vpn-gateway,Tags=[{Key=Name,Value=FaceAuth-VGW}]' \
  --profile dev

# VPC縺ｫ繧｢繧ｿ繝・メ
aws ec2 attach-vpn-gateway \
  --vpn-gateway-id vgw-xxxxx \
  --vpc-id vpc-0af2750e674368e60 \
  --profile dev
```

#### 3. Customer Gateway菴懈・

```bash
# Customer Gateway菴懈・・医が繝ｳ繝励Ξ繝溘せ蛛ｴ・・
aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip <繧ｪ繝ｳ繝励Ξ繝溘せ繧ｲ繝ｼ繝医え繧ｧ繧､縺ｮ繝代ヶ繝ｪ繝・けIP> \
  --bgp-asn 65000 \
  --tag-specifications 'ResourceType=customer-gateway,Tags=[{Key=Name,Value=FaceAuth-CGW}]' \
  --profile dev
```

#### 4. Direct Connect Gateway菴懈・

```bash
# Direct Connect Gateway菴懈・
aws directconnect create-direct-connect-gateway \
  --direct-connect-gateway-name FaceAuth-DXGW \
  --amazon-side-asn 64512 \
  --profile dev

# Virtual Private Gateway縺ｨ髢｢騾｣莉倥￠
aws directconnect create-direct-connect-gateway-association \
  --direct-connect-gateway-id <dxgw-id> \
  --virtual-gateway-id <vgw-id> \
  --profile dev
```

#### 5. 繝ｫ繝ｼ繝医ユ繝ｼ繝悶Ν譖ｴ譁ｰ

```bash
# Private Subnet縺ｮ繝ｫ繝ｼ繝医ユ繝ｼ繝悶Ν縺ｫ霑ｽ蜉
aws ec2 create-route \
  --route-table-id <rtb-id> \
  --destination-cidr-block 10.0.0.0/8 \
  --gateway-id <vgw-id> \
  --profile dev
```

#### 6. CDK繧ｳ繝ｼ繝峨・譖ｴ譁ｰ

`infrastructure/face_auth_stack.py` 繧堤ｷｨ髮・ｼ・

```python
# Customer Gateway縺ｮ繧ｳ繝｡繝ｳ繝医い繧ｦ繝医ｒ隗｣髯､
self.customer_gateway = ec2.CfnCustomerGateway(
    self, "OnPremisesCustomerGateway",
    bgp_asn=65000,  # 螳滄圀縺ｮASN縺ｫ螟画峩
    ip_address="203.0.113.1",  # 螳滄圀縺ｮIP縺ｫ螟画峩
    type="ipsec.1",
    tags=[{
        "key": "Name",
        "value": "FaceAuth-OnPremises-Gateway"
    }]
)

# Virtual Private Gateway霑ｽ蜉
self.vpn_gateway = ec2.CfnVPNGateway(
    self, "FaceAuthVPNGateway",
    type="ipsec.1",
    amazon_side_asn=64512,
    tags=[{
        "key": "Name",
        "value": "FaceAuth-VPN-Gateway"
    }]
)

# VPC縺ｫ繧｢繧ｿ繝・メ
ec2.CfnVPCGatewayAttachment(
    self, "VPNGatewayAttachment",
    vpc_id=self.vpc.vpc_id,
    vpn_gateway_id=self.vpn_gateway.ref
)
```

---

### 繧ｪ繝励す繝ｧ繝ｳ2: Site-to-Site VPN・井ｽ弱さ繧ｹ繝茨ｼ・

**繝｡繝ｪ繝・ヨ:**
- 菴弱さ繧ｹ繝・
- 霑・溘↑繧ｻ繝・ヨ繧｢繝・・
- 繧､繝ｳ繧ｿ繝ｼ繝阪ャ繝育ｵ檎罰・域囓蜿ｷ蛹厄ｼ・

**繝・Γ繝ｪ繝・ヨ:**
- 繝ｬ繧､繝・Φ繧ｷ繝ｼ縺碁ｫ倥＞
- 蟶ｯ蝓溷ｹ・′髯舌ｉ繧後ｋ

**謇矩・**

#### 1. Customer Gateway菴懈・

```bash
aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip <繧ｪ繝ｳ繝励Ξ繝溘せ繧ｲ繝ｼ繝医え繧ｧ繧､縺ｮ繝代ヶ繝ｪ繝・けIP> \
  --bgp-asn 65000 \
  --tag-specifications 'ResourceType=customer-gateway,Tags=[{Key=Name,Value=FaceAuth-CGW}]' \
  --profile dev
```

#### 2. Virtual Private Gateway菴懈・

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

#### 3. VPN Connection菴懈・

```bash
aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id cgw-xxxxx \
  --vpn-gateway-id vgw-xxxxx \
  --options TunnelOptions=[{TunnelInsideCidr=169.254.10.0/30},{TunnelInsideCidr=169.254.11.0/30}] \
  --tag-specifications 'ResourceType=vpn-connection,Tags=[{Key=Name,Value=FaceAuth-VPN}]' \
  --profile dev
```

#### 4. 繧ｪ繝ｳ繝励Ξ繝溘せ蛛ｴ縺ｮ險ｭ螳・

VPN Connection菴懈・蠕後∬ｨｭ螳壹ヵ繧｡繧､繝ｫ繧偵ム繧ｦ繝ｳ繝ｭ繝ｼ繝会ｼ・

```bash
aws ec2 describe-vpn-connections \
  --vpn-connection-ids vpn-xxxxx \
  --profile dev
```

險ｭ螳壹ヵ繧｡繧､繝ｫ繧偵が繝ｳ繝励Ξ繝溘せ縺ｮVPN繝・ヰ繧､繧ｹ縺ｫ驕ｩ逕ｨ縲・

---

### 繧ｪ繝励す繝ｧ繝ｳ3: AWS Client VPN・医ユ繧ｹ繝育畑・・

**逕ｨ騾・** 髢狗匱繝ｻ繝・せ繝育腸蠅・・縺ｿ

**繝｡繝ｪ繝・ヨ:**
- 蛟倶ｺｺ縺ｮPC縺九ｉ逶ｴ謗･謗･邯壼庄閭ｽ
- 繧ｻ繝・ヨ繧｢繝・・縺檎ｰ｡蜊・

**繝・Γ繝ｪ繝・ヨ:**
- 譛ｬ逡ｪ迺ｰ蠅・↓縺ｯ荳埼←蛻・
- 繧ｳ繧ｹ繝医′鬮倥＞

---

## 柏 ADConnector縺ｮ險ｭ螳・

### 迺ｰ蠅・､画焚

Lambda髢｢謨ｰ縺ｫ莉･荳九・迺ｰ蠅・､画焚繧定ｿｽ蜉縺吶ｋ蠢・ｦ√′縺ゅｊ縺ｾ縺呻ｼ・

```bash
# AD繧ｵ繝ｼ繝舌・險ｭ螳・
AD_SERVER_URL=ldaps://ad.company.com:636
AD_BASE_DN=DC=company,DC=com
AD_TIMEOUT=10

# 繧ｪ繝励す繝ｧ繝ｳ: 繧ｵ繝ｼ繝薙せ繧｢繧ｫ繧ｦ繝ｳ繝茨ｼ亥諺蜷阪ヰ繧､繝ｳ繝峨ｒ菴ｿ逕ｨ縺励↑縺・ｴ蜷茨ｼ・
AD_SERVICE_USER=CN=ServiceAccount,OU=ServiceAccounts,DC=company,DC=com
AD_SERVICE_PASSWORD=<Secrets Manager縺九ｉ蜿門ｾ・
```

### CDK繧ｳ繝ｼ繝峨・譖ｴ譁ｰ

`infrastructure/face_auth_stack.py` 繧堤ｷｨ髮・ｼ・

```python
# Lambda迺ｰ蠅・､画焚縺ｫ霑ｽ蜉
"environment": {
    # 譌｢蟄倥・迺ｰ蠅・､画焚...
    "AD_SERVER_URL": os.getenv("AD_SERVER_URL", "ldaps://ad.company.com:636"),
    "AD_BASE_DN": os.getenv("AD_BASE_DN", "DC=company,DC=com"),
    "AD_TIMEOUT": "10",
    # 繧ｪ繝励す繝ｧ繝ｳ: 繧ｵ繝ｼ繝薙せ繧｢繧ｫ繧ｦ繝ｳ繝・
    "AD_SERVICE_USER": os.getenv("AD_SERVICE_USER", ""),
    "AD_SERVICE_PASSWORD": f"{{{{resolve:secretsmanager:{ad_secret_arn}:SecretString:password}}}}"
}
```

### Secrets Manager縺ｮ險ｭ螳夲ｼ域耳螂ｨ・・

AD繝代せ繝ｯ繝ｼ繝峨・Secrets Manager縺ｫ菫晏ｭ假ｼ・

```bash
# Secret菴懈・
aws secretsmanager create-secret \
  --name FaceAuth/AD/ServiceAccount \
  --description "AD Service Account Credentials" \
  --secret-string '{"username":"ServiceAccount","password":"YourPassword"}' \
  --profile dev

# Lambda螳溯｡後Ο繝ｼ繝ｫ縺ｫ讓ｩ髯占ｿｽ蜉
aws iam attach-role-policy \
  --role-name FaceAuthLambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite \
  --profile dev
```

---

## ｧｪ 謗･邯壹ユ繧ｹ繝・

### 1. 繝阪ャ繝医Ρ繝ｼ繧ｯ謗･邯壹ユ繧ｹ繝・

Lambda髢｢謨ｰ縺九ｉ莉･荳九・繧ｳ繝槭Φ繝峨〒繝・せ繝茨ｼ・

```python
import socket

def test_ad_connection():
    try:
        # LDAPS謗･邯壹ユ繧ｹ繝・
        sock = socket.create_connection(("ad.company.com", 636), timeout=10)
        sock.close()
        print("笨・LDAPS connection successful")
        return True
    except Exception as e:
        print(f"笶・LDAPS connection failed: {e}")
        return False
```

### 2. LDAP謗･邯壹ユ繧ｹ繝・

ADConnector縺ｮ`test_connection()`繝｡繧ｽ繝・ラ繧剃ｽｿ逕ｨ・・

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

### 3. 遉ｾ蜩｡讀懆ｨｼ繝・せ繝・

```python
from lambda.shared.models import EmployeeInfo

employee_info = EmployeeInfo(
    employee_id="1234567",
    name="螻ｱ逕ｰ螟ｪ驛・,
    department="髢狗匱驛ｨ"
)

result = ad_connector.verify_employee("1234567", employee_info)

if result.success:
    print(f"笨・Employee verified: {result.employee_data}")
else:
    print(f"笶・Verification failed: {result.error}")
```

### 4. 繝代せ繝ｯ繝ｼ繝芽ｪ崎ｨｼ繝・せ繝・

```python
result = ad_connector.authenticate_password("1234567", "password123")

if result.success:
    print(f"笨・Authentication successful")
else:
    print(f"笶・Authentication failed: {result.error}")
```

---

## 投 ADConnector縺ｮ蜍穂ｽ・

### 遉ｾ蜩｡讀懆ｨｼ繝輔Ο繝ｼ

```
1. Lambda髢｢謨ｰ (handle_enrollment)
   竊・
2. ADConnector.verify_employee()
   竊・
3. LDAPS謗･邯・(ldaps://ad.company.com:636)
   竊・
4. LDAP讀懃ｴ｢ (employeeID={employee_id})
   竊・
5. 繧｢繧ｫ繧ｦ繝ｳ繝育憾諷狗｢ｺ隱・(userAccountControl)
   竊・
6. 遉ｾ蜩｡諠・ｱ豈碑ｼ・
   竊・
7. 邨先棡霑泌唆 (ADVerificationResult)
```

### 繝代せ繝ｯ繝ｼ繝芽ｪ崎ｨｼ繝輔Ο繝ｼ

```
1. Lambda髢｢謨ｰ (handle_emergency_auth)
   竊・
2. ADConnector.authenticate_password()
   竊・
3. LDAPS謗･邯・
   竊・
4. 遉ｾ蜩｡DN讀懃ｴ｢
   竊・
5. 繧｢繧ｫ繧ｦ繝ｳ繝育憾諷狗｢ｺ隱・
   竊・
6. LDAP Bind隧ｦ陦鯉ｼ医ヱ繧ｹ繝ｯ繝ｼ繝画､懆ｨｼ・・
   竊・
7. 邨先棡霑泌唆 (ADVerificationResult)
```

### 繧ｿ繧､繝繧｢繧ｦ繝育ｮ｡逅・

- **AD謗･邯壹ち繧､繝繧｢繧ｦ繝・** 10遘・
- **Lambda蜈ｨ菴薙ち繧､繝繧｢繧ｦ繝・** 15遘・
- **繧ｿ繧､繝繧｢繧ｦ繝郁ｶ・℃譎・** 繧ｨ繝ｩ繝ｼ繧ｳ繝ｼ繝・`AD_CONNECTION_ERROR` 繧定ｿ泌唆

---

## 白 繧ｻ繧ｭ繝･繝ｪ繝・ぅ閠・・莠矩・

### 1. LDAPS菴ｿ逕ｨ・域耳螂ｨ・・

```python
# Good: LDAPS (證怜捷蛹・
server_url = "ldaps://ad.company.com:636"

# Bad: LDAP (蟷ｳ譁・
server_url = "ldap://ad.company.com:389"
```

### 2. 繧ｵ繝ｼ繝薙せ繧｢繧ｫ繧ｦ繝ｳ繝医・譛蟆乗ｨｩ髯・

AD繧ｵ繝ｼ繝薙せ繧｢繧ｫ繧ｦ繝ｳ繝医↓縺ｯ莉･荳九・讓ｩ髯舌・縺ｿ莉倅ｸ趣ｼ・

- 笨・遉ｾ蜩｡諠・ｱ縺ｮ隱ｭ縺ｿ蜿悶ｊ
- 笨・繝代せ繝ｯ繝ｼ繝画､懆ｨｼ・・ind謫堺ｽ懶ｼ・
- 笶・譖ｸ縺崎ｾｼ縺ｿ讓ｩ髯舌・荳崎ｦ・
- 笶・邂｡逅・・ｨｩ髯舌・荳崎ｦ・

### 3. Secrets Manager菴ｿ逕ｨ

繝代せ繝ｯ繝ｼ繝峨・繧ｳ繝ｼ繝峨↓繝上・繝峨さ繝ｼ繝峨○縺壹ヾecrets Manager縺ｫ菫晏ｭ假ｼ・

```python
import boto3
import json

def get_ad_credentials():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='FaceAuth/AD/ServiceAccount')
    secret = json.loads(response['SecretString'])
    return secret['username'], secret['password']
```

### 4. 繝阪ャ繝医Ρ繝ｼ繧ｯ蛻・屬

- 笨・Lambda髢｢謨ｰ縺ｯPrivate Subnet縺ｫ驟咲ｽｮ
- 笨・繧ｻ繧ｭ繝･繝ｪ繝・ぅ繧ｰ繝ｫ繝ｼ繝励〒騾壻ｿ｡蛻ｶ髯・
- 笨・Direct Connect邨檎罰縺ｧ螳牙・縺ｪ謗･邯・

---

## 菅 繝医Λ繝悶Ν繧ｷ繝･繝ｼ繝・ぅ繝ｳ繧ｰ

### 蝠城｡・: 謗･邯壹ち繧､繝繧｢繧ｦ繝・

**逞・憾:**
```
AD connection timeout exceeded: 10.00s
```

**蜴溷屏:**
- Direct Connect/VPN謗･邯壹′遒ｺ遶九＆繧後※縺・↑縺・
- 繝ｫ繝ｼ繝医ユ繝ｼ繝悶Ν縺梧ｭ｣縺励￥險ｭ螳壹＆繧後※縺・↑縺・
- 繧ｻ繧ｭ繝･繝ｪ繝・ぅ繧ｰ繝ｫ繝ｼ繝励〒繝昴・繝・36/389縺瑚ｨｱ蜿ｯ縺輔ｌ縺ｦ縺・↑縺・

**隗｣豎ｺ遲・**
```bash
# 1. VPN/Direct Connect迥ｶ諷狗｢ｺ隱・
aws ec2 describe-vpn-connections --profile dev

# 2. 繝ｫ繝ｼ繝医ユ繝ｼ繝悶Ν遒ｺ隱・
aws ec2 describe-route-tables --filters "Name=vpc-id,Values=vpc-0af2750e674368e60" --profile dev

# 3. 繧ｻ繧ｭ繝･繝ｪ繝・ぅ繧ｰ繝ｫ繝ｼ繝礼｢ｺ隱・
aws ec2 describe-security-groups --group-names ADSecurityGroup --profile dev
```

### 蝠城｡・: LDAP Bind螟ｱ謨・

**逞・憾:**
```
LDAPBindError: invalid credentials
```

**蜴溷屏:**
- 繧ｵ繝ｼ繝薙せ繧｢繧ｫ繧ｦ繝ｳ繝医・繝代せ繝ｯ繝ｼ繝峨′髢馴＆縺｣縺ｦ縺・ｋ
- 繧ｵ繝ｼ繝薙せ繧｢繧ｫ繧ｦ繝ｳ繝医′辟｡蜉ｹ蛹悶＆繧後※縺・ｋ

**隗｣豎ｺ遲・**
```bash
# Secrets Manager遒ｺ隱・
aws secretsmanager get-secret-value --secret-id FaceAuth/AD/ServiceAccount --profile dev

# 繝代せ繝ｯ繝ｼ繝画峩譁ｰ
aws secretsmanager update-secret \
  --secret-id FaceAuth/AD/ServiceAccount \
  --secret-string '{"username":"ServiceAccount","password":"NewPassword"}' \
  --profile dev
```

### 蝠城｡・: 遉ｾ蜩｡縺瑚ｦ九▽縺九ｉ縺ｪ縺・

**逞・憾:**
```
Employee not found in AD: 1234567
```

**蜴溷屏:**
- Base DN縺碁俣驕輔▲縺ｦ縺・ｋ
- 遉ｾ蜩｡ID縺ｮ螻樊ｧ蜷阪′逡ｰ縺ｪ繧具ｼ・employeeID` vs `employeeNumber`・・

**隗｣豎ｺ遲・**

ADConnector縺ｮ繧ｳ繝ｼ繝峨ｒ菫ｮ豁｣・・

```python
# 螻樊ｧ蜷阪ｒ遒ｺ隱・
search_filter = f"(employeeNumber={employee_id})"  # employeeID縺ｧ縺ｯ縺ｪ縺銃mployeeNumber

# Base DN繧堤｢ｺ隱・
base_dn = "OU=Employees,DC=company,DC=com"  # 繧医ｊ蜈ｷ菴鍋噪縺ｪOU繧呈欠螳・
```

### 蝠城｡・: 繧｢繧ｫ繧ｦ繝ｳ繝育┌蜉ｹ蛹悶お繝ｩ繝ｼ

**逞・憾:**
```
AD account is disabled: 1234567
```

**蜴溷屏:**
- AD縺ｧ繧｢繧ｫ繧ｦ繝ｳ繝医′辟｡蜉ｹ蛹悶＆繧後※縺・ｋ

**隗｣豎ｺ遲・**
- AD邂｡逅・・↓繧｢繧ｫ繧ｦ繝ｳ繝医・譛牙柑蛹悶ｒ萓晞ｼ
- 縺ｾ縺溘・縲√ユ繧ｹ繝育畑縺ｫ蛻･縺ｮ繧｢繧ｫ繧ｦ繝ｳ繝医ｒ菴ｿ逕ｨ

---

## 搭 繝√ぉ繝・け繝ｪ繧ｹ繝・

### AD謗･邯夊ｨｭ螳壼燕

- [ ] 繧ｪ繝ｳ繝励Ξ繝溘せAD繧ｵ繝ｼ繝舌・縺ｮIP繧｢繝峨Ξ繧ｹ遒ｺ隱・
- [ ] LDAPS (繝昴・繝・36) 縺梧怏蜉ｹ縺狗｢ｺ隱・
- [ ] Base DN遒ｺ隱搾ｼ井ｾ・ `DC=company,DC=com`・・
- [ ] 繧ｵ繝ｼ繝薙せ繧｢繧ｫ繧ｦ繝ｳ繝井ｽ懈・・郁ｪｭ縺ｿ蜿悶ｊ讓ｩ髯舌・縺ｿ・・
- [ ] 繝阪ャ繝医Ρ繝ｼ繧ｯ繝励Ο繝舌う繝繝ｼ縺ｨ縺ｮ隱ｿ謨ｴ・・irect Connect菴ｿ逕ｨ譎ゑｼ・

### AWS蛛ｴ險ｭ螳・

- [ ] Customer Gateway菴懈・
- [ ] Virtual Private Gateway菴懈・
- [ ] Direct Connect Gateway菴懈・・・irect Connect菴ｿ逕ｨ譎ゑｼ・
- [ ] VPN Connection菴懈・・・PN菴ｿ逕ｨ譎ゑｼ・
- [ ] 繝ｫ繝ｼ繝医ユ繝ｼ繝悶Ν譖ｴ譁ｰ・・0.0.0.0/8 竊・VGW・・
- [ ] 繧ｻ繧ｭ繝･繝ｪ繝・ぅ繧ｰ繝ｫ繝ｼ繝礼｢ｺ隱搾ｼ医・繝ｼ繝・36/389險ｱ蜿ｯ・・
- [ ] Secrets Manager險ｭ螳夲ｼ医し繝ｼ繝薙せ繧｢繧ｫ繧ｦ繝ｳ繝茨ｼ・
- [ ] Lambda迺ｰ蠅・､画焚險ｭ螳・

### 繝・せ繝・

- [ ] 繝阪ャ繝医Ρ繝ｼ繧ｯ謗･邯壹ユ繧ｹ繝茨ｼ医・繝ｼ繝・36・・
- [ ] LDAP謗･邯壹ユ繧ｹ繝茨ｼ・test_connection()`・・
- [ ] 遉ｾ蜩｡讀懆ｨｼ繝・せ繝茨ｼ・verify_employee()`・・
- [ ] 繝代せ繝ｯ繝ｼ繝芽ｪ崎ｨｼ繝・せ繝茨ｼ・authenticate_password()`・・
- [ ] 繧ｿ繧､繝繧｢繧ｦ繝医ユ繧ｹ繝茨ｼ・0遘貞宛髯撰ｼ・

---

## 答 髢｢騾｣繝峨く繝･繝｡繝ｳ繝・

- `lambda/shared/ad_connector.py` - ADConnector縺ｮ螳溯｣・
- `docs/INFRASTRUCTURE_ARCHITECTURE.md` - 繧､繝ｳ繝輔Λ繧｢繝ｼ繧ｭ繝・け繝√Ε
- `DEPLOYMENT_STATUS_REPORT.md` - 繝・・繝ｭ繧､迥ｶ豕・

---

## 識 縺ｾ縺ｨ繧・

### 迴ｾ蝨ｨ縺ｮ迥ｶ豕・

- 笨・ADConnector繧ｳ繝ｼ繝牙ｮ溯｣・ｸ医∩
- 笨・繧ｻ繧ｭ繝･繝ｪ繝・ぅ繧ｰ繝ｫ繝ｼ繝苓ｨｭ螳壽ｸ医∩・医・繝ｼ繝・36/389險ｱ蜿ｯ・・
- 笨・Lambda髢｢謨ｰ縺ｯPrivate Subnet縺ｫ驟咲ｽｮ貂医∩
- 笞・・**Direct Connect/VPN謗･邯壹・譛ｪ險ｭ螳・*
- 笞・・**AD迺ｰ蠅・､画焚縺ｯ譛ｪ險ｭ螳・*

### 谺｡縺ｮ繧ｹ繝・ャ繝・

1. **Direct Connect縺ｾ縺溘・VPN謗･邯壹・遒ｺ遶・*
   - 繝阪ャ繝医Ρ繝ｼ繧ｯ繝励Ο繝舌う繝繝ｼ縺ｨ縺ｮ隱ｿ謨ｴ
   - Customer Gateway/Virtual Private Gateway菴懈・
   - 繝ｫ繝ｼ繝医ユ繝ｼ繝悶Ν譖ｴ譁ｰ

2. **AD迺ｰ蠅・､画焚縺ｮ險ｭ螳・*
   - `AD_SERVER_URL`
   - `AD_BASE_DN`
   - `AD_SERVICE_USER` (繧ｪ繝励す繝ｧ繝ｳ)
   - `AD_SERVICE_PASSWORD` (Secrets Manager)

3. **謗･邯壹ユ繧ｹ繝・*
   - 繝阪ャ繝医Ρ繝ｼ繧ｯ謗･邯夂｢ｺ隱・
   - LDAP謗･邯夂｢ｺ隱・
   - 遉ｾ蜩｡讀懆ｨｼ繝・せ繝・

4. **譛ｬ逡ｪ繝・・繝ｭ繧､**
   - CDK繧ｳ繝ｼ繝画峩譁ｰ
   - 蜀阪ョ繝励Ο繧､
   - E2E繝・せ繝・

---

**菴懈・譌･:** 2026蟷ｴ1譛・8譌･  
**繝舌・繧ｸ繝ｧ繝ｳ:** 1.0

