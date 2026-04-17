import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { updateAccount, AccountUpdateRequest } from '../api/auth';
import { useToast } from '../hooks/useToast';
import { useAuth } from '../contexts/AuthContext';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/Login.module.css';

export default function AccountSettingsPage() {
  const { user, logout } = useAuth();
  const { showError, showSuccess } = useToast();
  const navigate = useNavigate();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [newEmail, setNewEmail] = useState(user?.email || '');
  const [newUsername, setNewUsername] = useState(user?.username || '');
  const [newSpecialization, setNewSpecialization] = useState(user?.specialization || '');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    const payload: AccountUpdateRequest = {
      current_password: currentPassword,
    };
    const trimmedEmail = newEmail.trim();
    const trimmedUsername = newUsername.trim();

    if (newPassword || confirmNewPassword) {
      payload.new_password = newPassword;
      payload.new_password_confirm = confirmNewPassword;
    }
    if (trimmedEmail && trimmedEmail !== user?.email) {
      payload.new_email = trimmedEmail;
    }
    if (trimmedUsername && trimmedUsername !== user?.username) {
      payload.new_username = trimmedUsername;
    }
    if (user?.role === 'DOCTOR') {
      const trimmedSpecialization = newSpecialization.trim();
      if (!trimmedSpecialization) {
        showError('Specialization is required for doctors.');
        setIsSubmitting(false);
        return;
      }
      if (trimmedSpecialization !== (user?.specialization || '').trim()) {
        payload.new_specialization = trimmedSpecialization;
      }
    }

    try {
      const updated = await updateAccount(payload);
      showSuccess('Account updated successfully.');

      const passwordChanged = !!payload.new_password;
      if (passwordChanged) {
        // Force re-login on password change
        await logout();
        navigate('/login', { replace: true });
      } else {
        // Reload or navigate to dashboard to reflect changes
        navigate('/dashboard');
      }
    } catch (err: any) {
      const data = err?.responseData || {};
      const firstError =
        data.current_password?.[0] ||
        data.new_password?.[0] ||
        data.new_email?.[0] ||
        data.new_username?.[0] ||
        data.new_specialization?.[0] ||
        data.detail ||
        (err instanceof Error ? err.message : 'Failed to update account');
      showError(firstError);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={styles.loginContainer}>
      <div className={styles.loginCard} style={{ maxWidth: 520 }}>
        <BackToDashboard />
        <h1 className={styles.title}>Account Settings</h1>
        <h2 className={styles.subtitle}>Update your account details</h2>

        <form onSubmit={handleSubmit} className={styles.loginForm}>
          <div className={styles.formGroup}>
            <label htmlFor="currentPassword">Current password</label>
            <input
              id="currentPassword"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              disabled={isSubmitting}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="newPassword">New password (optional)</label>
            <input
              id="newPassword"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="confirmNewPassword">Confirm new password</label>
            <input
              id="confirmNewPassword"
              type="password"
              value={confirmNewPassword}
              onChange={(e) => setConfirmNewPassword(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="newEmail">Email (optional)</label>
            <input
              id="newEmail"
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="newUsername">Username (optional)</label>
            <input
              id="newUsername"
              type="text"
              value={newUsername}
              onChange={(e) => setNewUsername(e.target.value)}
              disabled={isSubmitting}
            />
          </div>

          {user?.role === 'DOCTOR' && (
            <div className={styles.formGroup}>
              <label htmlFor="newSpecialization">Specialization</label>
              <input
                id="newSpecialization"
                type="text"
                value={newSpecialization}
                onChange={(e) => setNewSpecialization(e.target.value)}
                disabled={isSubmitting}
                placeholder="e.g. Gynaecologist"
              />
            </div>
          )}

          <button
            type="submit"
            className={styles.submitButton}
            disabled={isSubmitting || !currentPassword}
          >
            {isSubmitting ? 'Saving changes...' : 'Save Changes'}
          </button>
        </form>
      </div>
    </div>
  );
}

