/**
 * Enrollment Component
 * Handles employee enrollment with ID card verification and face registration
 */

import React, { useState, useEffect } from 'react';
import CameraCapture from './CameraCapture';
import apiService from '../services/api';
import { AuthResponse } from '../types';
import './Enrollment.css';

interface EnrollmentProps {
  onSuccess: (response: AuthResponse) => void;
  onError: (error: string) => void;
}

type EnrollmentStep = 'idcard' | 'face' | 'processing' | 'complete';

interface DebugInfo {
  employeeId?: string;
  employeeName?: string;
  department?: string;
  confidence?: number;
  idCardImage?: string;
  faceImage?: string;
  rawResponse?: any;
}

const Enrollment: React.FC<EnrollmentProps> = ({ onSuccess, onError }) => {
  const [step, setStep] = useState<EnrollmentStep>('idcard');
  const [idCardImage, setIdCardImage] = useState<string>('');
  const [faceImage, setFaceImage] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
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

  const handleIdCardCapture = (imageBase64: string) => {
    setIdCardImage(imageBase64);
    if (debugMode) {
      setDebugInfo(prev => ({ ...prev, idCardImage: imageBase64 }));
    }
    setStep('face');
  };

  const handleFaceCapture = async (imageBase64: string) => {
    setStep('processing');
    setFaceImage(imageBase64);
    if (debugMode) {
      setDebugInfo(prev => ({ ...prev, faceImage: imageBase64 }));
    }

    try {
      const response = await apiService.enrollment({
        idCardImage,
        faceImage: imageBase64,
      });

      // Store debug information
      if (debugMode) {
        setDebugInfo(prev => ({
          ...prev,
          employeeId: response.employeeInfo?.employeeId,
          employeeName: response.employeeInfo?.name,
          department: response.employeeInfo?.department,
          confidence: debugInfo.confidence, // Keep from previous state if available
          rawResponse: response,
        }));
        console.log('🐛 Enrollment Response:', response);
      }

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
      <h2>新規登録 {debugMode && <span className="debug-badge">🐛 DEBUG</span>}</h2>

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

      {/* Debug Panel */}
      {debugMode && (
        <div className="debug-panel">
          <h3>🐛 デバッグ情報</h3>
          
          <div className="debug-section">
            <h4>OCR結果</h4>
            <div className="debug-info">
              <p><strong>社員番号:</strong> {debugInfo.employeeId || '未取得'}</p>
              <p><strong>氏名:</strong> {debugInfo.employeeName || '未取得'}</p>
              <p><strong>所属:</strong> {debugInfo.department || '未取得'}</p>
              <p><strong>信頼度:</strong> {debugInfo.confidence ? `${(debugInfo.confidence * 100).toFixed(1)}%` : '未取得'}</p>
            </div>
          </div>

          <div className="debug-section">
            <h4>キャプチャ画像</h4>
            <div className="debug-images">
              {debugInfo.idCardImage && (
                <div className="debug-image-container">
                  <p><strong>社員証画像:</strong></p>
                  <img 
                    src={debugInfo.idCardImage} 
                    alt="ID Card" 
                    className="debug-image"
                  />
                </div>
              )}
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

export default Enrollment;
