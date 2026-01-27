# Face-Auth IdP System - 繧ｯ繧､繝・け繧ｹ繧ｿ繝ｼ繝・繝・せ繝医ぎ繧､繝・

## 噫 縺吶＄縺ｫ蟋九ａ繧・

繧ｷ繧ｹ繝・Β縺ｮ繝・・繝ｭ繧､縺悟ｮ御ｺ・＠縺ｾ縺励◆縲ゅ％縺ｮ繧ｬ繧､繝峨↓蠕薙▲縺ｦ縲∝推讖溯・繧偵ユ繧ｹ繝医＠縺ｦ縺上□縺輔＞縲・

---

## 桃 繧｢繧ｯ繧ｻ繧ｹ諠・ｱ

### 繝輔Ο繝ｳ繝医お繝ｳ繝・
```
https://d3ecve2syriq5q.cloudfront.net
```

### API 繧ｨ繝ｳ繝峨・繧､繝ｳ繝・
```
https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/
```

### Cognito 諠・ｱ
- **User Pool ID:** `ap-northeast-1_ikSWDeIew`
- **Client ID:** `6u4blhui7p35ra4p882srvrpod`

---

## 笞・・驥崎ｦ√↑豕ｨ諢丈ｺ矩・

### IP蛻ｶ髯舌↓縺､縺・※

迴ｾ蝨ｨ縲∽ｻ･荳九・IP遽・峇縺九ｉ縺ｮ縺ｿ繧｢繧ｯ繧ｻ繧ｹ蜿ｯ閭ｽ縺ｧ縺呻ｼ・
```
210.128.54.64/27
```

**險ｱ蜿ｯ縺輔ｌ縺ｦ縺・↑縺ИP縺九ｉ繧｢繧ｯ繧ｻ繧ｹ縺吶ｋ縺ｨ403繧ｨ繝ｩ繝ｼ縺檎匱逕溘＠縺ｾ縺吶・*

蛻･縺ｮIP繧｢繝峨Ξ繧ｹ縺九ｉ繧｢繧ｯ繧ｻ繧ｹ縺吶ｋ蠢・ｦ√′縺ゅｋ蝣ｴ蜷茨ｼ・

1. `.env`繝輔ぃ繧､繝ｫ繧堤ｷｨ髮・
```bash
ALLOWED_IPS=210.128.54.64/27,<譁ｰ縺励＞IP>/32
```

2. CDK蜀阪ョ繝励Ο繧､
```bash
npx cdk deploy --profile dev --context allowed_ips="210.128.54.64/27,<譁ｰ縺励＞IP>/32"
```

---

## ｧｪ 繝・せ繝医す繝翫Μ繧ｪ

### 繧ｷ繝翫Μ繧ｪ1: 遉ｾ蜩｡逋ｻ骭ｲ繝輔Ο繝ｼ

**逶ｮ逧・** 譁ｰ隕冗､ｾ蜩｡縺ｮ鬘斐ョ繝ｼ繧ｿ繧堤匳骭ｲ縺吶ｋ

**謇矩・**

1. **繝輔Ο繝ｳ繝医お繝ｳ繝峨↓繧｢繧ｯ繧ｻ繧ｹ**
   ```
   https://d3ecve2syriq5q.cloudfront.net
   ```

2. **縲檎､ｾ蜩｡逋ｻ骭ｲ縲阪・繧ｿ繝ｳ繧偵け繝ｪ繝・け**

3. **遉ｾ蜩｡險ｼ逕ｻ蜒上ｒ繧｢繝・・繝ｭ繝ｼ繝・*
   - 遉ｾ蜩｡險ｼ縺ｮ蜀咏悄繧呈聴蠖ｱ縺ｾ縺溘・繧｢繝・・繝ｭ繝ｼ繝・
   - OCR縺ｧ遉ｾ蜩｡ID縲∵ｰ丞錐縲・Κ鄂ｲ繧定・蜍墓歓蜃ｺ

4. **AD隱崎ｨｼ**
   - 謚ｽ蜃ｺ縺輔ｌ縺滓ュ蝣ｱ縺ｧActive Directory縺ｫ辣ｧ莨・
   - 遉ｾ蜩｡諠・ｱ縺ｮ豁｣蠖捺ｧ繧堤｢ｺ隱・

