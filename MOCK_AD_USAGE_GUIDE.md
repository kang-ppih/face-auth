# Mock AD Connector 使用ガイド

## 📋 概要

Face-Auth IdP System では、オンプレミスActive Directory (AD) への接続が設定されていない場合でも、**Mock AD Connector** を使用してシステムをテストできます。

Mock AD Connectorは、実際のAD接続なしで社員番号ベースの認証をシミュレートします。

---

## ⚠️ 重要な注意事項

### Mock AD Connectorは開発・テスト専用です

- ✅ **開発環境での使用:** OK
- ✅ **テスト環境での使用:** OK
- ❌ **本番環境での使用:** 絶対NG

本番環境では、必ず実際のActive Directoryに接続してください。

---

## 🔧 設定方法

### 1. 環境変数の設定

`.env` ファイルを編集：

```bash
# Mock ADを使用する場合（デフォルト）
USE_MOCK_AD=true

# 実際のADを使用する場合
USE_MOCK_AD=false
AD_SERVER_URL=ldaps://ad.company.com:636
AD_BASE_DN=DC=company,DC=com
```

### 2. CDKデプロイ

環境変数が自動的にLambda関数に設定されます：

```bash
npx cdk deploy --profile dev
```

### 3. 確認

Lambda関数のログで以下のメッセージを確認：

```
⚠️ Using MOCK AD Connector - FOR DEVELOPMENT/TESTING ONLY!
[MOCK] Verifying employee: 123456
[MOCK] Employee verification successful: 123456 in 0.15s
```

---

## 🎯 Mock AD Connectorの動作

### 社員検証 (verify_employee)

**入力:**
- `employee_id`: 6桁の社員番号（例: "123456"）
- `extracted_info`: OCRで抽出した社員情報

**動作:**
1. 社員番号が6桁の数字かチェック
2. 有効な社員番号であれば、自動的に認証成功
3. モックの社員データを返却

**返却データ:**
```python
{
    'employee_id': '123456',
    'name': '山田太郎',  # OCRから抽出した名前、または自動生成
    'department': '開発部',  # OCRから抽出した部署、または「未設定」
    'email': 'employee123456@company.com',
    'title': '社員',
    'user_account_control': 512  # 有効なアカウント
}
```

### パスワード認証 (authenticate_password)

**入力:**
- `employee_id`: 6桁の社員番号
- `password`: 任意のパスワード

**動作:**
1. 社員番号が6桁の数字かチェック
2. パスワードが空でなければ、自動的に認証成功

**返却データ:**
```python
{
    'employee_id': '123456',
    'dn': 'CN=123456,DC=mock,DC=com'
}
```

---

## 📝 使用例

### 社員登録フロー

```
1. フロントエンドで社員証をスキャン
   ↓
2. OCRで社員番号を抽出（例: "123456"）
   ↓
3. Mock AD Connectorで検証
   - employee_id: "123456" → ✅ 自動的に認証成功
   ↓
4. 顔画像をキャプチャ
   ↓
5. Rekognitionに登録
   ↓
6. DynamoDBに保存
```

### 緊急認証フロー

```
1. フロントエンドで社員証をスキャン
   ↓
2. OCRで社員番号を抽出（例: "123456"）
   ↓
3. パスワード入力（任意の文字列でOK）
   ↓
4. Mock AD Connectorで認証
   - employee_id: "123456", password: "test123" → ✅ 自動的に認証成功
   ↓
5. セッション作成
   ↓
6. ログイン完了
```

---

## 🧪 テスト用の社員データ

Mock AD Connectorには、以下のテスト用社員データが事前登録されています：

### 有効なアカウント

| 社員番号 | 名前 | 部署 | メール |
|---------|------|------|--------|
| `123456` | 山田太郎 | 開発部 | yamada.taro@company.com |
| `789012` | 佐藤花子 | 営業部 | sato.hanako@company.com |
| `345678` | 鈴木一郎 | 人事部 | suzuki.ichiro@company.com |

### 無効なアカウント（テスト用）

| 社員番号 | 名前 | 部署 | ステータス |
|---------|------|------|-----------|
| `999999` | 無効アカウント | テスト部 | ❌ 無効化 |

**使用例:**
```bash
# 有効なアカウントでテスト
employee_id: "123456" → ✅ 認証成功

# 無効なアカウントでテスト
employee_id: "999999" → ❌ "AD account is disabled"
```

### その他の社員番号

上記以外の6桁の社員番号（例: "111111", "222222"）も使用可能です。
Mock AD Connectorは自動的にモックデータを生成します：

```python
{
    'employee_id': '111111',
    'name': '社員111111',  # OCRから抽出した名前、または自動生成
    'department': '未設定',  # OCRから抽出した部署、または「未設定」
    'email': 'employee111111@company.com',
    'title': '社員',
    'user_account_control': 512
}
```

---

## 🔄 実際のADへの切り替え

### 手順

#### 1. Direct Connect/VPN接続の確立

`AD_CONNECTION_GUIDE.md` を参照して、オンプレミスADへの接続を設定します。

#### 2. 環境変数の更新

`.env` ファイルを編集：

