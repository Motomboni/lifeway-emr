/**
 * Login Page
 *
 * Staff authentication — JWT with account lockout protection.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import AuthShell from '../components/auth/AuthShell';
import { APP_SHORT_NAME } from '../config/branding';
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

      const storedUser = localStorage.getItem('auth_user');
      const userData = storedUser ? JSON.parse(storedUser) : null;

      if (onLoginSuccess) {
        onLoginSuccess();
      } else if (userData?.role === 'PATIENT') {
        navigate('/patient-portal/dashboard', { replace: true });
      } else {
        navigate('/dashboard', { replace: true });
      }
    } catch (err: any) {
      let errorMessage = 'Login failed';
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (err?.responseData) {
        if (err.responseData.detail) {
          errorMessage =
            typeof err.responseData.detail === 'string'
              ? err.responseData.detail
              : String(err.responseData.detail);
        } else if (err.responseData.non_field_errors) {
          errorMessage = Array.isArray(err.responseData.non_field_errors)
            ? err.responseData.non_field_errors.join('; ')
            : err.responseData.non_field_errors;
        }
      }
      setError(errorMessage);
      showError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthShell title={APP_SHORT_NAME} subtitle="Staff sign in">
      {error && (
        <div className={styles.errorMessage} role="alert" aria-live="assertive">
          {error}
        </div>
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
            autoComplete="username"
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
            autoComplete="current-password"
            disabled={isLoading}
          />
        </div>

        <button
          type="submit"
          className={styles.submitButton}
          disabled={isLoading || !username || !password}
        >
          {isLoading ? 'Signing in…' : 'Sign In'}
        </button>
      </form>

      <div className={styles.footerLinks}>
        <button
          type="button"
          className={styles.linkButton}
          onClick={() => navigate('/forgot-password')}
          disabled={isLoading}
        >
          Forgot password?
        </button>
        <button
          type="button"
          className={styles.linkButton}
          onClick={() => navigate('/otp-login')}
          disabled={isLoading}
        >
          Patient portal login
        </button>
      </div>
    </AuthShell>
  );
}
