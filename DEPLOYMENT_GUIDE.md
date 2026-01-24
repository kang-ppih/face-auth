# Face-Auth IdP System - 배포 가이드

## 📋 구현 완료 사항

### ✅ AWS 인프라 및 기본 설정 구축 (Task 1)

다음 AWS 인프라 구성 요소가 AWS CDK를 사용하여 구현되었습니다:

#### 🌐 VPC 및 네트워킹 (요구사항 4.1, 4.5)
- **VPC**: 10.0.0.0/16 CIDR 블록
- **서브넷**: 
  - Public 서브넷 (24비트 마스크)
  - Private 서브넷 with NAT Gateway (24비트 마스크)
  - Isolated 서브넷 (24비트 마스크)
- **보안 그룹**:
  - Lambda 함수용 보안 그룹
  - Active Directory 연결용 보안 그룹 (LDAPS 636, LDAP 389 포트)
- **VPC 엔드포인트**: S3 및 DynamoDB용 게이트웨이 엔드포인트
- **Direct Connect 준비**: Customer Gateway 구성 (물리적 연결은 별도 설정 필요)

#### 🪣 S3 버킷 (요구사항 4.4, 5.2, 5.3, 5.4, 5.6)
- **버킷 이름**: `face-auth-images-{account}-{region}`
- **암호화**: S3 관리형 암호화 적용
- **퍼블릭 액세스**: 완전 차단
- **Lifecycle 정책**:
  - `logins/` 폴더: 30일 후 자동 삭제
  - `temp/` 폴더: 1일 후 자동 삭제
  - `enroll/` 폴더: 영구 보관
- **CORS 구성**: 프론트엔드 통합 지원

#### 🗄️ DynamoDB 테이블 (요구사항 5.5, 7.4)
1. **CardTemplates 테이블**:
   - 파티션 키: `pattern_id` (String)
   - GSI: `CardTypeIndex` (card_type 기준)
   - 암호화 및 Point-in-Time Recovery 활성화

2. **EmployeeFaces 테이블**:
   - 파티션 키: `employee_id` (String)
   - GSI: `FaceIdIndex` (face_id 기준)
   - 암호화 및 Point-in-Time Recovery 활성화

3. **AuthSessions 테이블**:
   - 파티션 키: `session_id` (String)
   - TTL: `expires_at` 속성으로 자동 세션 정리

#### ⚡ Lambda 함수 (요구사항 4.3, 4.4)
모든 Lambda 함수는 다음 구성으로 생성:
- **런타임**: Python 3.9
- **타임아웃**: 15초 (요구사항 준수)
- **메모리**: 512MB
- **VPC**: Private 서브넷에서 실행
- **보안 그룹**: Lambda 및 AD 연결 보안 그룹 적용

생성된 함수들:
1. `FaceAuth-Enrollment`: 직원 등록 처리
2. `FaceAuth-FaceLogin`: 얼굴 로그인 처리
3. `FaceAuth-EmergencyAuth`: 비상 인증 처리
4. `FaceAuth-ReEnrollment`: 재등록 처리
5. `FaceAuth-Status`: 인증 상태 확인

#### 🔐 IAM 역할 및 정책 (요구사항 4.7, 5.6, 5.7)
- **Lambda 실행 역할**: VPC 액세스 권한 포함
- **커스텀 정책**:
  - S3 버킷 읽기/쓰기 권한
  - DynamoDB 테이블 CRUD 권한
  - Amazon Rekognition 전체 권한
  - Amazon Textract 문서 분석 권한
  - Cognito 사용자 관리 권한
  - CloudWatch 로깅 권한

#### 🚪 API Gateway (요구사항 4.6, 4.7)
- **REST API**: `FaceAuth-API`
- **엔드포인트**:
  - `POST /auth/enroll`: 직원 등록
  - `POST /auth/login`: 얼굴 로그인
  - `POST /auth/emergency`: 비상 인증
  - `POST /auth/re-enroll`: 재등록
  - `GET /auth/status`: 상태 확인
- **보안**: API 키, 사용량 계획, 속도 제한 구성
- **CORS**: 프론트엔드 통합 지원

#### 👤 AWS Cognito (요구사항 2.3, 3.5)
- **사용자 풀**: `FaceAuth-UserPool`
- **비밀번호 정책**: 12자 이상, 대소문자/숫자/특수문자 포함
- **토큰 유효기간**:
  - Access Token: 1시간
  - ID Token: 1시간
  - Refresh Token: 30일