5. **鬘皮判蜒上く繝｣繝励メ繝｣**
   - 繧ｫ繝｡繝ｩ縺ｧ鬘斐ｒ謦ｮ蠖ｱ
   - Liveness讀懷・・・90%菫｡鬆ｼ蠎ｦ・・

6. **逋ｻ骭ｲ螳御ｺ・*
   - Rekognition縺ｫ鬘斐ョ繝ｼ繧ｿ繧堤匳骭ｲ
   - DynamoDB縺ｫ遉ｾ蜩｡諠・ｱ繧剃ｿ晏ｭ・

**譛溷ｾ・＆繧後ｋ邨先棡:**
- 笨・逋ｻ骭ｲ謌仙粥繝｡繝・そ繝ｼ繧ｸ縺瑚｡ｨ遉ｺ縺輔ｌ繧・
- 笨・DynamoDB `FaceAuth-EmployeeFaces` 繝・・繝悶Ν縺ｫ繝ｬ繧ｳ繝ｼ繝峨′霑ｽ蜉縺輔ｌ繧・
- 笨・Rekognition Collection `face-auth-employees` 縺ｫ鬘斐ョ繝ｼ繧ｿ縺檎匳骭ｲ縺輔ｌ繧・

**遒ｺ隱肴婿豕・**
```bash
# DynamoDB繝・・繝悶Ν遒ｺ隱・
aws dynamodb scan --table-name FaceAuth-EmployeeFaces --profile dev

# Rekognition Collection遒ｺ隱・
aws rekognition list-faces --collection-id face-auth-employees --profile dev
```

---

### 繧ｷ繝翫Μ繧ｪ2: 鬘碑ｪ崎ｨｼ繝ｭ繧ｰ繧､繝ｳ繝輔Ο繝ｼ

**逶ｮ逧・** 逋ｻ骭ｲ貂医∩遉ｾ蜩｡縺碁｡碑ｪ崎ｨｼ縺ｧ繝ｭ繧ｰ繧､繝ｳ縺吶ｋ

**蜑肴署譚｡莉ｶ:** 繧ｷ繝翫Μ繧ｪ1縺ｧ遉ｾ蜩｡逋ｻ骭ｲ縺悟ｮ御ｺ・＠縺ｦ縺・ｋ縺薙→

**謇矩・**

1. **繝輔Ο繝ｳ繝医お繝ｳ繝峨↓繧｢繧ｯ繧ｻ繧ｹ**
   ```
   https://d3ecve2syriq5q.cloudfront.net
   ```

2. **縲碁｡碑ｪ崎ｨｼ繝ｭ繧ｰ繧､繝ｳ縲阪・繧ｿ繝ｳ繧偵け繝ｪ繝・け**

3. **鬘皮判蜒上く繝｣繝励メ繝｣**
   - 繧ｫ繝｡繝ｩ縺ｧ鬘斐ｒ謦ｮ蠖ｱ
   - Liveness讀懷・・・90%菫｡鬆ｼ蠎ｦ・・

4. **1:N 鬘疲､懃ｴ｢**
   - Rekognition Collection縺ｧ鬘斐ｒ讀懃ｴ｢
   - 鬘樔ｼｼ蠎ｦ>90%縺ｮ鬘斐ｒ迚ｹ螳・

5. **繧ｻ繝・す繝ｧ繝ｳ菴懈・**
   - Cognito縺ｧ繧ｻ繝・す繝ｧ繝ｳ繧剃ｽ懈・
   - JWT繝医・繧ｯ繝ｳ繧堤匱陦・

6. **繝ｭ繧ｰ繧､繝ｳ螳御ｺ・*
   - 繝繝・す繝･繝懊・繝峨∪縺溘・繝帙・繝逕ｻ髱｢縺ｫ驕ｷ遘ｻ

