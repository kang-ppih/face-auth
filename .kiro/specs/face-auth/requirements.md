# 요구사항 문서

## 소개

Face-Auth IdP 시스템은 사원증 기반 신뢰 체인을 바탕으로 한 얼굴 인식(1:N) 무패스워드 인증을 제공하는 AWS 기반 직원 인증 시스템입니다. 이 시스템은 세 가지 인증 흐름을 지원합니다: 사원증 OCR 인증 후 얼굴 등록을 통한 최초 등록/재등록, 얼굴 인식(1:N)을 통한 일반 로그인, 얼굴 인식 실패 시 사원증 OCR + AD 비밀번호를 통한 비상 로그인.

## 용어집

- **Face_Auth_IdP_System**: AWS 기반 완전한 직원 얼굴 인증 신원 제공자 시스템
- **Employee**: 시스템에 등록하고 인증하는 개별 직원
- **Employee_ID_Card**: OCR 기반 인증에 사용되는 물리적 직원 신분증
- **Face_Data**: 인증을 위해 추출되고 저장되는 생체 얼굴 특징 (200x200 썸네일)
- **Authentication_Session**: 성공적인 인증 후 생성되는 시간 제한 세션
- **Face_Capture**: Amazon Rekognition Liveness를 사용한 얼굴 이미지 데이터 캡처 과정
- **Face_Matcher**: 1:N 얼굴 매칭을 수행하는 Amazon Rekognition 구성 요소
- **Enrollment**: ID 카드 확인 후 직원의 얼굴 데이터를 등록하는 과정
- **Re_Enrollment**: 기존 직원의 얼굴 데이터를 업데이트하는 과정
- **Liveness_Detection**: 캡처된 얼굴이 실제 사람의 것임을 보장하는 Amazon Rekognition Liveness 기술 (신뢰도 > 90%)
- **OCR_Engine**: 직원 ID 카드 텍스트 추출을 위한 Amazon Textract 구성 요소
- **AD_Connector**: 온프레미스 Active Directory와 AWS Direct Connect 인증을 관리하는 구성 요소
- **Card_Template**: ID 카드 인식을 위한 로고 위치와 Textract Query 문구를 정의하는 DynamoDB 저장 패턴
- **Thumbnail_Processor**: 원본 이미지에서 200x200 픽셀 썸네일을 생성하는 구성 요소
- **Login_Attempt_Image**: 30일 자동 삭제와 함께 logins/ 폴더에 저장되는 로그인 중 얼굴 캡처

## 요구사항

### 요구사항 1: 직원 신분증 인증 및 등록

**사용자 스토리:** 신규 직원으로서, 먼저 직원 신분증으로 신원을 확인한 후 향후 무패스워드 인증을 위해 얼굴을 등록하고 싶습니다.

#### 수락 기준

1. WHEN 직원이 등록을 시작하면, THE Face_Auth_IdP_System SHALL OCR_Engine을 사용하여 직원 신분증을 캡처하고 처리한다
2. WHEN 직원 신분증이 캡처되면, THE OCR_Engine SHALL DynamoDB의 Card_Template 패턴을 사용하여 직원 정보를 추출한다
3. WHEN OCR 추출이 성공하면, THE AD_Connector SHALL 10초 이내에 온프레미스 Active Directory에 대해 직원 정보를 확인한다
4. WHEN AD 확인이 성공하면, THE Face_Auth_IdP_System SHALL Liveness_Detection을 사용한 얼굴 캡처를 진행한다
5. WHEN 신뢰도 > 90%로 얼굴 캡처가 완료되면, THE Face_Auth_IdP_System SHALL 200x200 썸네일을 생성하고 S3 enroll/ 폴더에 저장한다
6. IF 직원 신분증 형식이 어떤 Card_Template과도 일치하지 않으면, THEN THE Face_Auth_IdP_System SHALL "사원증 규격 불일치" 메시지를 반환한다
7. IF 직원 정보가 AD 기록과 일치하지 않으면, THEN THE Face_Auth_IdP_System SHALL "등록 정보 불일치" 메시지를 반환한다
8. IF AD 계정이 비활성화되어 있으면, THEN THE Face_Auth_IdP_System SHALL "계정 비활성화" 메시지를 반환한다

