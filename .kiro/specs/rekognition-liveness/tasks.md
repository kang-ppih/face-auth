# Rekognition Liveness API 移行 - 実装タスク

**Feature:** Rekognition Liveness APIへの移行  
**Status:** Not Started  
**Created:** 2026-02-02

---

## タスク概要

このタスクリストは、Rekognition Liveness API移行の実装を段階的に進めるためのものです。
各タスクは要件と設計書に基づいており、テスト駆動開発（TDD）アプローチを採用しています。

---

## フェーズ1: インフラストラクチャとコアサービス（Week 1）

### 1. DynamoDBテーブル作成

- [ ] 1.1 LivenessSessionsテーブルをCDKで定義
  - session_id (PK)
  - employee_id (GSI)
  - TTL設定（expires_at）
  - タグ付け
- [ ] 1.2 CDKデプロイスクリプト更新
- [ ] 1.3 テーブル作成の検証

**要件:** FR-1.5, TR-3  
**成果物:** `infrastructure/face_auth_stack.py` (更新)

---

### 2. S3バケット構造準備

- [ ] 2.1 liveness-audit/ディレクトリ構造をCDKで定義
- [ ] 2.2 ライフサイクルポリシー設定（90日保持）
- [ ] 2.3 暗号化設定（SSE-S3）
- [ ] 2.4 IAM権限設定

**要件:** FR-3.4, NFR-2.3  
**成果物:** `infrastructure/face_auth_stack.py` (更新)

---

### 3. LivenessService実装

- [ ] 3.1 LivenessServiceクラス作成
  - `__init__`: 初期化とクライアント設定
  - `create_session`: セッション作成
  - `get_session_result`: 結果取得と評価
  - `store_audit_log`: 監査ログ保存
  - `_validate_confidence`: 信頼度検証
  - `_store_reference_image`: リファレンス画像保存
- [ ] 3.2 カスタム例外クラス作成
  - LivenessServiceError
  - SessionNotFoundError
  - SessionExpiredError
  - ConfidenceThresholdError
- [ ] 3.3 LivenessSessionResultデータクラス作成
- [ ] 3.4 Type hints とdocstrings追加

**要件:** FR-1, FR-3  
**成果物:** `lambda/shared/liveness_service.py`

---

### 4. LivenessService単体テスト

- [ ] 4.1 test_create_session_success
- [ ] 4.2 test_create_session_failure
- [ ] 4.3 test_get_session_result_live（信頼度 > 90%）
- [ ] 4.4 test_get_session_result_not_live（信頼度 < 90%）
- [ ] 4.5 test_get_session_result_not_found
- [ ] 4.6 test_get_session_result_expired
- [ ] 4.7 test_store_audit_log_success
- [ ] 4.8 test_confidence_threshold_configurable
- [ ] 4.9 モックを使用したRekognition API呼び出しテスト

**要件:** すべてのFR-1, FR-3要件  
**成果物:** `tests/test_liveness_service.py`  
**カバレッジ目標:** 90%以上

---

## フェーズ2: Lambda関数実装（Week 1-2）

### 5. CreateLivenessSession Lambda実装

- [ ] 5.1 ハンドラー関数作成
  - リクエストボディ解析
  - バリデーション
  - LivenessService呼び出し
  - レスポンス生成
- [ ] 5.2 エラーハンドリング追加
- [ ] 5.3 TimeoutManager統合
- [ ] 5.4 CloudWatchログ出力
- [ ] 5.5 環境変数設定

**要件:** FR-1.1, FR-1.2, FR-1.3  
**成果物:** `lambda/liveness/create_session_handler.py`

---

### 6. CreateLivenessSession Lambda単体テスト

- [ ] 6.1 test_handler_success
- [ ] 6.2 test_handler_missing_employee_id
- [ ] 6.3 test_handler_invalid_request
- [ ] 6.4 test_handler_rekognition_error
- [ ] 6.5 test_handler_timeout
- [ ] 6.6 test_handler_response_format

**要件:** FR-1  
**成果物:** `tests/test_create_liveness_session.py`

---

### 7. GetLivenessResult Lambda実装

- [ ] 7.1 ハンドラー関数作成
  - パスパラメータ取得
  - バリデーション
  - LivenessService呼び出し
  - レスポンス生成
- [ ] 7.2 エラーハンドリング追加
- [ ] 7.3 TimeoutManager統合
- [ ] 7.4 CloudWatchログ出力
- [ ] 7.5 環境変数設定

