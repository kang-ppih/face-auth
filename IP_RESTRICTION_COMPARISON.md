# IP制限メカニズム比較 - Face-Auth IdP System

**作成日:** 2026-02-04  
**更新日:** 2026-02-05  
**目的:** 現在実装されている3つのIP制限メカニズムの比較と推奨事項  
**実装状態:** ✅ オプション1（WAFのみ）実装完了

---

## 📊 実装状況

Face-Auth IdPシステムは**AWS WAFのみを使用したIP制限**に簡素化されました。

### ✅ 実装済み: AWS WAF（WAFレベル）

**適用対象:** API Gateway + CloudFront  
**設定場所:** `_create_waf()` メソッド  
**機能:**
- ✅ IP制限（IP Set使用）
- ✅ レート制限（1000 req/5min/IP）
- ✅ CloudWatchメトリクス
- ✅ WAFログ対応
- ✅ CloudFront対応

### ❌ 削除済み: Network ACL（IP制限部分）

**変更内容:**
- IP制限ルールを削除
- 基本的なネットワーク制御のみ維持（HTTPS/HTTP許可）
- WAFがIP制限を担当

### ❌ 削除済み: API Gateway Resource Policy

**変更内容:**
- `_create_api_resource_policy()` メソッドを完全削除
- API Gateway作成時の `policy` パラメータを削除
- WAFがIP制限を担当

---

## 🎯 実装されたアーキテクチャ（オプション1）

```
ユーザー
  │
  ▼
┌─────────────────────────────────┐
│ AWS WAF (唯一のIP制限層)         │
│  - IP Set: 許可IPリスト         │
│  - Rule 1: IP許可ルール          │
│  - Rule 2: レート制限            │
│  - Default Action: Block         │
└──────────────┬──────────────────┘
               │
       ┌───────┴───────┐
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│ CloudFront  │ │ API Gateway │
│ (Frontend)  │ │ (Backend)   │
└─────────────┘ └─────────────┘
```

---

## ✅ 実装の利点

### 1. 一元管理
- IP制限をWAFで一元管理
- 1箇所でIP更新が完了
- 管理の複雑さを大幅に削減

### 2. 柔軟性
- CloudFrontとAPI Gatewayの両方をカバー
- レート制限機能あり
- CloudWatchメトリクスとログが充実

### 3. 保守性
- トラブルシューティングが簡単
- 設定変更が容易
- ドキュメントが明確

### 4. コスト
- $14.60/月（許容範囲）
- 追加の複雑さなし

---

## 📝 実装詳細

### 環境変数

```bash
# .env
# WAF IP制限設定（カンマ区切りのCIDR形式）
# この環境変数はWAFでのみ使用されます
ALLOWED_IPS=203.0.113.10/32,198.51.100.0/24

# または開発環境では空にする（すべてのIPを許可）
# ALLOWED_IPS=
```

### デプロイ方法

```bash
# IP制限なし（開発モード）
cdk deploy

# 特定のIPアドレスのみ許可
cdk deploy --context allowed_ips="203.0.113.10/32"

# 複数のIPアドレス/範囲を許可
cdk deploy --context allowed_ips="203.0.113.10/32,198.51.100.0/24"
```

---

## 🔄 以前の構成との比較

| 項目 | 以前（多層防御） | 現在（WAFのみ） |
|------|----------------|----------------|
| **IP制限層** | 3層（NACL + API GW + WAF） | 1層（WAF） |
| **管理箇所** | 3箇所 | 1箇所 |
| **IP更新** | 3箇所で更新必要 | 1箇所で完了 |
| **CloudFront対応** | ✅ あり | ✅ あり |
| **レート制限** | ✅ あり | ✅ あり |
| **メトリクス** | ✅ 充実 | ✅ 充実 |
| **コスト** | $14.60/月 | $14.60/月 |
| **管理の容易さ** | ❌ 難 | ✅ 易 |
| **トラブルシューティング** | ❌ 複雑 | ✅ 簡単 |

---

## 📚 関連ドキュメント

- [WAF IP Restriction Guide](WAF_IP_RESTRICTION_GUIDE.md) - WAF設定の詳細ガイド
- [IP Access Control](docs/IP_ACCESS_CONTROL.md) - IPアクセス制御の概要
- [Infrastructure Architecture](docs/INFRASTRUCTURE_ARCHITECTURE.md) - インフラストラクチャ全体のアーキテクチャ

---

## 🎉 実装完了

**実装日:** 2026-02-05  
**実装者:** Face-Auth Development Team  
**バージョン:** 2.0（WAF専用版）

### 変更内容

1. ✅ `_create_network_acls()` メソッドを簡素化（IP制限削除）
2. ✅ `_create_api_resource_policy()` メソッドを完全削除
3. ✅ API Gateway作成時の `policy` パラメータを削除
4. ✅ WAFのみでIP制限を実装
5. ✅ ドキュメント更新

### 次のステップ

1. `cdk diff` でデプロイ前の差分確認
2. `cdk deploy` で本番環境にデプロイ
3. WAF設定の動作確認
4. IP制限のテスト実施

---

**最終更新:** 2026-02-05  
**作成者:** Face-Auth Development Team  
**ステータス:** ✅ 実装完了
