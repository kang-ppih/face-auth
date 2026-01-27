# Mock AD Connector 菴ｿ逕ｨ繧ｬ繧､繝・

## 搭 讎りｦ・

Face-Auth IdP System 縺ｧ縺ｯ縲√が繝ｳ繝励Ξ繝溘せActive Directory (AD) 縺ｸ縺ｮ謗･邯壹′險ｭ螳壹＆繧後※縺・↑縺・ｴ蜷医〒繧ゅ・*Mock AD Connector** 繧剃ｽｿ逕ｨ縺励※繧ｷ繧ｹ繝・Β繧偵ユ繧ｹ繝医〒縺阪∪縺吶・

Mock AD Connector縺ｯ縲∝ｮ滄圀縺ｮAD謗･邯壹↑縺励〒遉ｾ蜩｡逡ｪ蜿ｷ繝吶・繧ｹ縺ｮ隱崎ｨｼ繧偵す繝溘Η繝ｬ繝ｼ繝医＠縺ｾ縺吶・

---

## 笞・・驥崎ｦ√↑豕ｨ諢丈ｺ矩・

### Mock AD Connector縺ｯ髢狗匱繝ｻ繝・せ繝亥ｰら畑縺ｧ縺・

- 笨・**髢狗匱迺ｰ蠅・〒縺ｮ菴ｿ逕ｨ:** OK
- 笨・**繝・せ繝育腸蠅・〒縺ｮ菴ｿ逕ｨ:** OK
- 笶・**譛ｬ逡ｪ迺ｰ蠅・〒縺ｮ菴ｿ逕ｨ:** 邨ｶ蟇ｾNG

譛ｬ逡ｪ迺ｰ蠅・〒縺ｯ縲∝ｿ・★螳滄圀縺ｮActive Directory縺ｫ謗･邯壹＠縺ｦ縺上□縺輔＞縲・

---

## 肌 險ｭ螳壽婿豕・

### 1. 迺ｰ蠅・､画焚縺ｮ險ｭ螳・

`.env` 繝輔ぃ繧､繝ｫ繧堤ｷｨ髮・ｼ・

```bash
# Mock AD繧剃ｽｿ逕ｨ縺吶ｋ蝣ｴ蜷茨ｼ医ョ繝輔か繝ｫ繝茨ｼ・
USE_MOCK_AD=true

# 螳滄圀縺ｮAD繧剃ｽｿ逕ｨ縺吶ｋ蝣ｴ蜷・
USE_MOCK_AD=false
AD_SERVER_URL=ldaps://ad.company.com:636
AD_BASE_DN=DC=company,DC=com
```

### 2. CDK繝・・繝ｭ繧､

迺ｰ蠅・､画焚縺瑚・蜍慕噪縺ｫLambda髢｢謨ｰ縺ｫ險ｭ螳壹＆繧後∪縺呻ｼ・

```bash
npx cdk deploy --profile dev
```

### 3. 遒ｺ隱・

Lambda髢｢謨ｰ縺ｮ繝ｭ繧ｰ縺ｧ莉･荳九・繝｡繝・そ繝ｼ繧ｸ繧堤｢ｺ隱搾ｼ・

```
笞・・Using MOCK AD Connector - FOR DEVELOPMENT/TESTING ONLY!
[MOCK] Verifying employee: 1234567
[MOCK] Employee verification successful: 1234567 in 0.15s
```

---

## 識 Mock AD Connector縺ｮ蜍穂ｽ・

### 遉ｾ蜩｡讀懆ｨｼ (verify_employee)

**蜈･蜉・**
- `employee_id`: 6譯√・遉ｾ蜩｡逡ｪ蜿ｷ・井ｾ・ "1234567"・・
- `extracted_info`: OCR縺ｧ謚ｽ蜃ｺ縺励◆遉ｾ蜩｡諠・ｱ