**譛溷ｾ・＆繧後ｋ邨先棡:**
- 笨・繝ｭ繧ｰ繧､繝ｳ謌仙粥繝｡繝・そ繝ｼ繧ｸ縺瑚｡ｨ遉ｺ縺輔ｌ繧・
- 笨・DynamoDB `FaceAuth-AuthSessions` 繝・・繝悶Ν縺ｫ繧ｻ繝・す繝ｧ繝ｳ縺御ｽ懈・縺輔ｌ繧・
- 笨・`last_login` 繧ｿ繧､繝繧ｹ繧ｿ繝ｳ繝励′譖ｴ譁ｰ縺輔ｌ繧・

**遒ｺ隱肴婿豕・**
```bash
# 繧ｻ繝・す繝ｧ繝ｳ繝・・繝悶Ν遒ｺ隱・
aws dynamodb scan --table-name FaceAuth-AuthSessions --profile dev

# 遉ｾ蜩｡繝・・繝悶Ν縺ｮlast_login遒ｺ隱・
aws dynamodb get-item \
  --table-name FaceAuth-EmployeeFaces \
  --key '{"employee_id": {"S": "<遉ｾ蜩｡ID>"}}' \
  --profile dev
```

---

### 繧ｷ繝翫Μ繧ｪ3: 邱頑･隱崎ｨｼ繝輔Ο繝ｼ

**逶ｮ逧・** 鬘碑ｪ崎ｨｼ縺御ｽｿ縺医↑縺・ｴ蜷医↓遉ｾ蜩｡險ｼ+AD繝代せ繝ｯ繝ｼ繝峨〒繝ｭ繧ｰ繧､繝ｳ縺吶ｋ

**謇矩・**

1. **繝輔Ο繝ｳ繝医お繝ｳ繝峨↓繧｢繧ｯ繧ｻ繧ｹ**
   ```
   https://d3ecve2syriq5q.cloudfront.net
   ```

2. **縲檎ｷ頑･隱崎ｨｼ縲阪・繧ｿ繝ｳ繧偵け繝ｪ繝・け**

3. **遉ｾ蜩｡險ｼ逕ｻ蜒上ｒ繧｢繝・・繝ｭ繝ｼ繝・*
   - 遉ｾ蜩｡險ｼ縺ｮ蜀咏悄繧呈聴蠖ｱ縺ｾ縺溘・繧｢繝・・繝ｭ繝ｼ繝・
   - OCR縺ｧ遉ｾ蜩｡ID縲∵ｰ丞錐繧呈歓蜃ｺ

4. **AD繝代せ繝ｯ繝ｼ繝牙・蜉・*
   - Active Directory縺ｮ繝代せ繝ｯ繝ｼ繝峨ｒ蜈･蜉・

5. **AD隱崎ｨｼ**
   - LDAPS邨檎罰縺ｧAD隱崎ｨｼ・・0遘偵ち繧､繝繧｢繧ｦ繝茨ｼ・
   - 隱崎ｨｼ謌仙粥蠕後√そ繝・す繝ｧ繝ｳ菴懈・

6. **繝ｭ繧ｰ繧､繝ｳ螳御ｺ・*
   - 繝繝・す繝･繝懊・繝峨∪縺溘・繝帙・繝逕ｻ髱｢縺ｫ驕ｷ遘ｻ

**譛溷ｾ・＆繧後ｋ邨先棡:**
- 笨・繝ｭ繧ｰ繧､繝ｳ謌仙粥繝｡繝・そ繝ｼ繧ｸ縺瑚｡ｨ遉ｺ縺輔ｌ繧・
- 笨・DynamoDB `FaceAuth-AuthSessions` 繝・・繝悶Ν縺ｫ繧ｻ繝・す繝ｧ繝ｳ縺御ｽ懈・縺輔ｌ繧・
- 笨・螟ｱ謨励＠縺溷ｴ蜷医ヾ3 `logins/` 縺ｫ隧ｦ陦後Ο繧ｰ縺御ｿ晏ｭ倥＆繧後ｋ

**遒ｺ隱肴婿豕・**
```bash
# 繧ｻ繝・す繝ｧ繝ｳ繝・・繝悶Ν遒ｺ隱・
aws dynamodb scan --table-name FaceAuth-AuthSessions --profile dev

# 螟ｱ謨励Ο繧ｰ遒ｺ隱搾ｼ亥､ｱ謨励＠縺溷ｴ蜷茨ｼ・
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/logins/ --profile dev
```

---

