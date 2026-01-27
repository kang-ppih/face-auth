# 顔写真の蓄積場所ガイド

## 📍 概要

Face-Auth IdP System では、顔写真は以下の2つの場所に蓄積されます：

1. **Amazon S3** - 画像ファイル（サムネイル）の保存
2. **Amazon Rekognition Collection** - 顔特徴ベクトルの保存

---

## 🗂️ Amazon S3 バケット構造

### S3バケット名
```
face-auth-images-979431736455-ap-northeast-1
```

### フォルダ構造

```
face-auth-images-979431736455-ap-northeast-1/
├── enroll/                          # 社員登録時の顔写真（永久保存）
│   ├── {employee_id}/
│   │   └── face_thumbnail.jpg       # 200x200ピクセルのサムネイル
│   ├── 123456/
│   │   └── face_thumbnail.jpg
│   └── 789012/
│       └── face_thumbnail.jpg
│
├── logins/                          # ログイン試行時の顔写真（30日後自動削除）
│   ├── 2026-01-28/
│   │   ├── 20260128_120000_123456.jpg
│   │   ├── 20260128_120530_unknown_a1b2c3d4.jpg
│   │   └── 20260128_121000_789012.jpg
│   └── 2026-01-29/
│       └── ...
│
└── temp/                            # 一時処理ファイル（1日後自動削除）
    └── ...
```

---

## 📂 詳細説明

### 1. enroll/ フォルダ（社員登録）

**用途:** 社員登録時に撮影した顔写真を永久保存

**保存パス:**
```
enroll/{employee_id}/face_thumbnail.jpg
```

**例:**
```
enroll/123456/face_thumbnail.jpg
enroll/789012/face_thumbnail.jpg
```

**特徴:**
- ✅ **永久保存** - ライフサイクルポリシーなし
- ✅ **200x200ピクセル** - 標準化されたサムネイル
- ✅ **JPEG形式** - 品質85%で圧縮
- ✅ **暗号化** - S3管理キー（AES256）で暗号化
- ✅ **社員IDでフォルダ分け** - 管理しやすい構造

**メタデータ:**
```json
{
  "employee_id": "123456",
  "image_type": "enrollment_thumbnail",
  "processed_at": "2026-01-28T12:00:00",
  "size": "200x200"
}
```

**保存タイミング:**
- 社員登録フロー完了時
- 再登録フロー完了時（既存画像を上書き）

**アクセス方法:**
```bash
# AWS CLI
aws s3 cp s3://face-auth-images-979431736455-ap-northeast-1/enroll/123456/face_thumbnail.jpg ./

# Lambda関数内
s3_client.get_object(
    Bucket='face-auth-images-979431736455-ap-northeast-1',
    Key='enroll/123456/face_thumbnail.jpg'
)
```

---

### 2. logins/ フォルダ（ログイン試行）

**用途:** ログイン試行時の顔写真を記録（成功・失敗両方）

**保存パス:**
```
logins/{date}/{timestamp}_{employee_id_or_unknown}.jpg
```

**例:**
```
# 成功したログイン
logins/2026-01-28/20260128_120000_123456.jpg

# 失敗したログイン（社員ID不明）
logins/2026-01-28/20260128_120530_unknown_a1b2c3d4.jpg
```

**特徴:**
- ⏰ **30日後自動削除** - S3ライフサイクルポリシーで自動削除
- ✅ **200x200ピクセル** - 標準化されたサムネイル
- ✅ **JPEG形式** - 品質85%で圧縮
- ✅ **暗号化** - S3管理キー（AES256）で暗号化
- ✅ **日付でフォルダ分け** - 日次で整理
- ✅ **タイムスタンプ付き** - 試行時刻を記録

**メタデータ:**
```json
{
  "employee_id": "123456",  // または "unknown"
  "image_type": "login_attempt_thumbnail",
  "processed_at": "2026-01-28T12:00:00",
  "size": "200x200"
}
```

**保存タイミング:**
- 顔認証ログイン試行時（成功・失敗両方）
- 緊急認証試行時（失敗時のみ）

