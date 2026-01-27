import React, { useState } from 'react';
import Login from './components/Login';
import Enrollment from './components/Enrollment';
import EmergencyAuth from './components/EmergencyAuth';
import ReEnrollment from './components/ReEnrollment';
import { AuthResponse, AuthMode } from './types';
import './App.css';

function App() {
  const [mode, setMode] = useState<AuthMode>('LOGIN');
  const [authenticated, setAuthenticated] = useState(false);
  const [authResponse, setAuthResponse] = useState<AuthResponse | null>(null);

  const handleSuccess = (response: AuthResponse) => {
    setAuthResponse(response);
    setAuthenticated(true);
    console.log('Authentication successful:', response);
  };

  const handleError = (error: string) => {
    console.error('Authentication error:', error);
  };

  const handleLogout = () => {
    setAuthenticated(false);
    setAuthResponse(null);
    setMode('LOGIN');
  };

  if (authenticated && authResponse) {
    return (
      <div className="App">
        <div className="success-container">
          <h1>認証成功</h1>
          <div className="user-info">
            <p>社員ID: {authResponse.employeeInfo?.employeeId}</p>
            <p>氏名: {authResponse.employeeInfo?.name}</p>
          </div>
          <button onClick={handleLogout} className="logout-button">
            ログアウト
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>Face-Auth IdP System</h1>
        <p className="subtitle">顔認証による無パスワード認証システム</p>
      </header>

      <nav className="mode-selector">
        <button
          className={mode === 'LOGIN' ? 'active' : ''}
          onClick={() => setMode('LOGIN')}
        >
          ログイン
        </button>
        <button
          className={mode === 'ENROLL' ? 'active' : ''}
          onClick={() => setMode('ENROLL')}
        >
          新規登録
        </button>
        <button
          className={mode === 'RE_ENROLL' ? 'active' : ''}
          onClick={() => setMode('RE_ENROLL')}
        >
          再登録
        </button>
      </nav>

      <main className="App-main">
        {mode === 'LOGIN' && (
          <Login
            onSuccess={handleSuccess}
            onError={handleError}
            onEmergencyAuth={() => setMode('EMERGENCY')}
          />
        )}
        {mode === 'ENROLL' && (
          <Enrollment
            onSuccess={handleSuccess}
            onError={handleError}
          />
        )}
        {mode === 'EMERGENCY' && (
          <EmergencyAuth
            onSuccess={handleSuccess}
            onError={handleError}
            onBack={() => setMode('LOGIN')}
          />
        )}
        {mode === 'RE_ENROLL' && (
          <ReEnrollment
            onSuccess={handleSuccess}
            onError={handleError}
          />
        )}
      </main>

      <footer className="App-footer">
        <p>&copy; 2024 Face-Auth IdP System</p>
      </footer>
    </div>
  );
}

export default App;
