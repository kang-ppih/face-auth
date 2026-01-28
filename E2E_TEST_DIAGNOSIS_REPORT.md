# エンドツーエンドテスト診断レポート

## 実行日時
2026-01-28

## テスト概要
画面から社員登録してS3に格納されるまでの全体フローを確認するエンドツーエンドテストを実行しました。

## 実行したテスト
- **テストスクリプト**: `scripts/test_end_to_end_enrollment.py`
- **テスト対象**: 社員登録API (`/auth/enroll`)
- **使用画像**: `sample/社員証サンプル.png` (414KB)

## 修正した問題

### 1. OCRServiceメソッド名の誤り ✅ 修正完了
**問題**: Lambda関数が`extract_employee_info`メソッドを呼び出していたが、実際のメソッド名は`extract_id_card_info`
**影響**: AttributeError発生、500エラー
**修正内容**:
- `lambda/enrollment/handler.py`
- `lambda/emergency_auth/handler.py`
- `lambda/re_enrollment/handler.py`
- `scripts/test_ocr_with_sample.py`

### 2. OCRServiceのDynamoDB初期化不足 ✅ 修正完了
**問題**: OCRServiceが内部でDynamoDBServiceを使用するが、テーブル名が初期化されていなかった
**影響**: `'NoneType' object has no attribute 'scan'`エラー
**修正内容**:
- 各Lambda関数で`ocr_service.initialize_db_service()`を呼び出すように修正
- `lambda/enrollment/handler.py`
- `lambda/emergency_auth/handler.py`
- `lambda/re_enrollment/handler.py`

### 3. CardTemplateの未登録 ✅ 修正完了
**問題**: DynamoDBにCardTemplateが登録されていなかった
**影響**: 「社員証規格不一致」エラー
**修正内容**:
- `scripts/register_card_template.py`を修正（Decimal型対応）
- CardTemplate `STANDARD_EMPLOYEE_CARD_V1`を登録
- Textract Queries設定:
  - employee_id: "社員番号は何ですか？"
  - employee_name: "氏名は何ですか？"
  - department: "所属は何ですか？"

## 現在の問題

### Lambda関数タイムアウト ⚠️ 部分的に解決
**現象**: Lambda関数が30秒でタイムアウト（15秒→30秒に延長済み）
**原因**: Textract OCR処理に約29秒かかっている
**ログ**:
```
Duration: 30000.00 ms   Billed Duration: 30401 ms
Status: timeout
```

**根本原因の可能性**:
1. **サンプル画像に実際の社員証情報が含まれていない** ← 最も可能性が高い
   - Textractが情報を見つけられず、タイムアウトまで処理を続けている
   - Textract Queriesが適切に設定されていても、画像に該当する情報がない
2. 画像サイズが大きい（414KB、base64で552KB）
3. Textract Queriesの設定が不適切
4. API Gatewayのタイムアウト（29秒）がLambdaタイムアウト（30秒）より短い

**API Gateway 504エラー**:
- API Gatewayの最大タイムアウトは29秒
- Lambda関数が30秒に設定されているため、API Gatewayが先にタイムアウト
- Lambda関数は29秒以内に完了する必要がある

## 推奨される次のステップ

### 1. サンプル画像の確認 🔴 最優先
**問題**: `sample/社員証サンプル.png`に実際の社員証情報が含まれているか不明
**対応**:
- 画像を開いて、以下の情報が読み取り可能か確認:
  - 社員番号（7桁の数字）
  - 氏名（日本語）
  - 所属/部署
- 情報が含まれていない場合、実際の社員証画像（テスト用）を用意
- または、モックデータで簡単なテスト画像を作成

### 2. Textract Queriesのテスト
`scripts/test_ocr_with_sample.py`を実行して、Textractが正しく情報を抽出できるか確認:
```bash
$env:AWS_PROFILE='dev'
python scripts/test_ocr_with_sample.py
```

このテストで以下を確認:
- Textractが画像から何を抽出しているか
- Queriesが適切に機能しているか
- タイムアウトが発生するか

### 3. Lambda関数タイムアウトの調整 ✅ 完了
~~現在15秒のタイムアウトを30秒に延長することを検討~~
**完了**: 30秒に延長済み

