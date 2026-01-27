/**
 * API Service for Face-Auth IdP System
 */

import axios, { AxiosInstance } from 'axios';
import { API_CONFIG } from '../config/api';
import {
  AuthResponse,
  EnrollmentRequest,
  LoginRequest,
  EmergencyAuthRequest,
  ReEnrollmentRequest,
} from '../types';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_CONFIG.baseURL,
      timeout: API_CONFIG.timeout,
      headers: {
        'Content-Type': 'application/json',
        ...(API_CONFIG.apiKey && { 'x-api-key': API_CONFIG.apiKey }),
      },
    });
  }

  async enrollment(request: EnrollmentRequest): Promise<AuthResponse> {
    try {
      const response = await this.client.post(API_CONFIG.endpoints.enrollment, request);
      return response.data;
    } catch (error: any) {
      return this.handleError(error);
    }
  }

  async login(request: LoginRequest): Promise<AuthResponse> {
    try {
      const response = await this.client.post(API_CONFIG.endpoints.login, request);
      return response.data;
    } catch (error: any) {
      return this.handleError(error);
    }
  }

  async emergencyAuth(request: EmergencyAuthRequest): Promise<AuthResponse> {
    try {
      const response = await this.client.post(API_CONFIG.endpoints.emergency, request);
      return response.data;
    } catch (error: any) {
      return this.handleError(error);
    }
  }

  async reEnrollment(request: ReEnrollmentRequest): Promise<AuthResponse> {
    try {
      const response = await this.client.post(API_CONFIG.endpoints.reEnrollment, request);
      return response.data;
    } catch (error: any) {
      return this.handleError(error);
    }
  }

  async checkStatus(sessionId: string): Promise<AuthResponse> {
    try {
      const response = await this.client.get(`${API_CONFIG.endpoints.status}/${sessionId}`);
      return response.data;
    } catch (error: any) {
      return this.handleError(error);
    }
  }

  private handleError(error: any): AuthResponse {
    if (error.response?.data) {
      return {
        success: false,
        error: error.response.data,
      };
    }

    return {
      success: false,
      error: {
        code: 'NETWORK_ERROR',
        message: '明るい場所で再度お試しください',
        systemReason: error.message,
      },
    };
  }
}

const apiService = new ApiService();
export default apiService;