### 繧ｷ繝翫Μ繧ｪ4: 蜀咲匳骭ｲ繝輔Ο繝ｼ

**逶ｮ逧・** 譌｢蟄倡､ｾ蜩｡縺ｮ鬘斐ョ繝ｼ繧ｿ繧呈峩譁ｰ縺吶ｋ

**蜑肴署譚｡莉ｶ:** 繧ｷ繝翫Μ繧ｪ1縺ｧ遉ｾ蜩｡逋ｻ骭ｲ縺悟ｮ御ｺ・＠縺ｦ縺・ｋ縺薙→

**謇矩・**

1. **繝輔Ο繝ｳ繝医お繝ｳ繝峨↓繧｢繧ｯ繧ｻ繧ｹ**
   ```
   https://d3ecve2syriq5q.cloudfront.net
   ```

2. **縲悟・逋ｻ骭ｲ縲阪・繧ｿ繝ｳ繧偵け繝ｪ繝・け**

3. **遉ｾ蜩｡險ｼ逕ｻ蜒上ｒ繧｢繝・・繝ｭ繝ｼ繝・*
   - 遉ｾ蜩｡險ｼ縺ｮ蜀咏悄繧呈聴蠖ｱ縺ｾ縺溘・繧｢繝・・繝ｭ繝ｼ繝・
   - OCR縺ｧ遉ｾ蜩｡ID縲∵ｰ丞錐繧呈歓蜃ｺ

4. **AD隱崎ｨｼ**
   - Active Directory縺ｧ譛ｬ莠ｺ遒ｺ隱・

5. **蜿､縺・｡斐ョ繝ｼ繧ｿ蜑企勁**
   - Rekognition Collection縺九ｉ蜿､縺・｡斐ョ繝ｼ繧ｿ繧貞炎髯､

6. **譁ｰ縺励＞鬘皮判蜒上く繝｣繝励メ繝｣**
   - 繧ｫ繝｡繝ｩ縺ｧ鬘斐ｒ謦ｮ蠖ｱ
   - Liveness讀懷・・・90%菫｡鬆ｼ蠎ｦ・・

7. **蜀咲匳骭ｲ螳御ｺ・*
   - Rekognition縺ｫ譁ｰ縺励＞鬘斐ョ繝ｼ繧ｿ繧堤匳骭ｲ
   - DynamoDB縺ｮ`face_id`繧呈峩譁ｰ

**譛溷ｾ・＆繧後ｋ邨先棡:**
- 笨・蜀咲匳骭ｲ謌仙粥繝｡繝・そ繝ｼ繧ｸ縺瑚｡ｨ遉ｺ縺輔ｌ繧・
- 笨・DynamoDB `FaceAuth-EmployeeFaces` 繝・・繝悶Ν縺ｮ`face_id`縺梧峩譁ｰ縺輔ｌ繧・
- 笨・Rekognition Collection縺ｮ鬘斐ョ繝ｼ繧ｿ縺梧峩譁ｰ縺輔ｌ繧・

**遒ｺ隱肴婿豕・**
```bash
# 遉ｾ蜩｡繝・・繝悶Ν縺ｮface_id遒ｺ隱・
aws dynamodb get-item \
  --table-name FaceAuth-EmployeeFaces \
  --key '{"employee_id": {"S": "<遉ｾ蜩｡ID>"}}' \
  --profile dev

# Rekognition Collection遒ｺ隱・
aws rekognition list-faces --collection-id face-auth-employees --profile dev
```

---

### 繧ｷ繝翫Μ繧ｪ5: 繧ｹ繝・・繧ｿ繧ｹ遒ｺ隱・

**逶ｮ逧・** 迴ｾ蝨ｨ縺ｮ繧ｻ繝・す繝ｧ繝ｳ迥ｶ諷九ｒ遒ｺ隱阪☆繧・

**謇矩・**

1. **API繧ｨ繝ｳ繝峨・繧､繝ｳ繝医↓逶ｴ謗･繝ｪ繧ｯ繧ｨ繧ｹ繝・*
   ```bash
   curl -X GET https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
   ```

2. **繝ｬ繧ｹ繝昴Φ繧ｹ遒ｺ隱・*
   ```json
   {
     "statusCode": 200,
     "body": {
       "status": "healthy",
       "timestamp": "2026-01-28T12:00:00Z"
     }
   }
   ```

