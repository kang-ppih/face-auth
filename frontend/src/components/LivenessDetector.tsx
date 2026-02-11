/**
 * Liveness Detector Component
 * 
 * AWS Amplify UI FaceLivenessDetector統合コンポーネント
 * Rekognition Liveness APIを使用してライブネス検証を実行
 * 
 * Requirements: FR-2, US-1, US-2, US-3, US-4
 */

import React, { useState, useEffect } from 'react';
import { FaceLivenessDetector } from '@aws-amplify/ui-react-liveness';
import { Loader } from '@aws-amplify/ui-react';
import './LivenessDetector.css';

interface LivenessDetectorProps {
  employeeId: string;
  onSuccess: (sessionId: string) => void;
  onError: (error: string) => void;
}

interface SessionData {
  sessionId: string;
  expiresAt: string;
}

const LivenessDetector: React.FC<LivenessDetectorProps> = ({
  employeeId,
  onSuccess,
  onError
}) => {
  const [sessionData, setSessionData] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [debugMode] = useState<boolean>(
    new URLSearchParams(window.location.search).get('debug') === 'true'
  );

  // セッション作成（1回のみ実行、リトライなし）
  useEffect(() => {
    let isMounted = true;

    const createSession = async () => {
      try {
        setLoading(true);
        setError('');

        const apiUrl = process.env.REACT_APP_API_URL;
        if (!apiUrl) {
          throw new Error('API URLが設定されていません');
        }

        if (debugMode) {
          console.log('🐛 Creating liveness session for employee:', employeeId);
          console.log('🐛 API URL:', apiUrl);
        }

        const response = await fetch(`${apiUrl}/liveness/session/create`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ employee_id: employeeId }),
        });

        if (debugMode) {
          console.log('🐛 Response status:', response.status);
        }

        if (!response.ok) {
          let errorData;
          try {
            errorData = await response.json();
          } catch {
            errorData = { message: `HTTP ${response.status}: ${response.statusText}` };
          }
          if (debugMode) {
            console.error('🐛 API error:', errorData);
          }
          throw new Error(errorData.message || `セッション作成に失敗しました (${response.status})`);
        }

        const data = await response.json();
        if (debugMode) {
          console.log('🐛 Session created:', data);
        }

        if (isMounted) {
          setSessionData({
            sessionId: data.session_id,
            expiresAt: data.expires_at,
          });
        }
      } catch (err) {
        if (debugMode) {
          console.error('🐛 Session creation error:', err);
        }
        const errorMessage = err instanceof Error ? err.message : '不明なエラーが発生しました';
        if (isMounted) {
          setError(errorMessage);
          onError(errorMessage);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    createSession();

    // クリーンアップ関数（コンポーネントがアンマウントされた場合）
    return () => {
      isMounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 空の依存配列 = マウント時に1回のみ実行

  // ライブネス検証完了ハンドラ
  const handleAnalysisComplete = async () => {
    if (!sessionData) {
      onError('セッションデータがありません');
      return;
    }

    try {
      const apiUrl = process.env.REACT_APP_API_URL;
      const apiKey = process.env.REACT_APP_API_KEY;
      
      if (debugMode) {
        console.log('🐛 Fetching liveness result for session:', sessionData.sessionId);
      }
      
      const response = await fetch(
        `${apiUrl}/liveness/session/${sessionData.sessionId}/result`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': apiKey || '',
          },
        }
      );

      if (debugMode) {
        console.log('🐛 Liveness result response status:', response.status);
      }

      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          errorData = { message: `HTTP ${response.status}: ${response.statusText}` };
        }
        if (debugMode) {
          console.error('🐛 Liveness result error:', errorData);
        }
        throw new Error(errorData.message || 'ライブネス検証に失敗しました');
      }

      const result = await response.json();
      if (debugMode) {
        console.log('🐛 Liveness result:', result);
      }
      
      if (result.is_live) {
        onSuccess(sessionData.sessionId);
      } else {
        onError('ライブネス検証に失敗しました。もう一度お試しください。');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '検証結果の取得に失敗しました';
      onError(errorMessage);
    }
  };

  // エラーハンドラ
  const handleError = (livenessError: any) => {
    console.error('Liveness detection error:', livenessError);
    const errorMessage = livenessError?.message || livenessError?.state || 'ライブネス検証中にエラーが発生しました';
    onError(errorMessage);
  };

  if (loading) {
    return (
      <div className="liveness-detector-container">
        <Loader size="large" />
        <p>ライブネス検証セッションを準備中...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="liveness-detector-container error">
        <p className="error-message">{error}</p>
        <p className="error-details">
          エラーが発生しました。画面を閉じて最初からやり直してください。
        </p>
      </div>
    );
  }

  if (!sessionData) {
    return (
      <div className="liveness-detector-container error">
        <p className="error-message">セッションデータの取得に失敗しました</p>
      </div>
    );
  }

  return (
    <div className="liveness-detector-container">
      <div className="liveness-instructions">
        <h3>顔認証を開始します</h3>
        <ul>
          <li>カメラの前に顔を正面に向けてください</li>
          <li>画面の指示に従って顔を動かしてください</li>
          <li>明るい場所で実施してください</li>
        </ul>
      </div>
      
      <FaceLivenessDetector
        sessionId={sessionData.sessionId}
        region={process.env.REACT_APP_AWS_REGION || 'us-east-1'}
        onAnalysisComplete={handleAnalysisComplete}
        onError={handleError}
        displayText={{
          hintCenterFaceText: '顔を中央に配置してください',
          hintFaceDetectedText: '顔を検出しました',
          hintTooManyFacesText: '複数の顔が検出されました。一人で実施してください',
          hintTooCloseText: 'カメラから少し離れてください',
          hintTooFarText: 'カメラに近づいてください',
          hintConnectingText: '接続中...',
          hintVerifyingText: '検証中...',
          hintIlluminationTooBrightText: '明るすぎます',
          hintIlluminationTooDarkText: '暗すぎます',
          hintIlluminationNormalText: '照明は適切です',
          hintHoldFaceForFreshnessText: '顔を動かさないでください',
          photosensitivyWarningHeadingText: '光過敏性に関する警告',
          photosensitivyWarningBodyText: 'この検証では点滅する色が表示される場合があります。',
          photosensitivyWarningInfoText: '光過敏性てんかんをお持ちの方はご注意ください。',
          goodFitCaptionText: '良好',
          tooFarCaptionText: '遠すぎます',
          startScreenBeginCheckText: '検証を開始',
          cancelLivenessCheckText: 'キャンセル',
          recordingIndicatorText: '録画中',
        }}
      />
    </div>
  );
};

export default LivenessDetector;
