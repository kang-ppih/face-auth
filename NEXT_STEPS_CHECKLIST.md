# Face-Auth IdP System - 次のステップチェックリスト

## ✅ デプロイ完了

- [x] AWS CDKスタックデプロイ完了
- [x] 91個のリソース作成完了
- [x] API Gateway エンドポイント作成
- [x] Lambda関数デプロイ
- [x] DynamoDBテーブル作成
- [x] S3バケット作成
- [x] Cognito User Pool作成
- [x] VPC・セキュリティグループ作成

---

## 🚀 即座に実行すべきタスク

### 1. Rekognitionコレクション作成 ⚠️ 必須

**ステータス:** ⏳ 未完了

**コマンド:**
```bash
aws rekognition create-collection \
  --collection-id face-auth-employees \
  --region ap-northeast-1 \
  --profile dev
```

**確認:**
```bash
aws rekognition describe-collection \
  --collection-id face-auth-employees \
  --region ap-northeast-1 \
  --profile dev
```

**期待される出力:**
```json
{
    "FaceCount": 0,
    "FaceModelVersion": "7.0",
    "CollectionARN": "arn:aws:rekognition:ap-northeast-1:979431736455:collection/face-auth-employees"
}
```

---

### 2. DynamoDBカードテンプレート初期化 ⚠️ 必須

**ステータス:** ⏳ 未完了

**コマンド:**
```bash
# 仮想環境がアクティブでない場合
venv\Scripts\activate

# スクリプト実行
python scripts/init_dynamodb.py
```

**確認:**
```bash
aws dynamodb scan \
  --table-name FaceAuth-CardTemplates \
  --region ap-northeast-1 \
  --profile dev \
  --query "Items[*].template_id.S"
```

**期待される出力:**
```json
[
    "standard_card_v1",
    "premium_card_v1",
    "contractor_card_v1"
]
```

---

### 3. API動作確認 ⚠️ 必須

**ステータス:** ⏳ 未完了

**コマンド:**
```bash
curl -X GET https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
```

**期待される出力:**
```json
{
  "status": "healthy",
  "timestamp": "2024-XX-XXTXX:XX:XX.XXXXXXZ",
  "version": "1.0.0",
  "services": {
    "dynamodb": "available",
    "s3": "available",
    "rekognition": "available",
    "cognito": "available"
  }
}
```

---

### 4. API Key取得 🔑 推奨

**ステータス:** ⏳ 未完了

**コマンド:**
```bash
aws apigateway get-api-key \
  --api-key s3jyk9dhm1 \
  --include-value \
  --region ap-northeast-1 \
  --profile dev
```

**保管場所:** 安全な場所に保管（パスワードマネージャー推奨）

---

## 🧪 テスト実行

### 5. テストユーザーで登録テスト 📝 推奨

**ステータス:** ⏳ 未完了

**前提条件:**
- テスト用社員証画像（JPG/PNG）
- テスト用顔写真（JPG/PNG）

**手順:**
1. 画像をBase64エンコード
2. Enrollmentエンドポイントにリクエスト
3. レスポンス確認
4. DynamoDBに登録されたか確認
5. Rekognitionに顔が登録されたか確認

**詳細:** `POST_DEPLOYMENT_GUIDE.md` の「テストシナリオ1」参照

---

### 6. 顔認証ログインテスト 📝 推奨

**ステータス:** ⏳ 未完了

**前提条件:**
- タスク5で登録したユーザー
- 同じユーザーの顔写真

**手順:**
1. 顔写真をBase64エンコード
2. Face Loginエンドポイントにリクエスト
3. セッショントークン取得確認
4. Cognitoトークン検証

**詳細:** `POST_DEPLOYMENT_GUIDE.md` の「テストシナリオ2」参照

---

## 🔒 セキュリティ強化（本番環境移行前）

### 7. IP制限設定 ⚠️ 本番環境必須

**ステータス:** ⏳ 未完了

**現在の設定:** `0.0.0.0/0`（全IPアドレス許可）

**変更手順:**
1. `infrastructure/face_auth_stack.py` を編集
2. `allowed_ips` を特定IPレンジに変更
3. `npx cdk deploy --profile dev` で再デプロイ

**例:**
```python
allowed_ips = [
    "203.0.113.0/24",  # オフィスネットワーク
    "198.51.100.0/24"  # VPNネットワーク
]
```

---

### 8. CORS設定更新 ⚠️ 本番環境必須

**ステータス:** ⏳ 未完了

**現在の設定:** `*`（全オリジン許可）

**変更手順:**
1. `infrastructure/face_auth_stack.py` を編集
2. `allow_origins` を特定ドメインに変更
3. `npx cdk deploy --profile dev` で再デプロイ

**例:**
```python
allow_origins=[
    "https://your-frontend-domain.com",
    "https://admin.your-domain.com"
]
```

---

### 9. CloudWatch アラーム設定 📊 推奨

**ステータス:** ⏳ 未完了

