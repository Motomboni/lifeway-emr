/**
 * Wallet Page
 *
 * Patients: view own wallet and top up.
 * Receptionists/Admin: search and view patient wallets (read-only).
 */
import React, { useState, useEffect, useMemo } from 'react';
import { useRolePermissions } from '../hooks/useRolePermissions';
import { useToast } from '../hooks/useToast';
import {
  getMyWallet,
  listWallets,
  getWalletTransactions,
  topUpWallet,
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
  const { isReceptionist, isAdmin } = useRolePermissions();
  const { showSuccess, showError } = useToast();

  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [allWallets, setAllWallets] = useState<Wallet[]>([]);
  const [walletSearch, setWalletSearch] = useState('');
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [paymentChannels, setPaymentChannels] = useState<PaymentChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showTopUpForm, setShowTopUpForm] = useState(false);
  const [topUpAmount, setTopUpAmount] = useState('');
  const [selectedChannel, setSelectedChannel] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const isStaffWalletView = isReceptionist || isAdmin;

  useEffect(() => {
    loadWalletData();
  }, []);

  const loadWalletForId = async (selected: Wallet) => {
    setWallet(selected);
    try {
      const txns = await getWalletTransactions(selected.id);
      setTransactions(txns);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load transactions';
      showError(errorMessage);
      setTransactions([]);
    }
  };

  const loadWalletData = async () => {
    try {
      setLoading(true);
      if (isStaffWalletView) {
        const wallets = await listWallets();
        setAllWallets(wallets);
        setPaymentChannels([]);
      } else {
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
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load wallet';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const filteredWallets = useMemo(() => {
    const q = walletSearch.trim().toLowerCase();
    if (!q) return allWallets;
    return allWallets.filter(
      (w) =>
        w.patient_name?.toLowerCase().includes(q) ||
        String(w.patient_id ?? '').toLowerCase().includes(q)
    );
  }, [allWallets, walletSearch]);

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

  if (isStaffWalletView) {
    return (
      <div className={styles.walletContainer}>
        <BackToDashboard />
        <div className={styles.walletCard}>
          <div className={styles.walletHeader}>
            <h1>Patient Wallets</h1>
            <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
              Look up a patient wallet to check balance and transaction history.
            </p>
          </div>

          <div className={styles.formGroup} style={{ marginBottom: '1.5rem' }}>
            <label>Search by patient name or ID</label>
            <input
              type="text"
              value={walletSearch}
              onChange={(e) => setWalletSearch(e.target.value)}
              placeholder="e.g. John Doe or P-00123"
            />
          </div>

          {!wallet ? (
            <div className={styles.transactionsList}>
              {filteredWallets.length === 0 ? (
                <p className={styles.emptyMessage}>No wallets found</p>
              ) : (
                filteredWallets.map((w) => (
                  <button
                    key={w.id}
                    type="button"
                    className={styles.transactionItem}
                    onClick={() => loadWalletForId(w)}
                    style={{ width: '100%', textAlign: 'left', cursor: 'pointer' }}
                  >
                    <div className={styles.transactionInfo}>
                      <strong>{w.patient_name || 'Unknown patient'}</strong>
                      <p className={styles.transactionMeta}>
                        ID: {w.patient_id || '—'} · Balance: {formatCurrency(w.balance)}
                      </p>
                    </div>
                  </button>
                ))
              )}
            </div>
          ) : (
            <>
              <button
                type="button"
                className={styles.topUpButton}
                onClick={() => {
                  setWallet(null);
                  setTransactions([]);
                }}
                style={{ marginBottom: '1rem' }}
              >
                ← Back to wallet list
              </button>
              <div className={styles.balanceCard}>
                <div className={styles.balanceLabel}>{wallet.patient_name}</div>
                <div className={styles.balanceAmount}>{formatCurrency(wallet.balance)}</div>
              </div>
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
                              {formatDate(txn.created_at)} · Balance: {formatCurrency(txn.balance_after)}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
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
                        {formatDate(txn.created_at)} · Balance: {formatCurrency(txn.balance_after)}
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
