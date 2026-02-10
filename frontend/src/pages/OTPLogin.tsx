/**
 * OTP Login Page
 * 
 * Passwordless login for patient portal.
 * - Step 1: Enter email/phone, select channel
 * - Step 2: Enter 6-digit OTP
 * - Mobile-optimized UI
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

interface OTPLoginProps {
  onLoginSuccess?: (tokens: { access: string; refresh: string; user: any }) => void;
}

export default function OTPLogin({ onLoginSuccess }: OTPLoginProps) {
  const navigate = useNavigate();
  
  // Step 1: Request OTP
  const [step, setStep] = useState<'request' | 'verify'>('request');
  const [identifier, setIdentifier] = useState('');
  const [identifierType, setIdentifierType] = useState<'email' | 'phone'>('email');
  const [channel, setChannel] = useState<'email' | 'sms' | 'whatsapp'>('whatsapp');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Step 2: Verify OTP
  const [otpCode, setOtpCode] = useState('');
  const [maskedRecipient, setMaskedRecipient] = useState('');

  const handleRequestOTP = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const payload: any = { channel };
      
      if (identifierType === 'email') {
        payload.email = identifier;
      } else {
        payload.phone = identifier;
      }

      const response = await fetch('/api/v1/auth/request-otp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (data.success) {
        setMaskedRecipient(data.recipient);
        setStep('verify');
      } else {
        setError(data.detail || data.error || 'Failed to send OTP');
      }

    } catch (err: any) {
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
      const payload: any = {
        otp_code: otpCode,
        device_type: /iPhone|iPad/.test(navigator.userAgent) ? 'ios' 
                   : /Android/.test(navigator.userAgent) ? 'android' 
                   : 'web'
      };
      
      if (identifierType === 'email') {
        payload.email = identifier;
      } else {
        payload.phone = identifier;
      }

      const response = await fetch('/api/v1/auth/verify-otp/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (data.success) {
        // Store tokens
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('user', JSON.stringify(data.user));
        localStorage.setItem('auth_tokens', JSON.stringify({ access: data.access, refresh: data.refresh }));
        if (data.user) localStorage.setItem('auth_user', JSON.stringify(data.user));

        // Optional: register biometric for next time (patient portal)
        if (data.user?.role === 'PATIENT') {
          const deviceId = localStorage.getItem('emr_biometric_device_id') || 'web-' + Math.random().toString(36).slice(2) + '-' + Date.now();
          localStorage.setItem('emr_biometric_device_id', deviceId);
          const biometricToken = 'tk-' + Math.random().toString(36).slice(2) + Date.now();
          try {
            await fetch('/api/v1/auth/register-biometric/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${data.access}` },
              body: JSON.stringify({ device_id: deviceId, biometric_token: biometricToken }),
            });
            localStorage.setItem('emr_biometric_token', biometricToken);
          } catch (_) { /* ignore */ }
        }

        if (onLoginSuccess) {
          onLoginSuccess({
            access: data.access,
            refresh: data.refresh,
            user: data.user
          });
        } else {
          navigate('/patient-portal/dashboard');
        }
      } else {
        setError(data.detail || data.error || 'Invalid OTP');
      }

    } catch (err: any) {
      setError('Network error. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleResendOTP = () => {
    setStep('request');
    setOtpCode('');
    setError('');
  };

  // Step 1: Request OTP
  if (step === 'request') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
          {/* Logo/Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-blue-600 rounded-full mx-auto mb-4 flex items-center justify-center">
              <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Patient Portal</h1>
            <p className="text-gray-600 mt-2">Secure passwordless login</p>
          </div>

          <form onSubmit={handleRequestOTP} className="space-y-6">
            {/* Identifier Type Toggle */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <button
                type="button"
                onClick={() => setIdentifierType('email')}
                className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
                  identifierType === 'email'
                    ? 'bg-white text-blue-600 shadow'
                    : 'text-gray-600'
                }`}
              >
                Email
              </button>
              <button
                type="button"
                onClick={() => setIdentifierType('phone')}
                className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
                  identifierType === 'phone'
                    ? 'bg-white text-blue-600 shadow'
                    : 'text-gray-600'
                }`}
              >
                Phone
              </button>
            </div>

            {/* Identifier Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {identifierType === 'email' ? 'Email Address' : 'Phone Number'}
              </label>
              <input
                type={identifierType === 'email' ? 'email' : 'tel'}
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder={identifierType === 'email' ? 'patient@example.com' : '0801 234 5678'}
                className="w-full px-4 py-3 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
                disabled={isLoading}
              />
            </div>

            {/* Channel Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">
                How would you like to receive your code?
              </label>
              
              <div className="space-y-2">
                {identifierType === 'email' && (
                  <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                    <input
                      type="radio"
                      name="channel"
                      value="email"
                      checked={channel === 'email'}
                      onChange={(e) => setChannel(e.target.value as any)}
                      className="w-5 h-5 text-blue-600"
                      disabled={isLoading}
                    />
                    <div className="ml-3 flex items-center">
                      <span className="text-2xl mr-2">📧</span>
                      <span className="font-medium">Email</span>
                    </div>
                  </label>
                )}
                
                {identifierType === 'phone' && (
                  <>
                    <label className={`flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors ${
                      channel === 'whatsapp' ? 'border-green-500 bg-green-50' : 'border-gray-300'
                    }`}>
                      <input
                        type="radio"
                        name="channel"
                        value="whatsapp"
                        checked={channel === 'whatsapp'}
                        onChange={(e) => setChannel(e.target.value as any)}
                        className="w-5 h-5 text-green-600"
                        disabled={isLoading}
                      />
                      <div className="ml-3 flex items-center">
                        <span className="text-2xl mr-2">💬</span>
                        <div>
                          <span className="font-medium block">WhatsApp</span>
                          <span className="text-xs text-gray-500">Recommended for Nigeria</span>
                        </div>
                      </div>
                    </label>
                    
                    <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
                      <input
                        type="radio"
                        name="channel"
                        value="sms"
                        checked={channel === 'sms'}
                        onChange={(e) => setChannel(e.target.value as any)}
                        className="w-5 h-5 text-blue-600"
                        disabled={isLoading}
                      />
                      <div className="ml-3 flex items-center">
                        <span className="text-2xl mr-2">📱</span>
                        <span className="font-medium">SMS</span>
                      </div>
                    </label>
                  </>
                )}
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading || !identifier}
              className="w-full py-3 px-4 bg-blue-600 text-white text-lg font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
            >
              {isLoading ? (
                <>
                  <svg className="animate-spin h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Sending...
                </>
              ) : (
                'Send Login Code'
              )}
            </button>
          </form>

          {/* Footer */}
          <div className="mt-6 text-center text-sm text-gray-600">
            <p>Secure passwordless login</p>
            <p className="mt-1">Code expires in 5 minutes</p>
          </div>
        </div>
      </div>
    );
  }

  // Step 2: Verify OTP
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-full mx-auto mb-4 flex items-center justify-center">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Enter Code</h1>
          <p className="text-gray-600 mt-2">
            Code sent to <span className="font-medium">{maskedRecipient}</span>
          </p>
        </div>

        <form onSubmit={handleVerifyOTP} className="space-y-6">
          {/* OTP Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 text-center">
              Enter 6-Digit Code
            </label>
            <input
              type="text"
              inputMode="numeric"
              pattern="\d{6}"
              maxLength={6}
              value={otpCode}
              onChange={(e) => {
                const value = e.target.value.replace(/\D/g, '');
                setOtpCode(value);
                setError('');
              }}
              placeholder="000000"
              className="w-full px-4 py-4 text-center text-3xl font-bold tracking-widest border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              required
              disabled={isLoading}
              autoFocus
            />
            <p className="text-xs text-gray-500 text-center mt-2">
              Code expires in 5 minutes
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Verify Button */}
          <button
            type="submit"
            disabled={isLoading || otpCode.length !== 6}
            className="w-full py-3 px-4 bg-blue-600 text-white text-lg font-medium rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Verifying...' : 'Verify Code'}
          </button>

          {/* Resend */}
          <div className="text-center">
            <button
              type="button"
              onClick={handleResendOTP}
              disabled={isLoading}
              className="text-blue-600 hover:text-blue-700 font-medium text-sm disabled:opacity-50"
            >
              Didn't receive code? Send again
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
