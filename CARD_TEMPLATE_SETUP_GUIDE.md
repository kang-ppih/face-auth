# 社員証テンプレート設定ガイド

## 概要

このガイドでは、`sample/社員証サンプル.png`に基づいて社員証テンプレートを設定し、OCR処理を最適化する方法を説明します。

---

## 前提条件

- AWS認証情報が設定されていること
- DynamoDBテーブル `FaceAuth-CardTemplates` が作成されていること
- Python 3.9以上がインストールされていること
- 必要なPythonパッケージがインストールされていること

```bash
pip install boto3 Pillow
```

---

## ステップ1: 社員証レイアウトの分析

サンプル社員証画像を分析して、テキストの位置と社員番号の座標を取得します。

```bash
python scripts/analyze_card_layout.py sample/社員証サンプル.png
```

### 出力内容

このスクリプトは以下の情報を提供します：

1. **画像サイズ**: ピクセル単位の幅と高さ
2. **検出されたテキストブロック**: すべてのテキストとその位置
3. **社員番号候補**: 7桁の数字として認識されたテキスト
4. **推奨される bounding box**: CardTemplateに使用する座標

### 出力例

```
📐 Image Dimensions: 800x600 pixels

🔢 Employee Number Candidates (1 found):

Text: '1234567'
Confidence: 99.50%
Normalized BBox: {
  "Left": 0.15,
  "Top": 0.30,
  "Width": 0.35,
  "Height": 0.10
}

✅ Recommended employee_number_bbox for CardTemplate:
   {
       "Left": 0.15,
       "Top": 0.30,
       "Width": 0.35,
       "Height": 0.10
   }
```

### 分析結果の保存

分析結果は `card_layout_analysis.json` に保存されます。

---

## ステップ2: CardTemplateの更新

分析結果に基づいて、`scripts/register_card_template.py` の bounding box 座標を更新します。

### 編集箇所

```python
# scripts/register_card_template.py

# Employee number bounding box (分析結果から取得した座標を使用)
employee_number_bbox={
    "left": 0.15,    # 分析結果の Left 値
    "top": 0.30,     # 分析結果の Top 値
    "width": 0.35,   # 分析結果の Width 値
    "height": 0.10   # 分析結果の Height 値
},
```

### 座標の意味

- **left**: 画像左端からの距離（0.0 = 左端、1.0 = 右端）
- **top**: 画像上端からの距離（0.0 = 上端、1.0 = 下端）
- **width**: ボックスの幅（画像幅に対する比率）
- **height**: ボックスの高さ（画像高さに対する比率）

---

## ステップ3: CardTemplateの登録

更新したテンプレートをDynamoDBに登録します。

```bash
# 環境変数を設定
export AWS_REGION=ap-northeast-1
export CARD_TEMPLATES_TABLE=FaceAuth-CardTemplates

# テンプレートを登録
python scripts/register_card_template.py --register
```

### 成功時の出力

```
✅ Card template registered successfully!

Template Details:
  Pattern ID: STANDARD_EMPLOYEE_CARD_V1
  Description: 標準社員証フォーマット（sample/社員証サンプル.png準拠）
  Version: 1.0
  Active: True

Textract Queries:
  - 社員番号 (alias: EMPLOYEE_ID)
  - 氏名 (alias: EMPLOYEE_NAME)
  - 所属 (alias: DEPARTMENT)

Employee Number BBox:
  Left: 0.15
  Top: 0.30
  Width: 0.35
  Height: 0.10
```

### 登録済みテンプレートの確認

```bash
python scripts/register_card_template.py --list
```

---

## ステップ4: OCRテスト

サンプル社員証でOCR処理をテストします。

```bash
python scripts/test_ocr_with_sample.py
```

### 成功時の出力

```
✅ OCR extraction successful!

EXTRACTED EMPLOYEE INFORMATION
================================================================================

社員番号 (Employee ID): 1234567
氏名 (Name): 山田太郎
所属 (Department): 開発部

Validating extracted information...
✅ Employee information is valid
   - Employee ID format: 7 digits ✓
   - Name present: ✓

TEST SUMMARY
================================================================================

✅ OCR test PASSED

The CardTemplate is correctly configured for this ID card format.
You can now use this template for employee enrollment.
```

### エラーが発生した場合

#### 1. 社員番号が抽出できない

**原因:**
- bounding box の座標が正しくない
- 画像の品質が低い
- 社員番号のフォーマットが異なる

**解決策:**
```bash
# 再度レイアウトを分析
python scripts/analyze_card_layout.py sample/社員証サンプル.png

# 座標を確認して register_card_template.py を更新
# 再登録
python scripts/register_card_template.py --register

# 再テスト
python scripts/test_ocr_with_sample.py
```

#### 2. テンプレートが見つからない

**原因:**
- CardTemplateがDynamoDBに登録されていない
- テーブル名が間違っている

**解決策:**
```bash
# テーブル名を確認
aws dynamodb list-tables --profile dev

# テンプレートを登録
python scripts/register_card_template.py --register
```

#### 3. Textractエラー

**原因:**
- AWS認証情報が設定されていない
- Textractの権限がない

**解決策:**
```bash
# AWS認証情報を確認
aws sts get-caller-identity --profile dev

# IAMポリシーを確認（Textract権限が必要）
```

---

## CardTemplateの仕様

### データ構造

