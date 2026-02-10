/**
 * Wallet Payment Button Component
 * 
 * Allows patients to pay for visits using their wallet balance.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import { getMyWallet, payVisitWithWallet } from '../../api/wallet';
import { Wallet } from '../../types/wallet';
import LoadingSpinner from '../common/LoadingSpinner';
import styles from '../../styles/Wallet.module.css';

interface WalletPaymentButtonProps {
  visitId: number;
  amount: number;
  onPaymentSuccess?: () => void;
}

export default function WalletPaymentButton({
  visitId,
  amount,
  onPaymentSuccess,
}: WalletPaymentButtonProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [loading, setLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (user?.role === 'PATIENT') {
      loadWallet();
    }
  }, [user]);

  const loadWallet = async () => {
    try {
      const walletData = await getMyWallet();
      setWallet(walletData);
    } catch (error) {
      console.warn('Failed to load wallet:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePayWithWallet = async () => {
    if (!wallet) {
      showError('Wallet not found');
      return;
    }

    const walletBalance = parseFloat(wallet.balance);
    if (walletBalance < amount) {
      showError('Insufficient wallet balance. Please top up your wallet.');
      return;
    }

    if (!window.confirm(`Pay ₦${amount.toFixed(2)} from your wallet?`)) {
      return;
    }

    setIsProcessing(true);
    try {
      await payVisitWithWallet(wallet.id, {
        visit_id: visitId,
        amount,
        description: `Payment for visit ${visitId}`,
      });

      showSuccess('Payment successful! Visit payment cleared.');
      
      // Reload wallet to show updated balance
      await loadWallet();
      
      if (onPaymentSuccess) {
        onPaymentSuccess();
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Payment failed';
      showError(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  };

  if (user?.role !== 'PATIENT') {
    return null;
  }

  if (loading) {
    return <LoadingSpinner size="small" />;
  }

  if (!wallet) {
    return null;
  }

  const walletBalance = parseFloat(wallet.balance);
  const hasSufficientBalance = walletBalance >= amount;

  return (
    <div className={styles.walletPaymentButton}>
      <div className={styles.walletBalanceInfo}>
        <span>Wallet Balance: ₦{walletBalance.toFixed(2)}</span>
        {!hasSufficientBalance && (
          <span className={styles.insufficientBalance}>
            Insufficient balance
          </span>
        )}
      </div>
      <button
        className={styles.payWithWalletButton}
        onClick={handlePayWithWallet}
        disabled={isProcessing || !hasSufficientBalance}
      >
        {isProcessing ? (
          <>
            <LoadingSpinner size="small" />
            Processing...
          </>
        ) : (
          `Pay ₦${amount.toFixed(2)} with Wallet`
        )}
      </button>
    </div>
  );
}
