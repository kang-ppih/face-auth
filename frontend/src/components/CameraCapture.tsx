/**
 * Camera Capture Component
 * Handles video stream and face/ID card capture
 */

import React, { useRef, useEffect, useState } from 'react';
import { captureFromVideo } from '../utils/imageUtils';
import './CameraCapture.css';

interface CameraCaptureProps {
  onCapture: (imageBase64: string) => void;
  onError: (error: string) => void;
  captureMode: 'face' | 'idcard';
}

const CameraCapture: React.FC<CameraCaptureProps> = ({ onCapture, onError, captureMode }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [isReady, setIsReady] = useState(false);
  const [countdown, setCountdown] = useState<number | null>(null);
  const countdownTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
      if (countdownTimerRef.current) {
        clearInterval(countdownTimerRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-capture after camera is ready
  useEffect(() => {
    if (isReady && !countdown) {
      // Start countdown after 1 second delay
      setTimeout(() => {
        startCountdown();
      }, 1000);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isReady]);

  const startCountdown = () => {
    setCountdown(3);
    
    countdownTimerRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev === null || prev <= 1) {
          if (countdownTimerRef.current) {
            clearInterval(countdownTimerRef.current);
          }
          // Auto-capture when countdown reaches 0
          setTimeout(() => {
            handleCapture();
          }, 100);
          return null;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: captureMode === 'face' ? 'user' : 'environment',
        },
      });

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        setStream(mediaStream);
        setIsReady(true);
      }
    } catch (error: any) {
      onError('カメラへのアクセスに失敗しました。カメラの権限を確認してください。');
    }
  };

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
      setIsReady(false);
    }
  };

  const handleCapture = () => {
    if (videoRef.current && isReady) {
      try {
        const imageBase64 = captureFromVideo(videoRef.current);
        onCapture(imageBase64);
      } catch (error: any) {
        onError('画像のキャプチャに失敗しました。');
      }
    }
  };

  return (
    <div className="camera-capture">
      <div className="video-container">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="video-preview"
        />
        <div className="capture-guide">
          {captureMode === 'face' ? (
            <div className="face-guide">
              顔を枠内に合わせてください
              {countdown !== null && (
                <div className="countdown">{countdown}</div>
              )}
            </div>
          ) : (
            <div className="idcard-guide">
              社員証を枠内に合わせてください
              {countdown !== null && (
                <div className="countdown">{countdown}</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CameraCapture;