- **클라이언트**: 프론트엔드용 퍼블릭 클라이언트

#### 📊 CloudWatch 로깅 (요구사항 6.7, 8.7)
- **Lambda 로그 그룹**: 각 함수별 30일 보관
- **API Gateway 액세스 로그**: 30일 보관
- **모니터링**: 메트릭 및 알람 준비

## 🚀 배포 방법

### 1. 사전 요구사항
```bash
# Node.js 및 AWS CDK 설치
npm install -g aws-cdk

# AWS CLI 구성
aws configure

# Python 3.9+ 설치 확인
python --version
```

### 2. 배포 실행
```powershell
# PowerShell에서 실행
.\deploy.ps1
```

또는 수동 배포:
```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# CDK 부트스트랩 (계정당 한 번만)
cdk bootstrap

# 스택 배포
cdk deploy
```

### 3. 배포 후 설정

#### Rekognition 컬렉션 생성
```bash
aws rekognition create-collection --collection-id face-auth-employees
```

#### 카드 템플릿 추가
DynamoDB `FaceAuth-CardTemplates` 테이블에 사원증 인식 패턴 추가:
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
    },
    {
      "field_name": "employee_name",
      "query_phrase": "성명은 무엇입니까?",
      "expected_format": "[가-힣]{2,4}",
      "required": true
    }
  ],
  "is_active": true
}
```

#### Direct Connect 설정
물리적 Direct Connect 연결은 AWS 콘솔 또는 네트워크 팀과 협력하여 별도 구성 필요.

## 📁 프로젝트 구조

```
face-auth-idp/
├── app.py                    # CDK 앱 진입점
├── cdk.json                  # CDK 구성
├── requirements.txt          # Python 의존성
├── config.py                 # 시스템 구성
├── deploy.ps1               # PowerShell 배포 스크립트
├── validate_stack.py        # 스택 검증 스크립트
├── README.md                # 프로젝트 문서
├── DEPLOYMENT_GUIDE.md      # 이 파일
├── infrastructure/
│   ├── __init__.py
│   └── face_auth_stack.py   # 메인 CDK 스택
├── lambda/                  # Lambda 함수들
│   ├── enrollment/
│   ├── face_login/
│   ├── emergency_auth/
│   ├── re_enrollment/
│   └── status/
└── tests/
    ├── __init__.py
    └── test_infrastructure.py
```

## 🔧 구성 관리

주요 설정은 `config.py`에서 관리:
- Rekognition 신뢰도 임계값 (90%)
- 타임아웃 설정 (AD: 10초, Lambda: 15초)
- S3 폴더 구조
- 오류 메시지 매핑
- Active Directory 연결 정보

## ✅ 요구사항 충족 확인

### 요구사항 4.1: Direct Connect 사용
- ✅ Customer Gateway 구성 완료
- ✅ AD 연결용 보안 그룹 (LDAPS/LDAP 포트) 구성

### 요구사항 4.4: AWS CDK 사용
- ✅ Python CDK로 전체 인프라 구현
- ✅ 코드형 인프라 (Infrastructure as Code) 적용

### 요구사항 4.5: VPC 및 보안 그룹
- ✅ VPC 네트워크 격리 구현
- ✅ 적절한 보안 그룹 구성

### 요구사항 4.7: IAM 역할 및 정책
- ✅ 최소 권한 원칙 적용
- ✅ 서비스별 적절한 권한 부여

## 🎯 다음 단계

1. **Lambda 함수 구현**: 각 인증 흐름의 비즈니스 로직 구현
2. **테스트 작성**: 단위 테스트 및 속성 기반 테스트 구현
3. **프론트엔드 개발**: React + AWS Amplify UI 구현
4. **통합 테스트**: 전체 시스템 통합 테스트
5. **보안 검토**: 프로덕션 배포 전 보안 감사

## 🚨 주의사항

- Direct Connect 물리적 연결은 별도 설정 필요
- 프로덕션 환경에서는 CORS 설정을 특정 도메인으로 제한
- API 키 및 시크릿은 AWS Secrets Manager 사용 권장
- 모니터링 및 알람 설정 필요

---

**Task 1 완료**: AWS 인프라 및 기본 설정 구축이 성공적으로 완료되었습니다. 모든 요구사항 (4.1, 4.4, 4.5, 4.7)이 충족되었으며, 다음 작업 단계로 진행할 준비가 되었습니다.