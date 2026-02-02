/**
 * Login Component
 * Handles face-based login (1:N matching)
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

interface DebugInfo {
  employeeId?: string;
  employeeName?: string;
  similarity?: number;
  confidence?: number;
  faceImage?: string;
  rawResponse?: any;
}

const Login: React.FC<LoginProps> = ({ onSuccess, onError, onEmergencyAuth }) => {
  const [loading, setLoading] = useState(false);
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
    setLoading(true);
    setErrorMessage('');

    if (debugMode) {
      setDebugInfo(prev => ({ ...prev, faceImage: imageBase64 }));
    }

    try {
      const response = await apiService.login({
        faceImage: imageBase64,
      });

      // Store debug information
      if (debugMode) {
        setDebugInfo(prev => ({
          ...prev,
          employeeId: response.employeeInfo?.employeeId,
          employeeName: response.employeeInfo?.name,
          similarity: debugInfo.similarity, // Keep from previous state if available
          confidence: debugInfo.confidence, // Keep from previous state if available
          rawResponse: response,
        }));
        console.log('🐛 Login Response:', response);
      }

      if (response.success) {
        onSuccess(response);
      } else {
        const newFailedAttempts = failedAttempts + 1;
        setFailedAttempts(newFailedAttempts);
        setErrorMessage(response.error?.message || 'ログインに失敗しました');
        onError(response.error?.message || 'ログインに失敗しました');
      }
    } catch (error: any) {
      setErrorMessage('ログイン処理中にエラーが発生しました');
      onError('ログイン処理中にエラーが発生しました');
    } finally {
      setLoading(false);
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
        </div>
      )}

      {failedAttempts >= 2 && (
        <div className="emergency-prompt">
          <p>顔認証に失敗しました。緊急ログインをお試しください。</p>
          <button onClick={onEmergencyAuth} className="emergency-button">
            緊急ログイン
          </button>
        </div>
      )}

      {loading ? (
        <div className="login-step">
          <div className="loading-spinner"></div>
          <p>認証中...</p>
        </div>
      ) : (
        <div className="login-step">
          <p className="step-instruction">顔をカメラに向けてください</p>
          <CameraCapture
            onCapture={handleFaceCapture}
            onError={handleCameraError}
            captureMode="face"
          />
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
              <p><strong>類似度:</strong> {debugInfo.similarity ? `${debugInfo.similarity.toFixed(1)}%` : '未取得'}</p>
              <p><strong>信頼度:</strong> {debugInfo.confidence ? `${debugInfo.confidence.toFixed(1)}%` : '未取得'}</p>
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
