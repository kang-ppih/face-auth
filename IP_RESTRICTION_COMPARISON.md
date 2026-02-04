# IP制限メカニズム比較 - Face-Auth IdP System

**作成日:** 2026-02-04  
**目的:** 現在実装されている3つのIP制限メカニズムの比較と推奨事項

---

## 📊 現在の実装状況

Face-Auth IdPシステムには**3つの異なるIP制限メカニズム**が実装されています：

### 1. Network ACL（VPCレベル）
### 2. API Gateway Resource Policy（API Gatewayレベル）
### 3. AWS WAF（WAFレベル）- **新規追加**

---

## 🔍 詳細比較

| 項目 | Network ACL | API Gateway Resource Policy | AWS WAF |
|------|-------------|----------------------------|---------|
| **適用レベル** | VPC（ネットワーク層） | API Gateway（アプリケーション層） | WAF（アプリケーション層） |
| **適用対象** | Public Subnet | API Gateway のみ | API Gateway + CloudFront |
| **設定場所** | `_create_network_acls()` | `_create_api_resource_policy()` | `_create_waf()` |
| **IP制限** | ✅ あり | ✅ あり | ✅ あり |
| **レート制限** | ❌ なし | ❌ なし | ✅ あり（1000 req/5min） |
| **CloudWatchメトリクス** | ❌ なし | ❌ なし | ✅ あり |
| **ログ** | VPC Flow Logs | CloudWatch Logs | WAF Logs |
| **コスト** | 無料 | 無料 | $14.60/月 |
| **CloudFront対応** | ❌ 不可 | ❌ 不可 | ✅ 可能 |
| **柔軟性** | 低 | 中 | 高 |
| **管理の容易さ** | 難 | 中 | 易 |

---

## 🔄 重複の詳細

### 現在の状態

```
ユーザー
  │
  ▼
┌─────────────────────────────────┐
│ 1. Network ACL (VPC)            │ ← IP制限 ✅
│    - Public Subnetに適用        │
│    - HTTPS (443) のみ許可       │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 2. API Gateway Resource Policy  │ ← IP制限 ✅ (重複)
│    - API Gatewayに適用          │
│    - Allow/Deny statements      │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ 3. AWS WAF                      │ ← IP制限 ✅ (重複)
│    - API Gateway + CloudFront   │
│    - IP Set + Web ACL           │
│    - レート制限                 │
└─────────────────────────────────┘
```

### 重複している機能

1. **IP制限**: 3つすべてで同じIPアドレスリストを使用
2. **HTTPS制限**: Network ACLとAPI Gateway Resource Policyで重複
3. **アクセス制御**: API Gateway Resource PolicyとWAFで重複

---

## ✅ 推奨構成

### オプション1: WAFのみ使用（推奨）

**理由:**
- 最も柔軟で管理しやすい
- CloudFrontとAPI Gatewayの両方をカバー
- レート制限機能あり
- CloudWatchメトリクスとログが充実
- 一元管理が可能

**削除するもの:**
- ❌ Network ACL（IP制限部分）
- ❌ API Gateway Resource Policy

**残すもの:**
- ✅ AWS WAF（IP制限 + レート制限）
- ✅ Network ACL（基本的なネットワーク制御のみ）

**コスト:** $14.60/月

---

### オプション2: 多層防御（現状維持）

**理由:**
- 防御層が多い（Defense in Depth）
- 1つの層が突破されても他の層で防御
- セキュリティ要件が非常に厳しい場合

**維持するもの:**
- ✅ Network ACL（VPCレベル）
- ✅ API Gateway Resource Policy（API Gatewayレベル）
- ✅ AWS WAF（WAFレベル + CloudFront）

**コスト:** $14.60/月（WAF分のみ追加）

**デメリット:**
- 管理が複雑
- 3箇所でIP更新が必要
- トラブルシューティングが困難

---

### オプション3: Network ACL + API Gateway Resource Policy（WAF削除）

**理由:**
- コストを抑えたい
- CloudFrontのIP制限が不要

**削除するもの:**
- ❌ AWS WAF

**残すもの:**
- ✅ Network ACL
- ✅ API Gateway Resource Policy

**コスト:** 無料

**デメリット:**
- CloudFrontのIP制限ができない
- レート制限機能なし
- CloudWatchメトリクスなし

---

## 🎯 推奨アクション

### ステップ1: WAFのみ使用する構成に変更（推奨）

#### 1. Network ACLのIP制限を削除