**譛溷ｾ・＆繧後ｋ邨先棡:**
- 笨・200 OK 繝ｬ繧ｹ繝昴Φ繧ｹ
- 笨・繧ｷ繧ｹ繝・Β繧ｹ繝・・繧ｿ繧ｹ縺瑚ｿ斐＆繧後ｋ

---

## 剥 繝・ヰ繝・げ縺ｨ繝ｭ繧ｰ遒ｺ隱・

### Lambda髢｢謨ｰ縺ｮ繝ｭ繧ｰ遒ｺ隱・

```bash
# Enrollment Lambda
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev

# Face Login Lambda
aws logs tail /aws/lambda/FaceAuth-FaceLogin --follow --profile dev

# Emergency Auth Lambda
aws logs tail /aws/lambda/FaceAuth-EmergencyAuth --follow --profile dev

# Re-enrollment Lambda
aws logs tail /aws/lambda/FaceAuth-ReEnrollment --follow --profile dev

# Status Lambda
aws logs tail /aws/lambda/FaceAuth-Status --follow --profile dev
```

### API Gateway縺ｮ繧｢繧ｯ繧ｻ繧ｹ繝ｭ繧ｰ

```bash
aws logs tail /aws/apigateway/face-auth-access-logs --follow --profile dev
```

### 繧ｨ繝ｩ繝ｼ繝ｭ繧ｰ縺ｮ繝輔ぅ繝ｫ繧ｿ繝ｪ繝ｳ繧ｰ

```bash
# ERROR繝ｬ繝吶Ν縺ｮ繝ｭ繧ｰ縺ｮ縺ｿ陦ｨ遉ｺ
aws logs filter-log-events \
  --log-group-name /aws/lambda/FaceAuth-Enrollment \
  --filter-pattern "ERROR" \
  --profile dev
```

---

## 菅 繧医￥縺ゅｋ蝠城｡後→隗｣豎ｺ遲・

### 蝠城｡・: 繝輔Ο繝ｳ繝医お繝ｳ繝峨↓繧｢繧ｯ繧ｻ繧ｹ縺ｧ縺阪↑縺・

**逞・憾:** `https://d3ecve2syriq5q.cloudfront.net` 縺ｫ繧｢繧ｯ繧ｻ繧ｹ縺吶ｋ縺ｨ403繧ｨ繝ｩ繝ｼ

**隗｣豎ｺ遲・**
```bash
# CloudFront繧ｭ繝｣繝・す繝･辟｡蜉ｹ蛹・
aws cloudfront create-invalidation \
  --distribution-id E2G99Q4A3UQ8PU \
  --paths "/*" \
  --profile dev

# 5-10蛻・ｾ・▽
```

### 蝠城｡・: API蜻ｼ縺ｳ蜃ｺ縺励〒403繧ｨ繝ｩ繝ｼ

**逞・憾:** API蜻ｼ縺ｳ蜃ｺ縺励〒403 Forbidden繧ｨ繝ｩ繝ｼ

**蜴溷屏:** IP蛻ｶ髯舌↓繧医ｊ縲∬ｨｱ蜿ｯ縺輔ｌ縺ｦ縺・↑縺ИP繧｢繝峨Ξ繧ｹ縺九ｉ繧｢繧ｯ繧ｻ繧ｹ縺励※縺・ｋ

**隗｣豎ｺ遲・**
```bash
# 迴ｾ蝨ｨ縺ｮIP繧｢繝峨Ξ繧ｹ遒ｺ隱・
curl https://checkip.amazonaws.com

# .env繝輔ぃ繧､繝ｫ譖ｴ譁ｰ
ALLOWED_IPS=210.128.54.64/27,<譁ｰ縺励＞IP>/32

# 蜀阪ョ繝励Ο繧､
npx cdk deploy --profile dev \
  --context allowed_ips="210.128.54.64/27,<譁ｰ縺励＞IP>/32"
```

### 蝠城｡・: Lambda髢｢謨ｰ縺ｧImportError

**逞・憾:** `ModuleNotFoundError: No module named 'jwt'`

