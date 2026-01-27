# 要求仕様書

## はじめに

Face-Auth IdP システムは、社員証ベースの信頼チェーンを基盤とした顔認識(1:N)パスワードレス認証を提供するAWS基盤の従業員認証システムです。このシステムは3つの認証フローをサポートします：社員証OCR認証後の顔登録による初回登録/再登録、顔認識(1:N)による通常ログイン、顔認識失敗時の社員証OCR + ADパスワードによる緊急ログイン。

## 用語集

- **Face_Auth_IdP_System**: AWS基盤の完全な従業員顔認証IDプロバイダーシステム
- **Employee**: システムに登録して認証する個別の従業員
- **Employee_ID_Card**: OCRベース認証に使用される物理的な従業員身分証
- **Face_Data**: 認証のために抽出・保存される生体顔特徴 (200x200サムネイル)
- **Authentication_Session**: 認証成功後に生成される時間制限付きセッション
- **Face_Capture**: Amazon Rekognition Livenessを使用した顔画像データキャプチャプロセス
- **Face_Matcher**: 1:N顔マッチングを実行するAmazon Rekognitionコンポーネント
- **Enrollment**: IDカード確認後に従業員の顔データを登録するプロセス
- **Re_Enrollment**: 既存従業員の顔データを更新するプロセス
- **Liveness_Detection**: キャプチャされた顔が実際の人物のものであることを保証するAmazon Rekognition Liveness技術 (信頼度 > 90%)
- **OCR_Engine**: 従業員IDカードのテキスト抽出のためのAmazon Textractコンポーネント
- **AD_Connector**: オンプレミスActive DirectoryとAWS Direct Connect認証を管理するコンポーネント
- **Card_Template**: IDカード認識のためのロゴ位置とTextract Queryフレーズを定義するDynamoDB保存パターン
- **Thumbnail_Processor**: 元画像から200x200ピクセルのサムネイルを生成するコンポーネント
- **Login_Attempt_Image**: 30日自動削除とともにlogins/フォルダに保存されるログイン時の顔キャプチャ

## 要求事項

### 要求事項 1: 従業員身分証認証と登録

**ユーザーストーリー:** 新規従業員として、まず従業員身分証で身元を確認した後、将来のパスワードレス認証のために顔を登録したい。

#### 受入基準

1. WHEN 従業員が登録を開始すると、THE Face_Auth_IdP_System SHALL OCR_Engineを使用して従業員身分証をキャプチャして処理する
2. WHEN 従業員身分証がキャプチャされると、THE OCR_Engine SHALL DynamoDBのCard_Templateパターンを使用して従業員情報を抽出する
3. WHEN OCR抽出が成功すると、TNaHE AD_Connector SHALL 10秒以内にオンプレミスActive Directoryに対して従業員情報を確認する
4. WHEN AD確認が成功すると、THE Face_Auth_IdP_System SHALL Liveness_Detectionを使用した顔キャプチャを進行する
5. WHEN 信頼度 > 90%で顔キャプチャが完了すると、THE Face_Auth_IdP_System SHALL 200x200サムネイルを生成してS3 enroll/フォルダに保存する
6. IF 従業員身分証形式がどのCard_Templateとも一致しない場合、THEN THE Face_Auth_IdP_System SHALL "社員証規格不一致"メッセージを返す
7. IF 従業員情報がAD記録と一致しない場合、THEN THE Face_Auth_IdP_System SHALL "登録情報不一致"メッセージを返す
8. IF ADアカウントが無効化されている場合、THEN THE Face_Auth_IdP_System SHALL "アカウント無効化"メッセージを返す

### 要求事項 2: 顔認識ログイン (1:N認証)

**ユーザーストーリー:** 登録済み従業員として、資格情報を入力せずに顔だけで認証してシステムに迅速かつ安全にアクセスしたい。

#### 受入基準

1. WHEN 従業員が顔ログインを開始すると、THE Face_Auth_IdP_System SHALL Liveness_Detectionで顔画像をキャプチャする
2. WHEN 信頼度 > 90%で顔画像がキャプチャされると、THE Face_Matcher SHALL すべての登録済みFace_Dataに対して1:Nマッチングを実行する
3. WHEN 高信頼度で顔マッチングが成功すると、THE Face_Auth_IdP_System SHALL AWS Cognitoを通じてAuthentication_Sessionを生成する
4. WHEN 顔マッチングが失敗すると、THE Face_Auth_IdP_System SHALL 30日保管のためにS3 logins/フォルダにLogin_Attempt_Imageを保存する
5. WHEN 認証が成功すると、THE Face_Auth_IdP_System SHALL 保護されたリソースへのアクセスを許可する
6. WHEN 顔認識が失敗すると、THE Face_Auth_IdP_System SHALL 緊急ログインオプションを提供する
7. IF Liveness_Detectionが失敗するか、その他の技術的問題が発生した場合、THEN THE Face_Auth_IdP_System SHALL "明るい場所で再試行してください"メッセージを表示する

