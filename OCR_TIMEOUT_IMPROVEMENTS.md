# OCRタイムアウト改善レポート

## 実施日時
2026-01-29

## 実施した改善

### 1. Textract Queriesの変更 ✅
**変更前**:
```python
'社員番号は何ですか？'  # 「社員番号」というラベルを探す
'氏名は何ですか？'      # 「氏名」というラベルを探す
'所属は何ですか？'      # 「所属」というラベルを探す
```

**変更後**:
```python
'7桁の数字は何ですか？'  # 7桁の数字を直接探す
'名前は何ですか？'       # より一般的な表現
'部署は何ですか？'       # より一般的な表現
```

**理由**: サンプル画像に「社員番号」というラベルがない可能性が高いため、7桁の数字を直接探すように変更

### 2. Textractクライアントのタイムアウト設定 ✅
**追加した設定**:
```python
from botocore.config import Config

config = Config(
    read_timeout=20,  # 20秒でタイムアウト（30秒→20秒に短縮）
    connect_timeout=5,  # 接続タイムアウト5秒
    retries={'max_attempts': 1}  # リトライなし（高速失敗）
)

self.textract = boto3.client('textract', region_name=region_name, config=config)
```

**効果**: 
- Textract処理が20秒でタイムアウト
- Lambda関数の30秒タイムアウトより前に失敗を検出
- リトライなしで高速失敗

### 3. タイムアウト検出とエラーハンドリング ✅
**追加したコード**:
```python
import time
start_time = time.time()

try:
    response = self.textract.analyze_document(...)
    elapsed_time = time.time() - start_time
    logger.info(f"Textract completed in {elapsed_time:.2f} seconds")
    
except Exception as e:
    elapsed_time = time.time() - start_time
    logger.error(f"Textract failed after {elapsed_time:.2f} seconds: {str(e)}")
    
    if 'timeout' in str(e).lower() or 'timed out' in str(e).lower():
        return None, ErrorResponse(
            error_code=ErrorCodes.TIMEOUT_ERROR,
            user_message="処理時間が超過しました",
            system_reason=f"Textract timeout after {elapsed_time:.2f}s",
            ...
        )
    raise
```

**効果**:
- タイムアウトを明示的に検出
- 処理時間をログに記録
- ユーザーフレンドリーなエラーメッセージ

### 4. 早期失敗チェック ✅
**追加したバリデーション**:
```python
# 必須フィールドのチェック
required_fields = ['employee_id', 'employee_name']
missing_fields = [f for f in required_fields if f not in extracted_data or not extracted_data[f]]

if missing_fields:
    logger.warning(f"Missing required fields: {missing_fields}")
    return None, ErrorResponse(
        error_code=ErrorCodes.ID_CARD_FORMAT_MISMATCH,
        user_message="社員証規格不一致",
        system_reason=f"Missing required fields: {', '.join(missing_fields)}",
        ...
    )
```

**効果**:
- データが抽出できない場合、早期にエラーを返す
- 不要な処理を回避

## デプロイ状況

### 更新されたコンポーネント
1. ✅ `lambda/shared/ocr_service.py` - タイムアウト処理追加
2. ✅ `lambda/enrollment/shared/ocr_service.py` - コピー済み
3. ✅ `lambda/emergency_auth/shared/ocr_service.py` - コピー済み
4. ✅ `lambda/re_enrollment/shared/ocr_service.py` - コピー済み
5. ✅ DynamoDB CardTemplate - 更新済み

### デプロイ完了
```
FaceAuthIdPStack: UPDATE_COMPLETE
- EnrollmentFunction: UPDATE_COMPLETE
- EmergencyAuthFunction: UPDATE_COMPLETE
- ReEnrollmentFunction: UPDATE_COMPLETE
```

## 期待される動作

### 改善前
- Textract処理: 約29秒
- Lambda関数: 30秒でタイムアウト
- エラーメッセージ: なし（タイムアウトのみ）

### 改善後
- Textract処理: 最大20秒でタイムアウト
- Lambda関数: 20秒以内にエラーレスポンスを返す
- エラーメッセージ: 「処理時間が超過しました」または「社員証規格不一致」

## テスト結果

### 初回テスト（改善後）
- Lambda呼び出し: 31.08秒
- 結果: タイムアウト（レスポンスなし）

**分析**:
- まだ30秒でタイムアウトしている
- Textractの20秒タイムアウトが機能していない可能性
- または、画像に何らかのデータがあり、処理に時間がかかっている

## 次のステップ

### 1. CloudWatch Logsの詳細確認
```bash
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev --region ap-northeast-1
```

確認項目:
- Textractの実行時間
- タイムアウトエラーが発生しているか
- 抽出されたデータの内容

### 2. サンプル画像の確認（最優先）
画像を開いて、以下を確認:
- [ ] 7桁の数字が含まれているか
- [ ] 名前（日本語）が含まれているか
- [ ] テキストが読み取り可能な品質か

### 3. 代替テスト画像の作成
現在の画像で動作しない場合、新しいテスト画像を作成:
```
┌─────────────────────────┐
│  テスト社員証            │
│                         │
│  1234567                │
│  山田太郎               │
│  開発部                 │
└─────────────────────────┘
```

### 4. Textractタイムアウトの検証
より短いタイムアウト（10秒）でテスト:
```python
config = Config(
    read_timeout=10,  # 10秒に短縮
    connect_timeout=5,
    retries={'max_attempts': 1}
)
```

## まとめ

### 実施した改善
1. ✅ Textract Queriesを7桁数字ベースに変更
2. ✅ Textractクライアントに20秒タイムアウトを設定
3. ✅ タイムアウト検出とエラーハンドリングを追加
4. ✅ 早期失敗チェックを追加
5. ✅ Lambda関数をデプロイ

### 現状
- Lambda関数は更新済み
- CardTemplateは更新済み
- テストでは依然として30秒でタイムアウト

### 推奨アクション
1. **最優先**: サンプル画像の内容を確認
2. CloudWatch Logsで詳細なエラーを確認
3. 必要に応じて新しいテスト画像を作成
4. タイムアウト設定をさらに短縮（10秒）

---
**作成日**: 2026-01-29
**ステータス**: 改善実施済み、テスト継続中
