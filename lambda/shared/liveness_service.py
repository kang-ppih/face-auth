"""
Rekognition Liveness Service

This module provides integration with AWS Rekognition Face Liveness API
for detecting live faces and preventing spoofing attacks.

Requirements: FR-1, FR-3, NFR-2
"""

import boto3
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
import os


# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass
class LivenessSessionResult:
    """
    Liveness検証結果
    
    Attributes:
        session_id: セッションID
        is_live: 生体検出結果（True: 生体、False: なりすまし）
        confidence: 信頼度スコア（0-100）
        reference_image_s3_key: リファレンス画像のS3キー
        audit_image_s3_key: 監査画像のS3キー（オプション）
        status: ステータス（SUCCESS, FAILED, TIMEOUT, PENDING）
        error_message: エラーメッセージ（オプション）
    """
    session_id: str
    is_live: bool
    confidence: float
    reference_image_s3_key: Optional[str] = None
    audit_image_s3_key: Optional[str] = None
    status: str = "SUCCESS"
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# Custom exceptions
class LivenessServiceError(Exception):
    """Base exception for Liveness Service errors"""
    pass


class SessionNotFoundError(LivenessServiceError):
    """Raised when session is not found"""
    pass


class SessionExpiredError(LivenessServiceError):
    """Raised when session has expired"""
    pass


class ConfidenceThresholdError(LivenessServiceError):
    """Raised when confidence is below threshold"""
    pass



