# remove-liveness-detector.ps1
# LivenessDetectorコンポーネントをすべてのフローから削除

Write-Host "=== Remove LivenessDetector Component ===" -ForegroundColor Cyan
Write-Host ""

# Login.tsx - Livenessステップを削除して直接Face Captureから開始
Write-Host "Processing: Login.tsx" -ForegroundColor White

$loginContent = @'
/**
 * Login Component
 * Handles face-based login (1:N matching)
 * 
 * Flow: Face Capture → Submit
 * Requirements: US-2, FR-4.2
 */

import React, { useState, useEffect } from 'react';
import CameraCapture from './CameraCapture';
import apiService from '../services/api';
import { AuthResponse } from '../types';
import './Login.css';

interface LoginProps {
  onSuccess: (response: AuthResponse) => void;
  onError: (error: string) => void;
  onEmergencyAuth: () => void;
}

type LoginStep = 'face' | 'processing';

interface DebugInfo {
  employeeId?: string;
  employeeName?: string;
  similarity?: number;
  confidence?: number;
  faceImage?: string;
  rawResponse?: any;
}

const Login: React.FC<LoginProps> = ({ onSuccess, onError, onEmergencyAuth }) => {
  const [step, setStep] = useState<LoginStep>('face');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [failedAttempts, setFailedAttempts] = useState(0);
  const [debugMode, setDebugMode] = useState<boolean>(false);
  const [debugInfo, setDebugInfo] = useState<DebugInfo>({});

  // Check for debug mode in URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const debug = params.get('debug') === 'true';
    setDebugMode(debug);
    if (debug) {
      console.log('🐛 Debug mode enabled');
    }
  }, []);

  const handleFaceCapture = async (imageBase64: string) => {
    setStep('processing');
    setErrorMessage('');

    if (debugMode) {
      setDebugInfo(prev => ({ ...prev, faceImage: imageBase64 }));
    }

    try {
      const response = await apiService.login({
        faceImage: imageBase64,
        livenessSessionId: '', // No liveness session
      });

      // Store debug information
      if (debugMode) {
        setDebugInfo(prev => ({
          ...prev,
          employeeId: response.employeeInfo?.employeeId,
          employeeName: response.employeeInfo?.name,
          similarity: response.employeeInfo?.similarity,
          confidence: response.employeeInfo?.confidence,
          rawResponse: response,
        }));
        console.log('🐛 Login Response:', response);
      }

      if (response.success) {
        onSuccess(response);
      } else {
        const newFailedAttempts = failedAttempts + 1;
        setFailedAttempts(newFailedAttempts);
        
        const errorMsg = response.error?.message || 'ログインに失敗しました';
        setErrorMessage(errorMsg);
        onError(errorMsg);
        
        // デバッグモードの場合、エラー詳細をコンソールに出力
        if (debugMode) {
          console.error('🐛 Login Error:', response.error);
        }
        
        setStep('face');
      }
    } catch (error: any) {
      const newFailedAttempts = failedAttempts + 1;
      setFailedAttempts(newFailedAttempts);
      
      setErrorMessage('ログイン処理中にエラーが発生しました');
      onError('ログイン処理中にエラーが発生しました');
      setStep('face');
    }
  };

  const handleCameraError = (error: string) => {
    setErrorMessage(error);
    onError(error);
  };

  return (
    <div className="login-container">
      <h2>顔認証ログイン {debugMode && <span className="debug-badge">🐛 DEBUG</span>}</h2>

      {errorMessage && (
        <div className="error-message">
          {errorMessage}
          {failedAttempts >= 3 && (
            <div className="emergency-auth-prompt">
              <p>ログインに失敗しました。緊急認証を試してください。</p>
              <button onClick={onEmergencyAuth} className="emergency-button">
                緊急認証
              </button>
            </div>
          )}
        </div>
      )}

      {step === 'face' && (
        <div className="login-step">
          <p className="step-instruction">顔をカメラに向けてください</p>
          <CameraCapture
            onCapture={handleFaceCapture}
            onError={handleCameraError}
            captureMode="face"
          />
        </div>
      )}

      {step === 'processing' && (
        <div className="login-step">
          <div className="loading-spinner"></div>
          <p>認証中...</p>
        </div>
      )}

      {/* Debug Panel */}
      {debugMode && (
        <div className="debug-panel">
          <h3>🐛 デバッグ情報</h3>
          
          <div className="debug-section">
            <h4>認証結果</h4>
            <div className="debug-info">
              <p><strong>社員番号:</strong> {debugInfo.employeeId || '未取得'}</p>
              <p><strong>氏名:</strong> {debugInfo.employeeName || '未取得'}</p>
              <p><strong>類似度:</strong> {debugInfo.similarity ? `${debugInfo.similarity.toFixed(2)}%` : '未取得'}</p>
              <p><strong>信頼度:</strong> {debugInfo.confidence ? `${debugInfo.confidence.toFixed(2)}%` : '未取得'}</p>
              <p><strong>失敗回数:</strong> {failedAttempts}</p>
            </div>
          </div>

          <div className="debug-section">
            <h4>キャプチャ画像</h4>
            <div className="debug-images">
              {debugInfo.faceImage && (
                <div className="debug-image-container">
                  <p><strong>顔画像:</strong></p>
                  <img 
                    src={debugInfo.faceImage} 
                    alt="Face" 
                    className="debug-image"
                  />
                </div>
              )}
            </div>
          </div>

          {debugInfo.rawResponse && (
            <div className="debug-section">
              <h4>APIレスポンス</h4>
              <pre className="debug-json">
                {JSON.stringify(debugInfo.rawResponse, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Login;
'@

Set-Content "frontend/src/components/Login.tsx" $loginContent -NoNewline -Encoding UTF8
Write-Host "  ✓ Login.tsx updated" -ForegroundColor Green

Write-Host ""
Write-Host "✓ LivenessDetector removed from all components!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Build frontend: cd frontend && npm run build" -ForegroundColor White
Write-Host "2. Deploy to S3: aws s3 sync build/ s3://face-auth-frontend-979431736455-ap-northeast-1 --delete --profile dev" -ForegroundColor White
Write-Host "3. Invalidate CloudFront: aws cloudfront create-invalidation --distribution-id EE7F2PTRFZ6WV --paths '/*' --profile dev" -ForegroundColor White
Write-Host "4. Test in browser (Ctrl+Shift+R to clear cache)" -ForegroundColor White
'@

Set-Content "remove-liveness-detector.ps1" $script -NoNewline -Encoding UTF8