**蜍穂ｽ・**
1. 遉ｾ蜩｡逡ｪ蜿ｷ縺・譯√・謨ｰ蟄励°繝√ぉ繝・け
2. 譛牙柑縺ｪ遉ｾ蜩｡逡ｪ蜿ｷ縺ｧ縺ゅｌ縺ｰ縲∬・蜍慕噪縺ｫ隱崎ｨｼ謌仙粥
3. 繝｢繝・け縺ｮ遉ｾ蜩｡繝・・繧ｿ繧定ｿ泌唆

**霑泌唆繝・・繧ｿ:**
```python
{
    'employee_id': '1234567',
    'name': '螻ｱ逕ｰ螟ｪ驛・,  # OCR縺九ｉ謚ｽ蜃ｺ縺励◆蜷榊燕縲√∪縺溘・閾ｪ蜍慕函謌・
    'department': '髢狗匱驛ｨ',  # OCR縺九ｉ謚ｽ蜃ｺ縺励◆驛ｨ鄂ｲ縲√∪縺溘・縲梧悴險ｭ螳壹・
    'email': 'employee1234567@company.com',
    'title': '遉ｾ蜩｡',
    'user_account_control': 512  # 譛牙柑縺ｪ繧｢繧ｫ繧ｦ繝ｳ繝・
}
```

### 繝代せ繝ｯ繝ｼ繝芽ｪ崎ｨｼ (authenticate_password)

**蜈･蜉・**
- `employee_id`: 6譯√・遉ｾ蜩｡逡ｪ蜿ｷ
- `password`: 莉ｻ諢上・繝代せ繝ｯ繝ｼ繝・

**蜍穂ｽ・**
1. 遉ｾ蜩｡逡ｪ蜿ｷ縺・譯√・謨ｰ蟄励°繝√ぉ繝・け
2. 繝代せ繝ｯ繝ｼ繝峨′遨ｺ縺ｧ縺ｪ縺代ｌ縺ｰ縲∬・蜍慕噪縺ｫ隱崎ｨｼ謌仙粥

**霑泌唆繝・・繧ｿ:**
```python
{
    'employee_id': '1234567',
    'dn': 'CN=1234567,DC=mock,DC=com'
}
```

---

## 統 菴ｿ逕ｨ萓・

### 遉ｾ蜩｡逋ｻ骭ｲ繝輔Ο繝ｼ

```
1. 繝輔Ο繝ｳ繝医お繝ｳ繝峨〒遉ｾ蜩｡險ｼ繧偵せ繧ｭ繝｣繝ｳ
   竊・
2. OCR縺ｧ遉ｾ蜩｡逡ｪ蜿ｷ繧呈歓蜃ｺ・井ｾ・ "1234567"・・
   竊・
3. Mock AD Connector縺ｧ讀懆ｨｼ
   - employee_id: "1234567" 竊・笨・閾ｪ蜍慕噪縺ｫ隱崎ｨｼ謌仙粥
   竊・
4. 鬘皮判蜒上ｒ繧ｭ繝｣繝励メ繝｣
   竊・
5. Rekognition縺ｫ逋ｻ骭ｲ
   竊・
6. DynamoDB縺ｫ菫晏ｭ・
```

### 邱頑･隱崎ｨｼ繝輔Ο繝ｼ

```
1. 繝輔Ο繝ｳ繝医お繝ｳ繝峨〒遉ｾ蜩｡險ｼ繧偵せ繧ｭ繝｣繝ｳ
   竊・
2. OCR縺ｧ遉ｾ蜩｡逡ｪ蜿ｷ繧呈歓蜃ｺ・井ｾ・ "1234567"・・
   竊・
3. 繝代せ繝ｯ繝ｼ繝牙・蜉幢ｼ井ｻｻ諢上・譁・ｭ怜・縺ｧOK・・
   竊・
4. Mock AD Connector縺ｧ隱崎ｨｼ
   - employee_id: "1234567", password: "test123" 竊・笨・閾ｪ蜍慕噪縺ｫ隱崎ｨｼ謌仙粥
   竊・
5. 繧ｻ繝・す繝ｧ繝ｳ菴懈・
   竊・
6. 繝ｭ繧ｰ繧､繝ｳ螳御ｺ・
```