**注意**: API Gatewayの最大タイムアウトは29秒のため、Lambda関数は29秒以内に完了する必要があります。

### 4. 画像サイズの最適化
エンドツーエンドテストで使用する画像を最適化:
- 解像度を下げる（例: 800x600以下）
- JPEG形式に変換（PNG → JPEG）
- 品質を調整（80-90%）
- 目標サイズ: 200KB以下

### 5. 顔画像サンプルの追加
現在、顔画像サンプルが存在しないため、社員証画像を代用しています。
実際の顔写真サンプル（`sample/face_sample.jpg`）を追加することを推奨します。

### 6. 代替アプローチ: モックデータでのテスト
サンプル画像の問題を回避するため、以下のアプローチを検討:
- OCR処理をスキップして、ハードコードされた社員情報でテスト
- 環境変数で`SKIP_OCR=true`を設定し、テストモードで実行
- 顔認識とS3保存のみをテスト

## テスト結果サマリー

### 最新テスト結果（タイムアウト30秒）

| ステップ | 状態 | 詳細 |
|---------|------|------|
| 1. 画像準備 | ✅ PASS | 画像ロード成功 |
| 2. API リクエスト | ❌ FAIL | 504 エラー（API Gateway タイムアウト） |
| 3. S3 確認 | ❌ FAIL | 画像未保存 |
| 4. DynamoDB 確認 | ❌ FAIL | レコード未作成 |
| 5. Rekognition 確認 | ❌ FAIL | 顔未登録 |

**総合結果**: 1/5 ステップ成功

**Lambda実行時間**: 30秒（タイムアウト）
**API Gateway**: 29秒でタイムアウト（504エラー）

### 以前のテスト結果（タイムアウト15秒）

| ステップ | 状態 | 詳細 |
|---------|------|------|
| 1. 画像準備 | ✅ PASS | 画像ロード成功 |
| 2. API リクエスト | ❌ FAIL | 502 エラー（Lambda タイムアウト） |
| 3. S3 確認 | ❌ FAIL | 画像未保存 |
| 4. DynamoDB 確認 | ❌ FAIL | レコード未作成 |
| 5. Rekognition 確認 | ❌ FAIL | 顔未登録 |

**総合結果**: 1/5 ステップ成功

**Lambda実行時間**: 15秒（タイムアウト）

## 関連ファイル

### 修正済みファイル
- `lambda/enrollment/handler.py` - OCRメソッド名修正、DynamoDB初期化追加
- `lambda/emergency_auth/handler.py` - OCRメソッド名修正、DynamoDB初期化追加
- `lambda/re_enrollment/handler.py` - OCRメソッド名修正、DynamoDB初期化追加
- `scripts/register_card_template.py` - Decimal型対応、CardTemplate登録
- `scripts/test_ocr_with_sample.py` - OCRメソッド名修正
- `infrastructure/face_auth_stack.py` - Lambda タイムアウト 15秒→30秒に延長

### テストスクリプト
- `scripts/test_end_to_end_enrollment.py` - エンドツーエンドテスト
- `scripts/test_ocr_with_sample.py` - OCR単体テスト
- `scripts/register_card_template.py` - CardTemplate登録

### ドキュメント
- `CARD_TEMPLATE_SETUP_GUIDE.md` - CardTemplate設定ガイド
- `LAMBDA_IMPORT_ERROR_DIAGNOSIS.md` - Lambda依存関係問題の診断

## 次回セッションでの作業

1. **サンプル画像の検証**
   - 実際の社員証情報が含まれているか確認
   - OCR単体テストで抽出結果を確認

2. **Lambda タイムアウト延長**
   - CDKスタックでタイムアウトを30秒に延長
   - 再デプロイして動作確認

3. **エンドツーエンドテスト再実行**
   - 修正後、完全なフローが動作するか確認
   - S3、DynamoDB、Rekognitionへのデータ保存を確認

4. **フロントエンドとの統合テスト**
   - 実際のReactアプリから登録フローをテスト
   - ブラウザでの動作確認

---

**作成日**: 2026-01-28
**ステータス**: 調査中
