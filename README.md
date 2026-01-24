# Face-Auth IdP System

AWS 기반 Face-Auth Identity Provider 시스템은 사원증 기반 신뢰 체인과 Amazon Rekognition을 활용한 1:N 얼굴 인식을 통해 무패스워드 인증을 제공하는 엔터프라이즈급 직원 인증 시스템입니다.

## 🏗️ 아키텍처 개요

이 시스템은 다음과 같은 AWS 서비스를 사용합니다:

- **AWS CDK (Python)**: 인프라스트럭처 as 코드
- **Amazon VPC**: 네트워크 격리 및 보안
- **AWS Direct Connect**: 온프레미스 Active Directory 연결
- **Amazon S3**: 얼굴 이미지 저장 (lifecycle 정책 포함)
- **Amazon DynamoDB**: 카드 템플릿 및 직원 데이터 저장
- **AWS Lambda**: 인증 로직 처리
- **Amazon Rekognition**: 얼굴 인식 및 Liveness 감지
- **Amazon Textract**: 사원증 OCR 처리
- **AWS Cognito**: 사용자 세션 관리
- **Amazon API Gateway**: REST API 엔드포인트
- **Amazon CloudWatch**: 로깅 및 모니터링

## 🚀 빠른 시작

### 사전 요구사항

1. **AWS CLI 설치 및 구성**
   ```bash
   aws configure
   ```

2. **Node.js 및 AWS CDK 설치**
   ```bash
   npm install -g aws-cdk
   ```

3. **Python 3.9+ 설치**

### 배포 단계

1. **저장소 클론 및 의존성 설치**
   ```bash
   git clone <repository-url>
   cd face-auth-idp
   ```