```python
{
    "pattern_id": "STANDARD_EMPLOYEE_CARD_V1",
    "description": "標準社員証フォーマット（sample/社員証サンプル.png準拠）",
    
    # Textract Queries: 抽出するフィールド
    "textract_queries": [
        {
            "text": "社員番号",      # 検索するテキスト
            "alias": "EMPLOYEE_ID",  # フィールドの別名
            "pages": ["1"]           # ページ番号
        },
        {
            "text": "氏名",
            "alias": "EMPLOYEE_NAME",
            "pages": ["1"]
        },
        {
            "text": "所属",
            "alias": "DEPARTMENT",
            "pages": ["1"]
        }
    ],
    
    # Employee Number Bounding Box: 社員番号の位置
    "employee_number_bbox": {
        "left": 0.15,    # 正規化座標（0.0-1.0）
        "top": 0.30,
        "width": 0.35,
        "height": 0.10
    },
    
    # Logo Bounding Box: ロゴの位置（オプション）
    "logo_bbox": {
        "left": 0.05,
        "top": 0.05,
        "width": 0.20,
        "height": 0.15
    },
    
    # Confidence Threshold: マッチング信頼度閾値
    "confidence_threshold": 0.85,
    
    # Active Status: このテンプレートを使用するか
    "is_active": true,
    
    # Metadata
    "created_at": "2026-01-28T12:00:00",
    "updated_at": "2026-01-28T12:00:00",
    "version": "1.0"
}
```

---

## OCRサービスの動作

### 処理フロー

1. **テンプレート取得**: DynamoDBから有効なCardTemplateを取得
2. **Textract実行**: 画像からテキストを抽出
3. **テンプレートマッチング**: 抽出されたテキストがテンプレートと一致するか確認
4. **フィールド抽出**: Textract Queriesに基づいて情報を抽出
5. **検証**: 社員番号フォーマット（7桁）を検証

### テンプレートマッチングの条件

以下の条件をすべて満たす場合、テンプレートがマッチします：

1. ✅ Textract Queriesで指定されたフィールドが見つかる
2. ✅ 社員番号が7桁の数字である
3. ✅ 氏名フィールドが存在する
4. ✅ 信頼度が閾値（85%）以上

---

## 複数の社員証フォーマットへの対応

異なるフォーマットの社員証を使用する場合：

### 1. 新しいテンプレートを作成

```python
# scripts/register_card_template.py に追加

card_template_v2 = CardTemplate(
    pattern_id="STANDARD_EMPLOYEE_CARD_V2",
    description="新フォーマット社員証",
    textract_queries=[...],
    employee_number_bbox={...},
    # ...
)
```

### 2. 両方のテンプレートを登録

```bash
# V1を登録
python scripts/register_card_template.py --register

# V2を登録（スクリプトを修正後）
python scripts/register_card_template.py --register
```

### 3. OCRサービスが自動選択

OCRサービスは、画像に最も適したテンプレートを自動的に選択します。

---

## トラブルシューティング

### 問題: 社員番号が正しく抽出されない

**チェック項目:**
1. bounding box の座標が正しいか
2. 画像の解像度が十分か（推奨: 800x600以上）
3. 社員番号が7桁の数字か
4. 画像が鮮明か（ぼやけていないか）

**デバッグ方法:**
```bash
# レイアウト分析で座標を確認
python scripts/analyze_card_layout.py sample/社員証サンプル.png

# 検出されたすべてのテキストを確認
# card_layout_analysis.json を開いて text_blocks を確認
```

### 問題: テンプレートがマッチしない

**チェック項目:**
1. テンプレートが `is_active: true` になっているか
2. Textract Queriesのテキストが正しいか
3. 信頼度閾値が適切か

**デバッグ方法:**
```bash
# 登録済みテンプレートを確認
python scripts/register_card_template.py --list

# DynamoDBで直接確認
aws dynamodb scan --table-name FaceAuth-CardTemplates --profile dev
```

### 問題: Textractがエラーを返す

**チェック項目:**
1. AWS認証情報が設定されているか
2. Textractの権限があるか
3. 画像サイズが制限内か（最大10MB）
4. 画像フォーマットがサポートされているか（PNG, JPEG）

**解決方法:**
```bash
# 認証情報を確認
aws sts get-caller-identity --profile dev

# 画像サイズを確認
ls -lh sample/社員証サンプル.png

# 画像を圧縮（必要な場合）
python -c "from PIL import Image; img = Image.open('sample/社員証サンプル.png'); img.save('sample/compressed.png', optimize=True, quality=85)"
```

---

## ベストプラクティス

### 1. 高品質な画像を使用

- **解像度**: 最低800x600ピクセル
- **フォーマット**: PNG または JPEG
- **ファイルサイズ**: 10MB以下
- **明るさ**: 十分な照明で撮影
- **鮮明さ**: ぼやけていない画像

### 2. 正確な座標設定

- `analyze_card_layout.py` で取得した座標を使用
- 余裕を持たせた bounding box（テキストの周囲に少し余白）
- 複数のサンプル画像でテスト

### 3. テンプレートのバージョン管理

- 変更時は新しい `pattern_id` を使用
- 古いテンプレートは `is_active: false` に設定
- `version` フィールドで管理

### 4. 定期的なテスト

```bash
# 定期的にOCRテストを実行
python scripts/test_ocr_with_sample.py

# 新しい社員証フォーマットが追加されたら再テスト
```

---

## まとめ

このガイドに従って、以下の作業を完了しました：

1. ✅ 社員証レイアウトの分析
2. ✅ CardTemplateの作成と登録
3. ✅ OCR処理のテスト
4. ✅ 社員番号位置の最適化

これで、`sample/社員証サンプル.png`と同じフォーマットの社員証のみが認識され、正確にOCR処理されるようになりました。

---

**作成日:** 2026年1月28日  
**ステータス:** ✅ 完了