**ライフサイクルポリシー:**
```python
s3.LifecycleRule(
    id="LoginAttemptsCleanup",
    prefix="logins/",
    enabled=True,
    expiration=Duration.days(30)  # 30日後に自動削除
)
```

**アクセス方法:**
```bash
# 特定日のログイン試行画像一覧
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/logins/2026-01-28/

# 特定の画像をダウンロード
aws s3 cp s3://face-auth-images-979431736455-ap-northeast-1/logins/2026-01-28/20260128_120000_123456.jpg ./
```

---

### 3. temp/ フォルダ（一時ファイル）

**用途:** 処理中の一時ファイル保存

**保存パス:**
```
temp/{uuid}.jpg
```

**特徴:**
- ⏰ **1日後自動削除** - S3ライフサイクルポリシーで自動削除
- ✅ **一時的な保存** - 処理完了後は不要

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

### Collection名
```
face-auth-employees
```

### Collection ARN
```
aws:rekognition:ap-northeast-1:979431736455:collection/face-auth-employees
```

### 保存内容

**顔特徴ベクトル（Face Feature Vector）:**
- 顔の特徴を数値化したベクトルデータ
- 画像そのものは保存されない
- 高速な1:N検索が可能

**Face ID:**
- Rekognitionが自動生成する一意のID
- 例: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

**メタデータ:**
```json
{
  "FaceId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "ExternalImageId": "123456",  // employee_id
  "Confidence": 99.9,
  "ImageId": "uuid-of-source-image"
}
```

### 保存タイミング

1. **社員登録時**
   - 顔画像をRekognitionに送信
   - 顔特徴ベクトルを抽出
   - Collectionに登録

2. **再登録時**
   - 古いFace IDを削除
   - 新しい顔特徴ベクトルを登録

### アクセス方法

```bash
# Collection内の顔一覧
aws rekognition list-faces \
  --collection-id face-auth-employees \
  --profile dev

# 特定の顔を検索
aws rekognition search-faces-by-image \
  --collection-id face-auth-employees \
  --image-bytes fileb://face.jpg \
  --profile dev
```

---

## 📊 データフロー

### 社員登録フロー

```
1. フロントエンド
   ↓ 顔画像（元サイズ）
2. Lambda (handle_enrollment)
   ↓ 画像処理
3. ThumbnailProcessor
   ├─→ 200x200サムネイル作成
   ├─→ S3 enroll/{employee_id}/face_thumbnail.jpg に保存
   └─→ 元画像削除
4. FaceRecognitionService
   ├─→ Rekognition IndexFaces API呼び出し
   └─→ 顔特徴ベクトルをCollectionに保存
5. DynamoDB
   └─→ EmployeeFaces テーブルに face_id 保存
```

### 顔認証ログインフロー

```
1. フロントエンド
   ↓ 顔画像（元サイズ）
2. Lambda (handle_face_login)
   ↓ Liveness検出
3. FaceRecognitionService
   ├─→ Rekognition SearchFacesByImage API呼び出し
   ├─→ Collection内で1:N検索
   └─→ マッチした face_id を返す
4. ThumbnailProcessor（成功・失敗両方）
   ├─→ 200x200サムネイル作成
   └─→ S3 logins/{date}/{timestamp}_{employee_id}.jpg に保存
5. DynamoDB
   └─→ EmployeeFaces テーブルの last_login 更新
```

---

## 🔒 セキュリティ

### S3バケット

**暗号化:**
- ✅ サーバーサイド暗号化（SSE-S3）
- ✅ AES256アルゴリズム
- ✅ 転送中はHTTPS

**アクセス制御:**
- ✅ パブリックアクセスブロック有効
- ✅ Lambda実行ロールのみアクセス可能
- ✅ IAM最小権限の原則

**バケットポリシー:**
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
- ✅ Lambda実行ロールのみアクセス可能
- ✅ IAM最小権限の原則

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

## 📈 容量管理

### S3ストレージ見積もり

