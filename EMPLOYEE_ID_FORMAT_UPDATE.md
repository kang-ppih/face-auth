# 社員番号フォーマット変更 - 6桁 → 7桁

## 📋 変更概要

社員番号のフォーマットを **6桁** から **7桁** に変更しました。

**変更前:** `123456` (6桁)  
**変更後:** `1234567` (7桁)

---

## 🔧 変更されたファイル

### 1. コアモジュール

#### `lambda/shared/models.py`
- `EmployeeInfo` クラスの `employee_id` 属性: 6桁 → 7桁
- `validate()` メソッドの検証ロジック: `len == 6` → `len == 7`

#### `lambda/shared/ocr_service.py`
- `validate_employee_id_format()` 関数: 正規表現 `^\d{6}$` → `^\d{7}$`

#### `lambda/shared/thumbnail_processor.py`
- `store_enrollment_thumbnail()` メソッドのドキュメント: 6桁 → 7桁
- `validate_employee_id_format()` 関数: `len == 6` → `len == 7`

#### `lambda/shared/ad_connector_mock.py`
- `MOCK_EMPLOYEES` 辞書のキー: 6桁 → 7桁
  - `123456` → `1234567`
  - `789012` → `7890123`
  - `345678` → `3456789`
  - `999999` → `9999999`
- `verify_employee()` メソッド: 検証ロジック `len == 6` → `len == 7`
- `authenticate_password()` メソッド: 検証ロジック `len == 6` → `len == 7`

### 2. ドキュメント

#### `MOCK_AD_USAGE_GUIDE.md`
- すべての社員番号例: 6桁 → 7桁
- テスト用データの社員番号更新

#### `AD_CONNECTION_GUIDE.md`
- 社員番号の説明: 6桁 → 7桁
- 例の社員番号更新

#### `IMAGE_STORAGE_GUIDE.md`
- S3パス例の社員番号: 6桁 → 7桁

#### `QUICK_START_TESTING_GUIDE.md`
- テストシナリオの社員番号: 6桁 → 7桁

---

## 📝 新しい社員番号フォーマット

### 形式

```
7桁の数字
例: 1234567
```

### 検証ルール

```python
# Python
def validate_employee_id(employee_id: str) -> bool:
    return len(employee_id) == 7 and employee_id.isdigit()

# 正規表現
r'^\d{7}$'
```

### 有効な例

- ✅ `1234567` - 正しい
- ✅ `7890123` - 正しい
- ✅ `0000001` - 正しい（先頭ゼロあり）
- ❌ `123456` - 6桁（エラー）
- ❌ `12345678` - 8桁（エラー）
- ❌ `ABC1234` - 英字含む（エラー）

---

## 🧪 テスト用社員データ（更新版）

### Mock AD Connector

| 社員番号 | 名前 | 部署 | メール | ステータス |
|---------|------|------|--------|-----------|
| `1234567` | 山田太郎 | 開発部 | yamada.taro@company.com | ✅ 有効 |
| `7890123` | 佐藤花子 | 営業部 | sato.hanako@company.com | ✅ 有効 |
| `3456789` | 鈴木一郎 | 人事部 | suzuki.ichiro@company.com | ✅ 有効 |
| `9999999` | 無効アカウント | テスト部 | disabled@company.com | ❌ 無効 |

### その他の社員番号

上記以外の7桁の数字も使用可能です（自動生成）：
- `1111111`
- `2222222`
- `5555555`
- など

---

## 🔄 移行手順

### 既存データの移行

既にシステムに登録されている6桁の社員番号がある場合：

#### オプション1: 先頭にゼロを追加

```python
# 6桁 → 7桁変換
old_id = "123456"
new_id = "0" + old_id  # "0123456"
```

#### オプション2: 新しい7桁番号を割り当て

```python
# 新しい社員番号体系
new_id = "1234567"
```

#### DynamoDB更新スクリプト例

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('FaceAuth-EmployeeFaces')

# 全レコードをスキャン
response = table.scan()

for item in response['Items']:
    old_employee_id = item['employee_id']
    
    # 6桁の場合のみ更新
    if len(old_employee_id) == 6:
        new_employee_id = "0" + old_employee_id
        
        # 新しいレコード作成
        new_item = item.copy()
        new_item['employee_id'] = new_employee_id
        table.put_item(Item=new_item)
        
        # 古いレコード削除
        table.delete_item(Key={'employee_id': old_employee_id})
        
        print(f"Updated: {old_employee_id} → {new_employee_id}")