```bash
# Mock ADを無効化
USE_MOCK_AD=false

# 実際のAD設定
AD_SERVER_URL=ldaps://ad.company.com:636
AD_BASE_DN=DC=company,DC=com
AD_TIMEOUT=10
```

#### 3. CDK再デプロイ

```bash
npx cdk deploy --profile dev
```

#### 4. 接続テスト

```bash
# Lambda関数のログを確認
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev

# 期待されるログ:
# "Using REAL AD Connector: ldaps://ad.company.com:636"
# "AD verification successful for 123456"
```

---

## 🐛 トラブルシューティング

### 問題1: Mock ADが使用されない

**症状:**
```
Using REAL AD Connector: ldaps://ad.company.com:636
LDAPSocketOpenError: Failed to connect to AD server
```

**原因:**
- `USE_MOCK_AD` 環境変数が `false` に設定されている

**解決策:**
```bash
# .envファイル確認
cat .env | grep USE_MOCK_AD

# trueに変更
USE_MOCK_AD=true

# 再デプロイ
npx cdk deploy --profile dev
```

### 問題2: 社員番号が認証されない

**症状:**
```
[MOCK] Invalid employee_id format: ABC123
```

**原因:**
- 社員番号が6桁の数字ではない

**解決策:**
- 社員番号は必ず6桁の数字にしてください（例: "123456"）
- OCRで正しく抽出されているか確認

### 問題3: アカウント無効化エラー

**症状:**
```
[MOCK] Account is disabled: 999999
```

**原因:**
- テスト用の無効アカウント（999999）を使用している

**解決策:**
- 有効なアカウント（123456, 789012, 345678）を使用
- または、他の6桁の社員番号を使用

---

## 📊 Mock ADとReal ADの比較

| 項目 | Mock AD | Real AD |
|------|---------|---------|
| **接続** | 不要 | Direct Connect/VPN必要 |
| **認証** | 常に成功（6桁の数字） | 実際のAD認証 |
| **社員データ** | モックデータ | 実際のADデータ |
| **パスワード** | 任意の文字列でOK | 実際のADパスワード |
| **レスポンス時間** | 50-300ms（シミュレート） | 実際のネットワーク遅延 |
| **用途** | 開発・テスト | 本番環境 |
| **セキュリティ** | ❌ 低い | ✅ 高い |

---

## 📝 コード例

### Mock AD Connectorの使用

```python
from lambda.shared.ad_connector_mock import create_ad_connector

# Mock ADを使用
ad_connector = create_ad_connector(use_mock=True)

# 社員検証
from lambda.shared.models import EmployeeInfo

employee_info = EmployeeInfo(
    employee_id="123456",
    name="山田太郎",
    department="開発部"
)

result = ad_connector.verify_employee("123456", employee_info)

if result.success:
    print(f"✅ 認証成功: {result.employee_data}")
else:
    print(f"❌ 認証失敗: {result.error}")
```

### Real AD Connectorの使用

```python
from lambda.shared.ad_connector_mock import create_ad_connector

# Real ADを使用
ad_connector = create_ad_connector(
    use_mock=False,
    server_url="ldaps://ad.company.com:636",
    base_dn="DC=company,DC=com",
    timeout=10
)

# 社員検証（実際のADに接続）
result = ad_connector.verify_employee("123456", employee_info)
```

---

## ✅ チェックリスト

### Mock AD使用時

- [ ] `.env` ファイルで `USE_MOCK_AD=true` を設定
- [ ] CDKデプロイ完了
- [ ] Lambda関数のログで `[MOCK]` メッセージを確認
- [ ] 6桁の社員番号でテスト
- [ ] 社員登録フローが動作することを確認
- [ ] 緊急認証フローが動作することを確認

### Real AD切り替え時

- [ ] Direct Connect/VPN接続が確立されている
- [ ] `.env` ファイルで `USE_MOCK_AD=false` を設定
- [ ] `AD_SERVER_URL` と `AD_BASE_DN` を正しく設定
- [ ] CDK再デプロイ完了
- [ ] Lambda関数のログで `Using REAL AD Connector` を確認
- [ ] 実際の社員番号とパスワードでテスト
- [ ] AD接続が正常に動作することを確認

---

## 📚 関連ドキュメント

- `lambda/shared/ad_connector_mock.py` - Mock AD Connectorの実装
- `lambda/shared/ad_connector.py` - Real AD Connectorの実装
- `AD_CONNECTION_GUIDE.md` - AD接続設定ガイド
- `QUICK_START_TESTING_GUIDE.md` - テストガイド

---

## 🎯 まとめ

### Mock AD Connectorの利点

1. ✅ **AD接続不要** - Direct Connect/VPN設定なしでテスト可能
2. ✅ **簡単なテスト** - 6桁の社員番号だけで認証可能
3. ✅ **高速** - ネットワーク遅延なし
4. ✅ **開発効率向上** - すぐにシステムをテスト可能

### 使用上の注意

1. ⚠️ **開発・テスト専用** - 本番環境では使用しない
2. ⚠️ **セキュリティ** - 実際の認証は行われない
3. ⚠️ **データ** - モックデータのみ
4. ⚠️ **切り替え** - 本番前に必ずReal ADに切り替える

---

**作成日:** 2026年1月28日  
**バージョン:** 1.0

