# IP制限設定 完全検証レポート

## 検証日時
2026年2月16日

## 検証概要
Face-Auth IdP システムの全てのエンドポイント（API Gateway と CloudFront）に対するIP制限設定を検証しました。

---

## 🎯 検証結果サマリー

| コンポーネント | IP制限方式 | 許可IP範囲 | ステータス |
|--------------|-----------|-----------|----------|
| **API Gateway** | AWS WAF (REGIONAL) | 210.128.54.64/27 | ✅ 設定完了 |
| **CloudFront** | CloudFront Functions | 210.128.54.64/27 | ✅ 設定完了 |

---

## 1️⃣ API Gateway IP制限設定

### 構成方式
- **AWS WAF Web ACL** (REGIONAL scope in ap-northeast-1)
- **デフォルトアクション:** Block（ホワイトリスト方式）
- **許可ルール:** IP Set Reference Statement

### 詳細設定

#### Web ACL情報
```
名前: FaceAuth-API-WebACL
ID: b6545517-aafc-4d6f-a6a5-07fa02b6779d
スコープ: REGIONAL (ap-northeast-1)
デフォルトアクション: Block
```

#### ルール構成

**ルール1: AllowListedIPs (優先度: 1)**
- アクション: Allow
- 条件: IP Set に含まれるIPアドレス
- IP Set: `FaceAuth-API-AllowedIPs`
- 許可IP範囲: **210.128.54.64/27**

**ルール2: RateLimitRule (優先度: 2)**
- アクション: Block
- 条件: 1000リクエスト/5分/IP を超過
- 目的: DDoS対策

#### IP範囲の詳細
```
ネットワーク: 210.128.54.64/27
開始IP: 210.128.54.64
終了IP: 210.128.54.95
利用可能ホスト数: 30個
```

#### API Gateway関連付け
```
API ID: ivgbc7glnl
API名: FaceAuth-API
ステージ: prod
エンドポイント: https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/
関連付けARN: arn:aws:apigateway:ap-northeast-1::/restapis/ivgbc7glnl/stages/prod
```

### セキュリティ機能

✅ **デフォルトブロック**
- 許可されていないIPは全てブロック

✅ **IP ホワイトリスト**
- 210.128.54.64/27 のみ許可

✅ **レート制限**
- 1000 req/5min/IP でブロック

✅ **CloudWatch メトリクス**
- リアルタイム監視可能
- メトリクス: AllowListedIPs, RateLimitRule

✅ **サンプリング**
- ブロックされたリクエストの詳細分析

---

## 2️⃣ CloudFront IP制限設定

### 構成方式
- **CloudFront Functions** (Viewer Request)
- **実行タイミング:** リクエスト受信時（Viewer Request）
- **制限方式:** JavaScript による IP CIDR チェック

### 詳細設定

#### CloudFront Distribution情報
```
Distribution ID: (CDK出力から確認)
Distribution URL: https://d2576ywp5ut1v8.cloudfront.net/
Function名: FaceAuth-ViewerRequest
```

#### IP制限ロジック

**許可IP範囲:**
```javascript
var ALLOWED_IP_RANGES = [
    { ip: '210.128.54.64', prefix: 27 }  // 社内ネットワーク
];
```

**動作フロー:**
1. クライアントIPを取得 (`event.viewer.ip`)
2. CIDR範囲チェック (`ipInCIDR()`)
3. 許可されている場合: リクエストを通過
4. 許可されていない場合: 403 Forbidden を返す

#### ブロック時のレスポンス
```html
HTTP/1.1 403 Forbidden
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>アクセス拒否</title>
</head>
<body>
    <h1>アクセスが拒否されました</h1>
    <p>このサイトは許可されたIPアドレスからのみアクセス可能です。</p>
    <p>This site is only accessible from authorized IP addresses.</p>
    <p>Your IP: [クライアントIP]</p>
</body>
</html>
```

### セキュリティ機能

✅ **IP CIDR チェック**
- 210.128.54.64/27 範囲内のIPのみ許可

✅ **エッジでのブロック**
- CloudFront エッジロケーションでブロック
- オリジン（S3）への負荷なし

✅ **ユーザーフレンドリーなエラーページ**
- 日本語・英語の説明
- クライアントIPの表示