### 요구사항 2: 얼굴 인식 로그인 (1:N 인증)

**사용자 스토리:** 등록된 직원으로서, 자격 증명을 입력하지 않고 얼굴만으로 인증하여 시스템에 빠르고 안전하게 접근하고 싶습니다.

#### 수락 기준

1. WHEN 직원이 얼굴 로그인을 시작하면, THE Face_Auth_IdP_System SHALL Liveness_Detection으로 얼굴 이미지를 캡처한다
2. WHEN 신뢰도 > 90%로 얼굴 이미지가 캡처되면, THE Face_Matcher SHALL 모든 등록된 Face_Data에 대해 1:N 매칭을 수행한다
3. WHEN 높은 신뢰도로 얼굴 매칭이 성공하면, THE Face_Auth_IdP_System SHALL AWS Cognito를 통해 Authentication_Session을 생성한다
4. WHEN 얼굴 매칭이 실패하면, THE Face_Auth_IdP_System SHALL 30일 보관을 위해 S3 logins/ 폴더에 Login_Attempt_Image를 저장한다
5. WHEN 인증이 성공하면, THE Face_Auth_IdP_System SHALL 보호된 리소스에 대한 접근을 허용한다
6. WHEN 얼굴 인식이 실패하면, THE Face_Auth_IdP_System SHALL 비상 로그인 옵션을 제공한다
7. IF Liveness_Detection이 실패하거나 기타 기술적 문제가 발생하면, THEN THE Face_Auth_IdP_System SHALL "밝은 곳에서 다시 시도해주세요" 메시지를 표시한다

### 요구사항 3: 신분증 및 비밀번호를 통한 비상 인증

**사용자 스토리:** 얼굴 인식이 실패한 직원으로서, 얼굴 인증이 작동하지 않을 때도 시스템에 접근할 수 있도록 직원 신분증과 AD 비밀번호를 사용하여 인증하고 싶습니다.

#### 수락 기준

1. WHEN 얼굴 인식이 반복적으로 실패하면, THE Face_Auth_IdP_System SHALL 비상 인증 옵션을 제공한다
2. WHEN 비상 인증이 시작되면, THE Face_Auth_IdP_System SHALL OCR_Engine을 사용하여 직원 신분증을 캡처하고 처리한다
3. WHEN ID 카드 OCR이 성공하면, THE Face_Auth_IdP_System SHALL AD 비밀번호 입력을 요청한다
4. WHEN AD 자격 증명이 제공되면, THE AD_Connector SHALL 10초 이내에 온프레미스 Active Directory에 대해 인증한다
5. WHEN AD 인증이 성공하면, THE Face_Auth_IdP_System SHALL AWS Cognito를 통해 Authentication_Session을 생성한다
6. IF AD 인증이 실패하면, THEN THE Face_Auth_IdP_System SHALL 보안을 위해 속도 제한을 구현한다
7. IF 어떤 단계든 실패하면, THEN THE Face_Auth_IdP_System SHALL "밝은 곳에서 다시 시도해주세요" 메시지를 표시한다

### 요구사항 4: AWS 인프라 및 네트워크 보안

**사용자 스토리:** 시스템 관리자로서, 직원 데이터와 인증 프로세스가 보호되도록 온프레미스 시스템과의 적절한 네트워크 연결을 통해 AWS 인프라 내에서 시스템이 안전하게 작동하기를 원합니다.

#### 수락 기준

1. THE Face_Auth_IdP_System SHALL 온프레미스 Active Directory에 대한 보안 연결을 위해 AWS Direct Connect를 사용한다
2. WHEN AD 인증이 수행되면, THE AD_Connector SHALL 10초 타임아웃 제한 내에 완료한다
3. WHEN Lambda 함수가 실행되면, THE Face_Auth_IdP_System SHALL 총 15초 타임아웃 내에 모든 작업을 완료한다
4. THE Face_Auth_IdP_System SHALL 코드형 인프라를 위해 Python과 함께 AWS CDK를 사용하여 배포한다
5. THE Face_Auth_IdP_System SHALL 네트워크 격리를 위해 적절한 보안 그룹과 함께 AWS VPC를 사용한다
6. WHEN 데이터가 전송되면, THE Face_Auth_IdP_System SHALL 모든 통신에 암호화된 연결을 사용한다
7. THE Face_Auth_IdP_System SHALL 서비스 접근 제어를 위해 적절한 IAM 역할과 정책을 구현한다