**要件:** FR-1.4, FR-3  
**成果物:** `lambda/liveness/get_result_handler.py`

---

### 8. GetLivenessResult Lambda単体テスト

- [ ] 8.1 test_handler_success_live
- [ ] 8.2 test_handler_success_not_live
- [ ] 8.3 test_handler_missing_session_id
- [ ] 8.4 test_handler_session_not_found
- [ ] 8.5 test_handler_session_expired
- [ ] 8.6 test_handler_timeout
- [ ] 8.7 test_handler_response_format

**要件:** FR-3  
**成果物:** `tests/test_get_liveness_result.py`

---

### 9. Lambda関数のCDK定義

- [ ] 9.1 CreateLivenessSession Lambda定義
  - タイムアウト: 10秒
  - メモリ: 256MB
  - 環境変数設定
- [ ] 9.2 GetLivenessResult Lambda定義
  - タイムアウト: 15秒
  - メモリ: 256MB
  - 環境変数設定
- [ ] 9.3 IAM権限設定
  - Rekognition API権限
  - DynamoDB権限
  - S3権限
- [ ] 9.4 API Gatewayエンドポイント追加
  - POST /liveness/session/create
  - GET /liveness/session/{sessionId}/result

**要件:** TR-3, TR-4  
**成果物:** `infrastructure/face_auth_stack.py` (更新)

---

## フェーズ3: 既存Lambda関数の更新（Week 2）

### 10. Enrollment Handler更新

- [ ] 10.1 liveness_session_idパラメータ追加
- [ ] 10.2 Liveness検証ステップ追加（最初に実行）
- [ ] 10.3 検証失敗時のエラーハンドリング
- [ ] 10.4 監査ログ記録
- [ ] 10.5 既存テスト更新
- [ ] 10.6 新規テスト追加（Liveness統合）

**要件:** US-1, FR-4.1  
**成果物:** `lambda/enrollment/handler.py` (更新)

---

### 11. Face Login Handler更新

- [ ] 11.1 liveness_session_idパラメータ追加
- [ ] 11.2 Liveness検証ステップ追加（最初に実行）
- [ ] 11.3 検証失敗時のエラーハンドリング
- [ ] 11.4 失敗試行のS3記録
- [ ] 11.5 既存テスト更新
- [ ] 11.6 新規テスト追加（Liveness統合）

**要件:** US-2, FR-4.2  
**成果物:** `lambda/face_login/handler.py` (更新)

---

### 12. Emergency Auth Handler更新

- [ ] 12.1 liveness_session_idパラメータ追加
- [ ] 12.2 Liveness検証ステップ追加（OCR・AD認証後）
- [ ] 12.3 検証失敗時のエラーハンドリング
- [ ] 12.4 監査ログ記録
- [ ] 12.5 既存テスト更新
- [ ] 12.6 新規テスト追加（Liveness統合）

**要件:** US-3, FR-4.3  
**成果物:** `lambda/emergency_auth/handler.py` (更新)

---

### 13. Re-enrollment Handler更新

- [ ] 13.1 liveness_session_idパラメータ追加
- [ ] 13.2 Liveness検証ステップ追加（本人確認後）
- [ ] 13.3 検証失敗時のエラーハンドリング
- [ ] 13.4 監査ログ記録
- [ ] 13.5 既存テスト更新
- [ ] 13.6 新規テスト追加（Liveness統合）

**要件:** US-4, FR-4.4  
**成果物:** `lambda/re_enrollment/handler.py` (更新)

---

## フェーズ4: フロントエンド実装（Week 2-3）

### 14. Amplify UI Liveness依存関係追加

- [ ] 14.1 package.json更新
  - @aws-amplify/ui-react-liveness
  - @aws-amplify/ui-react
- [ ] 14.2 npm install実行
- [ ] 14.3 Amplify設定ファイル更新

**要件:** FR-2.1, TR-2  
**成果物:** `frontend/package.json` (更新)

---

### 15. LivenessDetectorコンポーネント実装

- [ ] 15.1 LivenessDetector.tsxコンポーネント作成
  - セッション作成API呼び出し
  - FaceLivenessDetector統合
  - 検証完了ハンドリング
  - エラーハンドリング
- [ ] 15.2 LivenessDetector.cssスタイル作成
- [ ] 15.3 ローディング状態管理
- [ ] 15.4 ユーザーフィードバック表示

**要件:** FR-2  
**成果物:** `frontend/src/components/LivenessDetector.tsx`

---

### 16. Enrollmentコンポーネント更新

