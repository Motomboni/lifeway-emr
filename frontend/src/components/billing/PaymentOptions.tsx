/**
 * Payment Options Component
 * 
 * Handles all payment methods: Cash, POS, Transfer, Paystack, Wallet
 * Per EMR Rules: Receptionist-only, visit-scoped
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import {
  createPayment,
  createWalletDebit,
  initializePaystackPayment,
  verifyPaystackPayment,
  getPaymentIntents,
  PaymentCreateData,
  WalletDebitData,
  BillingSummary,
} from '../../api/billing';
import { formatCurrency, isValidAmount } from '../../utils/currency';
import { BillingPermissions } from '../../hooks/useBillingPermissions';
import { Visit } from '../../types/visit';
import { apiRequest } from '../../utils/apiClient';
import LoadingSpinner from '../common/LoadingSpinner';
import styles from './PaymentOptions.module.css';

interface PaymentOptionsProps {
  visitId: number;
  visit: Visit;
  billingSummary: BillingSummary | null;
  permissions: BillingPermissions;
  onUpdate: () => void;
}

type PaymentMethod = 'CASH' | 'POS' | 'TRANSFER' | 'PAYSTACK' | 'WALLET';

export default function PaymentOptions({
  visitId,
  visit,
  billingSummary,
  permissions,
  onUpdate,
}: PaymentOptionsProps) {
  const { showSuccess, showError } = useToast();
  const [activeMethod, setActiveMethod] = useState<PaymentMethod | null>(null);
  const [loading, setLoading] = useState(false);
  const [paymentIntents, setPaymentIntents] = useState<any[]>([]);
  const [patientWallet, setPatientWallet] = useState<any>(null);

  // Form states
  const [cashForm, setCashForm] = useState({ amount: '', notes: '' });
  const [posForm, setPosForm] = useState({
    amount: '',
    transaction_reference: '',
    notes: '',
  });
  const [transferForm, setTransferForm] = useState({
    amount: '',
    transaction_reference: '',
    notes: '',
  });
  const [paystackForm, setPaystackForm] = useState({
    amount: '',
    customer_email: '',
  });
  const [walletForm, setWalletForm] = useState({ amount: '', description: '' });

  useEffect(() => {
    if (visit.status === 'OPEN') {
      loadPaymentIntents();
    }
    loadPatientWallet();
  }, [visitId, visit.status]);

  const loadPaymentIntents = async () => {
    try {
      const intents = await getPaymentIntents(visitId);
      setPaymentIntents(intents);
    } catch (error) {
      console.error('Failed to load payment intents:', error);
    }
  };

  const loadPatientWallet = async () => {
    try {
      const wallets = await apiRequest<any>(`/wallet/wallets/`);
      const walletList = Array.isArray(wallets) ? wallets : wallets.results || [];
      // Find wallet for this visit's patient
      const wallet = walletList.find((w: any) => w.patient === visit.patient || w.patient_id === visit.patient);
      setPatientWallet(wallet || null);
    } catch (error) {
      console.error('Failed to load wallet:', error);
    }
  };

  const handleCashPayment = async () => {
    if (!isValidAmount(cashForm.amount)) {
      showError('Please enter a valid amount');
      return;
    }

    try {
      setLoading(true);
      await createPayment(visitId, {
        amount: cashForm.amount,
        payment_method: 'CASH',
        notes: cashForm.notes,
        // status is handled by backend
      });
      showSuccess('Cash payment recorded successfully');
      setCashForm({ amount: '', notes: '' });
      setActiveMethod(null);
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to record cash payment');
    } finally {
      setLoading(false);
    }
  };

  const handlePOSPayment = async () => {
    if (!isValidAmount(posForm.amount)) {
      showError('Please enter a valid amount');
      return;
    }

    try {
      setLoading(true);
      await createPayment(visitId, {
        amount: posForm.amount,
        payment_method: 'POS',
        transaction_reference: posForm.transaction_reference,
        notes: posForm.notes,
        // status is handled by backend
      });
      showSuccess('POS payment recorded successfully');
      setPosForm({ amount: '', transaction_reference: '', notes: '' });
      setActiveMethod(null);
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to record POS payment');
    } finally {
      setLoading(false);
    }
  };

  const handleTransferPayment = async () => {
    if (!isValidAmount(transferForm.amount)) {
      showError('Please enter a valid amount');
      return;
    }

    if (!transferForm.transaction_reference) {
      showError('Please enter transaction reference');
      return;
    }

    try {
      setLoading(true);
      await createPayment(visitId, {
        amount: transferForm.amount,
        payment_method: 'TRANSFER',
        transaction_reference: transferForm.transaction_reference,
        notes: transferForm.notes,
        // status is handled by backend
      });
      showSuccess('Transfer payment recorded successfully');
      setTransferForm({ amount: '', transaction_reference: '', notes: '' });
      setActiveMethod(null);
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to record transfer payment');
    } finally {
      setLoading(false);
    }
  };

  const handlePaystackPayment = async () => {
    if (!isValidAmount(paystackForm.amount)) {
      showError('Please enter a valid amount');
      return;
    }

    try {
      setLoading(true);
      const response = await initializePaystackPayment(visitId, {
        visit_id: visitId,
        amount: paystackForm.amount,
        callback_url: `${window.location.origin}/visits/${visitId}`,
        customer_email: paystackForm.customer_email || undefined,
      });

      if (response.authorization_url) {
        // Open Paystack checkout in new window
        window.open(response.authorization_url, '_blank', 'width=800,height=600');
        showSuccess('Paystack payment initialized. Complete payment in the popup window.');
        setPaystackForm({ amount: '', customer_email: '' });
        setActiveMethod(null);
        await loadPaymentIntents();
        onUpdate();
      } else {
        showError('Failed to initialize Paystack payment');
      }
    } catch (error: any) {
      showError(error.message || 'Failed to initialize Paystack payment');
    } finally {
      setLoading(false);
    }
  };

  const handleWalletPayment = async () => {
    if (!patientWallet) {
      showError('Patient wallet not found');
      return;
    }

    if (!isValidAmount(walletForm.amount)) {
      showError('Please enter a valid amount');
      return;
    }

    const amount = parseFloat(walletForm.amount);
    if (amount > parseFloat(patientWallet.balance)) {
      showError('Insufficient wallet balance');
      return;
    }

    try {
      setLoading(true);
      await createWalletDebit(visitId, {
        wallet_id: patientWallet.id,
        amount: walletForm.amount,
        description: walletForm.description || `Payment for Visit ${visitId}`,
      });
      showSuccess('Wallet payment processed successfully');
      setWalletForm({ amount: '', description: '' });
      setActiveMethod(null);
      await loadPatientWallet();
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to process wallet payment');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyPaystack = async (paymentIntent: any) => {
    if (!paymentIntent.paystack_reference) {
      showError('Payment reference not found');
      return;
    }

    try {
      setLoading(true);
      await verifyPaystackPayment(visitId, paymentIntent.id, paymentIntent.paystack_reference);
      showSuccess('Payment verified successfully');
      await loadPaymentIntents();
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to verify payment');
    } finally {
      setLoading(false);
    }
  };

  const outstandingBalance = billingSummary
    ? parseFloat(billingSummary.outstanding_balance)
    : 0;

  const isVisitClosed = visit.status === 'CLOSED';
  const isInsuranceVisit = visit.payment_type === 'INSURANCE';

  if (!permissions.canProcessPayments) {
    return (
      <div className={styles.permissionMessage}>
        <p className={styles.permissionText}>Only Receptionists can process payments.</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Outstanding Balance */}
      {outstandingBalance > 0 && (
        <div className={styles.outstandingBalance}>
          <div className={styles.outstandingBalanceContent}>
            <div>
              <p className={styles.outstandingBalanceText}>Outstanding Balance</p>
              <p className={styles.outstandingBalanceAmount}>
                {formatCurrency(outstandingBalance.toString())}
              </p>
            </div>
            <span style={{ fontSize: '2rem' }}>⚠️</span>
          </div>
        </div>
      )}

      {/* Payment Methods Grid */}
      <div className={styles.paymentMethodsGrid}>
        {/* Cash Payment */}
        <button
          onClick={() => setActiveMethod(activeMethod === 'CASH' ? null : 'CASH')}
          disabled={isVisitClosed || isInsuranceVisit}
          className={`${styles.paymentMethodButton} ${activeMethod === 'CASH' ? styles.paymentMethodButtonActive : ''}`}
        >
          <div className={styles.paymentMethodIcon}>💵</div>
          <div className={styles.paymentMethodTitle}>Cash</div>
          <div className={styles.paymentMethodDescription}>Physical cash payment</div>
        </button>

        {/* POS Payment */}
        <button
          onClick={() => setActiveMethod(activeMethod === 'POS' ? null : 'POS')}
          disabled={isVisitClosed}
          className={`${styles.paymentMethodButton} ${activeMethod === 'POS' ? styles.paymentMethodButtonActive : ''}`}
        >
          <div className={styles.paymentMethodIcon}>💳</div>
          <div className={styles.paymentMethodTitle}>POS</div>
          <div className={styles.paymentMethodDescription}>Point of Sale card payment</div>
        </button>

        {/* Bank Transfer */}
        <button
          onClick={() => setActiveMethod(activeMethod === 'TRANSFER' ? null : 'TRANSFER')}
          disabled={isVisitClosed}
          className={`${styles.paymentMethodButton} ${activeMethod === 'TRANSFER' ? styles.paymentMethodButtonActive : ''}`}
        >
          <div className={styles.paymentMethodIcon}>🏦</div>
          <div className={styles.paymentMethodTitle}>Bank Transfer</div>
          <div className={styles.paymentMethodDescription}>Bank transfer payment</div>
        </button>

        {/* Paystack */}
        <button
          onClick={() => setActiveMethod(activeMethod === 'PAYSTACK' ? null : 'PAYSTACK')}
          disabled={isVisitClosed || isInsuranceVisit}
          className={`${styles.paymentMethodButton} ${activeMethod === 'PAYSTACK' ? styles.paymentMethodButtonActive : ''}`}
        >
          <div className={styles.paymentMethodIcon}>🌐</div>
          <div className={styles.paymentMethodTitle}>Paystack</div>
          <div className={styles.paymentMethodDescription}>Online payment gateway</div>
        </button>

        {/* Wallet */}
        <button
          onClick={() => setActiveMethod(activeMethod === 'WALLET' ? null : 'WALLET')}
          disabled={isVisitClosed || !patientWallet || parseFloat(patientWallet.balance) <= 0}
          className={`${styles.paymentMethodButton} ${activeMethod === 'WALLET' ? styles.paymentMethodButtonActive : ''}`}
        >
          <div className={styles.paymentMethodIcon}>💼</div>
          <div className={styles.paymentMethodTitle}>Wallet</div>
          <div className={styles.paymentMethodDescription}>
            {patientWallet
              ? `Balance: ${formatCurrency(patientWallet.balance)}`
              : 'No wallet found'}
          </div>
        </button>
      </div>

      {/* Payment Forms */}
      {activeMethod === 'CASH' && (
        <div className={styles.paymentForm}>
          <h4 className={styles.paymentFormTitle}>Cash Payment</h4>
          <div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Amount (₦) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={cashForm.amount}
                onChange={(e) => setCashForm({ ...cashForm, amount: e.target.value })}
                className={styles.formInput}
                placeholder="Enter amount"
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Notes</label>
              <textarea
                value={cashForm.notes}
                onChange={(e) => setCashForm({ ...cashForm, notes: e.target.value })}
                className={styles.formTextarea}
                rows={2}
                placeholder="Optional notes"
              />
            </div>
            <button
              onClick={handleCashPayment}
              disabled={loading || !isValidAmount(cashForm.amount)}
              className={`${styles.submitButton} ${styles.submitButtonCash}`}
            >
              {loading ? 'Processing...' : 'Record Cash Payment'}
            </button>
          </div>
        </div>
      )}

      {activeMethod === 'POS' && (
        <div className={styles.paymentForm}>
          <h4 className={styles.paymentFormTitle}>POS Payment</h4>
          <div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Amount (₦) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={posForm.amount}
                onChange={(e) => setPosForm({ ...posForm, amount: e.target.value })}
                className={styles.formInput}
                placeholder="Enter amount"
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Transaction Reference
              </label>
              <input
                type="text"
                value={posForm.transaction_reference}
                onChange={(e) => setPosForm({ ...posForm, transaction_reference: e.target.value })}
                className={styles.formInput}
                placeholder="Optional reference"
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Notes</label>
              <textarea
                value={posForm.notes}
                onChange={(e) => setPosForm({ ...posForm, notes: e.target.value })}
                className={styles.formTextarea}
                rows={2}
                placeholder="Optional notes"
              />
            </div>
            <button
              onClick={handlePOSPayment}
              disabled={loading || !isValidAmount(posForm.amount)}
              className={`${styles.submitButton} ${styles.submitButtonPOS}`}
            >
              {loading ? 'Processing...' : 'Record POS Payment'}
            </button>
          </div>
        </div>
      )}

      {activeMethod === 'TRANSFER' && (
        <div className={styles.paymentForm}>
          <h4 className={styles.paymentFormTitle}>Bank Transfer Payment</h4>
          <div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Amount (₦) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={transferForm.amount}
                onChange={(e) => setTransferForm({ ...transferForm, amount: e.target.value })}
                className={styles.formInput}
                placeholder="Enter amount"
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Transaction Reference *
              </label>
              <input
                type="text"
                value={transferForm.transaction_reference}
                onChange={(e) =>
                  setTransferForm({ ...transferForm, transaction_reference: e.target.value })
                }
                className={styles.formInput}
                placeholder="Enter bank reference"
                required
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Notes</label>
              <textarea
                value={transferForm.notes}
                onChange={(e) => setTransferForm({ ...transferForm, notes: e.target.value })}
                className={styles.formTextarea}
                rows={2}
                placeholder="Optional notes"
              />
            </div>
            <button
              onClick={handleTransferPayment}
              disabled={loading || !isValidAmount(transferForm.amount) || !transferForm.transaction_reference}
              className={`${styles.submitButton} ${styles.submitButtonTransfer}`}
            >
              {loading ? 'Processing...' : 'Record Transfer Payment'}
            </button>
          </div>
        </div>
      )}

      {activeMethod === 'PAYSTACK' && (
        <div className={styles.paymentForm}>
          <h4 className={styles.paymentFormTitle}>Paystack Payment</h4>
          <div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Amount (₦) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={paystackForm.amount}
                onChange={(e) => setPaystackForm({ ...paystackForm, amount: e.target.value })}
                className={styles.formInput}
                placeholder="Enter amount"
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Customer Email (Optional)
              </label>
              <input
                type="email"
                value={paystackForm.customer_email}
                onChange={(e) => setPaystackForm({ ...paystackForm, customer_email: e.target.value })}
                className={styles.formInput}
                placeholder="customer@example.com"
              />
            </div>
            <button
              onClick={handlePaystackPayment}
              disabled={loading || !isValidAmount(paystackForm.amount)}
              className={`${styles.submitButton} ${styles.submitButtonPaystack}`}
            >
              {loading ? 'Initializing...' : 'Initialize Paystack Payment'}
            </button>
            <p className={styles.helpText}>
              You will be redirected to Paystack checkout to complete the payment.
            </p>
          </div>
        </div>
      )}

      {activeMethod === 'WALLET' && patientWallet && (
        <div className={styles.paymentForm}>
          <h4 className={styles.paymentFormTitle}>Wallet Payment</h4>
          <div className={styles.walletBalanceInfo}>
            <p className={styles.walletBalanceText}>
              Available Balance: <span className={styles.walletBalanceAmount}>{formatCurrency(patientWallet.balance)}</span>
            </p>
          </div>
          <div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>
                Amount (₦) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max={patientWallet.balance}
                value={walletForm.amount}
                onChange={(e) => setWalletForm({ ...walletForm, amount: e.target.value })}
                className={styles.formInput}
                placeholder="Enter amount"
              />
            </div>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Description</label>
              <textarea
                value={walletForm.description}
                onChange={(e) => setWalletForm({ ...walletForm, description: e.target.value })}
                className={styles.formTextarea}
                rows={2}
                placeholder="Optional description"
              />
            </div>
            <button
              onClick={handleWalletPayment}
              disabled={
                loading ||
                !isValidAmount(walletForm.amount) ||
                parseFloat(walletForm.amount) > parseFloat(patientWallet.balance)
              }
              className={`${styles.submitButton} ${styles.submitButtonWallet}`}
            >
              {loading ? 'Processing...' : 'Process Wallet Payment'}
            </button>
          </div>
        </div>
      )}

      {/* Paystack Payment Intents */}
      {paymentIntents.length > 0 && (
        <div className={styles.paymentIntentsSection}>
          <h4 className={styles.paymentIntentsTitle}>Pending Paystack Payments</h4>
          <div className={styles.paymentIntentsList}>
            {paymentIntents.map((intent) => (
              <div
                key={intent.id}
                className={styles.paymentIntentCard}
              >
                <div className={styles.paymentIntentContent}>
                  <div className={styles.paymentIntentDetails}>
                    <p className={styles.paymentIntentAmount}>
                      Amount: {formatCurrency(intent.amount)}
                    </p>
                    <p className={styles.paymentIntentReference}>
                      Reference: {intent.paystack_reference}
                    </p>
                    <p className={styles.paymentIntentStatus}>
                      Status: <span className={styles.paymentIntentStatusValue}>{intent.status}</span>
                    </p>
                  </div>
                  {intent.status === 'INITIALIZED' && (
                    <button
                      onClick={() => handleVerifyPaystack(intent)}
                      disabled={loading}
                      className={styles.verifyButton}
                    >
                      {loading ? 'Verifying...' : 'Verify Payment'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

