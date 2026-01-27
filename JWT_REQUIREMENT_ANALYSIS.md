# JWT要件分析レポート

## 📋 分析概要

Face-Auth IdP SystemにおけるJWT（PyJWT）ライブラリの必要性を分析しました。

---

## 🔍 JWT使用状況

### 使用箇所

#### 1. cognito_service.py

**メソッド:** `validate_token(access_token: str)`

```python
def validate_token(self, access_token: str) -> Tuple[bool, Optional[Dict]]:
    """
    Validate a JWT access token
    
    Verifies:
    - Token signature using Cognito's public keys
    - Token expiration
    - Token issuer and audience
    """
    # Get the signing key from Cognito's JWKS
    signing_key = self.jwk_client.get_signing_key_from_jwt(access_token)
    
    # Decode and verify the token
    claims = jwt.decode(
        access_token,
        signing_key.key,
        algorithms=['RS256'],
        audience=self.client_id,
        issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
    )
    
    return True, claims
```

**依存ライブラリ:**
- `PyJWT` - JWT decode/encode
- `PyJWKClient` - Cognito公開鍵取得

---

#### 2. status Lambda関数

**ファイル:** `lambda/status/handler.py`

**使用箇所:**
```python
# Check 2: Validate Cognito token if access_token provided
if access_token:
    logger.info("Validating Cognito access token")
    is_valid, claims = cognito_service.validate_token(access_token)
    
    status_info['token_valid'] = is_valid
    
    if is_valid and claims:
        logger.info(f"Token is valid for user: {claims.get('username')}")
        status_info['authenticated'] = True
        status_info['employee_id'] = claims.get('username')
```

---

### 使用されていない箇所

以下のLambda関数では**JWT検証は使用されていません**：

- ❌ `lambda/enrollment/handler.py` - 社員登録
- ❌ `lambda/face_login/handler.py` - 顔認証ログイン
- ❌ `lambda/emergency_auth/handler.py` - 緊急認証
- ❌ `lambda/re_enrollment/handler.py` - 顔再登録

これらの関数は、Cognitoトークンを**生成**するのみで、**検証**はしません。

---

## 📊 システムアーキテクチャ分析

### 認証フロー

```
1. ユーザー認証（顔認証 or 緊急認証）
   ↓
2. Lambda関数が認証処理
   ↓
3. Cognito AdminInitiateAuth でトークン生成
   ↓
4. トークンをクライアントに返却
   ↓
5. クライアントがトークンを保持
   ↓
6. 以降のAPIリクエストでトークンを使用
```

### トークン検証の必要性

#### 現在の実装

- **トークン生成:** Cognito AdminInitiateAuth（boto3のみ）
- **トークン検証:** Status Lambda関数のみ（PyJWT必要）

#### 代替案

Cognitoトークンの検証は、以下の方法でも可能：

1. **API Gateway Cognito Authorizer**（推奨）
   - API Gatewayレベルでトークン検証
   - Lambda関数でJWT検証不要
   - AWS管理のため、ライブラリ不要

2. **boto3 AdminGetUser**
   - Cognitoユーザー情報を取得して検証
   - PyJWT不要
   - ただし、トークンの有効期限は直接確認できない

3. **DynamoDBセッション管理**
   - セッションIDベースの認証
   - トークン検証不要
   - 現在も実装済み

---

## 💡 推奨事項

### オプション1: JWT検証を削除（推奨）

**理由:**
- Status Lambda関数のトークン検証は**オプション機能**
- 主要な認証フローでは使用されていない
- セッションIDベースの認証で十分

**変更内容:**

#### 1. cognito_service.py を修正

```python
# JWT import を削除
# import jwt
# from jwt import PyJWKClient

class CognitoService:
    def __init__(self, user_pool_id: str, client_id: str, region: str = 'us-east-1'):
        self.cognito_client = boto3.client('cognito-idp', region_name=region)
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.region = region
        
        # JWT validation setup を削除
        # self.jwks_url = ...
        # self.jwk_client = ...
        
        self.session_duration_hours = int(os.getenv('SESSION_TIMEOUT_HOURS', '8'))
    
    def validate_token(self, access_token: str) -> Tuple[bool, Optional[Dict]]:
        """
        Validate a Cognito access token using boto3
        
        Alternative implementation without PyJWT
        """
        try:
            # Use Cognito GetUser API to validate token
            response = self.cognito_client.get_user(
                AccessToken=access_token
            )
            
            # Token is valid if GetUser succeeds
            username = response.get('Username')
            attributes = {attr['Name']: attr['Value'] for attr in response.get('UserAttributes', [])}
            
            claims = {
                'username': username,
                'attributes': attributes
            }
            
            logger.info(f"Token validated successfully for user: {username}")
            return True, claims
            
        except self.cognito_client.exceptions.NotAuthorizedException:
            logger.warning("Token validation failed: Not authorized")
            return False, None
            
        except Exception as e:
            logger.error(f"Unexpected error validating token: {str(e)}")
            return False, None
```

