/**
 * Wallet Callback Page
 * 
 * Handles payment gateway callbacks (e.g., Paystack redirect).
 */
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getMyWallet, verifyPayment } from '../api/wallet';
import { useToast } from '../hooks/useToast';
import LoadingSpinner from '../components/common/LoadingSpinner';
import styles from '../styles/Wallet.module.css';

export default function WalletCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { showSuccess, showError } = useToast();
  const [status, setStatus] = useState<'verifying' | 'success' | 'error'>('verifying');

  useEffect(() => {
    const verifyPaymentCallback = async () => {
      const reference = searchParams.get('reference');
      
      if (!reference) {
        setStatus('error');
        showError('Payment reference not found');
        setTimeout(() => navigate('/wallet'), 3000);
        return;
      }

      try {
        const wallet = await getMyWallet();
        const response = await verifyPayment(wallet.id, reference);
        
        if (response.status === 'success') {
          setStatus('success');
          showSuccess('Payment successful! Wallet topped up.');
          setTimeout(() => navigate('/wallet'), 2000);
        } else {
          setStatus('error');
          showError('Payment verification failed');
          setTimeout(() => navigate('/wallet'), 3000);
        }
      } catch (error) {
        setStatus('error');
        const errorMessage = error instanceof Error ? error.message : 'Payment verification failed';
        showError(errorMessage);
        setTimeout(() => navigate('/wallet'), 3000);
      }
    };

    verifyPaymentCallback();
  }, [searchParams, navigate, showSuccess, showError]);

  return (
    <div className={styles.callbackContainer}>
      {status === 'verifying' && (
        <div className={styles.callbackContent}>
          <LoadingSpinner size="large" />
          <p>Verifying payment...</p>
        </div>
      )}
      {status === 'success' && (
        <div className={styles.callbackContent}>
          <div className={styles.successIcon}>✓</div>
          <h2>Payment Successful!</h2>
          <p>Your wallet has been topped up successfully.</p>
          <p>Redirecting to wallet page...</p>
        </div>
      )}
      {status === 'error' && (
        <div className={styles.callbackContent}>
          <div className={styles.errorIcon}>✗</div>
          <h2>Payment Failed</h2>
          <p>There was an error processing your payment.</p>
          <p>Redirecting to wallet page...</p>
        </div>
      )}
    </div>
  );
}
