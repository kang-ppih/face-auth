# Rekognition Liveness API 移行 - 要求仕様

**Feature:** Rekognition Liveness APIへの移行  
**Priority:** High  
**Status:** Draft  
**Created:** 2026-01-30

---

## 概要

現在の簡易的なliveness検証（DetectFaces API）から、AWS Rekognition Liveness APIへ移行し、写真・動画を使ったなりすまし攻撃を防ぐ高度なセキュリティを実現する。

---

## 背景

### 現在の問題点

1. **セキュリティの脆弱性**
   - DetectFaces APIは静止画の品質チェックのみ
   - 写真や動画を使ったなりすまし攻撃に対して脆弱
   - 実際の生体検証ができない

2. **検証の限界**
   - 信頼度、明るさ、シャープネスのチェックのみ
   - 顔の動きや反応を検証できない
   - アンチスプーフィング機能なし

3. **コンプライアンスリスク**
   - 金融・医療などの厳格なセキュリティ要件に対応できない
   - 本人確認の信頼性が低い

### 移行の必要性

- **セキュリティ強化**: なりすまし攻撃の防止
- **信頼性向上**: 実際の生体検証
- **コンプライアンス対応**: 業界標準への準拠
- **ユーザー体験**: より確実な認証プロセス

---

## ユーザーストーリー

### US-1: セキュアな顔認証登録

**As a** 社員  
**I want to** 高度なliveness検証を通じて顔を登録したい  
**So that** 私の顔データが不正に登録されることを防げる

**Acceptance Criteria:**

1.1. 登録時にRekognition Liveness APIを使用した検証が実行される  
1.2. ユーザーは画面の指示に従って顔を動かす（チャレンジ）  
1.3. Liveness検証が成功した場合のみ、顔データが登録される  
1.4. 検証失敗時は明確なエラーメッセージが表示される  
1.5. 検証プロセスは30秒以内に完了する

### US-2: セキュアな顔認証ログイン

**As a** 社員  
**I want to** 高度なliveness検証を通じてログインしたい  
**So that** 他人が私の写真を使ってログインできないようにする

**Acceptance Criteria:**

2.1. ログイン時にRekognition Liveness APIを使用した検証が実行される  
2.2. ユーザーは画面の指示に従って顔を動かす（チャレンジ）  
2.3. Liveness検証成功後、1:N顔マッチングが実行される  
2.4. 両方の検証が成功した場合のみログインが許可される  
2.5. 検証プロセスは30秒以内に完了する

### US-3: 緊急認証でのLiveness検証

**As a** 社員  
**I want to** 緊急認証時もliveness検証を受けたい  
**So that** セキュリティレベルを維持できる

**Acceptance Criteria:**

3.1. 緊急認証（社員証+パスワード）でもliveness検証が実行される  
3.2. 社員証OCR、AD認証、Liveness検証の3つが成功する必要がある  
3.3. Liveness検証失敗時は緊急認証も失敗する  
3.4. 検証プロセスは全体で45秒以内に完了する

### US-4: 再登録でのLiveness検証

**As a** 社員  
**I want to** 顔データ再登録時もliveness検証を受けたい  
**So that** 不正な再登録を防げる

**Acceptance Criteria:**

4.1. 再登録時にRekognition Liveness APIを使用した検証が実行される  
4.2. 本人確認（社員証+AD認証）とliveness検証の両方が成功する必要がある  
4.3. 古い顔データの削除前にliveness検証が完了する  
4.4. 検証プロセスは全体で45秒以内に完了する

### US-5: Liveness検証の監査ログ

**As a** システム管理者  
**I want to** Liveness検証の結果を監査ログで確認したい  
**So that** セキュリティインシデントを追跡できる

**Acceptance Criteria:**

5.1. すべてのliveness検証結果がS3に保存される  
5.2. ログには以下の情報が含まれる：
   - セッションID
   - 社員ID
   - 検証結果（成功/失敗）
   - 信頼度スコア
   - タイムスタンプ
   - リファレンス画像のS3キー
5.3. 検証失敗時は失敗理由が記録される  
5.4. ログは90日間保持される

