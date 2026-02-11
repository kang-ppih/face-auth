# Liveness SERVER_ERROR Fix - Cognito Identity Pool Implementation

## 問題の概要

フロントエンドでライブネス検証を実行すると、カメラ許可後に「ライブネス検証エラー: SERVER_ERROR」が発生し、画面が停止する問題が発生していました。

## 根本原因

AWS Amplify UI の `FaceLivenessDetector` コンポーネントは、Rekognition Face Liveness API を呼び出すために AWS 認証情報が必要です。しかし、フロントエンドには以下の設定が不足していました：

1. **Cognito Identity Pool が未作成**
   - User Pool のみ存在し、Identity Pool が存在しなかった
   - Identity Pool は、未認証ユーザーに一時的な AWS 認証情報を提供するために必要

2. **Amplify 設定が不完全**
   - `index.tsx` で Amplify.configure() を呼び出していたが、Identity Pool ID が設定されていなかった
   - FaceLivenessDetector は Identity Pool から取得した認証情報を使用して Rekognition API を呼び出す

## 実装した解決策

### 1. Cognito Identity Pool の作成（CDK）

`infrastructure/face_auth_stack.py` の `_create_cognito_user_pool()` メソッドに以下を追加：

```python
# Create Identity Pool for FaceLivenessDetector
self.identity_pool = cognito.CfnIdentityPool(
    self, "FaceAuthIdentityPool",
    identity_pool_name="FaceAuthIdentityPool",
    allow_unauthenticated_identities=True,  # 未認証ユーザーを許可
    allow_classic_flow=False,
    cognito_identity_providers=[
        cognito.CfnIdentityPool.CognitoIdentityProviderProperty(
            client_id=self.user_pool_client.user_pool_client_id,
            provider_name=self.user_pool.user_pool_provider_name
        )
    ]
)
```

### 2. IAM ロールの作成

未認証ユーザー用と認証済みユーザー用の IAM ロールを作成し、Rekognition Liveness API へのアクセス権限を付与：

```python
# 未認証ユーザー用ロール
self.unauthenticated_role = iam.Role(
    self, "CognitoUnauthenticatedRole",
    assumed_by=iam.FederatedPrincipal(
        "cognito-identity.amazonaws.com",
        conditions={
            "StringEquals": {
                "cognito-identity.amazonaws.com:aud": self.identity_pool.ref
            },
            "ForAnyValue:StringLike": {
                "cognito-identity.amazonaws.com:amr": "unauthenticated"
            }
        },
        assume_role_action="sts:AssumeRoleWithWebIdentity"
    )
)

# Rekognition Liveness API へのアクセス権限
self.unauthenticated_role.add_to_policy(
    iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=["rekognition:StartFaceLivenessSession"],
        resources=["*"]
    )
)
```

### 3. Identity Pool ロールアタッチメント

```python
cognito.CfnIdentityPoolRoleAttachment(
    self, "IdentityPoolRoleAttachment",
    identity_pool_id=self.identity_pool.ref,
    roles={
        "authenticated": self.authenticated_role.role_arn,
        "unauthenticated": self.unauthenticated_role.role_arn
    }
)
```

### 4. CDK Output の追加

```python
CfnOutput(
    self, "IdentityPoolId",
    value=self.identity_pool.ref,
    description="Cognito Identity Pool ID for FaceLivenessDetector"
)
```

### 5. フロントエンド Amplify 設定の更新

`frontend/src/index.tsx`:

```typescript
import { Amplify } from 'aws-amplify';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID || '',
      userPoolClientId: process.env.REACT_APP_COGNITO_CLIENT_ID || '',
      identityPoolId: process.env.REACT_APP_IDENTITY_POOL_ID || '',  // 追加
    }
  }
});
```

### 6. 環境変数の追加

`frontend/.env`:

```bash
REACT_APP_IDENTITY_POOL_ID=ap-northeast-1:3c402eb3-35f0-4068-927f-4ef969195361
```

## デプロイ手順

### 1. CDK デプロイ

```bash
npx cdk deploy --profile dev --require-approval never
```

**結果:**
- Identity Pool ID: `ap-northeast-1:3c402eb3-35f0-4068-927f-4ef969195361`
- IAM ロール作成完了
- CloudFormation 出力に Identity Pool ID が追加