2. **PowerShell에서 배포 실행**
   ```powershell
   .\deploy.ps1
   ```

   또는 수동으로:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   cdk bootstrap
   cdk deploy
   ```

3. **Rekognition 컬렉션 생성**
   ```bash
   aws rekognition create-collection --collection-id face-auth-employees
   ```

## 📋 구성 요소

### 인프라스트럭처 구성 요소

#### VPC 및 네트워킹
- **VPC**: 10.0.0.0/16 CIDR 블록
- **서브넷**: Public, Private, Isolated 서브넷 각 2개 AZ
- **보안 그룹**: Lambda 및 AD 연결용 보안 그룹
- **VPC 엔드포인트**: S3 및 DynamoDB용 게이트웨이 엔드포인트

#### 스토리지
- **S3 버킷**: 
  - `enroll/`: 등록 썸네일 (영구 보관)
  - `logins/`: 로그인 시도 이미지 (30일 자동 삭제)
  - `temp/`: 임시 처리 파일 (1일 자동 삭제)

#### 데이터베이스
- **CardTemplates**: 사원증 인식 패턴 저장
- **EmployeeFaces**: 직원 얼굴 데이터 메타데이터
- **AuthSessions**: 인증 세션 관리 (TTL 적용)

#### 컴퓨팅
- **Lambda 함수들**:
  - `FaceAuth-Enrollment`: 직원 등록
  - `FaceAuth-FaceLogin`: 얼굴 로그인
  - `FaceAuth-EmergencyAuth`: 비상 인증
  - `FaceAuth-ReEnrollment`: 재등록
  - `FaceAuth-Status`: 상태 확인

### API 엔드포인트

```
POST /auth/enroll      # 직원 등록
POST /auth/login       # 얼굴 로그인
POST /auth/emergency   # 비상 인증
POST /auth/re-enroll   # 재등록
GET  /auth/status      # 인증 상태 확인
```

## 🔧 구성

### 환경 변수

주요 구성은 `config.py` 파일에서 관리됩니다:

```python
FACE_AUTH_CONFIG = {
    'LIVENESS_CONFIDENCE_THRESHOLD': 90.0,
    'FACE_MATCH_CONFIDENCE_THRESHOLD': 95.0,
    'AD_CONNECTION_TIMEOUT': 10,
    'LAMBDA_TIMEOUT': 15,
    # ... 기타 설정
}
```

### Active Directory 연결

`config.py`에서 AD 설정을 업데이트하세요:

```python
AD_CONFIG = {
    'SERVER_URL': 'ldaps://your-ad-server.com',
    'BASE_DN': 'ou=employees,dc=yourcompany,dc=com',
    'TIMEOUT': 10,
    'USE_SSL': True,
    'PORT': 636
}
```

### 카드 템플릿 설정

DynamoDB의 CardTemplates 테이블에 사원증 인식 패턴을 추가하세요:

```json
{
  "pattern_id": "company_standard_v1",
  "card_type": "standard_employee",
  "logo_position": {"x": 50, "y": 30, "width": 100, "height": 50},
  "fields": [
    {
      "field_name": "employee_id",
      "query_phrase": "사번은 무엇입니까?",
      "expected_format": "\\d{6}",
      "required": true
    }
  ],
  "is_active": true
}
```

## 🔒 보안 고려사항

### 네트워크 보안
- VPC 내 격리된 환경에서 실행
- Direct Connect를 통한 안전한 온프레미스 연결
- 보안 그룹을 통한 트래픽 제어

### 데이터 보안
- S3 및 DynamoDB 암호화 (AWS 관리형 키)
- IAM 역할 기반 최소 권한 원칙
- API Gateway를 통한 접근 제어

### 인증 보안
- 90% 이상 Liveness 감지 신뢰도 요구
- 10초 AD 연결 타임아웃
- 15초 Lambda 실행 타임아웃
- 속도 제한 및 감사 로깅

## 📊 모니터링 및 로깅

### CloudWatch 로그 그룹
- `/aws/lambda/FaceAuth-*`: Lambda 함수 로그
- `/aws/apigateway/face-auth-access-logs`: API 접근 로그

### 메트릭 및 알람
- Lambda 실행 시간 및 오류율
- API Gateway 요청 수 및 지연시간
- DynamoDB 읽기/쓰기 용량

## 🧪 테스트

### 단위 테스트
```bash
pytest tests/unit/
```

### 통합 테스트
```bash
pytest tests/integration/
```

### 속성 기반 테스트
```bash
pytest tests/property/
```

## 📈 성능 최적화

### Lambda 최적화
- 512MB 메모리 할당
- VPC 내 실행으로 보안 강화
- 환경 변수를 통한 구성 관리

### DynamoDB 최적화
- Pay-per-request 요금 모델
- 글로벌 보조 인덱스 활용
- TTL을 통한 자동 데이터 정리

### S3 최적화
- Lifecycle 정책을 통한 자동 데이터 관리
- CORS 구성으로 프론트엔드 통합 지원

## 🚨 문제 해결

### 일반적인 문제

1. **CDK 배포 실패**
   - AWS 자격 증명 확인
   - 필요한 IAM 권한 확인
   - 리전별 서비스 가용성 확인

2. **Lambda 타임아웃**
   - VPC 구성 확인 (NAT Gateway 필요)
   - 보안 그룹 아웃바운드 규칙 확인

3. **Direct Connect 연결 문제**
   - 네트워크 팀과 협력하여 물리적 연결 확인
   - 라우팅 테이블 및 BGP 설정 확인

## 📚 추가 리소스

- [AWS CDK 문서](https://docs.aws.amazon.com/cdk/)
- [Amazon Rekognition 개발자 가이드](https://docs.aws.amazon.com/rekognition/)
- [Amazon Textract 개발자 가이드](https://docs.aws.amazon.com/textract/)
- [AWS Direct Connect 사용자 가이드](https://docs.aws.amazon.com/directconnect/)

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 🤝 기여

버그 리포트, 기능 요청, 풀 리퀘스트를 환영합니다.

---

**주의**: 이 시스템은 프로덕션 환경에서 사용하기 전에 철저한 보안 검토와 테스트가 필요합니다.