### 要求事項 3: 身分証とパスワードによる緊急認証

**ユーザーストーリー:** 顔認識が失敗した従業員として、顔認証が動作しない場合でもシステムにアクセスできるように従業員身分証とADパスワードを使用して認証したい。

#### 受入基準

1. WHEN 顔認識が繰り返し失敗すると、THE Face_Auth_IdP_System SHALL 緊急認証オプションを提供する
2. WHEN 緊急認証が開始されると、THE Face_Auth_IdP_System SHALL OCR_Engineを使用して従業員身分証をキャプチャして処理する
3. WHEN IDカードOCRが成功すると、THE Face_Auth_IdP_System SHALL ADパスワード入力を要求する
4. WHEN AD資格情報が提供されると、THE AD_Connector SHALL 10秒以内にオンプレミスActive Directoryに対して認証する
5. WHEN AD認証が成功すると、THE Face_Auth_IdP_System SHALL AWS Cognitoを通じてAuthentication_Sessionを生成する
6. IF AD認証が失敗した場合、THEN THE Face_Auth_IdP_System SHALL セキュリティのためにレート制限を実装する
7. IF いずれかのステップが失敗した場合、THEN THE Face_Auth_IdP_System SHALL "明るい場所で再試行してください"メッセージを表示する

### 要求事項 4: AWSインフラとネットワークセキュリティ

**ユーザーストーリー:** システム管理者として、従業員データと認証プロセスが保護されるように、オンプレミスシステムとの適切なネットワーク接続を通じてAWSインフラ内でシステムが安全に動作することを望む。

#### 受入基準

1. THE Face_Auth_IdP_System SHALL オンプレミスActive Directoryへの安全な接続のためにAWS Direct Connectを使用する
2. WHEN AD認証が実行されると、THE AD_Connector SHALL 10秒タイムアウト制限内に完了する
3. WHEN Lambda関数が実行されると、THE Face_Auth_IdP_System SHALL 合計15秒タイムアウト内にすべての操作を完了する
4. THE Face_Auth_IdP_System SHALL Infrastructure as CodeのためにPythonとともにAWS CDKを使用してデプロイする
5. THE Face_Auth_IdP_System SHALL ネットワーク分離のために適切なセキュリティグループとともにAWS VPCを使用する
6. WHEN データが転送されると、THE Face_Auth_IdP_System SHALL すべての通信に暗号化された接続を使用する
7. THE Face_Auth_IdP_System SHALL サービスアクセス制御のために適切なIAMロールとポリシーを実装する

### 要求事項 5: データ管理とストレージポリシー

**ユーザーストーリー:** システム管理者として、セキュリティとコンプライアンスを維持しながらストレージコストを最適化できるように、顔画像と従業員データに対する適切なデータライフサイクル管理を望む。

#### 受入基準

1. WHEN 登録画像が処理されると、THE Thumbnail_Processor SHALL 200x200ピクセルのサムネイルを生成して元画像を削除する
2. WHEN 登録が完了すると、THE Face_Auth_IdP_System SHALL S3 enroll/フォルダにサムネイルを永久的に保存する
3. WHEN ログイン試行が発生すると、THE Face_Auth_IdP_System SHALL 画像をサムネイルに変換してS3 logins/フォルダに保存する
4. THE Face_Auth_IdP_System SHALL S3 Lifecycleポリシーを使用して30日後にLogin_Attempt_Imagesを自動的に削除する
5. WHEN 従業員身分証が処理されると、THE Face_Auth_IdP_System SHALL DynamoDBに複数のCard_Templateパターンを保存する
6. THE Face_Auth_IdP_System SHALL AWS暗号化標準を使用してすべての保存されたFace_Dataを暗号化する
7. WHEN Face_Dataにアクセスすると、THE Face_Auth_IdP_System SHALL 適切なアクセス制御と監査ログを実装する

### 要求事項 6: Amazon Rekognition統合とLiveness検出

**ユーザーストーリー:** セキュリティ管理者として、実際の従業員のみが認証に成功できるように、スプーフィング攻撃を防ぐ強力な顔認識とliveness検出を望む。

#### 受入基準

1. WHEN 顔キャプチャが発生すると、THE Face_Auth_IdP_System SHALL Amazon Rekognition Liveness検出を使用する
2. WHEN Liveness_Detectionが実行されると、THE Face_Auth_IdP_System SHALL 90%より大きい信頼度スコアを要求する
3. WHEN livenessチェックが失敗すると、THE Face_Auth_IdP_System SHALL 認証試行を拒否する
4. WHEN 顔マッチングが実行されると、THE Face_Matcher SHALL 1:N比較のためにAmazon Rekognitionを使用する
5. THE Face_Auth_IdP_System SHALL 登録済み従業員に対して95%以上の顔認識精度を維持する
6. WHEN 複数の認証失敗が発生すると、THE Face_Auth_IdP_System SHALL 段階的レート制限を実装する
7. THE Face_Auth_IdP_System SHALL タイムスタンプと信頼度スコアとともにすべての認証試行を記録する

