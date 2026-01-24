# Face-Auth 로컬 실행 가이드

## 개요

이 가이드는 Face-Auth IdP 시스템을 로컬 환경에서 실행하는 방법을 설명합니다.

## 전제 조건

### 1. Python 환경
```bash
python --version  # Python 3.9 이상 필요
```

### 2. 필수 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. AWS 계정 및 자격 증명
- AWS 계정 필요
- IAM 사용자 생성 및 액세스 키 발급

---

## AWS 자격 증명 설정

### 방법 1: AWS CLI 사용 (권장)

#### 1.1 AWS CLI 설치
```bash
# Windows (PowerShell)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# 설치 확인
aws --version
```

#### 1.2 AWS 자격 증명 구성
```bash
aws configure
```

입력 정보:
```
AWS Access Key ID [None]: YOUR_ACCESS_KEY_ID
AWS Secret Access Key [None]: YOUR_SECRET_ACCESS_KEY
Default region name [None]: us-east-1
Default output format [None]: json
```

#### 1.3 자격 증명 확인
```bash
aws sts get-caller-identity
```

성공 시 출력:
```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

### 방법 2: 환경 변수 설정

#### Windows (PowerShell)
```powershell
$env:AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY"
$env:AWS_DEFAULT_REGION="us-east-1"
```

#### 영구 설정 (시스템 환경 변수)
1. 시스템 속성 → 환경 변수
2. 새로 만들기:
   - `AWS_ACCESS_KEY_ID`: YOUR_ACCESS_KEY_ID
   - `AWS_SECRET_ACCESS_KEY`: YOUR_SECRET_ACCESS_KEY
   - `AWS_DEFAULT_REGION`: us-east-1

---

## AWS 리소스 생성

### 1. S3 버킷 생성
```bash
aws s3 mb s3://face-auth-dev-bucket --region us-east-1
```

### 2. DynamoDB 테이블 생성
```bash
# CardTemplates 테이블
aws dynamodb create-table \
    --table-name CardTemplates \
    --attribute-definitions AttributeName=pattern_id,AttributeType=S \
    --key-schema AttributeName=pattern_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# EmployeeFaces 테이블
aws dynamodb create-table \
    --table-name EmployeeFaces \
    --attribute-definitions AttributeName=employee_id,AttributeType=S \
    --key-schema AttributeName=employee_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# AuthSessions 테이블 (TTL 포함)
aws dynamodb create-table \
    --table-name AuthSessions \
    --attribute-definitions AttributeName=session_id,AttributeType=S \
    --key-schema AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# TTL 활성화
aws dynamodb update-time-to-live \
    --table-name AuthSessions \
    --time-to-live-specification "Enabled=true, AttributeName=expires_at" \
    --region us-east-1
```

### 3. Cognito User Pool 생성
```bash
# User Pool 생성
aws cognito-idp create-user-pool \
    --pool-name face-auth-users \
    --policies "PasswordPolicy={MinimumLength=8,RequireUppercase=false,RequireLowercase=false,RequireNumbers=false,RequireSymbols=false}" \
    --region us-east-1

# User Pool ID 저장 (출력에서 확인)
# 예: us-east-1_XXXXXXXXX

# App Client 생성
aws cognito-idp create-user-pool-client \
    --user-pool-id us-east-1_XXXXXXXXX \
    --client-name face-auth-client \
    --explicit-auth-flows ADMIN_NO_SRP_AUTH \
    --region us-east-1

# Client ID 저장 (출력에서 확인)
```

### 4. Rekognition Collection 생성
```bash
aws rekognition create-collection \
    --collection-id face-auth-employees \
    --region us-east-1
```

---

## 환경 변수 설정

### 로컬 실행용 환경 변수 파일 생성

`.env` 파일 생성:
```bash
# AWS 설정
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=YOUR_SECRET_ACCESS_KEY

# S3 설정
FACE_AUTH_BUCKET=face-auth-dev-bucket

# DynamoDB 설정
CARD_TEMPLATES_TABLE=CardTemplates
EMPLOYEE_FACES_TABLE=EmployeeFaces
AUTH_SESSIONS_TABLE=AuthSessions

# Cognito 설정
COGNITO_USER_POOL_ID=us-east-1_XXXXXXXXX
COGNITO_CLIENT_ID=your-client-id

# Rekognition 설정
REKOGNITION_COLLECTION_ID=face-auth-employees

# 세션 설정
SESSION_TIMEOUT_HOURS=8
```

### 환경 변수 로드 (PowerShell)
```powershell
# .env 파일에서 환경 변수 로드
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
    }
}
```

---

## 초기 데이터 설정

### 1. 카드 템플릿 초기화
```bash
python scripts/init_dynamodb.py
```

이 스크립트는 기본 카드 템플릿을 DynamoDB에 생성합니다.

### 2. 데이터 모델 데모 실행
```bash
python scripts/demo_data_models.py
```

---

## 로컬 테스트 실행

### 1. 단위 테스트 (AWS 불필요)
```bash
python -m pytest tests/ --ignore=tests/test_ad_connector.py -v
```

### 2. 통합 테스트 (AWS 필요)
```bash
# 환경 변수 설정 후
python -m pytest tests/test_backend_integration.py -v
```

---

## Lambda 핸들러 로컬 테스트

### 테스트 스크립트 생성

`test_local_handler.py` 파일 생성:
```python
import os
import sys
import json
import base64

