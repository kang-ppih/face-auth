/**
 * Re-Enrollment Component
 * Handles face data update for existing employees
 */

import React, { useState } from 'react';
import CameraCapture from './CameraCapture';
import apiService from '../services/api';
import { AuthResponse } from '../types';
import './ReEnrollment.css';

interface ReEnrollmentProps {
  onSuccess: (response: AuthResponse) => void;
  onError: (error: string) => void;
}

type ReEnrollmentStep = 'idcard' | 'face' | 'processing' | 'complete';

const ReEnrollment: React.FC<ReEnrollmentProps> = ({ onSuccess, onError }) => {
  const [step, setStep] = useState<ReEnrollmentStep>('idcard');
  const [idCardImage, setIdCardImage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleIdCardCapture = (imageBase64: string) => {
    setIdCardImage(imageBase64);
    setStep('face');
  };

  const handleFaceCapture = async (imageBase64: string) => {
    setStep('processing');

    try {
      const response = await apiService.reEnrollment({
        idCardImage,
        faceImage: imageBase64,
      });

      if (response.success) {
        setStep('complete');
        onSuccess(response);
      } else {
        setErrorMessage(response.error?.message || '再登録に失敗しました');
        onError(response.error?.message || '再登録に失敗しました');
        setStep('idcard');
      }
    } catch (error: any) {
      setErrorMessage('再登録処理中にエラーが発生しました');
      onError('再登録処理中にエラーが発生しました');
      setStep('idcard');
    }
  };

  const handleCameraError = (error: string) => {
    setErrorMessage(error);
    onError(error);
  };

  const resetReEnrollment = () => {
    setStep('idcard');
    setIdCardImage('');
    setErrorMessage('');
  };

  return (
    <div className="re-enrollment-container">
      <h2>顔データ再登録</h2>
      <p className="re-enrollment-description">
        外見が変わった場合は顔データを更新してください
      </p>

      {errorMessage && (
        <div className="error-message">
          {errorMessage}
        </div>
      )}

      {step === 'idcard' && (
        <div className="re-enrollment-step">
          <p className="step-instruction">社員証をスキャンしてください</p>
          <CameraCapture
            onCapture={handleIdCardCapture}
            onError={handleCameraError}
            captureMode="idcard"
          />
        </div>
      )}

      {step === 'face' && (
        <div className="re-enrollment-step">
          <p className="step-instruction">新しい顔データを登録してください</p>
          <CameraCapture
            onCapture={handleFaceCapture}
            onError={handleCameraError}
            captureMode="face"
          />
          <button onClick={resetReEnrollment} className="back-button">
            戻る
          </button>
        </div>
      )}

      {step === 'processing' && (
        <div className="re-enrollment-step">
          <div className="loading-spinner"></div>
          <p>再登録処理中...</p>
        </div>
      )}

      {step === 'complete' && (
        <div className="re-enrollment-step">
          <div className="success-icon">✓</div>
          <p>再登録が完了しました</p>
        </div>
      )}
    </div>
  );
};

export default ReEnrollment;
