/**
 * Biometric Login Page
 *
 * "Login with Face ID / Fingerprint" with fallback to OTP.
 * Biometric is supported after user has logged in via OTP and registered a device.
 */
import React, { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';

const BIOMETRIC_DEVICE_ID_KEY = 'emr_biometric_device_id';
const BIOMETRIC_TOKEN_KEY = 'emr_biometric_token';

function getStoredDeviceId(): string {
  let id = localStorage.getItem(BIOMETRIC_DEVICE_ID_KEY);
  if (!id) {
    id = 'web-' + Math.random().toString(36).slice(2) + '-' + Date.now();
    localStorage.setItem(BIOMETRIC_DEVICE_ID_KEY, id);
  }
  return id;
}

export default function BiometricLoginPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBiometricLogin = useCallback(async () => {
    setError(null);
    setLoading(true);
    const deviceId = getStoredDeviceId();
    const token = localStorage.getItem(BIOMETRIC_TOKEN_KEY);
    if (!token) {
      setError('Biometric not set up. Log in with OTP first, then enable Face ID / Fingerprint.');
      setLoading(false);
      return;
    }
    try {
      const res = await fetch('/api/v1/auth/biometric-login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_id: deviceId, biometric_token: token }),
      });
      const data = await res.json();
      if (data.success && data.access) {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('auth_tokens', JSON.stringify({ access: data.access, refresh: data.refresh }));
        if (data.user) {
          localStorage.setItem('auth_user', JSON.stringify(data.user));
          localStorage.setItem('user', JSON.stringify(data.user));
        }
        navigate('/patient-portal/dashboard', { replace: true });
        return;
      }
      setError(data.detail || data.error || 'Biometric login failed. Use OTP instead.');
    } catch (err) {
      setError('Network error. Try OTP login.');
    } finally {
      setLoading(false);
    }
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div
            className="w-20 h-20 bg-indigo-100 rounded-full mx-auto mb-4 flex items-center justify-center"
            aria-hidden
          >
            <svg
              className="w-10 h-10 text-indigo-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Patient Portal</h1>
          <p className="text-gray-600 mt-2">Sign in with biometrics or OTP</p>
        </div>

        {error && (
          <div
            className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-sm"
            role="alert"
          >
            {error}
          </div>
        )}

        <button
          type="button"
          onClick={handleBiometricLogin}
          disabled={loading}
          className="w-full py-4 px-4 bg-indigo-600 text-white text-lg font-semibold rounded-xl hover:bg-indigo-700 focus:ring-4 focus:ring-indigo-300 disabled:opacity-50 transition-colors flex items-center justify-center gap-3 min-h-[56px]"
          style={{ minHeight: 56 }}
        >
          {loading ? (
            <>
              <svg
                className="animate-spin h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              Verifying...
            </>
          ) : (
            <>
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 11c0 3.517-1.009 6.799-2.753 9.571m-3.44-2.04l.054-.09A13.916 13.916 0 008 11a4 4 0 118 0c0 1.017-.07 2.019-.203 3m-2.118 6.844A21.88 21.88 0 0015.171 17m3.839 1.132c.645-2.266.99-4.659.99-7.132A8 8 0 008 4.07M3 15.364c.64-1.319 1-2.8 1-4.364 0-1.457.39-2.823 1.07-4"
                />
              </svg>
              Login with Face ID / Fingerprint
            </>
          )}
        </button>

        <div className="mt-6 text-center">
          <Link
            to="/otp-login"
            className="text-indigo-600 font-medium hover:underline focus:ring-2 focus:ring-indigo-400 rounded"
          >
            Use OTP instead
          </Link>
        </div>
      </div>
    </div>
  );
}

export { BIOMETRIC_DEVICE_ID_KEY, BIOMETRIC_TOKEN_KEY };