---

## ｧｪ 繝・せ繝育畑縺ｮ遉ｾ蜩｡繝・・繧ｿ

Mock AD Connector縺ｫ縺ｯ縲∽ｻ･荳九・繝・せ繝育畑遉ｾ蜩｡繝・・繧ｿ縺御ｺ句燕逋ｻ骭ｲ縺輔ｌ縺ｦ縺・∪縺呻ｼ・

### 譛牙柑縺ｪ繧｢繧ｫ繧ｦ繝ｳ繝・

| 遉ｾ蜩｡逡ｪ蜿ｷ | 蜷榊燕 | 驛ｨ鄂ｲ | 繝｡繝ｼ繝ｫ |
|---------|------|------|--------|
| `1234567` | 螻ｱ逕ｰ螟ｪ驛・| 髢狗匱驛ｨ | yamada.taro@company.com |
| `7890123` | 菴占陸闃ｱ蟄・| 蝟ｶ讌ｭ驛ｨ | sato.hanako@company.com |
| `3456789` | 驤ｴ譛ｨ荳驛・| 莠ｺ莠矩Κ | suzuki.ichiro@company.com |

### 辟｡蜉ｹ縺ｪ繧｢繧ｫ繧ｦ繝ｳ繝茨ｼ医ユ繧ｹ繝育畑・・

| 遉ｾ蜩｡逡ｪ蜿ｷ | 蜷榊燕 | 驛ｨ鄂ｲ | 繧ｹ繝・・繧ｿ繧ｹ |
|---------|------|------|-----------|
| `9999999` | 辟｡蜉ｹ繧｢繧ｫ繧ｦ繝ｳ繝・| 繝・せ繝磯Κ | 笶・辟｡蜉ｹ蛹・|

**菴ｿ逕ｨ萓・**
```bash
# 譛牙柑縺ｪ繧｢繧ｫ繧ｦ繝ｳ繝医〒繝・せ繝・
employee_id: "1234567" 竊・笨・隱崎ｨｼ謌仙粥

# 辟｡蜉ｹ縺ｪ繧｢繧ｫ繧ｦ繝ｳ繝医〒繝・せ繝・
employee_id: "9999999" 竊・笶・"AD account is disabled"
```

### 縺昴・莉悶・遉ｾ蜩｡逡ｪ蜿ｷ

荳願ｨ倅ｻ･螟悶・6譯√・遉ｾ蜩｡逡ｪ蜿ｷ・井ｾ・ "1111111", "2222222"・峨ｂ菴ｿ逕ｨ蜿ｯ閭ｽ縺ｧ縺吶・
Mock AD Connector縺ｯ閾ｪ蜍慕噪縺ｫ繝｢繝・け繝・・繧ｿ繧堤函謌舌＠縺ｾ縺呻ｼ・

```python
{
    'employee_id': '1111111',
    'name': '遉ｾ蜩｡1111111',  # OCR縺九ｉ謚ｽ蜃ｺ縺励◆蜷榊燕縲√∪縺溘・閾ｪ蜍慕函謌・
    'department': '譛ｪ險ｭ螳・,  # OCR縺九ｉ謚ｽ蜃ｺ縺励◆驛ｨ鄂ｲ縲√∪縺溘・縲梧悴險ｭ螳壹・
    'email': 'employee1111111@company.com',
    'title': '遉ｾ蜩｡',
    'user_account_control': 512
}
```

---

## 売 螳滄圀縺ｮAD縺ｸ縺ｮ蛻・ｊ譖ｿ縺・

### 謇矩・

