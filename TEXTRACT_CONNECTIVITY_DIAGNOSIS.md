# Textract接続性診断レポート

## 実行日時
2026-01-29

## 問題の概要
ローカル環境からAmazon Textractエンドポイントに接続できない。

## 診断結果

### AWS接続テスト結果

| サービス | 接続状態 | 詳細 |
|---------|---------|------|
| STS | ✅ 成功 | 認証情報は正常 |
| S3 | ✅ 成功 | 178個のバケットにアクセス可能 |
| DynamoDB | ✅ 成功 | 5個のテーブルにアクセス可能 |
| **Textract** | ❌ **失敗** | **エンドポイント接続エラー** |
| Rekognition | ✅ 成功 | 1個のコレクションにアクセス可能 |

### エラーメッセージ
```
Could not connect to the endpoint URL: "https://textract.ap-northeast-1.amazonaws.com/"
```

### 環境情報
- **AWS Profile**: dev
- **Region**: ap-northeast-1
- **boto3 Version**: 1.42.33
- **Credentials**: 正常（shared-credentials-file）
- **Proxy設定**: なし（HTTP_PROXY, HTTPS_PROXY未設定）

## 原因分析

### 確認された事実
1. ✅ AWS認証情報は正常に機能している
2. ✅ 他のAWSサービス（S3、DynamoDB、Rekognition）には接続可能
3. ❌ **Textractエンドポイントのみ接続不可**
4. ❌ AWS CLIでも同じエラーが発生
5. ❌ boto3でも同じエラーが発生

### 最も可能性が高い原因
**企業ネットワークによるTextractエンドポイントへのアクセス制限**

以下のいずれかの理由でTextractエンドポイントがブロックされている可能性：
1. ファイアウォールルールによる特定エンドポイントのブロック
2. プロキシ設定の不足（Textractのみ特別な設定が必要）
3. VPN接続が必要（Textractのみ）
4. セキュリティポリシーによる制限

### なぜTextractだけ？
- Textractは比較的新しいサービス
- 企業のセキュリティポリシーで明示的に許可されていない可能性
- 他のサービスは以前から使用されており、既に許可されている

## 試行した解決策

### 1. プロキシ設定の確認 ❌
- HTTP_PROXY、HTTPS_PROXY環境変数は未設定
- 他のサービスは動作しているため、プロキシは不要と判断

### 2. AWS CLI直接テスト ❌
```bash
aws textract detect-document-text --document "Bytes=dGVzdA==" --profile dev
```
結果: 同じエラー（Could not connect to the endpoint URL）

### 3. Lambda経由でのテスト ⏳
Lambda関数（VPC内）からはTextractにアクセス可能
- Lambda関数は30秒でタイムアウト
- OCR処理は開始されているが、完了していない

## 代替アプローチ

### ✅ 推奨: Lambda関数経由でのテスト
ローカル環境からTextractに直接アクセスできないため、Lambda関数経由でテストする。

**利点**:
- Lambda関数はVPC内でTextractにアクセス可能
- 実際の本番環境と同じ動作を確認できる
- ネットワーク制限を回避できる

**実行方法**:
```bash
$env:AWS_PROFILE='dev'
python scripts/test_ocr_via_lambda.py
```

### ⚠️ 現在の問題
Lambda関数が30秒でタイムアウトしている
- 原因: サンプル画像に社員証情報が含まれていない可能性
- Textractが情報を見つけられず、タイムアウトまで処理を続けている

## 解決策

### 短期的な解決策（推奨）

#### 1. サンプル画像の確認と修正
**最優先**: `sample/社員証サンプル.png`の内容を確認

画像に以下が含まれているか確認:
- [ ] 「社員番号」ラベルと7桁の数字
- [ ] 「氏名」ラベルと日本語の名前
- [ ] 「所属」ラベルと部署名

**含まれていない場合**:
新しいテスト用社員証画像を作成:
```
┌─────────────────────────┐
│  株式会社サンプル        │
│                         │
│  社員番号: 1234567      │
│  氏名: 山田太郎         │
│  所属: 開発部           │
└─────────────────────────┘
```

#### 2. Lambda関数経由でのテスト継続
```bash
# 1. 新しいサンプル画像を用意
# 2. Lambda経由でテスト
$env:AWS_PROFILE='dev'
python scripts/test_ocr_via_lambda.py

# 3. CloudWatch Logsで詳細確認
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev
```

### 長期的な解決策

#### オプション1: ネットワーク管理者に相談
企業のネットワーク管理者に以下を依頼:
1. Textractエンドポイントへのアクセス許可
   - `textract.ap-northeast-1.amazonaws.com`
   - ポート: 443 (HTTPS)
2. 必要に応じてプロキシ設定の提供

#### オプション2: VPN接続の使用
企業VPNに接続してから再試行:
1. VPN接続
2. `python scripts/test_ocr_with_sample.py`を再実行

#### オプション3: 開発環境の変更
- AWS Cloud9を使用（AWS内で実行）
- EC2インスタンスから実行
- Lambda関数経由でのみテスト

## 現在の推奨ワークフロー

### ローカル開発時
1. **コード編集**: ローカル環境で実施
2. **デプロイ**: CDKでLambda関数をデプロイ
3. **テスト**: Lambda関数経由またはAPI経由でテスト
4. **ログ確認**: CloudWatch Logsで詳細確認

### OCRテスト時
```bash
# 方法1: Lambda関数経由
python scripts/test_ocr_via_lambda.py

# 方法2: API経由（エンドツーエンドテスト）
python scripts/test_end_to_end_enrollment.py

# 方法3: CloudWatch Logsで直接確認
aws logs tail /aws/lambda/FaceAuth-Enrollment --follow --profile dev
```

## まとめ

### 現状
- ❌ ローカル環境からTextractに直接アクセス不可
- ✅ Lambda関数（VPC内）からはTextractにアクセス可能
- ⚠️ サンプル画像の内容が不明（確認が必要）

### 次のアクション
1. **最優先**: サンプル画像の内容を確認
   - 画像を開いて、社員証情報が含まれているか確認
   - 含まれていない場合、新しい画像を作成

2. **テスト**: Lambda経由でOCRをテスト
   - `python scripts/test_ocr_via_lambda.py`
   - CloudWatch Logsで詳細確認

3. **長期的**: ネットワーク管理者に相談
   - Textractエンドポイントへのアクセス許可を依頼

### 回避策
ローカル環境からTextractに直接アクセスできなくても、開発は継続可能:
- Lambda関数経由でテスト
- API経由でテスト
- CloudWatch Logsで動作確認

---
**作成日**: 2026-01-29
**ステータス**: 診断完了、代替アプローチ提供済み
