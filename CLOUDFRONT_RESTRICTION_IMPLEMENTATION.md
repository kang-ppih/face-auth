# CloudFront アクセス制限実装完了レポート

**作成日:** 2026-02-06  
**実装方式:** Geo Restriction + Lambda@Edge  
**ステータス:** ✅ 実装完了（デプロイ待ち）

---

## 実装内容

### 採用した方式

**パターンA: Geo Restriction + Lambda@Edge**

すべてのリソースを`ap-northeast-1`リージョンで管理可能な方式を採用。

---

## アーキテクチャ

```
┌─────────────────────────────────────────┐
│  ユーザー                                │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  CloudFront Geo Restriction             │
│  ✅ 日本のみ許可                        │
│  ❌ 日本国外は完全ブロック              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Lambda@Edge (Viewer Request)           │
│  ✅ 特定IP許可 (210.128.54.64/27)       │
│  ✅ 日本国内でも特定IPのみアクセス可能  │
│  Region: ap-northeast-1で作成           │
│  (自動的にエッジロケーションに複製)     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  CloudFront Distribution                │
│  ↓                                      │
│  S3 Static Files (Frontend)             │
└─────────────────────────────────────────┘
```

---

## 実装詳細

### 1. Lambda@Edge関数

**ファイル:** `lambda_edge/viewer_request.py`

**機能:**
- CloudFront-Viewer-Countryヘッダーで国を確認
- 日本（JP）からのアクセスを許可
- 特定IPアドレス（`210.128.54.64/27`）からのアクセスを許可
- それ以外は403 Forbiddenを返す

**許可IPアドレス:**
```python
ALLOWED_IP_RANGES = [
    "210.128.54.64/27",  # 社内ネットワーク
]
```

**エラーレスポンス:**
- ステータス: 403 Forbidden
- 日本語と英語の両方でメッセージ表示
- HTMLフォーマットで見やすく表示

---

### 2. CloudFront Geo Restriction

**設定:**
```python
geo_restriction=cloudfront.GeoRestriction.allowlist("JP")
```

**動作:**
- 日本（JP）からのアクセスのみ許可
- 日本国外からのアクセスは即座にブロック（Lambda@Edgeに到達する前）

---

### 3. CDK実装

**変更ファイル:** `infrastructure/face_auth_stack.py`

**追加内容:**
1. Lambda@Edge関数の作成
2. Lambda@EdgeバージョンをCloudFrontに関連付け
3. Geo Restrictionの追加
4. 環境変数でALLOWED_IP_RANGESを渡す

**条件分岐:**
- `allowed_ips="0.0.0.0/0"`の場合、Lambda@Edgeは作成されない（開発モード）
- Geo Restrictionは常に有効（日本のみ）

---

## アクセス制御フロー

### ケース1: 日本国内 + 許可IP

```
[ユーザー: 日本, IP: 210.128.54.65]
    ↓
[Geo Restriction] ✅ 日本 → 通過
    ↓
[Lambda@Edge] ✅ 210.128.54.64/27に含まれる → 通過
    ↓
[CloudFront] → [S3] → ✅ アクセス成功
```

---

### ケース2: 日本国内 + 許可外IP

```
[ユーザー: 日本, IP: 192.168.1.1]
    ↓
[Geo Restriction] ✅ 日本 → 通過
    ↓
[Lambda@Edge] ❌ 許可IPリストにない → ブロック
    ↓
❌ 403 Forbidden
```

---

### ケース3: 日本国外

```
[ユーザー: アメリカ, IP: 任意]
    ↓
[Geo Restriction] ❌ 日本以外 → ブロック
    ↓
❌ 403 Forbidden (Lambda@Edgeに到達しない)
```

---

## デプロイ手順

### ステップ1: 差分確認

```bash
cdk diff --context allowed_ips="210.128.54.64/27" --profile dev
```

**期待される変更:**
- Lambda@Edge関数の作成
- CloudFront Distributionの更新（Lambda@Edge関連付け + Geo Restriction）

---

### ステップ2: デプロイ

```bash
cdk deploy --context allowed_ips="210.128.54.64/27" --profile dev
```

**注意:**
- CloudFront Distributionの更新には10-15分かかります
- Lambda@Edgeは自動的にエッジロケーションに複製されます

---

### ステップ3: 動作確認

#### 3-1. 日本国内 + 許可IPからのアクセス

```bash
# 許可されたIPから
curl https://d2576ywp5ut1v8.cloudfront.net/

# 期待結果: 200 OK (index.htmlが返される)
```

#### 3-2. 日本国内 + 許可外IPからのアクセス

```bash
# VPNなどで日本国内の別IPから
curl https://d2576ywp5ut1v8.cloudfront.net/

# 期待結果: 403 Forbidden
# {
#   "status": "403",
#   "statusDescription": "Forbidden",
#   "body": "アクセスが拒否されました..."
# }
```

#### 3-3. 日本国外からのアクセス

```bash
# VPNでアメリカなどから
curl https://d2576ywp5ut1v8.cloudfront.net/

# 期待結果: 403 Forbidden (Geo Restrictionによるブロック)
```

---

## コスト

### Lambda@Edge

| 項目 | 料金 | 説明 |
|------|------|------|
| リクエスト | $0.60/100万リクエスト | Lambda実行料金 |
| Lambda@Edge追加料金 | $0.50/100万リクエスト | エッジロケーション実行 |
| **合計** | **$1.10/100万リクエスト** | |

