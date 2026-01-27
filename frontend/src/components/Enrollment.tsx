/**
 * Enrollment Component
 * Handles employee enrollment with ID card verification and face registration
 */

import React, { useState } from 'react';
import CameraCapture from './CameraCapture';
import apiService from '../services/api';
import { AuthResponse } from '../types';
import './Enrollment.css';

interface EnrollmentProps {
  onSuccess: (response: AuthResponse) => void;
  onError: (error: string) => void;
}

type EnrollmentStep = 'idcard' | 'face' | 'processing' | 'complete';

const Enrollment: React.FC<EnrollmentProps> = ({ onSuccess, onError }) => {
  const [step, setStep] = useState<EnrollmentStep>('idcard');
  const [idCardImage, setIdCardImage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleIdCardCapture = (imageBase64: string) => {
    setIdCardImage(imageBase64);
    setStep('face');
  };

  const handleFaceCapture = async (imageBase64: string) => {
    setStep('processing');

    try {
      const response = await apiService.enrollment({
        idCardImage,
        faceImage: imageBase64,
      });

      if (response.success) {
        setStep('complete');
        onSuccess(response);
      } else {
        setErrorMessage(response.error?.message || '登録に失敗しました');
        onError(response.error?.message || '登録に失敗しました');
        setStep('idcard');
      }
    } catch (error: any) {
      setErrorMessage('登録処理中にエラーが発生しました');
      onError('登録処理中にエラーが発生しました');
      setStep('idcard');
    }
  };

  const handleCameraError = (error: string) => {
    setErrorMessage(error);
    onError(error);
  };

  const resetEnrollment = () => {
    setStep('idcard');
    setIdCardImage('');
    setErrorMessage('');
  };

  return (
    <div className="enrollment-container">
      <h2>新規登録</h2>

      {errorMessage && (
        <div className="error-message">
          {errorMessage}
        </div>
      )}

      {step === 'idcard' && (
        <div className="enrollment-step">
          <p className="step-instruction">社員証をスキャンしてください</p>
          <CameraCapture
            onCapture={handleIdCardCapture}
            onError={handleCameraError}
            captureMode="idcard"
          />
        </div>
      )}

      {step === 'face' && (
        <div className="enrollment-step">
          <p className="step-instruction">顔を登録してください</p>
          <CameraCapture
            onCapture={handleFaceCapture}
            onError={handleCameraError}
            captureMode="face"
          />
          <button onClick={resetEnrollment} className="back-button">
            戻る
          </button>
        </div>
      )}

      {step === 'processing' && (
        <div className="enrollment-step">
          <div className="loading-spinner"></div>
          <p>登録処理中...</p>
        </div>
      )}

      {step === 'complete' && (
        <div className="enrollment-step">
          <div className="success-icon">✓</div>
          <p>登録が完了しました</p>
        </div>
      )}
    </div>
  );
};

export default Enrollment;