---

## 機能要件

### FR-1: Liveness Session管理

**説明:** Rekognition Liveness APIのセッション作成と管理

**要件:**
- FR-1.1: Livenessセッションを作成するAPIエンドポイント
- FR-1.2: セッションIDをクライアントに返却
- FR-1.3: セッションの有効期限は10分
- FR-1.4: セッション結果を取得するAPIエンドポイント
- FR-1.5: セッション情報をDynamoDBに保存

### FR-2: クライアント統合

**説明:** フロントエンドでのLiveness検証UI実装

**要件:**
- FR-2.1: AWS Amplify UI Liveness Componentの統合
- FR-2.2: ユーザーへのチャレンジ指示表示
- FR-2.3: カメラアクセス許可の取得
- FR-2.4: リアルタイムフィードバック表示
- FR-2.5: 検証完了後の結果表示

### FR-3: バックエンド検証

**説明:** Liveness検証結果の取得と評価

**要件:**
- FR-3.1: GetFaceLivenessSessionResults APIの呼び出し
- FR-3.2: 信頼度スコアの評価（閾値: 90%）
- FR-3.3: 検証失敗時のエラーハンドリング
- FR-3.4: リファレンス画像の取得とS3保存
- FR-3.5: 監査ログの記録

### FR-4: 既存フローへの統合

**説明:** 既存の認証フローへのLiveness検証の組み込み

**要件:**
- FR-4.1: 登録フローへの統合
- FR-4.2: ログインフローへの統合
- FR-4.3: 緊急認証フローへの統合
- FR-4.4: 再登録フローへの統合
- FR-4.5: 後方互換性の維持（段階的移行）

### FR-5: エラーハンドリング

**説明:** Liveness検証失敗時の適切な処理

**要件:**
- FR-5.1: タイムアウトエラーの処理
- FR-5.2: カメラアクセス拒否の処理
- FR-5.3: 信頼度不足の処理
- FR-5.4: ネットワークエラーの処理
- FR-5.5: ユーザーフレンドリーなエラーメッセージ

---

## 非機能要件

### NFR-1: パフォーマンス

- NFR-1.1: Liveness検証は30秒以内に完了
- NFR-1.2: セッション作成は3秒以内
- NFR-1.3: 結果取得は5秒以内
- NFR-1.4: 同時セッション数: 100セッション/分

### NFR-2: セキュリティ

- NFR-2.1: セッションIDは暗号学的に安全な乱数
- NFR-2.2: セッション結果は暗号化してS3に保存
- NFR-2.3: リファレンス画像は暗号化して保存
- NFR-2.4: セッション情報は10分後に自動削除
- NFR-2.5: 監査ログは改ざん防止

### NFR-3: 可用性

- NFR-3.1: Liveness API障害時のフォールバック機能
- NFR-3.2: エラー時の自動リトライ（最大3回）
- NFR-3.3: サービス稼働率: 99.9%
- NFR-3.4: 障害時の通知機能

### NFR-4: 保守性

- NFR-4.1: Liveness検証ロジックの独立性
- NFR-4.2: 設定値の外部化（信頼度閾値など）
- NFR-4.3: 詳細なログ出力
- NFR-4.4: テスト容易性（モック対応）

### NFR-5: コスト

- NFR-5.1: Livenessセッション数の監視
- NFR-5.2: 月間コスト上限アラート
- NFR-5.3: 不要なセッションの自動削除
- NFR-5.4: コスト最適化レポート

---

## 技術要件

### TR-1: AWS Rekognition Liveness API

**使用API:**
- `CreateFaceLivenessSession`: セッション作成
- `GetFaceLivenessSessionResults`: 結果取得
- `StartFaceLivenessSession`: セッション開始（クライアント側）

**設定:**
- Region: ap-northeast-1
- Confidence Threshold: 90%
- Session Timeout: 10分

### TR-2: フロントエンド

**技術スタック:**
- AWS Amplify UI React
- @aws-amplify/ui-react-liveness
- React 18+
- TypeScript