**月間100万リクエストの場合:** 約$1.10/月

### Geo Restriction

**無料**（CloudFrontの標準機能）

### 合計コスト

**月間100万リクエスト:** 約$1.10/月

**比較:**
- CloudFront WAF: 約$8.60/月
- Lambda@Edge: 約$1.10/月
- **コスト削減: 約$7.50/月（約87%削減）**

---

## メリット

### 1. すべて`ap-northeast-1`で管理

✅ Lambda@Edgeは`ap-northeast-1`で作成
✅ CDKが自動的にエッジロケーションに複製
✅ 単一スタックで完結
✅ リージョン間の複雑な管理不要

### 2. 強力なアクセス制御

✅ 二重の保護（Geo Restriction + Lambda@Edge）
✅ 日本国外からのアクセスを完全ブロック
✅ 日本国内でも特定IPのみ許可

### 3. 柔軟性

✅ Lambda関数でカスタムロジック実装可能
✅ IPアドレスリストの動的更新が可能
✅ 複雑な条件分岐も実装可能

### 4. コスト効率

✅ WAFより約87%安い
✅ 月額約$1.10で強力な保護

---

## デメリットと対策

### デメリット1: Lambda実行コスト

すべてのリクエストでLambda関数が実行される。

**対策:**
- Geo Restrictionで日本国外を事前にブロック（Lambda実行前）
- Lambda関数は軽量（5秒タイムアウト、128MBメモリ）

### デメリット2: デバッグの複雑さ

Lambda@Edgeのログは各エッジロケーションに分散。

**対策:**
- CloudWatch Logsで集約
- `print()`でログ出力（CloudWatch Logsに記録）

---

## モニタリング

### CloudWatch Logs

Lambda@Edgeのログは自動的にCloudWatch Logsに記録されます。

**ログ確認:**
```bash
# 最新のログを確認
aws logs tail /aws/lambda/us-east-1.ViewerRequestFunction --follow

# 特定のログを検索
aws logs filter-log-events \
  --log-group-name /aws/lambda/us-east-1.ViewerRequestFunction \
  --filter-pattern "Access denied"
```

### CloudWatch Metrics

**カスタムメトリクス:**
- AllowedRequests: 許可されたリクエスト数
- BlockedRequests: ブロックされたリクエスト数
- JapanRequests: 日本からのリクエスト数
- WhitelistedIPRequests: 許可IPからのリクエスト数

---

## トラブルシューティング

### 問題1: 許可されたIPからアクセスできない

**確認事項:**
1. Lambda@Edge関数のALLOWED_IP_RANGESが正しいか
2. CIDR表記が正しいか（例: `/32`は単一IP、`/27`は32個のIP）
3. CloudFront Distributionが更新されているか

**確認コマンド:**
```bash
# 自分のIPアドレス確認
curl https://checkip.amazonaws.com

# Lambda@Edge関数の環境変数確認
aws lambda get-function-configuration \
  --function-name ViewerRequestFunction \
  --query 'Environment.Variables.ALLOWED_IP_RANGES'
```

### 問題2: 日本国内からアクセスできない

**原因:**
- Geo Restrictionが正しく設定されていない可能性

**確認:**
```bash
# CloudFront Distribution設定確認
aws cloudfront get-distribution \
  --id EE7F2PTRFZ6WV \
  --query 'Distribution.DistributionConfig.Restrictions.GeoRestriction'
```

**期待結果:**
```json
{
  "RestrictionType": "whitelist",
  "Quantity": 1,
  "Items": ["JP"]
}
```

---

## IP許可リストの更新

### 方法1: 環境変数更新 + 再デプロイ

```bash
# Lambda@Edge関数の環境変数を更新
# infrastructure/face_auth_stack.pyのALLOWED_IP_RANGESを更新

# 再デプロイ
cdk deploy --context allowed_ips="210.128.54.64/27,203.0.113.0/24" --profile dev
```

### 方法2: Lambda関数コード更新

```python
# lambda_edge/viewer_request.py
ALLOWED_IP_RANGES = [
    "210.128.54.64/27",
    "203.0.113.0/24",  # 新しいIP範囲を追加
]
```

```bash
# 再デプロイ
cdk deploy --profile dev
```

---

## セキュリティベストプラクティス

### 1. 最小権限の原則

✅ 必要最小限のIPアドレス範囲のみを許可
✅ 定期的にIPリストをレビュー

### 2. ログとモニタリング

✅ CloudWatch Logsでアクセスログを確認
✅ ブロックされたリクエストを定期的に監視
✅ 異常なアクセスパターンを検出

### 3. 定期的な更新

✅ 不要になったIPアドレスは削除
✅ 新しいIPアドレスは必要に応じて追加

---

## 参考資料

- [AWS Lambda@Edge Documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-edge.html)
- [CloudFront Geo Restriction](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/georestrictions.html)
- [CLOUDFRONT_ACCESS_RESTRICTION_OPTIONS.md](CLOUDFRONT_ACCESS_RESTRICTION_OPTIONS.md)

---

**最終更新:** 2026-02-06  
**作成者:** Face-Auth Development Team  
**ステータス:** ✅ 実装完了（デプロイ待ち）
