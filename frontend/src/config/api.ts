/**
 * API Configuration for Face-Auth IdP System
 */

export const API_CONFIG = {
  baseURL: process.env.REACT_APP_API_ENDPOINT || '',
  apiKey: process.env.REACT_APP_API_KEY || '',
  region: process.env.REACT_APP_AWS_REGION || 'ap-northeast-1',
  endpoints: {
    enrollment: '/auth/enroll',
    login: '/auth/login',
    emergency: '/auth/emergency',
    reEnrollment: '/auth/re-enroll',
    status: '/auth/status',
  },
  timeout: 30000, // 30 seconds
};

export const COGNITO_CONFIG = {
  userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID || '',
  clientId: process.env.REACT_APP_COGNITO_CLIENT_ID || '',
  region: process.env.REACT_APP_AWS_REGION || 'ap-northeast-1',
};