**1社員あたりの容量:**
- enroll/ フォルダ: 約10-20KB（200x200 JPEG）
- logins/ フォルダ: 約10-20KB × ログイン回数 × 30日

**例: 1000人の社員、1日1回ログイン:**
```
enroll/: 1000人 × 15KB = 15MB（永久保存）
logins/: 1000人 × 1回/日 × 30日 × 15KB = 450MB（30日間）
合計: 約465MB
```

**年間コスト見積もり（東京リージョン）:**
```
S3 Standard: $0.025/GB/月
465MB = 0.465GB
月額: 0.465GB × $0.025 = $0.012（約1.5円）
年額: $0.144（約18円）
```

### Rekognition Collection容量

**1社員あたりの容量:**
- 顔特徴ベクトル: 約1KB

**例: 1000人の社員:**
```
1000人 × 1KB = 1MB
```

**コスト:**
- Collection保存: 無料
- IndexFaces: $0.001/画像
- SearchFacesByImage: $0.001/検索

---

## 🛠️ 管理コマンド

### S3バケット内容確認

```bash
# enroll/ フォルダ一覧
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/enroll/ --recursive --profile dev

# logins/ フォルダ一覧（特定日）
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/logins/2026-01-28/ --profile dev

# バケット全体のサイズ確認
aws s3 ls s3://face-auth-images-979431736455-ap-northeast-1/ --recursive --summarize --profile dev
```

### Rekognition Collection管理

```bash
# Collection情報確認
aws rekognition describe-collection \
  --collection-id face-auth-employees \
  --profile dev

# 登録されている顔の数確認
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

### DynamoDB確認

```bash
# 社員の face_id 確認
aws dynamodb get-item \
  --table-name FaceAuth-EmployeeFaces \
  --key '{"employee_id": {"S": "123456"}}' \
  --profile dev

# 全社員一覧
aws dynamodb scan \
  --table-name FaceAuth-EmployeeFaces \
  --profile dev
```

---

## 🔄 バックアップとリストア

### S3バケットのバックアップ

**バージョニング:**
- フロントエンドバケット: 有効
- 画像バケット: 無効（容量削減のため）

**推奨バックアップ方法:**
```bash
# enroll/ フォルダのバックアップ（永久保存データ）
aws s3 sync s3://face-auth-images-979431736455-ap-northeast-1/enroll/ \
  ./backup/enroll/ \
  --profile dev
```

### Rekognition Collectionのバックアップ

**注意:** Rekognition Collectionは直接バックアップできません。

**推奨方法:**
1. DynamoDBの`EmployeeFaces`テーブルをバックアップ
2. 必要に応じて、enroll/ フォルダの画像から再登録

```bash
# DynamoDBバックアップ
aws dynamodb create-backup \
  --table-name FaceAuth-EmployeeFaces \
  --backup-name FaceAuth-EmployeeFaces-Backup-20260128 \
  --profile dev
```

---

## 📝 まとめ

### 顔写真の蓄積場所

| 場所 | 用途 | 保存期間 | 容量 |
|------|------|---------|------|
| **S3: enroll/** | 社員登録時の顔写真 | 永久 | 10-20KB/人 |
| **S3: logins/** | ログイン試行時の顔写真 | 30日 | 10-20KB/試行 |
| **S3: temp/** | 一時処理ファイル | 1日 | 可変 |
| **Rekognition Collection** | 顔特徴ベクトル | 永久 | 1KB/人 |
| **DynamoDB** | face_id、メタデータ | 永久 | 1KB/人 |

### 重要ポイント

1. ✅ **画像はS3に保存** - サムネイル（200x200）のみ
2. ✅ **顔特徴はRekognitionに保存** - 高速検索用
3. ✅ **メタデータはDynamoDBに保存** - face_id、employee_id紐付け
4. ✅ **自動削除** - logins/は30日、temp/は1日で自動削除
5. ✅ **暗号化** - すべてのデータが暗号化されて保存

---

**作成日:** 2026年1月28日  
**バージョン:** 1.0