### 요구사항 5: 데이터 관리 및 저장 정책

**사용자 스토리:** 시스템 관리자로서, 보안과 규정 준수를 유지하면서 저장 비용을 최적화할 수 있도록 얼굴 이미지와 직원 데이터에 대한 적절한 데이터 수명 주기 관리를 원합니다.

#### 수락 기준

1. WHEN 등록 이미지가 처리되면, THE Thumbnail_Processor SHALL 200x200 픽셀 썸네일을 생성하고 원본 이미지를 삭제한다
2. WHEN 등록이 완료되면, THE Face_Auth_IdP_System SHALL S3 enroll/ 폴더에 썸네일을 영구적으로 저장한다
3. WHEN 로그인 시도가 발생하면, THE Face_Auth_IdP_System SHALL 이미지를 썸네일로 변환하고 S3 logins/ 폴더에 저장한다
4. THE Face_Auth_IdP_System SHALL S3 Lifecycle 정책을 사용하여 30일 후 Login_Attempt_Images를 자동으로 삭제한다
5. WHEN 직원 신분증이 처리되면, THE Face_Auth_IdP_System SHALL DynamoDB에 여러 Card_Template 패턴을 저장한다
6. THE Face_Auth_IdP_System SHALL AWS 암호화 표준을 사용하여 모든 저장된 Face_Data를 암호화한다
7. WHEN Face_Data에 접근하면, THE Face_Auth_IdP_System SHALL 적절한 접근 제어와 감사 로깅을 구현한다

### 요구사항 6: Amazon Rekognition 통합 및 Liveness 감지

**사용자 스토리:** 보안 관리자로서, 실제 직원만 성공적으로 인증할 수 있도록 스푸핑 공격을 방지하는 강력한 얼굴 인식과 liveness 감지를 원합니다.

#### 수락 기준

1. WHEN 얼굴 캡처가 발생하면, THE Face_Auth_IdP_System SHALL Amazon Rekognition Liveness 감지를 사용한다
2. WHEN Liveness_Detection이 수행되면, THE Face_Auth_IdP_System SHALL 90%보다 큰 신뢰도 점수를 요구한다
3. WHEN liveness 검사가 실패하면, THE Face_Auth_IdP_System SHALL 인증 시도를 거부한다
4. WHEN 얼굴 매칭이 수행되면, THE Face_Matcher SHALL 1:N 비교를 위해 Amazon Rekognition을 사용한다
5. THE Face_Auth_IdP_System SHALL 등록된 직원에 대해 95% 이상의 얼굴 인식 정확도를 유지한다
6. WHEN 여러 인증 실패가 발생하면, THE Face_Auth_IdP_System SHALL 점진적 속도 제한을 구현한다
7. THE Face_Auth_IdP_System SHALL 타임스탬프와 신뢰도 점수와 함께 모든 인증 시도를 기록한다

### 요구사항 7: 직원 신분증 처리 및 템플릿 관리

**사용자 스토리:** 시스템 관리자로서, 시스템이 다양한 직원 카드 디자인에 걸쳐 확장할 수 있도록 다양한 카드 형식과 레이아웃을 처리할 수 있는 유연한 ID 카드 인식을 원합니다.

#### 수락 기준

1. WHEN ID 카드가 처리되면, THE OCR_Engine SHALL 텍스트 추출을 위해 Amazon Textract를 사용한다
2. WHEN Textract 처리가 발생하면, THE Face_Auth_IdP_System SHALL DynamoDB의 Card_Template 패턴을 사용한다
3. WHEN 새로운 카드 형식이 도입되면, THE Face_Auth_IdP_System SHALL 여러 Card_Template 구성을 지원한다
4. THE Face_Auth_IdP_System SHALL Card_Template 레코드에 로고 위치와 Textract Query 문구를 저장한다
5. WHEN OCR이 어떤 템플릿과도 일치하지 않으면, THE Face_Auth_IdP_System SHALL 특정 "사원증 규격 불일치" 오류를 반환한다
6. THE Face_Auth_IdP_System SHALL 카드 패턴을 기반으로 한 동적 Textract Query 구성을 지원한다
7. WHEN 카드 템플릿이 업데이트되면, THE Face_Auth_IdP_System SHALL 시스템 재시작 없이 변경 사항을 적용한다