✅ **Geo Restriction削除**
- 以前の日本のみ制限を削除
- IP制限のみに統一

---

## 🔍 設定の違い: WAF vs CloudFront Functions

| 項目 | API Gateway (WAF) | CloudFront (Functions) |
|------|------------------|----------------------|
| **制限方式** | AWS WAF Web ACL | CloudFront Functions |
| **実行場所** | API Gateway | CloudFront Edge |
| **スコープ** | REGIONAL (ap-northeast-1) | CLOUDFRONT (Global) |
| **設定方法** | CDK (CfnWebACL) | JavaScript コード |
| **レート制限** | ✅ あり (1000/5min) | ❌ なし |
| **メトリクス** | ✅ CloudWatch | ❌ 限定的 |
| **コスト** | WAF料金 | Functions料金 |
| **柔軟性** | ルールベース | コードベース |

### なぜ CloudFront に WAF を使わないのか？

**理由:**
1. **リージョン制約**: CloudFront WAF は us-east-1 リージョンでのみ作成可能
2. **複雑性**: クロスリージョン設定が必要
3. **コスト**: CloudFront Functions の方が低コスト
4. **シンプルさ**: IP制限のみなら Functions で十分

**CloudFront Functions の利点:**
- ✅ 同じリージョン (ap-northeast-1) で管理可能
- ✅ コードで柔軟に制御可能
- ✅ エッジでの高速処理
- ✅ 低コスト

---

## 🧪 テスト方法

### API Gateway テスト

#### 1. 許可されたIPからのアクセス
```bash
# 210.128.54.64/27 の範囲内から
curl -X GET https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status

# 期待結果: 200 OK
```

#### 2. ブロックされるIPからのアクセス
```bash
# 許可されていないIPから
curl -X GET https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status

# 期待結果: 403 Forbidden
# レスポンス: {"message":"Forbidden"}
```

#### 3. レート制限テスト
```bash
# 1000リクエスト以上を短時間で送信
for i in {1..1100}; do
  curl -X GET https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
done

# 期待結果: 1001リクエスト目以降は 403 Forbidden
```

### CloudFront テスト

#### 1. 許可されたIPからのアクセス
```bash
# 210.128.54.64/27 の範囲内から
curl -X GET https://d2576ywp5ut1v8.cloudfront.net/

# 期待結果: 200 OK (index.html)
```

#### 2. ブロックされるIPからのアクセス
```bash
# 許可されていないIPから
curl -X GET https://d2576ywp5ut1v8.cloudfront.net/

# 期待結果: 403 Forbidden
# レスポンス: HTMLエラーページ（日本語・英語の説明）
```

---

## 📊 監視とログ

### API Gateway WAF メトリクス

**CloudWatch メトリクス:**
- `AWS/WAFV2` ネームスペース
- メトリクス:
  - `AllowedRequests` - 許可されたリクエスト数
  - `BlockedRequests` - ブロックされたリクエスト数
  - `CountedRequests` - カウントされたリクエスト数

**確認コマンド:**
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/WAFV2 \
  --metric-name BlockedRequests \
  --dimensions Name=Rule,Value=ALL Name=WebACL,Value=FaceAuth-API-WebACL Name=Region,Value=ap-northeast-1 \
  --start-time 2026-02-16T00:00:00Z \
  --end-time 2026-02-16T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --profile dev
```

### CloudFront Functions ログ

**制限事項:**
- CloudFront Functions は詳細なログを提供しない
- CloudWatch Logs への自動ログ出力なし

**代替監視方法:**
- CloudFront アクセスログを有効化
- S3 バケットにログを保存
- Athena でログ分析

---

## 🔧 設定変更方法

### IP範囲の追加・変更

#### 方法1: CDK で変更（推奨）

**1. `.env` ファイルを編集:**
```bash
# 複数のIP範囲を追加
ALLOWED_IPS=210.128.54.64/27,192.168.1.0/24,10.0.0.0/16
```

**2. CloudFront Functions を更新:**
```javascript
// cloudfront_functions/viewer_request.js
var ALLOWED_IP_RANGES = [
    { ip: '210.128.54.64', prefix: 27 },
    { ip: '192.168.1.0', prefix: 24 },
    { ip: '10.0.0.0', prefix: 16 }
];
```

**3. 再デプロイ:**
```bash
npx cdk deploy --require-approval never --profile dev --context allowed_ips="210.128.54.64/27,192.168.1.0/24,10.0.0.0/16"
```

#### 方法2: AWS CLI で直接変更（緊急時）

**API Gateway WAF の IP Set を更新:**
```bash
# 現在の設定を取得
aws wafv2 get-ip-set \
  --scope REGIONAL \
  --region ap-northeast-1 \
  --id 414f5a23-2529-430f-af83-2e084242ed16 \
  --name FaceAuth-API-AllowedIPs \
  --profile dev