### 要求事項 7: 従業員身分証処理とテンプレート管理

**ユーザーストーリー:** システム管理者として、システムが様々な従業員カードデザインに対応できるように、多様なカード形式とレイアウトを処理できる柔軟なIDカード認識を望む。

#### 受入基準

1. WHEN IDカードが処理されると、THE OCR_Engine SHALL テキスト抽出のためにAmazon Textractを使用する
2. WHEN Textract処理が発生すると、THE Face_Auth_IdP_System SHALL DynamoDBのCard_Templateパターンを使用する
3. WHEN 新しいカード形式が導入されると、THE Face_Auth_IdP_System SHALL 複数のCard_Template構成をサポートする
4. THE Face_Auth_IdP_System SHALL Card_Templateレコードにロゴ位置とTextract Queryフレーズを保存する
5. WHEN OCRがどのテンプレートとも一致しない場合、THE Face_Auth_IdP_System SHALL 特定の"社員証規格不一致"エラーを返す
6. THE Face_Auth_IdP_System SHALL カードパターンに基づく動的Textract Query構成をサポートする
7. WHEN カードテンプレートが更新されると、THE Face_Auth_IdP_System SHALL システム再起動なしに変更を適用する

### 要求事項 8: エラー処理とユーザーメッセージング

**ユーザーストーリー:** システムを使用する従業員として、認証が失敗した際に何が間違っていて、どのように解決するかを理解できるように、明確で役立つエラーメッセージを望む。

#### 受入基準

1. WHEN システム判断エラーが発生すると、THE Face_Auth_IdP_System SHALL 具体的なエラーメッセージを提供する
2. WHEN IDカード形式が認識されない場合、THE Face_Auth_IdP_System SHALL "社員証規格不一致"を表示する
3. WHEN 従業員データがAD記録と一致しない場合、THE Face_Auth_IdP_System SHALL "登録情報不一致"を表示する
4. WHEN ADアカウントが非アクティブ状態の場合、THE Face_Auth_IdP_System SHALL "アカウント無効化"を表示する
5. WHEN 技術的問題(照明、カメラ、ネットワーク)が発生した場合、THE Face_Auth_IdP_System SHALL "明るい場所で再試行してください"を表示する
6. THE Face_Auth_IdP_System SHALL system_reason(ログ用)とuser_message(表示用)を分離する
7. WHEN エラーが記録されると、THE Face_Auth_IdP_System SHALL 問題解決のための詳細な技術情報を含める

### 要求事項 9: 再登録と顔データ更新

**ユーザーストーリー:** 登録済み従業員として、外見が大きく変わった際に顔認証を継続して安定的に使用できるように顔データを更新したい。

#### 受入基準

1. WHEN 従業員が再登録を要求すると、THE Face_Auth_IdP_System SHALL 従業員身分証OCRを使用して身元を確認する
2. WHEN 再登録ID確認が成功すると、THE Face_Auth_IdP_System SHALL 新しい顔キャプチャを進行する
3. WHEN 新しい顔データがキャプチャされると、THE Face_Auth_IdP_System SHALL 既存のFace_Dataを新しいサムネイルで置き換える
4. WHEN 再登録が完了すると、THE Face_Auth_IdP_System SHALL 従業員に更新成功を確認する
5. THE Face_Auth_IdP_System SHALL すべての再登録活動の監査証跡を維持する
6. WHEN 再登録が失敗した場合、THE Face_Auth_IdP_System SHALL 既存のFace_Dataを変更せずに保存する
7. THE Face_Auth_IdP_System SHALL 再登録を許可する前に追加認証を要求する

### 要求事項 10: フロントエンド統合とユーザーインターフェース

**ユーザーストーリー:** 従業員として、様々なデバイスとブラウザで安定的に動作する直感的なWebインターフェースを通じてシステムに簡単にアクセスできることを望む。

#### 受入基準

1. THE Face_Auth_IdP_System SHALL AWS Amplify UIコンポーネントを使用するReactベースのフロントエンドを提供する
2. WHEN 顔キャプチャが必要な場合、THE Face_Auth_IdP_System SHALL FaceLivenessDetectorコンポーネントを使用する
3. WHEN 認証モードが選択されると、THE Face_Auth_IdP_System SHALL LOGIN、ENROLL、ID_SCANモードをサポートする
4. THE Face_Auth_IdP_System SHALL 顔キャプチャプロセス中にリアルタイムフィードバックを提供する
5. WHEN エラーが発生した場合、THE Face_Auth_IdP_System SHALL インターフェースに適切なユーザーメッセージを表示する
6. THE Face_Auth_IdP_System SHALL 様々なデバイスとカメラ構成で動作する
7. WHEN 認証が成功した場合、THE Face_Auth_IdP_System SHALL 適切な保護されたリソースにリダイレクトする