**蜴溷屏:** 螟夜Κ繝ｩ繧､繝悶Λ繝ｪ縺後ヰ繝ｳ繝峨Ν縺輔ｌ縺ｦ縺・↑縺・

**隗｣豎ｺ遲・** Lambda Layer繧剃ｽ懈・・郁ｩｳ邏ｰ縺ｯ`DEPLOYMENT_STATUS_REPORT.md`蜿ら・・・

### 蝠城｡・: CORS繧ｨ繝ｩ繝ｼ

**逞・憾:** 繝悶Λ繧ｦ繧ｶ繧ｳ繝ｳ繧ｽ繝ｼ繝ｫ縺ｫ`CORS policy: No 'Access-Control-Allow-Origin' header`

**隗｣豎ｺ遲・**
```bash
# .env繝輔ぃ繧､繝ｫ遒ｺ隱・
cat .env | grep FRONTEND_ORIGINS

# 豁｣縺励＞繧ｪ繝ｪ繧ｸ繝ｳ繧定ｨｭ螳・
FRONTEND_ORIGINS=https://d3ecve2syriq5q.cloudfront.net

# 蜀阪ョ繝励Ο繧､
npx cdk deploy --profile dev \
  --context frontend_origins="https://d3ecve2syriq5q.cloudfront.net"
```

### 蝠城｡・: Rekognition Collection not found

**逞・憾:** `ResourceNotFoundException: Collection face-auth-employees not found`

**隗｣豎ｺ遲・**
```bash
# Collection菴懈・
aws rekognition create-collection \
  --collection-id face-auth-employees \
  --profile dev
```

---

## 投 繝代ヵ繧ｩ繝ｼ繝槭Φ繧ｹ繝・せ繝・

### Lambda髢｢謨ｰ縺ｮ繝ｬ繧ｹ繝昴Φ繧ｹ繧ｿ繧､繝貂ｬ螳・

```bash
# 10蝗槫ｮ溯｡後＠縺ｦ蟷ｳ蝮・Ξ繧ｹ繝昴Φ繧ｹ繧ｿ繧､繝繧呈ｸｬ螳・
for i in {1..10}; do
  time curl -X GET https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
done
```

### 蜷梧凾螳溯｡後ユ繧ｹ繝・

```bash
# Apache Bench・郁ｦ√う繝ｳ繧ｹ繝医・繝ｫ・・
ab -n 100 -c 10 https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
```

---

## 柏 繧ｻ繧ｭ繝･繝ｪ繝・ぅ繝√ぉ繝・け

### 1. S3繝舌こ繝・ヨ縺ｮ繝代ヶ繝ｪ繝・け繧｢繧ｯ繧ｻ繧ｹ遒ｺ隱・

```bash
# 繝代ヶ繝ｪ繝・け繧｢繧ｯ繧ｻ繧ｹ縺後ヶ繝ｭ繝・け縺輔ｌ縺ｦ縺・ｋ縺薙→繧堤｢ｺ隱・
aws s3api get-public-access-block \
  --bucket face-auth-images-979431736455-ap-northeast-1 \
  --profile dev

aws s3api get-public-access-block \
  --bucket face-auth-frontend-979431736455-ap-northeast-1 \
  --profile dev
```

**譛溷ｾ・＆繧後ｋ邨先棡:**
```json
{
  "PublicAccessBlockConfiguration": {
    "BlockPublicAcls": true,
    "IgnorePublicAcls": true,
    "BlockPublicPolicy": true,
    "RestrictPublicBuckets": true
  }
}
```

### 2. Lambda螳溯｡後Ο繝ｼ繝ｫ縺ｮ讓ｩ髯千｢ｺ隱・

```bash
# Lambda螳溯｡後Ο繝ｼ繝ｫ縺ｮ繝昴Μ繧ｷ繝ｼ遒ｺ隱・
aws iam list-attached-role-policies \
  --role-name FaceAuthIdPStack-FaceAuthLambdaExecutionRole* \
  --profile dev
```

### 3. API Gateway IP蛻ｶ髯千｢ｺ隱・

```bash
# API Gateway Resource Policy遒ｺ隱・
aws apigateway get-rest-api \
  --rest-api-id zao7evz9jk \
  --profile dev \
  --query "policy"
```

