# API Gateway WAF Verification Report

## 検証日時
2026年2月16日

## 検証概要
API Gateway に設定された AWS WAF の構成を確認し、IP制限が正しく設定されていることを検証しました。

---

## ✅ WAF 構成確認結果

### 1. Web ACL 基本情報

| 項目 | 値 |
|------|-----|
| **名前** | `FaceAuth-API-WebACL` |
| **ID** | `b6545517-aafc-4d6f-a6a5-07fa02b6779d` |
| **スコープ** | `REGIONAL` (ap-northeast-1) |
| **説明** | WAF Web ACL for Face-Auth API Gateway with IP whitelist and rate limiting |
| **デフォルトアクション** | **Block** (デフォルトで全てブロック) |
| **容量** | 3 WCU |

### 2. WAF ルール構成

#### ルール 1: AllowListedIPs (優先度: 1)
- **目的:** 許可されたIPアドレスからのアクセスを許可
- **アクション:** Allow
- **ステートメント:** IPSetReferenceStatement
- **IP Set ARN:** `arn:aws:wafv2:ap-northeast-1:979431736455:regional/ipset/FaceAuth-API-AllowedIPs/414f5a23-2529-430f-af83-2e084242ed16`
- **メトリクス:** 有効 (CloudWatch)
- **サンプリング:** 有効

#### ルール 2: RateLimitRule (優先度: 2)
- **目的:** レート制限（DDoS対策）
- **アクション:** Block
- **制限:** 1000リクエスト/5分/IP
- **集約キー:** IP アドレス
- **メトリクス:** 有効 (CloudWatch)
- **サンプリング:** 有効

### 3. IP Set 構成

| 項目 | 値 |
|------|-----|
| **名前** | `FaceAuth-API-AllowedIPs` |
| **ID** | `414f5a23-2529-430f-af83-2e084242ed16` |
| **説明** | Allowed IP addresses for Face-Auth API Gateway |
| **IPバージョン** | IPv4 |
| **許可されたIP範囲** | **210.128.54.64/27** |

**IP範囲の詳細:**
- **ネットワーク:** 210.128.54.64/27
- **開始IP:** 210.128.54.64
- **終了IP:** 210.128.54.95
- **利用可能IP数:** 32個 (ネットワークアドレスとブロードキャストアドレスを含む)
- **ホスト数:** 30個 (実際に使用可能なホストIP)

### 4. API Gateway との関連付け

| 項目 | 値 |
|------|-----|
| **API Gateway ID** | `ivgbc7glnl` |
| **API 名** | `FaceAuth-API` |
| **ステージ** | `prod` |
| **関連付けARN** | `arn:aws:apigateway:ap-northeast-1::/restapis/ivgbc7glnl/stages/prod` |
| **エンドポイント** | `https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/` |

---

## ✅ セキュリティ設定の確認

### IP制限の動作

1. **デフォルトアクション: Block**
   - すべてのリクエストはデフォルトでブロックされます

2. **許可ルール (優先度1)**
   - `210.128.54.64/27` からのリクエストのみ許可
   - このルールに一致した場合、リクエストは許可されます

3. **レート制限 (優先度2)**
   - 許可されたIPからでも、5分間に1000リクエストを超えるとブロック
   - DDoS攻撃や過度なリクエストを防止

### セキュリティレベル

✅ **高セキュリティ構成**
- デフォルトブロック + ホワイトリスト方式
- レート制限による追加保護
- CloudWatch メトリクスによる監視
- サンプリングによる詳細分析

---

## 📊 CloudWatch メトリクス

以下のメトリクスが有効化されています：

1. **FaceAuthAPIWebACL** - Web ACL全体のメトリクス
2. **AllowListedIPs** - 許可されたIPからのリクエスト数
3. **RateLimitRule** - レート制限によってブロックされたリクエスト数

### メトリクスの確認方法

```bash
# CloudWatch メトリクスの確認
aws cloudwatch get-metric-statistics \
  --namespace AWS/WAFV2 \
  --metric-name AllowedRequests \
  --dimensions Name=Rule,Value=AllowListedIPs Name=WebACL,Value=FaceAuth-API-WebACL Name=Region,Value=ap-northeast-1 \
  --start-time 2026-02-16T00:00:00Z \
  --end-time 2026-02-16T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --profile dev
```

