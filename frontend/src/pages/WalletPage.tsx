/**
 * Wallet Page
 *
 * Patients: view own wallet and top up.
 * Receptionists/Admin: search for a patient wallet by name or MRN.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
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
import {
  getOnlineTopUpChannels,
  getPaymentChannelLabel,
  parsePaymentChannelId,
  pickDefaultTopUpChannelId,
} from '../utils/walletPaymentChannels';
import styles from '../styles/Wallet.module.css';

export default function WalletPage() {
  const { isReceptionist, isAdmin } = useRolePermissions();
  const { showError } = useToast();

  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [searchResults, setSearchResults] = useState<Wallet[]>([]);
  const [walletSearch, setWalletSearch] = useState('');
  const [searching, setSearching] = useState(false);
  const [transactions, setTransactions] = useState<WalletTransaction[]>([]);
  const [paymentChannels, setPaymentChannels] = useState<PaymentChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [showTopUpForm, setShowTopUpForm] = useState(false);
  const [topUpAmount, setTopUpAmount] = useState('');
  const [selectedChannel, setSelectedChannel] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isStaffWalletView = isReceptionist || isAdmin;

  const formatCurrency = useCallback(
    (amount: string, currency = wallet?.currency || 'NGN') =>
      new Intl.NumberFormat('en-NG', {
        style: 'currency',
        currency,
      }).format(parseFloat(amount)),
    [wallet?.currency]
  );

  const formatDate = (dateString: string) => new Date(dateString).toLocaleString();

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

  const loadPatientWalletData = useCallback(async () => {
    const [walletData, channels] = await Promise.all([
      getMyWallet(),
      getPaymentChannels(),
    ]);
    const onlineChannels = getOnlineTopUpChannels(channels);
    setWallet(walletData);
    setPaymentChannels(onlineChannels);
    setSelectedChannel(pickDefaultTopUpChannelId(onlineChannels));
    if (walletData) {
      const txns = await getWalletTransactions(walletData.id);
      setTransactions(txns);
    }
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        if (!isStaffWalletView) {
          await loadPatientWalletData();
        }
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to load wallet';
        showError(errorMessage);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [isStaffWalletView, loadPatientWalletData, showError]);

  useEffect(() => {
    if (!isStaffWalletView || wallet) {
      return;
    }

    const query = walletSearch.trim();
    if (query.length < 2) {
      setSearchResults([]);
      setSearching(false);
      return;
    }

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }

    setSearching(true);
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const wallets = await listWallets({ search: query });
        setSearchResults(wallets);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Wallet search failed';
        showError(errorMessage);
        setSearchResults([]);
      } finally {
        setSearching(false);
      }
    }, 350);

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, [isStaffWalletView, wallet, walletSearch, showError]);

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
            <p className={styles.pageHint}>
              Search by patient name or MRN to view balance and transaction history.
            </p>
          </div>

          {!wallet ? (
            <>
              <div className={styles.formGroup}>
                <label htmlFor="walletSearch">Search patient</label>
                <input
                  id="walletSearch"
                  type="text"
                  value={walletSearch}
                  onChange={(e) => setWalletSearch(e.target.value)}
                  placeholder="Type at least 2 characters…"
                  autoFocus
                />
              </div>

              <div className={styles.transactionsList}>
                {searching ? (
                  <p className={styles.emptyMessage}>Searching…</p>
                ) : walletSearch.trim().length < 2 ? (
                  <p className={styles.emptyMessage}>
                    Enter a patient name or MRN to find their wallet.
                  </p>
                ) : searchResults.length === 0 ? (
                  <p className={styles.emptyMessage}>No wallets found for that search.</p>
                ) : (
                  searchResults.map((w) => (
                    <button
                      key={w.id}
                      type="button"
                      className={styles.walletSearchResult}
                      onClick={() => loadWalletForId(w)}
                    >
                      <div className={styles.transactionInfo}>
                        <strong>{w.patient_name || 'Unknown patient'}</strong>
                        <p className={styles.transactionMeta}>
                          MRN: {w.patient_id || '—'} · Balance: {formatCurrency(w.balance, w.currency)}
                        </p>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </>
          ) : (
            <>
              <button
                type="button"
                className={styles.backLink}
                onClick={() => {
                  setWallet(null);
                  setTransactions([]);
                }}
              >
                ← Back to search
              </button>
              <div className={styles.balanceCard}>
                <div className={styles.balanceLabel}>{wallet.patient_name}</div>
                <div className={styles.balanceAmount}>{formatCurrency(wallet.balance)}</div>
                <p className={styles.balanceSubtext}>MRN: {wallet.patient_id}</p>
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
          <p className={styles.pageHint}>
            If you just registered, try refreshing the page or logging out and back in.
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
              <label htmlFor="walletPaymentMethod">Payment Method</label>
              <select
                id="walletPaymentMethod"
                value={selectedChannel ?? ''}
                onChange={(e) => setSelectedChannel(parsePaymentChannelId(e.target.value))}
                disabled={paymentChannels.length === 0 || isProcessing}
              >
                {paymentChannels.length === 0 ? (
                  <option value="">No online payment methods available</option>
                ) : (
                  paymentChannels.map((channel) => (
                    <option key={channel.id} value={channel.id}>
                      {getPaymentChannelLabel(channel)}
                    </option>
                  ))
                )}
              </select>
              {paymentChannels.length === 0 && (
                <p className={styles.pageHint}>
                  Online top-up is unavailable right now. Please contact the clinic.
                </p>
              )}
            </div>
            <button
              className={styles.submitButton}
              onClick={handleTopUp}
              disabled={isProcessing || !topUpAmount || !selectedChannel}
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