---

## 嶋 繝｢繝九ち繝ｪ繝ｳ繧ｰ繝繝・す繝･繝懊・繝・

### CloudWatch 繝｡繝医Μ繧ｯ繧ｹ遒ｺ隱・

```bash
# Lambda髢｢謨ｰ縺ｮ繧ｨ繝ｩ繝ｼ謨ｰ
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=FaceAuth-Enrollment \
  --start-time 2026-01-28T00:00:00Z \
  --end-time 2026-01-28T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --profile dev

# API Gateway縺ｮ繝ｪ繧ｯ繧ｨ繧ｹ繝域焚
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=FaceAuth-API \
  --start-time 2026-01-28T00:00:00Z \
  --end-time 2026-01-28T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --profile dev
```

---

## 笨・繝・せ繝亥ｮ御ｺ・メ繧ｧ繝・け繝ｪ繧ｹ繝・

- [ ] 繝輔Ο繝ｳ繝医お繝ｳ繝峨↓繧｢繧ｯ繧ｻ繧ｹ縺ｧ縺阪ｋ
- [ ] 遉ｾ蜩｡逋ｻ骭ｲ繝輔Ο繝ｼ縺悟虚菴懊☆繧・
- [ ] 鬘碑ｪ崎ｨｼ繝ｭ繧ｰ繧､繝ｳ繝輔Ο繝ｼ縺悟虚菴懊☆繧・
- [ ] 邱頑･隱崎ｨｼ繝輔Ο繝ｼ縺悟虚菴懊☆繧・
- [ ] 蜀咲匳骭ｲ繝輔Ο繝ｼ縺悟虚菴懊☆繧・
- [ ] 繧ｹ繝・・繧ｿ繧ｹ遒ｺ隱喉PI縺悟虚菴懊☆繧・
- [ ] CORS險ｭ螳壹′豁｣縺励￥蜍穂ｽ懊☆繧・
- [ ] IP蛻ｶ髯舌′豁｣縺励￥蜍穂ｽ懊☆繧・
- [ ] Lambda髢｢謨ｰ縺ｮ繝ｭ繧ｰ縺檎｢ｺ隱阪〒縺阪ｋ
- [ ] DynamoDB縺ｫ繝・・繧ｿ縺御ｿ晏ｭ倥＆繧後ｋ
- [ ] Rekognition Collection縺ｫ鬘斐ョ繝ｼ繧ｿ縺檎匳骭ｲ縺輔ｌ繧・
- [ ] 繧ｻ繝・す繝ｧ繝ｳ邂｡逅・′豁｣縺励￥蜍穂ｽ懊☆繧・

---

## 到 繧ｵ繝昴・繝・

蝠城｡後′逋ｺ逕溘＠縺溷ｴ蜷医・縲∽ｻ･荳九・繝峨く繝･繝｡繝ｳ繝医ｒ蜿ら・縺励※縺上□縺輔＞・・

- `DEPLOYMENT_STATUS_REPORT.md` - 繝・・繝ｭ繧､螳御ｺ・Ξ繝昴・繝・
- `DEPLOYMENT_GUIDE.md` - 繝・・繝ｭ繧､謇矩・
- `CORS_AND_IP_RESTRICTION_GUIDE.md` - CORS繝ｻIP蛻ｶ髯舌ぎ繧､繝・
- `docs/INFRASTRUCTURE_ARCHITECTURE.md` - 繧､繝ｳ繝輔Λ繧｢繝ｼ繧ｭ繝・け繝√Ε

---

**菴懈・譌･:** 2026蟷ｴ1譛・8譌･  
**繧ｹ繝・・繧ｿ繧ｹ:** 笨・繝・せ繝域ｺ門ｙ螳御ｺ・

繧ｷ繧ｹ繝・Β縺ｯ遞ｼ蜒榊庄閭ｽ縺ｪ迥ｶ諷九〒縺吶ゆｸ願ｨ倥・繝・せ繝医す繝翫Μ繧ｪ縺ｫ蠕薙▲縺ｦ縲∝推讖溯・縺ｮ蜍穂ｽ懃｢ｺ隱阪ｒ螳滓命縺励※縺上□縺輔＞縲・