### 2. フロントエンドビルド & デプロイ

```bash
cd frontend
npm run build
aws s3 sync build/ s3://face-auth-frontend-979431736455-ap-northeast-1 --delete --profile dev
aws cloudfront create-invalidation --distribution-id EE7F2PTRFZ6WV --paths "/*" --profile dev
```

## 動作確認方法

1. **ブラウザでフロントエンドにアクセス**
   - URL: https://d2576ywp5ut1v8.cloudfront.net

2. **ブラウザコンソールを開く（F12 > Console タブ）**
   - Amplify 設定ログを確認:
     ```
     Amplify configured:
     - Region: ap-northeast-1
     - User Pool ID: ap-northeast-1_Mg04RQ15H
     - User Pool Client ID: 1hgfirru3r4jrasg9g8s1j0kme
     - Identity Pool ID: ap-northeast-1:3c402eb3-35f0-4068-927f-4ef969195361
     ```

3. **ライブネス検証を実行**
   - 社員IDを入力してログイン画面に進む
   - カメラ許可を承認
   - FaceLivenessDetector が正常に起動することを確認

4. **エラーが発生した場合**
   - ブラウザコンソールでエラーメッセージを確認
   - Network タブで Rekognition API 呼び出しを確認
   - Lambda ログを確認:
     ```bash
     aws logs tail /aws/lambda/FaceAuth-CreateLivenessSession --since 5m --profile dev
     ```

## 技術的な詳細

### Cognito Identity Pool の役割

1. **一時的な AWS 認証情報の提供**
   - 未認証ユーザーに対して、一時的な AWS アクセスキー、シークレットキー、セッショントークンを発行
   - これらの認証情報は短時間（通常1時間）で期限切れになる

2. **最小権限の原則**
   - 未認証ユーザーには `rekognition:StartFaceLivenessSession` のみを許可
   - 他の AWS サービスへのアクセスは拒否

3. **セキュリティ**
   - Identity Pool は User Pool と統合されており、認証済みユーザーには追加の権限を付与可能
   - IAM ロールの条件により、特定の Identity Pool からのリクエストのみを許可

### FaceLivenessDetector の動作フロー

1. **コンポーネントマウント時**
   - Amplify から Identity Pool 経由で一時的な AWS 認証情報を取得
   - バックエンド API (`/liveness/session/create`) を呼び出してセッション ID を取得

2. **カメラ許可後**
   - 取得した AWS 認証情報を使用して `rekognition:StartFaceLivenessSession` を呼び出し
   - Rekognition がライブネス検証を実行
   - 検証完了後、バックエンド API (`/liveness/session/{sessionId}/result`) で結果を取得

3. **エラーハンドリング**
   - AWS 認証情報が取得できない場合: "No credentials" エラー
   - Rekognition API 呼び出しが失敗した場合: "SERVER_ERROR"
   - セッション ID が無効な場合: "Invalid session" エラー

## 変更されたファイル

### バックエンド
- `infrastructure/face_auth_stack.py` - Identity Pool、IAM ロール、出力の追加

### フロントエンド
- `frontend/src/index.tsx` - Amplify 設定に Identity Pool ID を追加
- `frontend/.env` - Identity Pool ID 環境変数を追加
- `frontend/.env.example` - Identity Pool ID のサンプルを追加

## 今後の改善点

1. **認証済みユーザーの活用**
   - 現在は未認証ユーザーとして Liveness 検証を実行
   - 将来的には、ログイン後のユーザーに対して認証済みロールを使用可能

2. **エラーメッセージの改善**
   - FaceLivenessDetector のエラーをより詳細にログ出力
   - ユーザーフレンドリーなエラーメッセージを表示

3. **セキュリティ強化**
   - Identity Pool の未認証アクセスを特定の IP アドレスに制限
   - Rekognition API の呼び出し回数を制限（レート制限）

## 参考資料

- [AWS Amplify UI Liveness Documentation](https://ui.docs.amplify.aws/react/connected-components/liveness)
- [Amazon Rekognition Face Liveness Prerequisites](https://docs.aws.amazon.com/rekognition/latest/dg/face-liveness-prerequisites.html)
- [Cognito Identity Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/identity-pools.html)

---

**作成日:** 2026-02-11
**ステータス:** ✅ 完了
**デプロイ済み:** はい