#### 1. Direct Connect/VPN謗･邯壹・遒ｺ遶・

`AD_CONNECTION_GUIDE.md` 繧貞盾辣ｧ縺励※縲√が繝ｳ繝励Ξ繝溘せAD縺ｸ縺ｮ謗･邯壹ｒ險ｭ螳壹＠縺ｾ縺吶・

#### 2. 迺ｰ蠅・､画焚縺ｮ譖ｴ譁ｰ

`.env` 繝輔ぃ繧､繝ｫ繧堤ｷｨ髮・ｼ・

```bash
# Mock AD繧堤┌蜉ｹ蛹・
USE_MOCK_AD=false

# 螳滄圀縺ｮAD險ｭ螳・
AD_SERVER_URL=ldaps://ad.company.com:636
AD_BASE_DN=DC=company,DC=com
AD_TIMEOUT=10
```

#### 3. CDK蜀阪ョ繝励Ο繧､

```bash
npx cdk deploy --profile dev
```

#### 4. 謗･邯壹ユ繧ｹ繝・

```bash
# Lambda髢｢謨ｰ縺ｮ繝ｭ繧ｰ繧堤｢ｺ隱・
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev

# 譛溷ｾ・＆繧後ｋ繝ｭ繧ｰ:
# "Using REAL AD Connector: ldaps://ad.company.com:636"
# "AD verification successful for 1234567"
```

---

## 菅 繝医Λ繝悶Ν繧ｷ繝･繝ｼ繝・ぅ繝ｳ繧ｰ

### 蝠城｡・: Mock AD縺御ｽｿ逕ｨ縺輔ｌ縺ｪ縺・

**逞・憾:**
```
Using REAL AD Connector: ldaps://ad.company.com:636
LDAPSocketOpenError: Failed to connect to AD server
```

**蜴溷屏:**
- `USE_MOCK_AD` 迺ｰ蠅・､画焚縺・`false` 縺ｫ險ｭ螳壹＆繧後※縺・ｋ

**隗｣豎ｺ遲・**
```bash
# .env繝輔ぃ繧､繝ｫ遒ｺ隱・
cat .env | grep USE_MOCK_AD

# true縺ｫ螟画峩
USE_MOCK_AD=true

# 蜀阪ョ繝励Ο繧､
npx cdk deploy --profile dev
```

### 蝠城｡・: 遉ｾ蜩｡逡ｪ蜿ｷ縺瑚ｪ崎ｨｼ縺輔ｌ縺ｪ縺・

**逞・憾:**
```
[MOCK] Invalid employee_id format: ABC123
```

**蜴溷屏:**
- 遉ｾ蜩｡逡ｪ蜿ｷ縺・譯√・謨ｰ蟄励〒縺ｯ縺ｪ縺・

**隗｣豎ｺ遲・**
- 遉ｾ蜩｡逡ｪ蜿ｷ縺ｯ蠢・★6譯√・謨ｰ蟄励↓縺励※縺上□縺輔＞・井ｾ・ "1234567"・・
- OCR縺ｧ豁｣縺励￥謚ｽ蜃ｺ縺輔ｌ縺ｦ縺・ｋ縺狗｢ｺ隱・

### 蝠城｡・: 繧｢繧ｫ繧ｦ繝ｳ繝育┌蜉ｹ蛹悶お繝ｩ繝ｼ

**逞・憾:**
```
[MOCK] Account is disabled: 9999999
```

**蜴溷屏:**
- 繝・せ繝育畑縺ｮ辟｡蜉ｹ繧｢繧ｫ繧ｦ繝ｳ繝茨ｼ・99999・峨ｒ菴ｿ逕ｨ縺励※縺・ｋ

**隗｣豎ｺ遲・**
- 譛牙柑縺ｪ繧｢繧ｫ繧ｦ繝ｳ繝茨ｼ・23456, 7890123, 3456789・峨ｒ菴ｿ逕ｨ
- 縺ｾ縺溘・縲∽ｻ悶・6譯√・遉ｾ蜩｡逡ｪ蜿ｷ繧剃ｽｿ逕ｨ

