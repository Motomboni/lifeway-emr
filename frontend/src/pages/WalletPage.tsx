/**
 * Wallet Page
 * 
 * View wallet balance, transactions, and top up wallet.
 */
import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import {
  getMyWallet,
  getWalletTransactions,
  topUpWallet,
  verifyPayment,
  getPaymentChannels,
} from '../api/wallet';
import {
  Wallet,
  WalletTransaction,
  PaymentChannel,
  WalletTopUpRequest,
} from '../types/wallet';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/Wallet.module.css';

export default function WalletPage() {
  const { user } = useAuth();
  const location = useLocation();
  const { showSuccess, showError } = useToast();

  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [paymentChannels, setPaymentChannels] = useState<PaymentChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showTopUpForm, setShowTopUpForm] = useState(false);
  const [topUpAmount, setTopUpAmount] = useState('');
  const [selectedChannel, setSelectedChannel] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    loadWalletData();
  }, []);

  const loadWalletData = async () => {
    try {
      setLoading(true);
      const [walletData, channels] = await Promise.all([
        getMyWallet(),
        getPaymentChannels(),
      ]);
      setWallet(walletData);
      setPaymentChannels(channels);
      
      if (walletData) {
        const txns = await getWalletTransactions(walletData.id);
        setTransactions(txns);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load wallet';
      showError(errorMessage);
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
      
      // Redirect to Paystack payment page
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

  const formatCurrency = (amount: string) => {
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: wallet?.currency || 'NGN',
    }).format(parseFloat(amount));
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className={styles.walletContainer}>
        <BackToDashboard />
        <LoadingSkeleton count={5} />
      </div>
    );
  }

  if (!wallet) {
    return (
      <div className={styles.walletContainer}>
        <BackToDashboard />
        <div className={styles.errorMessage}>
          <p>Wallet not found. Please contact support.</p>
          <p style={{ fontSize: '0.9rem', marginTop: '8px', opacity: 0.8 }}>
            If you just registered, please try refreshing the page or logging out and back in.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.walletContainer}>
      <BackToDashboard />
      <div className={styles.walletCard}>
        <div className={styles.walletHeader}>
          <h1>My Wallet</h1>
          <div className={styles.balanceCard}>
            <div className={styles.balanceLabel}>Current Balance</div>
            <div className={styles.balanceAmount}>{formatCurrency(wallet.balance)}</div>
          </div>
        </div>

        <div className={styles.walletActions}>
          <button
            className={styles.topUpButton}
            onClick={() => setShowTopUpForm(!showTopUpForm)}
            type="button"
          >
            {showTopUpForm ? 'Cancel Top Up' : '➕ Top Up Wallet'}
          </button>
        </div>

        {showTopUpForm && (
          <div className={styles.topUpForm}>
            <h3>Top Up Wallet</h3>
            <div className={styles.formGroup}>
              <label>Amount</label>
              <input
                type="number"
                min="0.01"
                step="0.01"
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
                <option value="">Select payment method</option>
                {paymentChannels
                  .filter((channel) => {
                    // Only show online payment channels for wallet top-up
                    // CASH, BANK_TRANSFER, etc. cannot be used for online top-ups
                    const onlineChannels = ['PAYSTACK', 'CARD'];
                    return onlineChannels.includes(channel.channel_type);
                  })
                  .map((channel) => (
                    <option key={channel.id} value={channel.id}>
                      {channel.name}
                    </option>
                  ))}
              </select>
            </div>
            <button
              className={styles.submitButton}
              onClick={handleTopUp}
              disabled={isProcessing}
            >
              {isProcessing ? 'Processing...' : 'Continue to Payment'}
            </button>
          </div>
        )}

        <div className={styles.transactionsSection}>
          <h2>Transaction History</h2>
          {transactions.length === 0 ? (
            <p className={styles.emptyMessage}>No transactions yet</p>
          ) : (
            <div className={styles.transactionsList}>
              {transactions.map((txn) => (
                <div key={txn.id} className={styles.transactionItem}>
                  <div className={styles.transactionInfo}>
                    <div className={styles.transactionType}>
                      <span className={txn.transaction_type === 'CREDIT' ? styles.credit : styles.debit}>
                        {txn.transaction_type}
                      </span>
                      <span className={styles.amount}>
                        {txn.transaction_type === 'CREDIT' ? '+' : '-'}
                        {formatCurrency(txn.amount)}
                      </span>
                    </div>
                    <div className={styles.transactionDetails}>
                      <p>{txn.description || 'No description'}</p>
                      <p className={styles.transactionMeta}>
                        {formatDate(txn.created_at)} • Balance: {formatCurrency(txn.balance_after)}
                      </p>
                    </div>
                  </div>
                  <div className={styles.transactionStatus}>
                    <span className={`${styles.statusBadge} ${styles[txn.status.toLowerCase()]}`}>
                      {txn.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
