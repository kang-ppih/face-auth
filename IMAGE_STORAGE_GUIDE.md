# 顔�E真�E蓁E��場所ガイチE

## 📍 概要E

Face-Auth IdP System では、E���E真�E以下�E2つの場所に蓁E��されます！E

1. **Amazon S3** - 画像ファイル�E�サムネイル�E��E保孁E
2. **Amazon Rekognition Collection** - 顔特徴ベクトルの保孁E

---

## 🗂�E�EAmazon S3 バケチE��構造

### S3バケチE��吁E
```
face-auth-images-979431736455-ap-northeast-1
```

### フォルダ構造

```
face-auth-images-979431736455-ap-northeast-1/
├── enroll/                          # 社員登録時�E顔�E真（永乁E��存！E
━E  ├── {employee_id}/
━E  ━E  └── face_thumbnail.jpg       # 200x200ピクセルのサムネイル
━E  ├── 1234567/
━E  ━E  └── face_thumbnail.jpg
━E  └── 7890123/
━E      └── face_thumbnail.jpg
━E
├── logins/                          # ログイン試行時の顔�E真！E0日後�E動削除�E�E
━E  ├── 2026-01-28/
━E  ━E  ├── 20260128_120000_1234567.jpg
━E  ━E  ├── 20260128_120530_unknown_a1b2c3d4.jpg
━E  ━E  └── 20260128_121000_7890123.jpg
━E  └── 2026-01-29/
━E      └── ...
━E
└── temp/                            # 一時�E琁E��ァイル�E�E日後�E動削除�E�E
    └── ...
```

---

## 📂 詳細説昁E

### 1. enroll/ フォルダ�E�社員登録�E�E

**用送E** 社員登録時に撮影した顔�E真を永乁E��孁E

**保存パス:**
```
enroll/{employee_id}/face_thumbnail.jpg
```

**侁E**
```
enroll/1234567/face_thumbnail.jpg
enroll/7890123/face_thumbnail.jpg
```

**特徴:**
- ✁E**永乁E��孁E* - ライフサイクルポリシーなぁE
- ✁E**200x200ピクセル** - 標準化されたサムネイル
- ✁E**JPEG形弁E* - 品質85%で圧縮
- ✁E**暗号匁E* - S3管琁E��ー�E�EES256�E�で暗号匁E
- ✁E**社員IDでフォルダ刁E��** - 管琁E��めE��ぁE��造

**メタチE�Eタ:**
```json
{
  "employee_id": "1234567",
  "image_type": "enrollment_thumbnail",
  "processed_at": "2026-01-28T12:00:00",
  "size": "200x200"
}
```

**保存タイミング:**
- 社員登録フロー完亁E��
- 再登録フロー完亁E���E�既存画像を上書き！E

**アクセス方況E**
```bash
# AWS CLI
aws s3 cp s3://face-auth-images-979431736455-ap-northeast-1/enroll/1234567/face_thumbnail.jpg ./

# Lambda関数冁E
s3_client.get_object(
    Bucket='face-auth-images-979431736455-ap-northeast-1',
    Key='enroll/1234567/face_thumbnail.jpg'
)
```

---

### 2. logins/ フォルダ�E�ログイン試行！E

**用送E** ログイン試行時の顔�E真を記録�E��E功�E失敗両方�E�E

**保存パス:**
```
logins/{date}/{timestamp}_{employee_id_or_unknown}.jpg
```

**侁E**
```
# 成功したログイン
logins/2026-01-28/20260128_120000_1234567.jpg

# 失敗したログイン�E�社員ID不�E�E�E
logins/2026-01-28/20260128_120530_unknown_a1b2c3d4.jpg
```

**特徴:**
- ⏰ **30日後�E動削除** - S3ライフサイクルポリシーで自動削除
- ✁E**200x200ピクセル** - 標準化されたサムネイル
- ✁E**JPEG形弁E* - 品質85%で圧縮
- ✁E**暗号匁E* - S3管琁E��ー�E�EES256�E�で暗号匁E
- ✁E**日付でフォルダ刁E��** - 日次で整琁E
- ✁E**タイムスタンプ付き** - 試行時刻を記録

**メタチE�Eタ:**
```json
{
  "employee_id": "1234567",  // また�E "unknown"
  "image_type": "login_attempt_thumbnail",
  "processed_at": "2026-01-28T12:00:00",
  "size": "200x200"
}
```

**保存タイミング:**
- 顔認証ログイン試行時�E��E功�E失敗両方�E�E
- 緊急認証試行時�E�失敗時のみ�E�E

**ライフサイクルポリシー:**
```python
s3.LifecycleRule(
    id="LoginAttemptsCleanup",
    prefix="logins/",
    enabled=True,
    expiration=Duration.days(30)  # 30日後に自動削除
)
```