# 환경 변수 설정
os.environ['FACE_AUTH_BUCKET'] = 'face-auth-dev-bucket'
os.environ['CARD_TEMPLATES_TABLE'] = 'CardTemplates'
os.environ['EMPLOYEE_FACES_TABLE'] = 'EmployeeFaces'
os.environ['AUTH_SESSIONS_TABLE'] = 'AuthSessions'
os.environ['COGNITO_USER_POOL_ID'] = 'us-east-1_XXXXXXXXX'
os.environ['COGNITO_CLIENT_ID'] = 'your-client-id'
os.environ['REKOGNITION_COLLECTION_ID'] = 'face-auth-employees'
os.environ['AWS_REGION'] = 'us-east-1'

# Lambda 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lambda'))

from enrollment.handler import handle_enrollment

# Mock context
class MockContext:
    aws_request_id = 'test-request-id'
    function_name = 'test-function'
    memory_limit_in_mb = 512
    invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:test'

# 테스트 이미지 (1x1 픽셀 PNG)
test_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01').decode()

# 테스트 이벤트
event = {
    'body': json.dumps({
        'id_card_image': test_image,
        'face_image': test_image
    }),
    'requestContext': {
        'identity': {
            'sourceIp': '127.0.0.1'
        }
    },
    'headers': {
        'User-Agent': 'Test/1.0'
    }
}

# 핸들러 실행
context = MockContext()
response = handle_enrollment(event, context)

print(json.dumps(json.loads(response['body']), indent=2, ensure_ascii=False))
```

### 실행
```bash
python test_local_handler.py
```

---

## IAM 권한 설정

로컬 실행을 위한 최소 IAM 권한:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": "arn:aws:s3:::face-auth-dev-bucket/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:us-east-1:*:table/CardTemplates",
                "arn:aws:dynamodb:us-east-1:*:table/EmployeeFaces",
                "arn:aws:dynamodb:us-east-1:*:table/AuthSessions"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:AdminCreateUser",
                "cognito-idp:AdminGetUser",
                "cognito-idp:AdminInitiateAuth",
                "cognito-idp:AdminSetUserPassword",
                "cognito-idp:AdminEnableUser",
                "cognito-idp:AdminDisableUser",
                "cognito-idp:AdminUserGlobalSignOut"
            ],
            "Resource": "arn:aws:cognito-idp:us-east-1:*:userpool/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "rekognition:CreateCollection",
                "rekognition:DeleteCollection",
                "rekognition:DetectFaces",
                "rekognition:IndexFaces",
                "rekognition:SearchFacesByImage",
                "rekognition:DeleteFaces",
                "rekognition:ListFaces"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "textract:AnalyzeDocument"
            ],
            "Resource": "*"
        }
    ]
}
```

---

## 비용 관리

### 예상 비용 (개발/테스트 환경)

- **S3**: 거의 무료 (GB당 $0.023)
- **DynamoDB**: 무료 티어 (25GB, 25 읽기/쓰기 단위)
- **Cognito**: 무료 티어 (월 50,000 MAU)
- **Rekognition**: 
  - 얼굴 감지: 1,000건당 $1.00
  - 얼굴 검색: 1,000건당 $1.00
- **Textract**: 1,000페이지당 $1.50

### 비용 절감 팁

1. **테스트 후 리소스 삭제**
```bash
# S3 버킷 비우기 및 삭제
aws s3 rm s3://face-auth-dev-bucket --recursive
aws s3 rb s3://face-auth-dev-bucket

# DynamoDB 테이블 삭제
aws dynamodb delete-table --table-name CardTemplates
aws dynamodb delete-table --table-name EmployeeFaces
aws dynamodb delete-table --table-name AuthSessions

# Rekognition Collection 삭제
aws rekognition delete-collection --collection-id face-auth-employees

# Cognito User Pool 삭제
aws cognito-idp delete-user-pool --user-pool-id us-east-1_XXXXXXXXX
```

2. **개발 시간 제한**
   - 필요할 때만 리소스 생성
   - 사용 후 즉시 삭제

3. **무료 티어 모니터링**
   - AWS Billing Dashboard에서 사용량 확인

---

## 문제 해결

### 1. 자격 증명 오류
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**해결:**
```bash
aws configure
# 또는
$env:AWS_ACCESS_KEY_ID="YOUR_KEY"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET"
```

### 2. 권한 오류
```
botocore.exceptions.ClientError: An error occurred (AccessDenied)
```

**해결:**
- IAM 사용자에 필요한 권한 추가
- 위의 IAM 권한 정책 참조

### 3. 리전 오류
```
botocore.exceptions.ClientError: The specified bucket does not exist
```

**해결:**
```bash
$env:AWS_DEFAULT_REGION="us-east-1"
```

### 4. Rekognition Collection 없음
```
InvalidParameterException: Collection face-auth-employees not found
```

**해결:**
```bash
aws rekognition create-collection --collection-id face-auth-employees
```

---

## 다음 단계

1. ✅ AWS 자격 증명 설정
2. ✅ AWS 리소스 생성
3. ✅ 환경 변수 설정
4. ✅ 초기 데이터 설정
5. ✅ 로컬 테스트 실행
6. 🔄 Lambda 핸들러 테스트
7. 🔄 프론트엔드 개발
8. 🔄 AWS 배포

---

## 참고 자료

- [AWS CLI 설치 가이드](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [AWS 자격 증명 구성](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [boto3 자격 증명](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)
- [AWS 무료 티어](https://aws.amazon.com/free/)

---

**작성일:** 2024
**버전:** 1.0