---

## 投 Mock AD縺ｨReal AD縺ｮ豈碑ｼ・

| 鬆・岼 | Mock AD | Real AD |
|------|---------|---------|
| **謗･邯・* | 荳崎ｦ・| Direct Connect/VPN蠢・ｦ・|
| **隱崎ｨｼ** | 蟶ｸ縺ｫ謌仙粥・・譯√・謨ｰ蟄暦ｼ・| 螳滄圀縺ｮAD隱崎ｨｼ |
| **遉ｾ蜩｡繝・・繧ｿ** | 繝｢繝・け繝・・繧ｿ | 螳滄圀縺ｮAD繝・・繧ｿ |
| **繝代せ繝ｯ繝ｼ繝・* | 莉ｻ諢上・譁・ｭ怜・縺ｧOK | 螳滄圀縺ｮAD繝代せ繝ｯ繝ｼ繝・|
| **繝ｬ繧ｹ繝昴Φ繧ｹ譎る俣** | 50-300ms・医す繝溘Η繝ｬ繝ｼ繝茨ｼ・| 螳滄圀縺ｮ繝阪ャ繝医Ρ繝ｼ繧ｯ驕・ｻｶ |
| **逕ｨ騾・* | 髢狗匱繝ｻ繝・せ繝・| 譛ｬ逡ｪ迺ｰ蠅・|
| **繧ｻ繧ｭ繝･繝ｪ繝・ぅ** | 笶・菴弱＞ | 笨・鬮倥＞ |

---

## 統 繧ｳ繝ｼ繝我ｾ・

### Mock AD Connector縺ｮ菴ｿ逕ｨ

```python
from lambda.shared.ad_connector_mock import create_ad_connector

# Mock AD繧剃ｽｿ逕ｨ
ad_connector = create_ad_connector(use_mock=True)

# 遉ｾ蜩｡讀懆ｨｼ
from lambda.shared.models import EmployeeInfo

employee_info = EmployeeInfo(
    employee_id="1234567",
    name="螻ｱ逕ｰ螟ｪ驛・,
    department="髢狗匱驛ｨ"
)

result = ad_connector.verify_employee("1234567", employee_info)

if result.success:
    print(f"笨・隱崎ｨｼ謌仙粥: {result.employee_data}")
else:
    print(f"笶・隱崎ｨｼ螟ｱ謨・ {result.error}")
```

### Real AD Connector縺ｮ菴ｿ逕ｨ

```python
from lambda.shared.ad_connector_mock import create_ad_connector

# Real AD繧剃ｽｿ逕ｨ
ad_connector = create_ad_connector(
    use_mock=False,
    server_url="ldaps://ad.company.com:636",
    base_dn="DC=company,DC=com",
    timeout=10
)

# 遉ｾ蜩｡讀懆ｨｼ・亥ｮ滄圀縺ｮAD縺ｫ謗･邯夲ｼ・
result = ad_connector.verify_employee("1234567", employee_info)
```

---

## 笨・繝√ぉ繝・け繝ｪ繧ｹ繝・

### Mock AD菴ｿ逕ｨ譎・

- [ ] `.env` 繝輔ぃ繧､繝ｫ縺ｧ `USE_MOCK_AD=true` 繧定ｨｭ螳・
- [ ] CDK繝・・繝ｭ繧､螳御ｺ・
- [ ] Lambda髢｢謨ｰ縺ｮ繝ｭ繧ｰ縺ｧ `[MOCK]` 繝｡繝・そ繝ｼ繧ｸ繧堤｢ｺ隱・
- [ ] 6譯√・遉ｾ蜩｡逡ｪ蜿ｷ縺ｧ繝・せ繝・
- [ ] 遉ｾ蜩｡逋ｻ骭ｲ繝輔Ο繝ｼ縺悟虚菴懊☆繧九％縺ｨ繧堤｢ｺ隱・
- [ ] 邱頑･隱崎ｨｼ繝輔Ο繝ｼ縺悟虚菴懊☆繧九％縺ｨ繧堤｢ｺ隱・