**アクセス方況E**
```bash
# 特定日のログイン試行画像一覧
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/logins/2026-01-28/

# 特定�E画像をダウンローチE
aws s3 cp s3://face-auth-images-979431736455-ap-northeast-1/logins/2026-01-28/20260128_120000_1234567.jpg ./
```

---

### 3. temp/ フォルダ�E�一時ファイル�E�E

**用送E** 処琁E��の一時ファイル保孁E

**保存パス:**
```
temp/{uuid}.jpg
```

**特徴:**
- ⏰ **1日後�E動削除** - S3ライフサイクルポリシーで自動削除
- ✁E**一時的な保孁E* - 処琁E��亁E���E不要E

**ライフサイクルポリシー:**
```python
s3.LifecycleRule(
    id="TempFilesCleanup",
    prefix="temp/",
    enabled=True,
    expiration=Duration.days(1)  # 1日後に自動削除
)
```

---

## 🔍 Amazon Rekognition Collection

### Collection吁E
```
face-auth-employees
```

### Collection ARN
```
aws:rekognition:ap-northeast-1:979431736455:collection/face-auth-employees
```

### 保存�E容

**顔特徴ベクトル�E�Eace Feature Vector�E�E**
- 顔�E特徴を数値化した�EクトルチE�Eタ
- 画像そのも�Eは保存されなぁE
- 高速な1:N検索が可能

**Face ID:**
- Rekognitionが�E動生成する一意�EID
- 侁E `a1b2c3d4-e5f6-7890-abcd-ef12345677890`

**メタチE�Eタ:**
```json
{
  "FaceId": "a1b2c3d4-e5f6-7890-abcd-ef12345677890",
  "ExternalImageId": "1234567",  // employee_id
  "Confidence": 99.9,
  "ImageId": "uuid-of-source-image"
}
```

### 保存タイミング

1. **社員登録晁E*
   - 顔画像をRekognitionに送信
   - 顔特徴ベクトルを抽出
   - Collectionに登録

2. **再登録晁E*
   - 古いFace IDを削除
   - 新しい顔特徴ベクトルを登録

### アクセス方況E

```bash
# Collection冁E�E顔一覧
aws rekognition list-faces \
  --collection-id face-auth-employees \
  --profile dev

# 特定�E顔を検索
aws rekognition search-faces-by-image \
  --collection-id face-auth-employees \
  --image-bytes fileb://face.jpg \
  --profile dev
```

---

## 📊 チE�Eタフロー

### 社員登録フロー

```
1. フロントエンチE
   ↁE顔画像（�Eサイズ�E�E
2. Lambda (handle_enrollment)
   ↁE画像�E琁E
3. ThumbnailProcessor
   ├─ↁE200x200サムネイル作�E
   ├─ↁES3 enroll/{employee_id}/face_thumbnail.jpg に保孁E
   └─ↁE允E��像削除
4. FaceRecognitionService
   ├─ↁERekognition IndexFaces API呼び出ぁE
   └─ↁE顔特徴ベクトルをCollectionに保孁E
5. DynamoDB
   └─ↁEEmployeeFaces チE�Eブルに face_id 保孁E
```

### 顔認証ログインフロー

```
1. フロントエンチE
   ↁE顔画像（�Eサイズ�E�E
2. Lambda (handle_face_login)
   ↁELiveness検�E
3. FaceRecognitionService
   ├─ↁERekognition SearchFacesByImage API呼び出ぁE
   ├─ↁECollection冁E��1:N検索
   └─ↁEマッチしぁEface_id を返す
4. ThumbnailProcessor�E��E功�E失敗両方�E�E
   ├─ↁE200x200サムネイル作�E
   └─ↁES3 logins/{date}/{timestamp}_{employee_id}.jpg に保孁E
5. DynamoDB
   └─ↁEEmployeeFaces チE�Eブルの last_login 更新
```

---

## 🔒 セキュリチE��

### S3バケチE��

**暗号匁E**
- ✁Eサーバ�Eサイド暗号化！ESE-S3�E�E
- ✁EAES256アルゴリズム
- ✁E転送中はHTTPS

**アクセス制御:**
- ✁EパブリチE��アクセスブロチE��有効
- ✁ELambda実行ロールのみアクセス可能
- ✁EIAM最小権限�E原則

**バケチE��ポリシー:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::979431736455:role/FaceAuthLambdaExecutionRole"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::face-auth-images-979431736455-ap-northeast-1/*"
    }
  ]
}
```

### Rekognition Collection

**アクセス制御:**
- ✁ELambda実行ロールのみアクセス可能
- ✁EIAM最小権限�E原則

**IAMポリシー:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rekognition:IndexFaces",
        "rekognition:SearchFacesByImage",
        "rekognition:DeleteFaces",
        "rekognition:ListFaces"
      ],
      "Resource": "arn:aws:rekognition:ap-northeast-1:979431736455:collection/face-auth-employees"
    }
  ]
}
```

