바이브 코딩 AI(Vibe Coding AI)가 시스템 전체를 한눈에 파악하고 즉시 코딩을 시작할 수 있도록 최적화된 마크다운(Markdown) 작업 지시서입니다.

이 내용을 복사하여 .md 파일로 저장하거나 AI 채팅창에 그대로 붙여넣으세요.

📄 Project Specification: Face-Auth IdP System (AWS \& Python)

1\. 개요 (Overview)

&nbsp;\* 목표: 사원증 기반의 신뢰 체인을 바탕으로 한 얼굴 인식(1:N) Passwordless 인증 시스템 구축.

&nbsp;\* 핵심 흐름: 1. 최초 등록/재등록: 사원증 OCR 인증 → 얼굴 등록.

&nbsp;  2. 일반 로그인: 얼굴 인식(1:N) → 성공 시 로그인.

&nbsp;  3. 비상 로그인: 얼굴 인식 실패 시 사원증 OCR + AD 비밀번호 인증.

2\. 기술 스택 (Tech Stack)

&nbsp;\* Infrastructure: AWS CDK (Python)

&nbsp;\* Backend: Python 3.9 (Boto3, ldap3, Pillow)

&nbsp;\* Frontend: React (AWS Amplify UI)

&nbsp;\* Services: Cognito, Rekognition, Textract, DynamoDB, S3, Direct Connect

3\. 핵심 요구사항 (Key Requirements)

A. 네트워크 및 보안

&nbsp;\* 연결: AWS Direct Connect를 통해 온프레미스 AD와 연결.

&nbsp;\* 타임아웃: AD 연결 및 인증 타임아웃은 10초로 제한 (전체 Lambda 타임아웃 15초).

&nbsp;\* Liveness: 모든 얼굴 캡처 시 Amazon Rekognition Liveness 적용 (Confidence > 90%).

B. 데이터 관리 정책 (S3 \& DynamoDB)

&nbsp;\* 이미지 보관:

&nbsp;  \* 등록/재등록 이미지: 원본 삭제 후 200x200 섬네일만 생성하여 영구 보관.

&nbsp;  \* 로그인 시도 이미지: 섬네일 변환 후 logins/ 폴더에 저장, 30일 후 자동 삭제 (S3 Lifecycle).

&nbsp;\* 사원증 관리: DynamoDB에 다중 사원증 패턴(로고 위치, Textract Query 문구 등)을 관리하여 확장성 확보.

C. 사용자 메시지 가이드

&nbsp;\* 시스템 판단 에러: "사원증 규격 불일치", "등록 정보 불일치", "계정 비활성화" 등 구체적 명시.

&nbsp;\* 기타 상황: "밝은 곳에서 다시 시도해주세요"로 통일.

4\. 파일 구조 및 샘플 코드 (File Structure \& Code)

📂 infra/auth\_stack.py (AWS CDK)

from aws\_cdk import (

&nbsp;   Stack, aws\_cognito as cognito, aws\_lambda as \_lambda,

&nbsp;   aws\_s3 as s3, aws\_dynamodb as dynamodb, aws\_ec2 as ec2, Duration

)



class FaceAuthStack(Stack):

&nbsp;   def \_\_init\_\_(self, scope, id, \*\*kwargs):

&nbsp;       super().\_\_init\_\_(scope, id, \*\*kwargs)



&nbsp;       # 1. VPC \& Direct Connect Security Group

&nbsp;       vpc = ec2.Vpc.from\_lookup(self, "ExistingVpc", vpc\_id="vpc-xxxx") # DX 연결 전제



&nbsp;       # 2. S3 Bucket with Lifecycle Policy

&nbsp;       bucket = s3.Bucket(self, "FaceAuthAssets",

&nbsp;           lifecycle\_rules=\[s3.LifecycleRule(

&nbsp;               prefix="logins/",

&nbsp;               expiration=Duration.days(30)

&nbsp;           )]

&nbsp;       )