```

### Rekognition Collection更新

```python
import boto3

rekognition = boto3.client('rekognition')
collection_id = 'face-auth-employees'

# 全顔データを取得
response = rekognition.list_faces(CollectionId=collection_id)

for face in response['Faces']:
    external_image_id = face['ExternalImageId']
    
    # 6桁の場合のみ更新
    if len(external_image_id) == 6:
        # 注意: Rekognitionは既存のExternalImageIdを変更できないため、
        # 再登録が必要
        print(f"Re-enrollment required for: {external_image_id}")
```

---

## ⚠️ 注意事項

### 1. 既存データとの互換性

- 既に6桁の社員番号で登録されているデータは、7桁に移行する必要があります
- DynamoDB、Rekognition Collection、S3の全データを更新してください

### 2. フロントエンド

- OCRで抽出される社員番号が7桁であることを確認してください
- 社員証のフォーマットが7桁に対応しているか確認してください

### 3. テスト

- 新しい7桁フォーマットで全フローをテストしてください
  - 社員登録
  - 顔認証ログイン
  - 緊急認証
  - 再登録

---

## 🧪 テスト方法

### 1. Mock ADでテスト

```bash
# .envファイル確認
USE_MOCK_AD=true

# CDKデプロイ
npx cdk deploy --profile dev

# テスト用社員番号
1234567  # 山田太郎
7890123  # 佐藤花子
3456789  # 鈴木一郎
9999999  # 無効アカウント（エラーテスト用）
```

### 2. 社員登録フロー

```
1. 社員証をスキャン
2. OCRで7桁の社員番号を抽出
3. Mock ADで検証（自動成功）
4. 顔画像をキャプチャ
5. Rekognitionに登録
6. DynamoDBに保存
```

### 3. ログ確認

```bash
# Lambda関数のログ
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev

# 期待されるログ:
# [MOCK] Verifying employee: 1234567
# [MOCK] Employee verification successful: 1234567 in 0.15s
```

---

## 📊 影響範囲

### 変更が必要なコンポーネント

- ✅ Lambda関数（共有モジュール）
- ✅ Mock AD Connector
- ✅ ドキュメント
- ⚠️ 既存のDynamoDBデータ（移行必要）
- ⚠️ 既存のRekognition Collection（再登録必要）
- ⚠️ 既存のS3データ（パス変更必要）

### 変更不要なコンポーネント

- ✅ インフラストラクチャ（CDK）
- ✅ API Gateway
- ✅ Cognito
- ✅ フロントエンド（OCRが正しく7桁を抽出すれば問題なし）

---

## ✅ チェックリスト

### コード変更

- [x] `lambda/shared/models.py` - 7桁検証
- [x] `lambda/shared/ocr_service.py` - 7桁正規表現
- [x] `lambda/shared/thumbnail_processor.py` - 7桁検証
- [x] `lambda/shared/ad_connector_mock.py` - 7桁検証、テストデータ更新

### ドキュメント更新

- [x] `MOCK_AD_USAGE_GUIDE.md` - 7桁に更新
- [x] `AD_CONNECTION_GUIDE.md` - 7桁に更新
- [x] `IMAGE_STORAGE_GUIDE.md` - 7桁に更新
- [x] `QUICK_START_TESTING_GUIDE.md` - 7桁に更新

### デプロイとテスト

- [ ] CDK再デプロイ
- [ ] 7桁社員番号でテスト
- [ ] 既存データの移行（必要な場合）
- [ ] 全フローの動作確認

---

## 🚀 次のステップ

1. **CDK再デプロイ**
   ```bash
   npx cdk deploy --profile dev
   ```

2. **テスト実行**
   - 7桁社員番号（例: `1234567`）で社員登録
   - 顔認証ログイン
   - 緊急認証

3. **既存データ移行（必要な場合）**
   - DynamoDBデータ更新
   - Rekognition Collection再登録
   - S3パス変更

4. **本番デプロイ前の確認**
   - すべてのテストが通過
   - ドキュメント更新完了
   - 移行スクリプト準備完了

---

**変更日:** 2026年1月28日  
**バージョン:** 2.0  
**変更理由:** 社員番号フォーマットを7桁に統一

