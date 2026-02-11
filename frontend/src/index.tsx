import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { Amplify } from 'aws-amplify';

// Configure Amplify for Rekognition Liveness
// Identity Pool provides temporary AWS credentials for unauthenticated users
// to call Rekognition Face Liveness APIs
Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: process.env.REACT_APP_COGNITO_USER_POOL_ID || '',
      userPoolClientId: process.env.REACT_APP_COGNITO_CLIENT_ID || '',
      identityPoolId: process.env.REACT_APP_IDENTITY_POOL_ID || '',
    }
  }
});

console.log('Amplify configured:');
console.log('- Region:', process.env.REACT_APP_AWS_REGION);
console.log('- User Pool ID:', process.env.REACT_APP_COGNITO_USER_POOL_ID);
console.log('- User Pool Client ID:', process.env.REACT_APP_COGNITO_CLIENT_ID);
console.log('- Identity Pool ID:', process.env.REACT_APP_IDENTITY_POOL_ID);

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