- [ ] 16.1 LivenessDetectorコンポーネント統合
- [ ] 16.2 ステップフロー実装（Liveness → Capture → Submit）
- [ ] 16.3 liveness_session_idの状態管理
- [ ] 16.4 API呼び出し更新（liveness_session_id追加）
- [ ] 16.5 エラーハンドリング更新
- [ ] 16.6 UI/UX改善

**要件:** US-1, FR-4.1  
**成果物:** `frontend/src/components/Enrollment.tsx` (更新)

---

### 17. Loginコンポーネント更新

- [ ] 17.1 LivenessDetectorコンポーネント統合
- [ ] 17.2 ステップフロー実装
- [ ] 17.3 liveness_session_idの状態管理
- [ ] 17.4 API呼び出し更新
- [ ] 17.5 エラーハンドリング更新

**要件:** US-2, FR-4.2  
**成果物:** `frontend/src/components/Login.tsx` (更新)

---

### 18. EmergencyAuthコンポーネント更新

- [ ] 18.1 LivenessDetectorコンポーネント統合
- [ ] 18.2 ステップフロー実装
- [ ] 18.3 liveness_session_idの状態管理
- [ ] 18.4 API呼び出し更新
- [ ] 18.5 エラーハンドリング更新

**要件:** US-3, FR-4.3  
**成果物:** `frontend/src/components/EmergencyAuth.tsx` (更新)

---

### 19. ReEnrollmentコンポーネント更新

- [ ] 19.1 LivenessDetectorコンポーネント統合
- [ ] 19.2 ステップフロー実装
- [ ] 19.3 liveness_session_idの状態管理
- [ ] 19.4 API呼び出し更新
- [ ] 19.5 エラーハンドリング更新

**要件:** US-4, FR-4.4  
**成果物:** `frontend/src/components/ReEnrollment.tsx` (更新)

---

## フェーズ5: 統合テストとE2Eテスト（Week 3）

### 20. Liveness統合テスト

- [ ] 20.1 test_full_liveness_flow（実際のAWS API使用）
- [ ] 20.2 test_session_creation_and_retrieval
- [ ] 20.3 test_session_expiration
- [ ] 20.4 test_confidence_threshold_validation
- [ ] 20.5 test_audit_log_storage

**要件:** すべてのFR要件  
**成果物:** `tests/test_liveness_integration.py`

---

### 21. E2Eテスト（Liveness統合）

- [ ] 21.1 test_enrollment_with_liveness
- [ ] 21.2 test_login_with_liveness
- [ ] 21.3 test_emergency_auth_with_liveness
- [ ] 21.4 test_re_enrollment_with_liveness
- [ ] 21.5 test_liveness_failure_scenarios

**要件:** US-1, US-2, US-3, US-4  
**成果物:** `tests/test_liveness_e2e.py`

---

## フェーズ6: 監視とロギング（Week 3）

### 22. CloudWatchメトリクス実装

- [ ] 22.1 LivenessSuccessRateメトリクス
- [ ] 22.2 AverageConfidenceメトリクス
- [ ] 22.3 SessionCountメトリクス
- [ ] 22.4 ErrorRateメトリクス
- [ ] 22.5 メトリクス送信ロジック実装

**要件:** NFR-3, 運用設計  
**成果物:** `lambda/shared/liveness_service.py` (更新)

---

### 23. CloudWatchアラーム設定

- [ ] 23.1 成功率低下アラーム（< 95%）
- [ ] 23.2 コスト超過アラーム（> 20,000セッション/月）
- [ ] 23.3 エラー率アラーム（> 1%）
- [ ] 23.4 平均検証時間アラーム（> 30秒）
- [ ] 23.5 SNS通知設定

**要件:** NFR-3, 運用設計  
**成果物:** `infrastructure/face_auth_stack.py` (更新)

---

### 24. 構造化ログ実装

- [ ] 24.1 セッション作成ログ
- [ ] 24.2 検証完了ログ
- [ ] 24.3 検証失敗ログ
- [ ] 24.4 エラーログ
- [ ] 24.5 ログフォーマット統一

**要件:** US-5, NFR-4.3  
**成果物:** すべてのLambda関数 (更新)

---

## フェーズ7: ドキュメントと移行準備（Week 4）

### 25. 技術ドキュメント作成

- [ ] 25.1 LIVENESS_SERVICE.md作成
  - アーキテクチャ説明
  - API仕様
  - 使用例
- [ ] 25.2 LIVENESS_MIGRATION_GUIDE.md作成
  - 移行手順
  - ロールバック手順
  - トラブルシューティング
