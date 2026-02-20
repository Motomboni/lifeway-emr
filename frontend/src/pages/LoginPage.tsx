/**
 * Login Page
 * 
 * Per EMR Rules:
 * - Strong authentication (JWT)
 * - Account lockout after repeated failures
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import styles from '../styles/Login.module.css';

interface LoginPageProps {
  onLoginSuccess?: () => void;
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const { login } = useAuth();
  const { showError } = useToast();
  const navigate = useNavigate();
  
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login(username, password);
      
      // Get user from localStorage (set by AuthContext after login)
      const storedUser = localStorage.getItem('auth_user');
      const userData = storedUser ? JSON.parse(storedUser) : null;
      
      if (onLoginSuccess) {
        onLoginSuccess();
      } else {
        // Redirect based on user role
        if (userData?.role === 'PATIENT') {
          navigate('/patient-portal/dashboard', { replace: true });
        } else {
          navigate('/dashboard', { replace: true });
        }
      }
    } catch (err: any) {
      // Extract error message from API response
      let errorMessage = 'Login failed';
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (err?.responseData) {
        // Handle DRF validation errors
        if (err.responseData.non_field_errors) {
          errorMessage = Array.isArray(err.responseData.non_field_errors) 
            ? err.responseData.non_field_errors.join('; ')
            : err.responseData.non_field_errors;
        } else if (err.responseData.detail) {
          errorMessage = err.responseData.detail;
        } else if (err.responseData.username) {
          errorMessage = Array.isArray(err.responseData.username)
            ? err.responseData.username.join('; ')
            : err.responseData.username;
        } else if (err.responseData.password) {
          errorMessage = Array.isArray(err.responseData.password)
            ? err.responseData.password.join('; ')
            : err.responseData.password;
        }
      }
      setError(errorMessage);
      showError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={styles.loginContainer}>
      <div className={styles.loginCard}>
        <h1 className={styles.title}>EMR System</h1>
        <h2 className={styles.subtitle}>Sign In</h2>
        
        {error && (
          <div className={styles.errorMessage}>{error}</div>
        )}

        <form onSubmit={handleSubmit} className={styles.loginForm}>
          <div className={styles.formGroup}>
            <label htmlFor="username">Username or email</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              disabled={isLoading}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            className={styles.submitButton}
            disabled={isLoading || !username || !password}
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