---

## 🧪 テスト方法

### 1. 許可されたIPからのアクセステスト

```bash
# 210.128.54.64/27 の範囲内のIPからアクセス
curl -X GET https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status

# 期待される結果: 200 OK (または適切なレスポンス)
```

### 2. ブロックされるIPからのアクセステスト

```bash
# 許可されていないIPからアクセス
curl -X GET https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status

# 期待される結果: 403 Forbidden
# レスポンスボディ: {"message":"Forbidden"}
```

### 3. レート制限テスト

```bash
# 許可されたIPから大量のリクエストを送信
for i in {1..1100}; do
  curl -X GET https://ivgbc7glnl.execute-api.ap-northeast-1.amazonaws.com/prod/auth/status
done

# 期待される結果: 
# - 最初の1000リクエスト: 200 OK
# - 1001リクエスト目以降: 403 Forbidden (レート制限)
```

---

## 🔍 WAF ログの確認

### WAF ログの有効化 (オプション)

```bash
# S3バケットにWAFログを保存
aws wafv2 put-logging-configuration \
  --logging-configuration \
    ResourceArn=arn:aws:wafv2:ap-northeast-1:979431736455:regional/webacl/FaceAuth-API-WebACL/b6545517-aafc-4d6f-a6a5-07fa02b6779d,\
    LogDestinationConfigs=arn:aws:s3:::aws-waf-logs-face-auth-979431736455-ap-northeast-1 \
  --region ap-northeast-1 \
  --profile dev
```

### ログの確認

```bash
# CloudWatch Logs Insights でWAFログを確認
# ログストリーム: aws-waf-logs-face-auth
```

---

## 📋 設定変更方法

### IP範囲の追加

```bash
# 現在のIP Setを取得
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
  --lock-token <LOCK_TOKEN> \
  --profile dev
```

### CDKでの設定変更

`.env` ファイルを編集:

```bash
# 複数のIP範囲を追加
ALLOWED_IPS=210.128.54.64/27,192.168.1.0/24,10.0.0.0/16
```

再デプロイ:

```bash
npx cdk deploy --require-approval never --profile dev --context allowed_ips="210.128.54.64/27,192.168.1.0/24"
```

---

## ✅ 検証結果サマリー

| 項目 | 状態 | 詳細 |
|------|------|------|
| **WAF Web ACL作成** | ✅ 完了 | FaceAuth-API-WebACL |
| **IP Set作成** | ✅ 完了 | 210.128.54.64/27 |
| **API Gateway関連付け** | ✅ 完了 | prod ステージに関連付け済み |
| **デフォルトアクション** | ✅ Block | すべてブロック（ホワイトリスト方式） |
| **許可ルール** | ✅ 設定済み | 210.128.54.64/27 のみ許可 |
| **レート制限** | ✅ 設定済み | 1000 req/5min/IP |
| **CloudWatch メトリクス** | ✅ 有効 | 監視可能 |
| **サンプリング** | ✅ 有効 | 詳細分析可能 |

---

## 🎯 結論

API Gateway の WAF 設定は正しく構成されています：

1. ✅ **IP制限が有効**: `210.128.54.64/27` からのアクセスのみ許可
2. ✅ **デフォルトブロック**: 許可されていないIPは全てブロック
3. ✅ **レート制限**: DDoS対策として1000 req/5min/IP
4. ✅ **監視体制**: CloudWatch メトリクスで監視可能
5. ✅ **API Gateway関連付け**: prod ステージに正しく関連付け

**セキュリティレベル: 高**

---

## 📝 次のステップ

1. **実際のIPからアクセステスト**
   - 許可されたIP範囲 (210.128.54.64/27) からAPIにアクセス
   - 正常にレスポンスが返ることを確認

2. **ブロックテスト**
   - 許可されていないIPからアクセス
   - 403 Forbidden が返ることを確認

3. **CloudWatch メトリクスの確認**
   - WAF メトリクスを確認
   - ブロックされたリクエスト数を監視

4. **WAF ログの有効化 (オプション)**
   - 詳細なログ分析が必要な場合
   - S3バケットにログを保存

---

**検証完了日:** 2026年2月16日
**検証者:** Kiro AI Assistant
**ステータス:** ✅ 全ての設定が正しく構成されています