**実装:**
- FaceLivenessDetector Component
- セッション管理ロジック
- エラーハンドリング

### TR-3: バックエンド

**Lambda関数:**
- `create-liveness-session`: セッション作成
- `get-liveness-result`: 結果取得
- 既存Lambda関数の更新（liveness統合）

**DynamoDB:**
- LivenessSessions テーブル
  - session_id (PK)
  - employee_id
  - status
  - confidence
  - created_at
  - expires_at (TTL)

**S3:**
- liveness-audit-images/
  - {session_id}/reference.jpg
  - {session_id}/audit.jpg

### TR-4: IAM権限

**Lambda実行ロール:**
```json
{
  "Effect": "Allow",
  "Action": [
    "rekognition:CreateFaceLivenessSession",
    "rekognition:GetFaceLivenessSessionResults"
  ],
  "Resource": "*"
}
```

---

## 制約条件

### C-1: AWS制限

- Rekognition Liveness APIは特定リージョンのみ対応
- セッション有効期限は最大10分
- 同時セッション数に制限あり

### C-2: コスト

- Livenessセッションごとに課金（$0.025/セッション）
- 月間予算: $500（20,000セッション）
- コスト超過時の対応策が必要

### C-3: ブラウザ互換性

- カメラアクセスが必要（HTTPS必須）
- WebRTC対応ブラウザのみ
- モバイルブラウザでの動作確認必要

### C-4: 移行期間

- 段階的移行（2週間）
- 既存ユーザーへの影響最小化
- ロールバック計画の準備

---

## 成功基準

### SC-1: セキュリティ

- [ ] 写真を使ったなりすまし攻撃を100%防御
- [ ] 動画を使ったなりすまし攻撃を95%以上防御
- [ ] 不正アクセス試行の検出率: 99%以上

### SC-2: ユーザー体験

- [ ] Liveness検証成功率: 95%以上
- [ ] 平均検証時間: 20秒以内
- [ ] ユーザー満足度: 4.0/5.0以上

### SC-3: システム

- [ ] API可用性: 99.9%以上
- [ ] エラー率: 1%以下
- [ ] 平均応答時間: 3秒以内

### SC-4: コスト

- [ ] 月間コスト: 予算内（$500以下）
- [ ] セッション単価: $0.025以下
- [ ] ROI: セキュリティインシデント削減効果

---

## リスクと対策

### R-1: コスト超過

**リスク:** Livenessセッション数が予想を超える

**対策:**
- セッション数の監視とアラート
- 月間上限の設定
- 不要なセッションの削除

### R-2: API障害

**リスク:** Rekognition Liveness APIが利用不可

**対策:**
- フォールバック機能（DetectFaces API）
- エラー時の通知
- 自動リトライ機能

### R-3: ユーザー体験の低下

**リスク:** Liveness検証が煩わしい

**対策:**
- 明確な指示とフィードバック
- 検証時間の最適化
- ユーザーテストの実施

### R-4: 移行の失敗

**リスク:** 既存機能への影響

**対策:**
- 段階的移行
- 十分なテスト
- ロールバック計画

---

## 依存関係

### 既存機能

- Face Recognition Service
- Enrollment Handler
- Face Login Handler
- Emergency Auth Handler
- Re-enrollment Handler

### 外部サービス

- AWS Rekognition Liveness API
- AWS Amplify UI
- DynamoDB
- S3

### インフラ

- Lambda関数
- API Gateway
- CloudFront
- IAM Role

---

## 参考資料

- [AWS Rekognition Liveness API Documentation](https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness.html)
- [Amplify UI Liveness Component](https://ui.docs.amplify.aws/react/connected-components/liveness)
- [Rekognition Liveness Pricing](https://aws.amazon.com/rekognition/pricing/)
- [Best Practices for Face Liveness](https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness-best-practices.html)

---

**Next Steps:**
1. 設計書の作成（design.md）
2. タスク分解（tasks.md）
3. プロトタイプ実装
4. ユーザーテスト
5. 本番展開

---

**Version:** 1.0  
**Last Updated:** 2026-01-30  
**Author:** Kiro AI Assistant
