/**
 * Wallet Top-Up Button Component
 * 
 * Allows patients to top up their wallet from visit details page.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import { getMyWallet, topUpWallet, getPaymentChannels } from '../../api/wallet';
import { Wallet, PaymentChannel, WalletTopUpRequest } from '../../types/wallet';
import LoadingSpinner from '../common/LoadingSpinner';
import styles from '../../styles/Wallet.module.css';

interface WalletTopUpButtonProps {
  onTopUpSuccess?: () => void;
}

export default function WalletTopUpButton({ onTopUpSuccess }: WalletTopUpButtonProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [paymentChannels, setPaymentChannels] = useState<PaymentChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [topUpAmount, setTopUpAmount] = useState('');
  const [selectedChannel, setSelectedChannel] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (user?.role === 'PATIENT') {
      loadWalletData();
    }
  }, [user]);

  const loadWalletData = async () => {
    try {
      setLoading(true);
      const [walletData, channels] = await Promise.all([
        getMyWallet(),
        getPaymentChannels(),
      ]);
      setWallet(walletData);
      setPaymentChannels(channels);
      
      // Pre-select Paystack if available
      const paystackChannel = channels.find(c => 
        c.name.toLowerCase().includes('paystack')
      );
      if (paystackChannel) {
        setSelectedChannel(paystackChannel.id);
      } else if (channels.length > 0) {
        setSelectedChannel(channels[0].id);
      }
    } catch (error) {
      console.warn('Failed to load wallet:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTopUp = async () => {
    if (!wallet || !selectedChannel || !topUpAmount) {
      showError('Please fill all fields');
      return;
    }

    const amount = parseFloat(topUpAmount);
    if (isNaN(amount) || amount <= 0) {
      showError('Please enter a valid amount');
      return;
    }

    setIsProcessing(true);
    try {
      const request: WalletTopUpRequest = {
        amount,
        payment_channel_id: selectedChannel,
        callback_url: `${window.location.origin}/wallet/callback`,
      };

      const response = await topUpWallet(wallet.id, request);
      
      // Redirect to payment gateway (Paystack, etc.)
      if (response.authorization_url) {
        window.location.href = response.authorization_url;
      } else {
        showError('Failed to initialize payment');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to top up wallet';
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

  return (
    <div className={styles.walletTopUpButton}>
      {!showForm ? (
        <button
          className={styles.topUpButton}
          onClick={() => setShowForm(true)}
        >
          💳 Top Up Wallet
        </button>
      ) : (
        <div className={styles.topUpForm}>
          <div className={styles.formGroup}>
            <label>Amount (NGN)</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={topUpAmount}
              onChange={(e) => setTopUpAmount(e.target.value)}
              placeholder="Enter amount"
            />
          </div>

          <div className={styles.formGroup}>
            <label>Payment Method</label>
            <select
              value={selectedChannel || ''}
              onChange={(e) => setSelectedChannel(parseInt(e.target.value))}
            >
              <option value="">Select payment method...</option>
              {paymentChannels.map((channel) => (
                <option key={channel.id} value={channel.id}>
                  {channel.name}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.walletBalanceInfo}>
            <span>Current Balance: ₦{walletBalance.toFixed(2)}</span>
          </div>

          <div className={styles.formActions}>
            <button
              className={styles.cancelButton}
              onClick={() => {
                setShowForm(false);
                setTopUpAmount('');
              }}
              disabled={isProcessing}
            >
              Cancel
            </button>
            <button
              className={styles.submitButton}
              onClick={handleTopUp}
              disabled={isProcessing || !topUpAmount || !selectedChannel}
            >
              {isProcessing ? 'Processing...' : 'Proceed to Payment'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