# IP範囲を更新
aws wafv2 update-ip-set \
  --scope REGIONAL \
  --region ap-northeast-1 \
  --id 414f5a23-2529-430f-af83-2e084242ed16 \
  --name FaceAuth-API-AllowedIPs \
  --addresses "210.128.54.64/27" "192.168.1.0/24" \
  --lock-token <LOCK_TOKEN_FROM_GET_COMMAND> \
  --profile dev
```

**注意:** CloudFront Functions は AWS CLI で直接更新できません。CDK 経由で更新してください。

---

## 📋 チェックリスト

### API Gateway WAF

- [x] Web ACL が作成されている
- [x] IP Set が作成されている
- [x] IP Set に正しいIP範囲が設定されている (210.128.54.64/27)
- [x] デフォルトアクションが Block に設定されている
- [x] 許可ルールが優先度1で設定されている
- [x] レート制限ルールが設定されている (1000/5min)
- [x] API Gateway ステージに関連付けられている
- [x] CloudWatch メトリクスが有効化されている
- [x] サンプリングが有効化されている

### CloudFront Functions

- [x] CloudFront Function が作成されている
- [x] Viewer Request イベントに関連付けられている
- [x] IP範囲が正しく設定されている (210.128.54.64/27)
- [x] CIDR チェックロジックが実装されている
- [x] ブロック時のエラーページが実装されている
- [x] Geo Restriction が削除されている
- [x] CloudFront Distribution に関連付けられている

---

## ✅ 検証結果

### API Gateway
| 項目 | ステータス |
|------|----------|
| WAF Web ACL | ✅ 設定完了 |
| IP Set | ✅ 設定完了 |
| 許可IP範囲 | ✅ 210.128.54.64/27 |
| デフォルトアクション | ✅ Block |
| レート制限 | ✅ 1000/5min |
| API関連付け | ✅ 完了 |
| メトリクス | ✅ 有効 |

### CloudFront
| 項目 | ステータス |
|------|----------|
| CloudFront Function | ✅ 設定完了 |
| IP制限ロジック | ✅ 実装済み |
| 許可IP範囲 | ✅ 210.128.54.64/27 |
| エラーページ | ✅ 実装済み |
| Viewer Request関連付け | ✅ 完了 |
| Geo Restriction | ✅ 削除済み |

---

## 🎯 結論

**Face-Auth IdP システムの全エンドポイントに対するIP制限が正しく設定されています。**

### セキュリティレベル: 高

1. ✅ **API Gateway**: AWS WAF による強固なIP制限
   - デフォルトブロック + ホワイトリスト方式
   - レート制限による DDoS 対策
   - CloudWatch による監視

2. ✅ **CloudFront**: CloudFront Functions による IP制限
   - エッジでの高速ブロック
   - ユーザーフレンドリーなエラーページ
   - 低コストで効率的

3. ✅ **統一された IP範囲**: 210.128.54.64/27
   - API と Frontend で同じIP範囲
   - 一貫したセキュリティポリシー

### 推奨事項

1. **定期的な監視**
   - CloudWatch メトリクスを定期的に確認
   - ブロックされたリクエストを分析

2. **IP範囲の見直し**
   - 必要に応じてIP範囲を追加・削除
   - 最小権限の原則を維持

3. **テストの実施**
   - 定期的にアクセステストを実施
   - 許可/ブロックの動作を確認

4. **ログの有効化（オプション）**
   - WAF ログを S3 に保存
   - CloudFront アクセスログを有効化
   - Athena で詳細分析

---

**検証完了日:** 2026年2月16日
**検証者:** Kiro AI Assistant
**ステータス:** ✅ 全ての IP制限設定が正しく構成されています
