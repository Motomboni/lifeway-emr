/**
 * OTP Login — passwordless patient portal access.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AuthShell from '../components/auth/AuthShell';
import styles from '../styles/OTPLogin.module.css';
import loginStyles from '../styles/Login.module.css';

interface OTPLoginProps {
  onLoginSuccess?: (tokens: { access: string; refresh: string; user: unknown }) => void;
}

export default function OTPLogin({ onLoginSuccess }: OTPLoginProps) {
  const navigate = useNavigate();

  const [step, setStep] = useState<'request' | 'verify'>('request');
  const [identifier, setIdentifier] = useState('');
  const [identifierType, setIdentifierType] = useState<'email' | 'phone'>('email');
  const [channel, setChannel] = useState<'email' | 'sms' | 'whatsapp'>('email');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [maskedRecipient, setMaskedRecipient] = useState('');

  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const payload: Record<string, string> = { channel };
      if (identifierType === 'email') {
        payload.email = identifier;
      } else {
        payload.phone = identifier;
      }

      const response = await fetch('/api/v1/auth/request-otp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (data.success) {
        setMaskedRecipient(data.recipient);
        setStep('verify');
      } else {
        setError(data.detail || data.error || 'Failed to send OTP');
      }
    } catch {
      setError('Network error. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleVerifyOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const payload: Record<string, string> = {
        otp_code: otpCode,
        device_type: /iPhone|iPad/.test(navigator.userAgent)
          ? 'ios'
          : /Android/.test(navigator.userAgent)
            ? 'android'
            : 'web',
      };

      if (identifierType === 'email') {
        payload.email = identifier;
      } else {
        payload.phone = identifier;
      }

      const response = await fetch('/api/v1/auth/verify-otp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (data.success) {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('user', JSON.stringify(data.user));
        localStorage.setItem(
          'auth_tokens',
          JSON.stringify({ access: data.access, refresh: data.refresh })
        );
        if (data.user) {
          localStorage.setItem('auth_user', JSON.stringify(data.user));
        }

        if (onLoginSuccess) {
          onLoginSuccess({ access: data.access, refresh: data.refresh, user: data.user });
        } else {
          navigate('/patient-portal/dashboard');
        }
      } else {
        setError(data.detail || data.error || 'Invalid OTP');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  if (step === 'request') {
    return (
      <AuthShell title="Patient Portal" subtitle="Secure passwordless login">
        {error && (
          <div className={styles.errorMessage} role="alert" aria-live="assertive">
            {error}
          </div>
        )}

        <form onSubmit={handleRequestOTP} className={styles.form}>
          <div className={styles.toggleRow}>
            <button
              type="button"
              className={`${styles.toggleButton} ${identifierType === 'email' ? styles.toggleActive : ''}`}
              onClick={() => {
                setIdentifierType('email');
                setChannel('email');
              }}
            >
              Email
            </button>
            <button
              type="button"
              className={`${styles.toggleButton} ${identifierType === 'phone' ? styles.toggleActive : ''}`}
              onClick={() => setChannel('whatsapp')}
            >
              Phone
            </button>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="otp-identifier">
              {identifierType === 'email' ? 'Email address' : 'Phone number'}
            </label>
            <input
              id="otp-identifier"
              type={identifierType === 'email' ? 'email' : 'tel'}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder={identifierType === 'email' ? 'patient@example.com' : '08012345678'}
              required
              disabled={isLoading}
              autoComplete={identifierType === 'email' ? 'email' : 'tel'}
            />
          </div>

          {identifierType === 'phone' && (
            <div className={styles.formGroup}>
              <span>Delivery channel</span>
              <div className={styles.channelList}>
                <label
                  className={`${styles.channelOption} ${channel === 'whatsapp' ? styles.channelOptionSelected : ''}`}
                >
                  <input
                    type="radio"
                    name="channel"
                    value="whatsapp"
                    checked={channel === 'whatsapp'}
                    onChange={() => setChannel('whatsapp')}
                  />
                  WhatsApp
                </label>
                <label
                  className={`${styles.channelOption} ${channel === 'sms' ? styles.channelOptionSelected : ''}`}
                >
                  <input
                    type="radio"
                    name="channel"
                    value="sms"
                    checked={channel === 'sms'}
                    onChange={() => setChannel('sms')}
                  />
                  SMS
                </label>
              </div>
            </div>
          )}

          <button type="submit" className={styles.submitButton} disabled={isLoading || !identifier}>
            {isLoading ? 'Sending…' : 'Send login code'}
          </button>
        </form>

        <div className={styles.footerLinks}>
          <button type="button" className={loginStyles.linkButton} onClick={() => navigate('/login')}>
            Staff login
          </button>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Enter code" subtitle={`Code sent to ${maskedRecipient}`}>
      {error && (
        <div className={styles.errorMessage} role="alert" aria-live="assertive">
          {error}
        </div>
      )}

      <form onSubmit={handleVerifyOTP} className={styles.form}>
        <div className={styles.formGroup}>
          <label htmlFor="otp-code">6-digit code</label>
          <input
            id="otp-code"
            type="text"
            inputMode="numeric"
            pattern="\d{6}"
            maxLength={6}
            value={otpCode}
            onChange={(e) => {
              setOtpCode(e.target.value.replace(/\D/g, ''));
              setError('');
            }}
            className={styles.otpInput}
            placeholder="000000"
            required
            disabled={isLoading}
            autoFocus
          />
          <p className={styles.hint}>Code expires in 5 minutes</p>
        </div>

        <button
          type="submit"
          className={styles.submitButton}
          disabled={isLoading || otpCode.length !== 6}
        >
          {isLoading ? 'Verifying…' : 'Verify code'}
        </button>

        <button type="button" className={styles.linkButton} onClick={() => setStep('request')} disabled={isLoading}>
          Didn&apos;t receive a code? Send again
        </button>
      </form>
    </AuthShell>
  );
}