- [ ] 25.3 README.md更新
- [ ] 25.4 API仕様書更新

**要件:** NFR-4  
**成果物:** `docs/LIVENESS_SERVICE.md`, `docs/LIVENESS_MIGRATION_GUIDE.md`

---

### 26. 運用手順書作成

- [ ] 26.1 監視手順書
- [ ] 26.2 アラート対応手順書
- [ ] 26.3 トラブルシューティングガイド
- [ ] 26.4 コスト管理手順書

**要件:** 運用設計  
**成果物:** `docs/LIVENESS_OPERATIONS.md`

---

### 27. 移行計画の最終確認

- [ ] 27.1 段階的展開計画レビュー
- [ ] 27.2 ロールバック計画レビュー
- [ ] 27.3 リスク評価
- [ ] 27.4 成功基準の確認
- [ ] 27.5 ステークホルダー承認

**要件:** 移行戦略  
**成果物:** 移行計画書

---

## フェーズ8: 段階的展開（Week 4-6）

### 28. 開発環境デプロイ

- [ ] 28.1 CDKデプロイ実行
- [ ] 28.2 Lambda関数デプロイ確認
- [ ] 28.3 DynamoDBテーブル確認
- [ ] 28.4 S3バケット確認
- [ ] 28.5 API Gatewayエンドポイント確認
- [ ] 28.6 統合テスト実行

**要件:** すべての要件  
**成果物:** デプロイ済み開発環境

---

### 29. オプトイン機能実装

- [ ] 29.1 機能フラグ実装（環境変数）
- [ ] 29.2 ユーザーグループ管理
- [ ] 29.3 A/Bテスト設定
- [ ] 29.4 メトリクス収集設定

**要件:** 移行戦略  
**成果物:** オプトイン機能

---

### 30. パイロットユーザーテスト

- [ ] 30.1 パイロットユーザー選定（10-20人）
- [ ] 30.2 Liveness機能有効化
- [ ] 30.3 ユーザーフィードバック収集
- [ ] 30.4 メトリクス分析
- [ ] 30.5 問題点の特定と修正

**要件:** 移行戦略  
**成果物:** パイロットテスト報告書

---

### 31. 段階的展開（50%）

- [ ] 31.1 50%のユーザーに展開
- [ ] 31.2 メトリクス監視（24時間）
- [ ] 31.3 エラー率確認
- [ ] 31.4 ユーザーフィードバック収集
- [ ] 31.5 問題なければ次へ、問題あればロールバック

**要件:** 移行戦略  
**成果物:** 展開報告書

---

### 32. 完全展開（100%）

- [ ] 32.1 全ユーザーに展開
- [ ] 32.2 メトリクス監視（1週間）
- [ ] 32.3 成功基準の確認
  - 成功率 > 95%
  - 平均検証時間 < 20秒
  - エラー率 < 1%
- [ ] 32.4 ユーザー満足度調査
- [ ] 32.5 最終報告書作成

**要件:** 移行戦略、成功基準  
**成果物:** 完全展開報告書

---

### 33. レガシーコード削除

- [ ] 33.1 DetectFaces APIコード削除
- [ ] 33.2 不要な環境変数削除
- [ ] 33.3 不要なテスト削除
- [ ] 33.4 コードレビュー
- [ ] 33.5 最終デプロイ

**要件:** FR-4.5  
**成果物:** クリーンアップ済みコードベース

---

## 完了基準

### 機能要件
- [ ] すべてのユーザーストーリーが実装されている
- [ ] すべての機能要件が満たされている
- [ ] すべての非機能要件が満たされている

### テスト
- [ ] 単体テストカバレッジ > 90%
- [ ] すべての統合テストが通過
- [ ] すべてのE2Eテストが通過

### パフォーマンス
- [ ] Liveness検証時間 < 30秒
- [ ] セッション作成時間 < 3秒
- [ ] 結果取得時間 < 5秒

### セキュリティ
- [ ] 写真なりすまし防御率 100%
- [ ] 動画なりすまし防御率 > 95%
- [ ] すべての監査ログが記録されている

### 運用
- [ ] メトリクスが正常に収集されている
- [ ] アラームが正常に動作している
- [ ] ドキュメントが完成している

### コスト
- [ ] 月間コスト < $500
- [ ] コスト監視が有効

---

**Version:** 1.0  
**Last Updated:** 2026-02-02  
**Total Tasks:** 33  
**Estimated Duration:** 6 weeks