### Real AD蛻・ｊ譖ｿ縺域凾

- [ ] Direct Connect/VPN謗･邯壹′遒ｺ遶九＆繧後※縺・ｋ
- [ ] `.env` 繝輔ぃ繧､繝ｫ縺ｧ `USE_MOCK_AD=false` 繧定ｨｭ螳・
- [ ] `AD_SERVER_URL` 縺ｨ `AD_BASE_DN` 繧呈ｭ｣縺励￥險ｭ螳・
- [ ] CDK蜀阪ョ繝励Ο繧､螳御ｺ・
- [ ] Lambda髢｢謨ｰ縺ｮ繝ｭ繧ｰ縺ｧ `Using REAL AD Connector` 繧堤｢ｺ隱・
- [ ] 螳滄圀縺ｮ遉ｾ蜩｡逡ｪ蜿ｷ縺ｨ繝代せ繝ｯ繝ｼ繝峨〒繝・せ繝・
- [ ] AD謗･邯壹′豁｣蟶ｸ縺ｫ蜍穂ｽ懊☆繧九％縺ｨ繧堤｢ｺ隱・

---

## 答 髢｢騾｣繝峨く繝･繝｡繝ｳ繝・

- `lambda/shared/ad_connector_mock.py` - Mock AD Connector縺ｮ螳溯｣・
- `lambda/shared/ad_connector.py` - Real AD Connector縺ｮ螳溯｣・
- `AD_CONNECTION_GUIDE.md` - AD謗･邯夊ｨｭ螳壹ぎ繧､繝・
- `QUICK_START_TESTING_GUIDE.md` - 繝・せ繝医ぎ繧､繝・

---

## 識 縺ｾ縺ｨ繧・

### Mock AD Connector縺ｮ蛻ｩ轤ｹ

1. 笨・**AD謗･邯壻ｸ崎ｦ・* - Direct Connect/VPN險ｭ螳壹↑縺励〒繝・せ繝亥庄閭ｽ
2. 笨・**邁｡蜊倥↑繝・せ繝・* - 6譯√・遉ｾ蜩｡逡ｪ蜿ｷ縺縺代〒隱崎ｨｼ蜿ｯ閭ｽ
3. 笨・**鬮倬・* - 繝阪ャ繝医Ρ繝ｼ繧ｯ驕・ｻｶ縺ｪ縺・
4. 笨・**髢狗匱蜉ｹ邇・髄荳・* - 縺吶＄縺ｫ繧ｷ繧ｹ繝・Β繧偵ユ繧ｹ繝亥庄閭ｽ

### 菴ｿ逕ｨ荳翫・豕ｨ諢・

1. 笞・・**髢狗匱繝ｻ繝・せ繝亥ｰら畑** - 譛ｬ逡ｪ迺ｰ蠅・〒縺ｯ菴ｿ逕ｨ縺励↑縺・
2. 笞・・**繧ｻ繧ｭ繝･繝ｪ繝・ぅ** - 螳滄圀縺ｮ隱崎ｨｼ縺ｯ陦後ｏ繧後↑縺・
3. 笞・・**繝・・繧ｿ** - 繝｢繝・け繝・・繧ｿ縺ｮ縺ｿ
4. 笞・・**蛻・ｊ譖ｿ縺・* - 譛ｬ逡ｪ蜑阪↓蠢・★Real AD縺ｫ蛻・ｊ譖ｿ縺医ｋ

---

**菴懈・譌･:** 2026蟷ｴ1譛・8譌･  
**繝舌・繧ｸ繝ｧ繝ｳ:** 1.0