**メリット:**
- ✅ 外部ライブラリ不要
- ✅ デプロイパッケージが小さい
- ✅ メンテナンスが簡単
- ✅ Cognitoの公式APIを使用

**デメリット:**
- ⚠️ トークンの詳細なクレーム情報（exp, iat等）は取得できない
- ⚠️ オフライン検証ができない（Cognito APIを毎回呼び出す）

---

#### 2. status Lambda関数を修正

トークン検証部分はそのまま使用可能（boto3ベースの実装に変更）

---

### オプション2: JWT検証を維持

**理由:**
- トークンの詳細な検証が必要
- オフライン検証が必要
- 将来的に他のサービスでもトークン検証が必要

**必要な作業:**

#### 1. 外部ライブラリをバンドル

```powershell
# Status Lambda関数のみ
cd lambda\status
pip install PyJWT cryptography -t .
cd ..\..

# 再デプロイ
$env:ALLOWED_IPS="210.128.54.64/27"; npx cdk deploy --profile dev
```

**メリット:**
- ✅ 完全なJWT検証機能
- ✅ トークンの詳細情報取得可能
- ✅ オフライン検証可能

**デメリット:**
- ❌ 外部ライブラリの管理が必要
- ❌ デプロイパッケージが大きくなる
- ❌ ライブラリの脆弱性管理が必要

---

### オプション3: API Gateway Cognito Authorizer（最も推奨）

**理由:**
- AWS管理のため、ライブラリ不要
- Lambda関数でトークン検証不要
- パフォーマンスが良い

**実装方法:**

#### 1. CDKでCognito Authorizerを追加

```python
# infrastructure/face_auth_stack.py

# Cognito Authorizer作成
cognito_authorizer = apigateway.CognitoUserPoolsAuthorizer(
    self, "CognitoAuthorizer",
    cognito_user_pools=[self.user_pool]
)

# Status エンドポイントにAuthorizerを適用
status_resource.add_method(
    "GET",
    status_integration,
    authorizer=cognito_authorizer,
    authorization_type=apigateway.AuthorizationType.COGNITO
)
```

#### 2. Lambda関数を簡素化

```python
# lambda/status/handler.py

def handle_status(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    # API Gatewayが既にトークンを検証済み
    # event['requestContext']['authorizer']['claims'] からユーザー情報取得
    
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})
    employee_id = claims.get('username')
    
    # トークン検証不要！
    status_info = {
        'authenticated': True,  # API Gatewayが検証済み
        'employee_id': employee_id,
        ...
    }
```

**メリット:**
- ✅ Lambda関数でJWT検証不要
- ✅ 外部ライブラリ不要
- ✅ AWS管理のため、セキュリティが高い
- ✅ パフォーマンスが良い
- ✅ コードが簡潔

**デメリット:**
- ⚠️ Status エンドポイントが認証必須になる（現在はオプション）

---

## 🎯 最終推奨

### 短期的な対応（即座に実行可能）

**オプション1を採用: JWT検証をboto3ベースに変更**

**理由:**
- 外部ライブラリ不要
- 最小限のコード変更
- 即座にデプロイ可能

**実装手順:**
1. `cognito_service.py` の `validate_token` メソッドを修正
2. JWT import を削除
3. boto3 `get_user` APIを使用
4. 再デプロイ

**所要時間:** 10分

---

### 長期的な対応（推奨）

**オプション3を採用: API Gateway Cognito Authorizer**

**理由:**
- ベストプラクティス
- AWS管理のため、メンテナンスフリー
- セキュリティが高い
- パフォーマンスが良い

**実装手順:**
1. CDKでCognito Authorizerを追加
2. Status エンドポイントにAuthorizerを適用
3. Lambda関数を簡素化
4. 再デプロイ

**所要時間:** 30分

---

## 📝 結論

### JWT（PyJWT）は必要か？

**答え: いいえ、必須ではありません**

**理由:**
1. Status Lambda関数のみで使用（オプション機能）
2. boto3で代替可能
3. API Gateway Authorizerがより適切
4. 主要な認証フローでは不要

### 推奨アクション

**即座に実行:**
- ✅ オプション1を実装（boto3ベースのトークン検証）
- ✅ JWT依存を削除
- ✅ 再デプロイ

**将来的に実装:**
- ⏳ オプション3を実装（API Gateway Authorizer）
- ⏳ Lambda関数を簡素化

---

**作成日:** 2024年
**分析者:** Kiro AI Assistant
**ステータス:** ✅ 分析完了 - 実装推奨事項あり

