/**
 * Login Component
 * Handles face-based login (1:N matching)
 */

import React, { useState } from 'react';
import CameraCapture from './CameraCapture';
import apiService from '../services/api';
import { AuthResponse } from '../types';
import './Login.css';

interface LoginProps {
  onSuccess: (response: AuthResponse) => void;
  onError: (error: string) => void;
  onEmergencyAuth: () => void;
}

const Login: React.FC<LoginProps> = ({ onSuccess, onError, onEmergencyAuth }) => {
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [failedAttempts, setFailedAttempts] = useState(0);

  const handleFaceCapture = async (imageBase64: string) => {
    setLoading(true);
    setErrorMessage('');

    try {
      const response = await apiService.login({
        faceImage: imageBase64,
      });

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
      <h2>顔認証ログイン</h2>

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
    </div>
  );
};

export default Login;