class LivenessService:
    """
    AWS Rekognition Liveness API統合サービス
    
    このサービスは、AWS Rekognition Face Liveness APIを使用して、
    写真や動画を使ったなりすまし攻撃を防ぐ高度な生体検証を提供します。
    
    主な機能:
    - Livenessセッションの作成
    - セッション結果の取得と評価
    - 監査ログの保存
    - 信頼度スコアの検証
    
    Requirements: FR-1, FR-3
    """
    
    def __init__(
        self,
        rekognition_client: Optional[Any] = None,
        dynamodb_client: Optional[Any] = None,
        s3_client: Optional[Any] = None,
        cloudwatch_client: Optional[Any] = None,
        confidence_threshold: float = 90.0,
        session_timeout_minutes: int = 10,
        liveness_sessions_table: Optional[str] = None,
        face_auth_bucket: Optional[str] = None
    ):
        """
        Initialize Liveness Service
        
        Args:
            rekognition_client: Boto3 Rekognition client (optional)
            dynamodb_client: Boto3 DynamoDB client (optional)
            s3_client: Boto3 S3 client (optional)
            cloudwatch_client: Boto3 CloudWatch client (optional)
            confidence_threshold: 信頼度閾値（デフォルト: 90.0%）
            session_timeout_minutes: セッションタイムアウト（デフォルト: 10分）
            liveness_sessions_table: DynamoDBテーブル名（オプション）
            face_auth_bucket: S3バケット名（オプション）
        """
        self.rekognition = rekognition_client or boto3.client('rekognition')
        self.dynamodb = dynamodb_client or boto3.client('dynamodb')
        self.s3 = s3_client or boto3.client('s3')
        self.cloudwatch = cloudwatch_client or boto3.client('cloudwatch')
        
        self.confidence_threshold = confidence_threshold
        self.session_timeout_minutes = session_timeout_minutes
        
        # Get table and bucket names from environment or parameters
        self.liveness_sessions_table = liveness_sessions_table or os.environ.get(
            'LIVENESS_SESSIONS_TABLE', 'FaceAuth-LivenessSessions'
        )
        self.face_auth_bucket = face_auth_bucket or os.environ.get(
            'FACE_AUTH_BUCKET'
        )
        
        logger.info(
            f"LivenessService initialized with confidence_threshold={confidence_threshold}, "
            f"session_timeout={session_timeout_minutes}min"
        )

    
    def create_session(self, employee_id: str) -> Dict[str, str]:
        """
        Livenessセッションを作成
        
        AWS Rekognition CreateFaceLivenessSession APIを呼び出して、
        新しいセッションを作成し、セッションIDを返します。
        
        Args:
            employee_id: 社員ID
            
        Returns:
            {
                'session_id': str,  # セッションID
                'expires_at': str   # 有効期限（ISO 8601形式）
            }
            
        Raises:
            LivenessServiceError: セッション作成失敗
            
        Requirements: FR-1.1, FR-1.2, FR-1.3
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Generate unique client request token
            client_request_token = str(uuid.uuid4())
            
            # Calculate expiration time
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=self.session_timeout_minutes)
            expires_at_unix = int(expires_at.timestamp())
            
            # Create Liveness session with S3 output configuration
            response = self.rekognition.create_face_liveness_session(
                ClientRequestToken=client_request_token,
                Settings={
                    'OutputConfig': {
                        'S3Bucket': self.face_auth_bucket,
                        'S3KeyPrefix': 'liveness-audit/'
                    },
                    'AuditImagesLimit': 2  # Store up to 2 audit images
                }
            )
            
            session_id = response['SessionId']
            
            # Store session in DynamoDB
            self.dynamodb.put_item(
                TableName=self.liveness_sessions_table,
                Item={
                    'session_id': {'S': session_id},
                    'employee_id': {'S': employee_id},
                    'status': {'S': 'PENDING'},
                    'created_at': {'S': datetime.now(timezone.utc).isoformat()},
                    'expires_at': {'N': str(expires_at_unix)}
                }
            )
            
            # Send metrics
            elapsed_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self._send_metric('SessionCreationTime', elapsed_time, 'Seconds')
            self._send_metric('SessionCreated', 1.0, 'Count')
            
            logger.info(
                f"Liveness session created",
                extra={
                    'session_id': session_id,
                    'employee_id': employee_id,
                    'expires_at': expires_at.isoformat(),
                    'elapsed_time': elapsed_time
                }
            )
            
            return {
                'session_id': session_id,
                'expires_at': expires_at.isoformat()
            }
            
        except Exception as e:
            # Send error metric
            self._send_metric('SessionCreationError', 1.0, 'Count')
            logger.error(f"Failed to create liveness session: {str(e)}")
            raise LivenessServiceError(f"Failed to create liveness session: {str(e)}")

    
    def get_session_result(self, session_id: str) -> LivenessSessionResult:
        """
        Livenessセッション結果を取得・評価
        
        AWS Rekognition GetFaceLivenessSessionResults APIを呼び出して、
        セッションの検証結果を取得し、信頼度スコアを評価します。
        
        Args:
            session_id: セッションID
            
        Returns:
            LivenessSessionResult: 検証結果
            
        Raises:
            SessionNotFoundError: セッションが存在しない
            SessionExpiredError: セッションが期限切れ
            LivenessServiceError: 結果取得失敗
            
        Requirements: FR-1.4, FR-3
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Check session exists in DynamoDB
            db_response = self.dynamodb.get_item(
                TableName=self.liveness_sessions_table,
                Key={'session_id': {'S': session_id}}
            )
            
            if 'Item' not in db_response:
                self._send_metric('SessionNotFound', 1.0, 'Count')
                raise SessionNotFoundError(f"Session not found: {session_id}")
            
            item = db_response['Item']
            
            # Check if session has expired
            expires_at = int(item['expires_at']['N'])
            if datetime.now(timezone.utc).timestamp() > expires_at:
                self._send_metric('SessionExpired', 1.0, 'Count')
                raise SessionExpiredError(f"Session expired: {session_id}")
            
            # Get liveness session results from Rekognition
            response = self.rekognition.get_face_liveness_session_results(
                SessionId=session_id
            )
            
            # Extract results
            status = response.get('Status', 'UNKNOWN')
            confidence = response.get('Confidence', 0.0)
            
            # Validate confidence threshold
            is_live = self._validate_confidence(confidence)
            
            # Extract reference image S3 key
            reference_image_s3_key = None
            if 'ReferenceImage' in response and 'S3Object' in response['ReferenceImage']:
                s3_obj = response['ReferenceImage']['S3Object']
                reference_image_s3_key = f"{s3_obj.get('Name', '')}"
            
            # Extract audit images S3 keys
            audit_image_s3_key = None
            if 'AuditImages' in response and len(response['AuditImages']) > 0:
                s3_obj = response['AuditImages'][0].get('S3Object', {})
                audit_image_s3_key = f"{s3_obj.get('Name', '')}"
            
            # Determine final status
            final_status = "SUCCESS" if is_live and status == "SUCCEEDED" else "FAILED"
            error_message = None if is_live else f"Confidence {confidence:.2f}% below threshold {self.confidence_threshold}%"
            
            # Update DynamoDB with results
            self.dynamodb.update_item(
                TableName=self.liveness_sessions_table,
                Key={'session_id': {'S': session_id}},
                UpdateExpression="SET #status = :status, confidence = :confidence, reference_image_s3_key = :ref_key",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': {'S': final_status},
                    ':confidence': {'N': str(confidence)},
                    ':ref_key': {'S': reference_image_s3_key or ''}
                }
            )
            
            result = LivenessSessionResult(
                session_id=session_id,
                is_live=is_live,
                confidence=confidence,
                reference_image_s3_key=reference_image_s3_key,
                audit_image_s3_key=audit_image_s3_key,
                status=final_status,
                error_message=error_message
            )
            
            # Send metrics
            elapsed_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            self.send_liveness_metrics(session_id, result, elapsed_time)
            
            logger.info(
                f"Liveness verification completed",
                extra={
                    'session_id': session_id,
                    'is_live': is_live,
                    'confidence': confidence,
                    'status': final_status,
                    'elapsed_time': elapsed_time
                }
            )
            
            return result
            
        except (SessionNotFoundError, SessionExpiredError):
            raise
        except Exception as e:
            self._send_metric('VerificationError', 1.0, 'Count')
            logger.error(f"Failed to get liveness session result: {str(e)}")
            raise LivenessServiceError(f"Failed to get liveness session result: {str(e)}")

    
    def _validate_confidence(self, confidence: float) -> bool:
        """
        信頼度スコアを検証
        
        Args:
            confidence: 信頼度スコア（0-100）
            
        Returns:
            bool: 閾値以上の場合True
        """
        return confidence >= self.confidence_threshold
    
    def _send_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = 'None',
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """
        CloudWatchメトリクスを送信
        
        Args:
            metric_name: メトリクス名
            value: メトリクス値
            unit: 単位（Count, Percent, Seconds等）
            dimensions: ディメンション（オプション）
            
        Requirements: NFR-3, Task 22
        """
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.now(timezone.utc)
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace='FaceAuth/Liveness',
                MetricData=[metric_data]
            )
            
            logger.debug(f"Metric sent: {metric_name}={value} {unit}")
            
        except Exception as e:
            # メトリクス送信失敗はログのみ（処理は継続）
            logger.warning(f"Failed to send metric {metric_name}: {str(e)}")
    
    def send_liveness_metrics(
        self,
        session_id: str,
        result: LivenessSessionResult,
        elapsed_time: float
    ) -> None:
        """
        Liveness検証のメトリクスを送信
        
        Args:
            session_id: セッションID
            result: 検証結果
            elapsed_time: 処理時間（秒）
            
        Requirements: NFR-3, Task 22
        """
        try:
            # 成功/失敗カウント
            self._send_metric(
                'SessionCount',
                1.0,
                'Count',
                {'Status': result.status}
            )
            
            # 信頼度スコア
            self._send_metric(
                'ConfidenceScore',
                result.confidence,
                'Percent'
            )
            
            # 検証時間
            self._send_metric(
                'VerificationTime',
                elapsed_time,
                'Seconds'
            )
            
            # 成功率計算用
            if result.is_live:
                self._send_metric('SuccessCount', 1.0, 'Count')
            else:
                self._send_metric('FailureCount', 1.0, 'Count')
            
            logger.info(
                f"Liveness metrics sent",
                extra={
                    'session_id': session_id,
                    'status': result.status,
                    'confidence': result.confidence,
                    'elapsed_time': elapsed_time
                }
            )
            
        except Exception as e:
            logger.warning(f"Failed to send liveness metrics: {str(e)}")
    
    def store_audit_log(
        self,
        session_id: str,
        result: LivenessSessionResult,
        employee_id: str,
        client_info: Optional[Dict[str, str]] = None
    ) -> None:
        """
        監査ログをS3に保存
        
        Args:
            session_id: セッションID
            result: 検証結果
            employee_id: 社員ID
            client_info: クライアント情報（オプション）
            
        Requirements: FR-3.4, US-5
        """
        try:
            # Prepare audit log
            audit_log = {
                'session_id': session_id,
                'employee_id': employee_id,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'result': result.to_dict(),
                'client_info': client_info or {}
            }
            
            # Store in S3
            s3_key = f"liveness-audit/{session_id}/audit-log.json"
            self.s3.put_object(
                Bucket=self.face_auth_bucket,
                Key=s3_key,
                Body=json.dumps(audit_log, indent=2),
                ContentType='application/json',
                ServerSideEncryption='AES256'
            )
            
            logger.info(
                f"Audit log stored",
                extra={
                    'session_id': session_id,
                    'employee_id': employee_id,
                    's3_key': s3_key
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to store audit log: {str(e)}")
            # Don't raise exception - audit log failure shouldn't block the flow