```python
# infrastructure/face_auth_stack.py の _create_network_acls() メソッドを簡素化

def _create_network_acls(self):
    """
    Create Network ACLs for basic network security
    (IP restriction moved to WAF)
    """
    # Get public subnets
    public_subnets = self.vpc.public_subnets
    
    if not public_subnets:
        return
    
    # Create Network ACL for public subnets
    self.public_nacl = ec2.NetworkAcl(
        self, "PublicSubnetNACL",
        vpc=self.vpc,
        network_acl_name="FaceAuth-Public-NACL"
    )
    
    # Allow all outbound traffic
    ec2.NetworkAclEntry(
        self, "AllowAllOutbound",
        network_acl=self.public_nacl,
        cidr=ec2.AclCidr.any_ipv4(),
        rule_number=100,
        traffic=ec2.AclTraffic.all_traffic(),
        direction=ec2.TrafficDirection.EGRESS,
        rule_action=ec2.Action.ALLOW
    )
    
    # Allow all inbound HTTPS traffic (WAF will handle IP restriction)
    ec2.NetworkAclEntry(
        self, "AllowHTTPS",
        network_acl=self.public_nacl,
        cidr=ec2.AclCidr.any_ipv4(),
        rule_number=100,
        traffic=ec2.AclTraffic.tcp_port(443),
        direction=ec2.TrafficDirection.INGRESS,
        rule_action=ec2.Action.ALLOW
    )
    
    # Allow ephemeral ports for return traffic
    ec2.NetworkAclEntry(
        self, "AllowEphemeral",
        network_acl=self.public_nacl,
        cidr=ec2.AclCidr.any_ipv4(),
        rule_number=110,
        traffic=ec2.AclTraffic.tcp_port_range(1024, 65535),
        direction=ec2.TrafficDirection.INGRESS,
        rule_action=ec2.Action.ALLOW
    )
    
    # Associate NACL with public subnets
    for idx, subnet in enumerate(public_subnets):
        ec2.CfnSubnetNetworkAclAssociation(
            self, f"PublicSubnetNACLAssoc{idx}",
            network_acl_id=self.public_nacl.network_acl_id,
            subnet_id=subnet.subnet_id
        )
```

#### 2. API Gateway Resource Policyを削除

```python
# infrastructure/face_auth_stack.py の _create_api_gateway() メソッドを更新

# 変更前:
policy=self._create_api_resource_policy() if self.allowed_ip_ranges != ["0.0.0.0/0"] else None

# 変更後:
policy=None  # IP restriction handled by WAF
```

#### 3. `_create_api_resource_policy()` メソッドを削除

```python
# infrastructure/face_auth_stack.py から以下のメソッドを削除
# def _create_api_resource_policy(self):
#     ...
```

---

### ステップ2: 環境変数の整理

#### 現在の環境変数

```bash
# .env
ALLOWED_IPS=203.0.113.10/32,198.51.100.0/24
```

#### 使用箇所

1. ✅ **WAF**: IP Set作成に使用
2. ❌ **Network ACL**: 削除推奨
3. ❌ **API Gateway Resource Policy**: 削除推奨

#### 推奨設定

```bash
# .env
# WAF IP制限設定（カンマ区切りのCIDR形式）
ALLOWED_IPS=203.0.113.10/32,198.51.100.0/24

# または開発環境では空にする（すべてのIPを許可）
# ALLOWED_IPS=
```

---

### ステップ3: デプロイ

```bash
# 変更をコミット
git add infrastructure/face_auth_stack.py
git commit -m "refactor(security): Simplify IP restriction to use WAF only"

# デプロイ
cdk deploy --context allowed_ips="203.0.113.10/32,198.51.100.0/24"
```

---

## 📝 各オプションの比較表

| 項目 | オプション1<br>(WAFのみ) | オプション2<br>(多層防御) | オプション3<br>(WAFなし) |
|------|------------------------|------------------------|----------------------|
| **セキュリティレベル** | 高 | 最高 | 中 |
| **管理の容易さ** | ✅ 易 | ❌ 難 | 中 |
| **コスト** | $14.60/月 | $14.60/月 | 無料 |
| **CloudFront対応** | ✅ あり | ✅ あり | ❌ なし |
| **レート制限** | ✅ あり | ✅ あり | ❌ なし |
| **メトリクス** | ✅ 充実 | ✅ 充実 | ❌ 限定的 |
| **IP更新箇所** | 1箇所 | 3箇所 | 2箇所 |
| **推奨度** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |

---

## 🎯 結論

### 推奨: オプション1（WAFのみ使用）

**理由:**
1. **一元管理**: IP制限をWAFで一元管理
2. **柔軟性**: CloudFrontとAPI Gatewayの両方をカバー
3. **機能性**: レート制限、メトリクス、ログが充実
4. **コスト**: $14.60/月は許容範囲
5. **保守性**: 管理が容易、トラブルシューティングが簡単

### 現在の状態（オプション2）を維持する場合

**条件:**
- セキュリティ要件が非常に厳しい
- 多層防御が必須
- 管理の複雑さを許容できる

**注意点:**
- IP更新時は3箇所すべてを更新する必要がある
- トラブルシューティングが複雑になる

---

## 📚 関連ドキュメント

- [WAF IP Restriction Guide](WAF_IP_RESTRICTION_GUIDE.md)
- [IP Access Control](docs/IP_ACCESS_CONTROL.md)
- [CORS and IP Restriction Guide](CORS_AND_IP_RESTRICTION_GUIDE.md)

---

**最終更新:** 2026-02-04  
**作成者:** Face-Auth Development Team  
**バージョン:** 1.0
