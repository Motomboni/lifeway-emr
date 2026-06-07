import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { resetPassword } from '../api/auth';
import { useToast } from '../hooks/useToast';
import styles from '../styles/Login.module.css';

function useQuery() {
  return new URLSearchParams(useLocation().search);
}

export default function ResetPasswordPage() {
  const query = useQuery();
  const uid = query.get('uid') || '';
  const token = query.get('token') || '';

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const { showError, showSuccess } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setMessage(null);

    if (!uid || !token) {
      const msg = 'Invalid or expired reset link.';
      setMessage(msg);
      showError(msg);
      setIsSubmitting(false);
      return;
    }

    try {
      await resetPassword({
        uid,
        token,
        new_password: newPassword,
        new_password_confirm: confirmPassword,
      });
      const msg = 'Your password has been reset successfully. You can now sign in.';
      showSuccess(msg);
      setMessage(msg);
      setTimeout(() => navigate('/login'), 1200);
    } catch (err: any) {
      const errorMessage =
        err?.responseData?.detail ||
        err?.responseData?.new_password?.[0] ||
        (err instanceof Error ? err.message : 'Failed to reset password');
      showError(errorMessage);
      setMessage(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.loginContainer}>
      <div className={styles.loginCard}>
        <h1 className={styles.title}>Reset Password</h1>
        <h2 className={styles.subtitle}>Choose a new password</h2>

        {message && <div className={styles.errorMessage}>{message}</div>}

        <form onSubmit={handleSubmit} className={styles.loginForm}>
          <div className={styles.formGroup}>
            <label htmlFor="newPassword">New password</label>
            <input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              disabled={isSubmitting}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="confirmPassword">Confirm new password</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={isSubmitting}
            />
          </div>

          <button
            type="submit"
            className={styles.submitButton}
            disabled={
              isSubmitting || !newPassword || !confirmPassword || newPassword !== confirmPassword
            }
          >
            {isSubmitting ? 'Resetting password...' : 'Reset Password'}
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