&nbsp;       # 3. DynamoDB for Templates \& User Mapping

&nbsp;       template\_table = dynamodb.Table(self, "IDCardTemplates",

&nbsp;           partition\_key=dynamodb.Attribute(name="pattern\_id", type=dynamodb.AttributeType.STRING))



&nbsp;       # 4. Auth Lambda (VPC Configured)

&nbsp;       auth\_handler = \_lambda.Function(self, "AuthHandler",

&nbsp;           runtime=\_lambda.Runtime.PYTHON\_3\_9,

&nbsp;           handler="handler.main",

&nbsp;           code=\_lambda.Code.from\_asset("lambda"),

&nbsp;           vpc=vpc,

&nbsp;           timeout=Duration.seconds(15)

&nbsp;       )



📂 lambda/handler.py (Backend Logic Snippet)

import boto3

from ldap3 import Server, Connection, ALL

from image\_utils import process\_thumbnail



def verify\_ad\_password(user\_id, password):

&nbsp;   # Direct Connect를 통한 AD 인증 (10초 타임아웃)

&nbsp;   try:

&nbsp;       server = Server('ldaps://your-ad-server', get\_info=ALL, connect\_timeout=10)

&nbsp;       with Connection(server, user=f'uid={user\_id},ou=users,dc=company', password=password) as conn:

&nbsp;           return conn.bind()

&nbsp;   except Exception:

&nbsp;       return False



def main(event, context):

&nbsp;   # logic: 1. Mode Check -> 2. Process Image -> 3. Rekognition/Textract -> 4. Respond

&nbsp;   pass



📂 frontend/App.js (Minimal React UI)

import React, { useState } from 'react';

import { FaceLivenessDetector } from '@aws-amplify/ui-react-ai';



function AuthPage() {

&nbsp; const \[mode, setMode] = useState('LOGIN'); // LOGIN, ENROLL, ID\_SCAN



&nbsp; return (

&nbsp;   <div className="auth-container">

&nbsp;     {mode === 'LOGIN' \&\& (

&nbsp;       <FaceLivenessDetector 

&nbsp;         onAnalysisComplete={async (res) => { /\* 얼굴 인식 로직 \*/ }}

&nbsp;         onError={(err) => alert("밝은 곳에서 다시 시도해주세요.")}

&nbsp;       />

&nbsp;     )}

&nbsp;     <button onClick={() => setMode('ID\_SCAN')}>사원증으로 인증/등록</button>

&nbsp;   </div>

&nbsp; );

}



5\. AI 작업 지시 사항 (Action Items for AI)

&nbsp;\* AD 연동 심화: ldap3를 사용하여 VPC 환경 내에서 AD 계정 상태(활성/비활성)를 체크하는 로직을 완성해줘.

&nbsp;\* 사원증 패턴 처리: DynamoDB에서 사원증 패턴 정보를 읽어와 Amazon Textract Queries를 동적으로 구성하는 기능을 구현해줘.

&nbsp;\* 이미지 처리: Pillow를 사용하여 이미지를 200x200 크기로 리사이징하고 S3의 적절한 경로(enroll/ 또는 logins/)에 저장하는 유틸리티를 작성해줘.

&nbsp;\* 에러 핸들링: 백엔드 응답 시 system\_reason과 user\_message를 분리하여 프론트엔드에 전달하는 구조를 설계해줘.

📥 마크다운 파일 활용 방법

&nbsp;\* 위 내용을 복사하여 face\_auth\_spec.md 파일로 저장하세요.

&nbsp;\* 바이브 코딩 AI에게 이 파일을 업로드하며 \*\*"이 사양서대로 전체 프로젝트 구조를 잡고 파이썬 코드를 작성해줘"\*\*라고 지시하세요.

추가로 특정 기능(예: 상세 LDAP 쿼리, 사원증 인식용 Textract Query 설정 등)에 대한 코드가 더 필요하시면 말씀해 주세요!



