/**
 * Type definitions for Face-Auth IdP System
 */

export interface AuthError {
  code: string;
  message: string;
  systemReason?: string;
  timestamp?: string;
  requestId?: string;
}

export interface EmployeeInfo {
  employeeId: string;
  name: string;
  department?: string;
  cardType?: string;
}

export interface AuthResponse {
  success: boolean;
  token?: string;
  sessionId?: string;
  employeeInfo?: EmployeeInfo;
  error?: AuthError;
}

export interface EnrollmentRequest {
  idCardImage: string; // base64
  faceImage: string; // base64
  livenessSessionId?: string; // Rekognition Liveness session ID
}

export interface LoginRequest {
  faceImage: string; // base64
  livenessSessionId?: string; // Rekognition Liveness session ID
}

export interface EmergencyAuthRequest {
  idCardImage: string; // base64
  password: string;
  livenessSessionId?: string; // Rekognition Liveness session ID
}

export interface ReEnrollmentRequest {
  idCardImage: string; // base64
  faceImage: string; // base64
  livenessSessionId?: string; // Rekognition Liveness session ID
}

export type AuthMode = 'LOGIN' | 'ENROLL' | 'EMERGENCY' | 'RE_ENROLL';

export interface CameraConfig {
  resolution: { width: number; height: number };
  facingMode: 'user' | 'environment';
}
