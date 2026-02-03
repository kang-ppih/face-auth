/**
 * Emergency Authentication Component
 * Handles ID card + AD password authentication
 * 
 * Flow: ID Card → Password → Liveness → Submit
 * Requirements: US-3, FR-4.3
 */

import React, { useState } from 'react';
import CameraCapture from './CameraCapture';
import LivenessDetector from './LivenessDetector';
import apiService from '../services/api';
import { AuthResponse } from '../types';
import './EmergencyAuth.css';

interface EmergencyAuthProps {
  onSuccess: (response: AuthResponse) => void;
  onError: (error: string) => void;
  onBack: () => void;
}

type EmergencyStep = 'idcard' | 'password' | 'liveness' | 'processing';

const EmergencyAuth: React.FC<EmergencyAuthProps> = ({ onSuccess, onError, onBack }) => {
  const [step, setStep] = useState<EmergencyStep>('idcard');
  const [idCardImage, setIdCardImage] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [livenessSessionId, setLivenessSessionId] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleIdCardCapture = (imageBase64: string) => {
    setIdCardImage(imageBase64);
    setStep('password');
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!password) {
      setErrorMessage('パスワードを入力してください');
      return;
    }

    // Password → Liveness
    setStep('liveness');
  };

  const handleLivenessSuccess = async (sessionId: string) => {
    setLivenessSessionId(sessionId);
    setStep('processing');

    try {
      const response = await apiService.emergencyAuth({
        idCardImage,
        password,
        livenessSessionId: sessionId, // Add liveness session ID
      });

      if (response.success) {
        onSuccess(response);
      } else {
        setErrorMessage(response.error?.message || '認証に失敗しました');
        onError(response.error?.message || '認証に失敗しました');
        setStep('idcard');
        setPassword('');
        setLivenessSessionId('');
      }
    } catch (error: any) {
      setErrorMessage('認証処理中にエラーが発生しました');
      onError('認証処理中にエラーが発生しました');
      setStep('idcard');
      setPassword('');
      setLivenessSessionId('');
    }
  };

  const handleLivenessError = (error: string) => {
    setErrorMessage(`ライブネス検証エラー: ${error}`);
    onError(error);
    // Retry liveness
    setStep('liveness');
  };

  const handleCameraError = (error: string) => {
    setErrorMessage(error);
    onError(error);
  };

  const resetAuth = () => {
    setStep('idcard');
    setIdCardImage('');
    setPassword('');
    setLivenessSessionId('');
    setErrorMessage('');
  };

  return (
    <div className="emergency-auth-container">
      <h2>緊急ログイン</h2>
      <p className="emergency-description">
        社員証とADパスワードで認証します
      </p>

      {errorMessage && (
        <div className="error-message">
          {errorMessage}
        </div>
      )}

      {step === 'idcard' && (
        <div className="emergency-step">
          <p className="step-instruction">社員証をスキャンしてください</p>
          <CameraCapture
            onCapture={handleIdCardCapture}
            onError={handleCameraError}
            captureMode="idcard"
          />
          <button onClick={onBack} className="back-button">
            戻る
          </button>
        </div>
      )}

      {step === 'password' && (
        <div className="emergency-step">
          <p className="step-instruction">ADパスワードを入力してください</p>
          <form onSubmit={handlePasswordSubmit} className="password-form">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="パスワード"
              className="password-input"
              autoFocus
            />
            <div className="form-buttons">
              <button type="button" onClick={resetAuth} className="back-button">
                戻る
              </button>
              <button type="submit" className="submit-button">
                次へ
              </button>
            </div>
          </form>
        </div>
      )}

      {step === 'liveness' && (
        <div className="emergency-step">
          <p className="step-instruction">ライブネス検証を実施してください</p>
          <LivenessDetector
            employeeId="EMERGENCY"
            onSuccess={handleLivenessSuccess}
            onError={handleLivenessError}
          />
          <button onClick={() => setStep('password')} className="back-button">
            戻る
          </button>
        </div>
      )}

      {step === 'processing' && (
        <div className="emergency-step">
          <div className="loading-spinner"></div>
          <p>認証中...</p>
        </div>
      )}
    </div>
  );
};

export default EmergencyAuth;