---

## 📈 容量管琁E

### S3ストレージ見積もめE

**1社員あたり�E容釁E**
- enroll/ フォルダ: 紁E0-20KB�E�E00x200 JPEG�E�E
- logins/ フォルダ: 紁E0-20KB ÁEログイン回数 ÁE30日

**侁E 1000人の社員、E日1回ログイン:**
```
enroll/: 1000人 ÁE15KB = 15MB�E�永乁E��存！E
logins/: 1000人 ÁE1囁E日 ÁE30日 ÁE15KB = 450MB�E�E0日間！E
合訁E 紁E65MB
```

**年間コスト見積もり（東京リージョン�E�E**
```
S3 Standard: $0.025/GB/朁E
465MB = 0.465GB
月顁E 0.465GB ÁE$0.025 = $0.012�E�紁E.5冁E��E
年顁E $0.144�E�紁E8冁E��E
```

### Rekognition Collection容釁E

**1社員あたり�E容釁E**
- 顔特徴ベクトル: 紁EKB

**侁E 1000人の社員:**
```
1000人 ÁE1KB = 1MB
```

**コスチE**
- Collection保孁E 無斁E
- IndexFaces: $0.001/画僁E
- SearchFacesByImage: $0.001/検索

---

## 🛠�E�E管琁E��マンチE

### S3バケチE��冁E��確誁E

```bash
# enroll/ フォルダ一覧
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/enroll/ --recursive --profile dev

# logins/ フォルダ一覧�E�特定日�E�E
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/logins/2026-01-28/ --profile dev

# バケチE��全体�Eサイズ確誁E
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/ --recursive --summarize --profile dev
```

### Rekognition Collection管琁E

```bash
# Collection惁E��確誁E
aws rekognition describe-collection \
  --collection-id face-auth-employees \
  --profile dev

# 登録されてぁE��顔�E数確誁E
aws rekognition list-faces \
  --collection-id face-auth-employees \
  --profile dev \
  --query 'length(Faces)'

# 特定社員の顔削除
aws rekognition delete-faces \
  --collection-id face-auth-employees \
  --face-ids "face-id-here" \
  --profile dev
```

### DynamoDB確誁E

```bash
# 社員の face_id 確誁E
aws dynamodb get-item \
  --table-name FaceAuth-EmployeeFaces \
  --key '{"employee_id": {"S": "1234567"}}' \
  --profile dev

# 全社員一覧
aws dynamodb scan \
  --table-name FaceAuth-EmployeeFaces \
  --profile dev
```

---

## 🔄 バックアチE�Eとリストア

### S3バケチE��のバックアチE�E

**バ�Eジョニング:**
- フロントエンドバケチE��: 有効
- 画像バケチE��: 無効�E�容量削減�Eため�E�E

**推奨バックアチE�E方況E**
```bash
# enroll/ フォルダのバックアチE�E�E�永乁E��存データ�E�E
aws s3 sync s3://face-auth-images-979431736455-ap-northeast-1/enroll/ \
  ./backup/enroll/ \
  --profile dev
```

### Rekognition CollectionのバックアチE�E

**注愁E** Rekognition Collectionは直接バックアチE�Eできません、E

**推奨方況E**
1. DynamoDBの`EmployeeFaces`チE�EブルをバチE��アチE�E
2. 忁E��に応じて、enroll/ フォルダの画像から�E登録

```bash
# DynamoDBバックアチE�E
aws dynamodb create-backup \
  --table-name FaceAuth-EmployeeFaces \
  --backup-name FaceAuth-EmployeeFaces-Backup-20260128 \
  --profile dev
```

---

## 📝 まとめE

### 顔�E真�E蓁E��場所

| 場所 | 用送E| 保存期閁E| 容釁E|
|------|------|---------|------|
| **S3: enroll/** | 社員登録時�E顔�E省E| 永乁E| 10-20KB/人 |
| **S3: logins/** | ログイン試行時の顔�E省E| 30日 | 10-20KB/試衁E|
| **S3: temp/** | 一時�E琁E��ァイル | 1日 | 可夁E|
| **Rekognition Collection** | 顔特徴ベクトル | 永乁E| 1KB/人 |
| **DynamoDB** | face_id、メタチE�Eタ | 永乁E| 1KB/人 |

### 重要�EインチE

1. ✁E**画像�ES3に保孁E* - サムネイル�E�E00x200�E��Eみ
2. ✁E**顔特徴はRekognitionに保孁E* - 高速検索用
3. ✁E**メタチE�EタはDynamoDBに保孁E* - face_id、employee_id紐付け
4. ✁E**自動削除** - logins/は30日、temp/は1日で自動削除
5. ✁E**暗号匁E* - すべてのチE�Eタが暗号化されて保孁E

---

**作�E日:** 2026年1朁E8日  
**バ�Eジョン:** 1.0

