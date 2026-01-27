# IP制限変更サマリー

## 変更日時
**日付:** 2024年

---

## 変更内容

### 変更前
```
許可IPレンジ: 0.0.0.0/0 (全IPアドレス許可)
```

### 変更後
```
許可IPレンジ: 210.128.54.64/27
```

---

## 影響範囲

### ✅ 許可されるアクセス

**IPレンジ:** `210.128.54.64/27`

**含まれるIPアドレス:** 210.128.54.64 〜 210.128.54.95 (32個のIPアドレス)

このIPレンジからのみ、以下のエンドポイントにアクセス可能：

- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/enrollment`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/face-login`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/emergency`
- `https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/re-enrollment`

### ❌ 拒否されるアクセス

上記のIPレンジ以外からのアクセスは **403 Forbidden** エラーになります。

**エラーレスポンス例:**
```json
{
  "message": "User is not authorized to access this resource"
}
```

---

## デプロイ詳細

### デプロイコマンド
```bash
$env:ALLOWED_IPS="210.128.54.64/27"; npx cdk deploy --profile dev --require-approval never
```

### デプロイ時間
約48秒

### 変更されたリソース

1. **AWS::ApiGateway::RestApi** - リソースポリシー追加
   - Allow: 210.128.54.64/27 からのアクセスを許可
   - Deny: それ以外からのアクセスを拒否

2. **AWS::ApiGateway::Deployment** - 新しいデプロイメント作成

3. **AWS::ApiGateway::Stage** - ステージ更新

### CloudFormation出力
```
AllowedIPRanges = 210.128.54.64/27
```

---

## セキュリティ向上

### 変更前のリスク
- ✅ 全世界からアクセス可能
- ❌ 不正アクセスのリスク大
- ❌ DDoS攻撃のリスク
- ❌ ブルートフォース攻撃のリスク

### 変更後のセキュリティ
- ✅ 特定のIPレンジのみアクセス可能
- ✅ 不正アクセスのリスク低減
- ✅ DDoS攻撃のリスク低減
- ✅ ブルートフォース攻撃のリスク低減
- ✅ API Keyと組み合わせた多層防御

---

## 動作確認

### 許可されたIPからのアクセス（成功）

```bash
# 210.128.54.64/27 レンジ内のIPから実行
curl -X GET https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
```

**期待される結果:**
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

### 許可されていないIPからのアクセス（失敗）

```bash
# 210.128.54.64/27 レンジ外のIPから実行
curl -X GET https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
```

**期待される結果:**
```json
{
  "message": "User is not authorized to access this resource"
}
```

**HTTPステータスコード:** 403 Forbidden

---

## 追加のIPレンジを許可する方法

### 手順

1. `.env` ファイルを編集
```bash
# 複数のIPレンジをカンマ区切りで指定
ALLOWED_IPS=210.128.54.64/27,203.0.113.0/24,198.51.100.0/24
```

2. デプロイ実行
```bash
$env:ALLOWED_IPS="210.128.54.64/27,203.0.113.0/24"; npx cdk deploy --profile dev
```

詳細は `IP_RESTRICTION_UPDATE.md` を参照してください。

---

## ロールバック方法

### 全IPアドレスを許可する場合（開発環境のみ）

```bash
# 環境変数を空に設定
$env:ALLOWED_IPS=""; npx cdk deploy --profile dev
```

または

```bash
# 明示的に0.0.0.0/0を設定
$env:ALLOWED_IPS="0.0.0.0/0"; npx cdk deploy --profile dev
```

**⚠️ 注意:** 本番環境では推奨しません

---

## 更新されたドキュメント

以下のドキュメントが更新されました：

1. ✅ `.env.sample` - ALLOWED_IPS のデフォルト値を更新
2. ✅ `DEPLOYED_RESOURCES.md` - 現在のIP制限を反映
3. ✅ `POST_DEPLOYMENT_GUIDE.md` - IP制限の設定方法を更新
4. ✅ `IP_RESTRICTION_UPDATE.md` - IP制限の詳細ガイド（新規作成）
5. ✅ `IP_RESTRICTION_CHANGE_SUMMARY.md` - 変更サマリー（このファイル）

---

## 次のステップ

### 即座に実行

1. ✅ 動作確認
   - 許可されたIPレンジからAPIにアクセスできることを確認
   - 許可されていないIPレンジからアクセスが拒否されることを確認

2. ✅ ドキュメント確認
   - `IP_RESTRICTION_UPDATE.md` を読んで、IP制限の管理方法を理解

### 今後の作業

3. ⏳ 追加のIPレンジが必要な場合
   - VPNネットワーク
   - 他のオフィスネットワーク
   - パートナー企業のネットワーク

4. ⏳ 本番環境への適用
   - 本番環境用のIPレンジを設定
   - 本番環境にデプロイ

---

## トラブルシューティング

### 問題: 403 Forbiddenエラーが発生する

**解決策:**

1. 現在のIPアドレスを確認
```bash
curl https://api.ipify.org
```

2. そのIPアドレスが許可リストに含まれているか確認
```bash
aws cloudformation describe-stacks \
  --stack-name FaceAuthIdPStack \
  --region ap-northeast-1 \
  --profile dev \
  --query "Stacks[0].Outputs[?OutputKey=='AllowedIPRanges'].OutputValue" \
  --output text
```

3. 必要に応じてIPレンジを追加

詳細は `IP_RESTRICTION_UPDATE.md` のトラブルシューティングセクションを参照してください。

---

## 参考情報

### API Gateway エンドポイント
```
https://zao7evz9jk.execute-api.ap-northeast-1.amazonaws.com/prod/
```

### 現在の設定
```
許可IPレンジ: 210.128.54.64/27
IPアドレス範囲: 210.128.54.64 〜 210.128.54.95
IPアドレス数: 32個
```

### CloudFormation スタック
```
スタック名: FaceAuthIdPStack
リージョン: ap-northeast-1
ARN: arn:aws:cloudformation:ap-northeast-1:979431736455:stack/FaceAuthIdPStack/91ad3310-fba8-11f0-bdc9-0e43e32a811b
```

---

**作成日:** 2024年
**変更者:** Kiro AI Assistant
**承認者:** （承認が必要な場合は記入）

