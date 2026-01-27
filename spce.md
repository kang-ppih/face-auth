Vibe Coding AIがシステム全体を一目で把握し、すぐにコーディングを開始できるように最適化されたMarkdown作業指示書です。

この内容をコピーして.mdファイルとして保存するか、AIチャットウィンドウにそのまま貼り付けてください。

📄 Project Specification: Face-Auth IdP System (AWS \& Python)

1\. 概要 (Overview)

&nbsp;\* 目標: 社員証ベースの信頼チェーンに基づく顔認識(1:N) Passwordless認証システム構築。

&nbsp;\* 核心フロー: 1. 初回登録/再登録: 社員証OCR認証 → 顔登録。

&nbsp;  2. 一般ログイン: 顔認識(1:N) → 成功時ログイン。

&nbsp;  3. 緊急ログイン: 顔認識失敗時 社員証OCR + ADパスワード認証。

2\. 技術スタック (Tech Stack)

&nbsp;\* Infrastructure: AWS CDK (Python)

&nbsp;\* Backend: Python 3.9 (Boto3, ldap3, Pillow)

&nbsp;\* Frontend: React (AWS Amplify UI)

&nbsp;\* Services: Cognito, Rekognition, Textract, DynamoDB, S3, Direct Connect

3\. 核心要求事項 (Key Requirements)

A. ネットワークおよびセキュリティ

&nbsp;\* 連結: AWS Direct Connectを通じてオンプレミスADと接続。

&nbsp;\* タイムアウト: AD接続および認証タイムアウトは10秒に制限（全体Lambdaタイムアウト15秒）。

&nbsp;\* Liveness: すべての顔キャプチャ時にAmazon Rekognition Livenessを適用（Confidence > 90%）。

B. データ管理ポリシー (S3 \& DynamoDB)

&nbsp;\* 画像保管:

&nbsp;  \* 登録/再登録画像: 原本削除後200x200サムネイルのみ生成して永久保管。

&nbsp;  \* ログイン試行画像: サムネイル変換後logins/フォルダに保存、30日後自動削除（S3 Lifecycle）。

&nbsp;\* 社員証管理: DynamoDBに複数社員証パターン（ロゴ位置、Textract Query文句など）を管理して拡張性確保。

C. ユーザーメッセージガイド

&nbsp;\* システム判定エラー: "社員証規格不一致"、"登録情報不一致"、"アカウント無効化"など具体的に明示。

&nbsp;\* その他状況: "明るい場所で再度お試しください"で統一。

4\. ファイル構造およびサンプルコード (File Structure \& Code)

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

&nbsp;   # Direct Connectを通じたAD認証（10秒タイムアウト）

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

&nbsp;         onAnalysisComplete={async (res) => { /\* 顔認識ロジック \*/ }}

&nbsp;         onError={(err) => alert("明るい場所で再度お試しください。")}

&nbsp;       />

&nbsp;     )}

&nbsp;     <button onClick={() => setMode('ID\_SCAN')}>社員証で認証/登録</button>

&nbsp;   </div>

&nbsp; );

}



5\. AI作業指示事項 (Action Items for AI)

&nbsp;\* AD連携深化: ldap3を使用してVPC環境内でADアカウント状態（有効/無効）をチェックするロジックを完成させてください。

&nbsp;\* 社員証パターン処理: DynamoDBから社員証パターン情報を読み込んでAmazon Textract Queriesを動的に構成する機能を実装してください。

&nbsp;\* 画像処理: Pillowを使用して画像を200x200サイズにリサイズし、S3の適切なパス（enroll/またはlogins/）に保存するユーティリティを作成してください。

&nbsp;\* エラーハンドリング: バックエンドレスポンス時にsystem\_reasonとuser\_messageを分離してフロントエンドに伝達する構造を設計してください。

📥 マークダウンファイル活用方法

&nbsp;\* 上記内容をコピーしてface\_auth\_spec.mdファイルとして保存してください。

&nbsp;\* Vibe Coding AIにこのファイルをアップロードし、\*\*「この仕様書通りに全体プロジェクト構造を作成してPythonコードを作成してください」\*\*と指示してください。

追加で特定機能（例: 詳細LDAPクエリ、社員証認識用Textract Query設定など）に対するコードがさらに必要な場合はお知らせください！



