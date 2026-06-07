import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { forgotPassword } from '../api/auth';
import { useToast } from '../hooks/useToast';
import styles from '../styles/Login.module.css';

export default function ForgotPasswordPage() {
  const [identifier, setIdentifier] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const { showError, showSuccess } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage(null);

    try {
      await forgotPassword({ identifier });
      const msg =
        'If an account exists for this username or email, a password reset link has been sent.';
      setMessage(msg);
      showSuccess(msg);
    } catch (err: any) {
      const errorMessage =
        err?.responseData?.detail ||
        (err instanceof Error ? err.message : 'Failed to request password reset');
      showError(errorMessage);
      setMessage(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.loginContainer}>
      <div className={styles.loginCard}>
        <h1 className={styles.title}>Forgot Password</h1>
        <h2 className={styles.subtitle}>Reset your account password</h2>

        {message && <div className={styles.errorMessage}>{message}</div>}

        <form onSubmit={handleSubmit} className={styles.loginForm}>
          <div className={styles.formGroup}>
            <label htmlFor="identifier">Username or email</label>
            <input
              id="identifier"
              type="text"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              disabled={isSubmitting}
            />
          </div>

          <button
            type="submit"
            className={styles.submitButton}
            disabled={isSubmitting || !identifier.trim()}
          >
            {isSubmitting ? 'Sending reset link...' : 'Send reset link'}
          </button>
        </form>

        <div style={{ marginTop: '1rem', textAlign: 'center' }}>
          <button
            type="button"
            style={{ border: 'none', background: 'none', color: '#4f46e5', cursor: 'pointer' }}
            onClick={() => navigate('/login')}
            disabled={isSubmitting}
          >
            Back to Sign In
          </button>
        </div>
      </div>
    </div>
  );
}