**設定すべきアラーム:**
- Lambda エラー率 > 5%
- API Gateway 5xxエラー > 10件/5分
- DynamoDB スロットリング
- Rekognition エラー率

**詳細:** `POST_DEPLOYMENT_GUIDE.md` の「CloudWatch アラーム設定」参照

---

### 10. バックアップ設定 💾 推奨

**ステータス:** ⏳ 未完了

**設定すべき項目:**
- DynamoDB ポイントインタイムリカバリ（3テーブル）
- S3 バージョニング有効化
- S3 ライフサイクルポリシー設定

**詳細:** `POST_DEPLOYMENT_GUIDE.md` の「バックアップ設定」参照

---

## 🔄 オプション設定

### 11. Direct Connect設定 🌐 オプション

**ステータス:** ⏳ 未完了

**用途:** オンプレミスActive Directory接続

**前提条件:**
- Direct Connect物理接続確立済み
- ネットワークチームとの調整完了

**詳細:** `POST_DEPLOYMENT_GUIDE.md` の「Direct Connect設定」参照

---

### 12. カスタムドメイン設定 🌍 オプション

**ステータス:** ⏳ 未完了

**現在のURL:**
```
https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/
```

**カスタムドメイン例:**
```
https://api.face-auth.your-company.com/
```

**必要な作業:**
1. Route 53でドメイン管理
2. ACM証明書取得
3. API Gatewayカスタムドメイン設定
4. DNS レコード追加

---

### 13. WAF設定 🛡️ オプション（本番環境推奨）

**ステータス:** ⏳ 未完了

**保護対象:**
- API Gateway エンドポイント

**推奨ルール:**
- レート制限（100リクエスト/5分/IP）
- SQLインジェクション保護
- XSS保護
- 地理的制限（必要に応じて）

---

## 📊 モニタリング設定

### 14. CloudWatch ダッシュボード作成 📈 推奨

**ステータス:** ⏳ 未完了

**表示すべきメトリクス:**
- Lambda実行回数・エラー率
- API Gatewayリクエスト数・レイテンシ
- DynamoDB読み書き容量
- Rekognition API呼び出し数
- Cognito アクティブユーザー数

---

### 15. ログ保持期間設定 📝 推奨

**ステータス:** ⏳ 未完了

**現在の設定:** 7日間

**本番環境推奨:** 30日〜90日

**変更方法:**
```bash
aws logs put-retention-policy \
  --log-group-name /aws/lambda/FaceAuth-Enrollment \
  --retention-in-days 30 \
  --region ap-northeast-1 \
  --profile dev
```

---

## 📚 ドキュメント更新

### 16. 運用マニュアル作成 📖 推奨

**ステータス:** ⏳ 未完了

**含めるべき内容:**
- 日常運用手順
- トラブルシューティング
- エスカレーション手順
- 緊急連絡先

---

### 17. API仕様書作成 📄 推奨

**ステータス:** ⏳ 未完了

**フォーマット:** OpenAPI 3.0 / Swagger

**含めるべき内容:**
- 全エンドポイント仕様
- リクエスト/レスポンス例
- エラーコード一覧
- 認証方法

---

## 🎯 優先度別まとめ

### 🔴 最優先（即座に実行）

1. ✅ Rekognitionコレクション作成
2. ✅ DynamoDBテーブル初期化
3. ✅ API動作確認
4. ✅ API Key取得

### 🟡 高優先（1週間以内）

5. ⏳ テストユーザー登録・ログインテスト
6. ⏳ CloudWatch アラーム設定
7. ⏳ バックアップ設定
8. ⏳ ログ保持期間設定

### 🟢 中優先（本番環境移行前）

9. ⏳ IP制限設定
10. ⏳ CORS設定更新
11. ⏳ CloudWatch ダッシュボード作成
12. ⏳ 運用マニュアル作成

### 🔵 低優先（必要に応じて）

13. ⏳ Direct Connect設定
14. ⏳ カスタムドメイン設定
15. ⏳ WAF設定
16. ⏳ API仕様書作成

---

## 📞 参考ドキュメント

- **デプロイ済みリソース一覧:** `DEPLOYED_RESOURCES.md`
- **デプロイ後セットアップガイド:** `POST_DEPLOYMENT_GUIDE.md`
- **最終テスト結果:** `FINAL_TEST_SUMMARY.md`
- **デプロイガイド:** `DEPLOYMENT_GUIDE.md`
- **README:** `README.md`

---

## ✅ 進捗トラッキング

**完了タスク:** 0 / 17
**進捗率:** 0%

**最終更新:** 2024年

---

**次のアクション:**
1. このチェックリストを印刷またはブックマーク
2. タスク1〜4を順番に実行
3. 各タスク完了後、チェックボックスにチェック
4. 問題が発生した場合は `POST_DEPLOYMENT_GUIDE.md` のトラブルシューティングを参照

**頑張ってください！ 🚀**