### 요구사항 8: 오류 처리 및 사용자 메시징

**사용자 스토리:** 시스템을 사용하는 직원으로서, 인증이 실패할 때 무엇이 잘못되었는지와 어떻게 해결할지 이해할 수 있도록 명확하고 도움이 되는 오류 메시지를 원합니다.

#### 수락 기준

1. WHEN 시스템 판단 오류가 발생하면, THE Face_Auth_IdP_System SHALL 구체적인 오류 메시지를 제공한다
2. WHEN ID 카드 형식이 인식되지 않으면, THE Face_Auth_IdP_System SHALL "사원증 규격 불일치"를 표시한다
3. WHEN 직원 데이터가 AD 기록과 일치하지 않으면, THE Face_Auth_IdP_System SHALL "등록 정보 불일치"를 표시한다
4. WHEN AD 계정이 비활성 상태이면, THE Face_Auth_IdP_System SHALL "계정 비활성화"를 표시한다
5. WHEN 기술적 문제(조명, 카메라, 네트워크)가 발생하면, THE Face_Auth_IdP_System SHALL "밝은 곳에서 다시 시도해주세요"를 표시한다
6. THE Face_Auth_IdP_System SHALL system_reason(로깅용)과 user_message(표시용)를 분리한다
7. WHEN 오류가 기록되면, THE Face_Auth_IdP_System SHALL 문제 해결을 위한 상세한 기술 정보를 포함한다

### 요구사항 9: 재등록 및 얼굴 데이터 업데이트

**사용자 스토리:** 등록된 직원으로서, 외모가 크게 변했을 때 얼굴 인증을 계속 안정적으로 사용할 수 있도록 얼굴 데이터를 업데이트하고 싶습니다.

#### 수락 기준

1. WHEN 직원이 재등록을 요청하면, THE Face_Auth_IdP_System SHALL 직원 신분증 OCR을 사용하여 신원을 확인한다
2. WHEN 재등록 ID 확인이 성공하면, THE Face_Auth_IdP_System SHALL 새로운 얼굴 캡처를 진행한다
3. WHEN 새로운 얼굴 데이터가 캡처되면, THE Face_Auth_IdP_System SHALL 기존 Face_Data를 새로운 썸네일로 교체한다
4. WHEN 재등록이 완료되면, THE Face_Auth_IdP_System SHALL 직원에게 성공적인 업데이트를 확인한다
5. THE Face_Auth_IdP_System SHALL 모든 재등록 활동의 감사 추적을 유지한다
6. WHEN 재등록이 실패하면, THE Face_Auth_IdP_System SHALL 기존 Face_Data를 변경하지 않고 보존한다
7. THE Face_Auth_IdP_System SHALL 재등록을 허용하기 전에 추가 인증을 요구한다

### 요구사항 10: 프론트엔드 통합 및 사용자 인터페이스

**사용자 스토리:** 직원으로서, 다양한 장치와 브라우저에서 안정적으로 작동하는 직관적인 웹 인터페이스를 통해 시스템에 쉽게 접근할 수 있기를 원합니다.

#### 수락 기준

1. THE Face_Auth_IdP_System SHALL AWS Amplify UI 구성 요소를 사용하는 React 기반 프론트엔드를 제공한다
2. WHEN 얼굴 캡처가 필요하면, THE Face_Auth_IdP_System SHALL FaceLivenessDetector 구성 요소를 사용한다
3. WHEN 인증 모드가 선택되면, THE Face_Auth_IdP_System SHALL LOGIN, ENROLL, ID_SCAN 모드를 지원한다
4. THE Face_Auth_IdP_System SHALL 얼굴 캡처 과정 중 실시간 피드백을 제공한다
5. WHEN 오류가 발생하면, THE Face_Auth_IdP_System SHALL 인터페이스에 적절한 사용자 메시지를 표시한다
6. THE Face_Auth_IdP_System SHALL 다양한 장치와 카메라 구성에서 작동한다
7. WHEN 인증이 성공하면, THE Face_Auth_IdP_System SHALL 적절한 보호된 리소스로 리디렉션한다