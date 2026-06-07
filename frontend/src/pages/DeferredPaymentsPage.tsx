/**
 * Deferred legacy payments — LIFEWAY flexible-payment services awaiting settlement.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import ToastContainer from '../components/common/ToastContainer';
import {
  DeferredLegacyPayment,
  getDeferredLegacyPayments,
  settleDeferredLegacyPayment,
} from '../api/billing';
import { formatCurrency, isValidAmount } from '../utils/currency';
import styles from '../styles/PaymentProcessing.module.css';

type PaymentMethod = 'CASH' | 'POS' | 'TRANSFER';

function defaultSettlementAmount(item: DeferredLegacyPayment): string {
  if (!item.needs_price && parseFloat(item.amount_due) > 0) {
    return item.amount_due;
  }
  if (item.catalog_amount && parseFloat(item.catalog_amount) > 0) {
    return item.catalog_amount;
  }
  return '';
}

function priceSourceLabel(source?: string): string {
  switch (source) {
    case 'catalog':
      return 'Service catalog';
    case 'legacy_median':
      return 'LIFEWAY median price';
    case 'recorded':
      return 'Recorded amount';
    default:
      return '';
  }
}

export default function DeferredPaymentsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess, toasts, removeToast } = useToast();
  const [items, setItems] = useState<DeferredLegacyPayment[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 48;
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<DeferredLegacyPayment | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('CASH');
  const [amount, setAmount] = useState('');
  const [transactionReference, setTransactionReference] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadItems = useCallback(async () => {
    try {
      setLoading(true);
      const response = await getDeferredLegacyPayments(search, page, pageSize);
      setItems(response.results || []);
      setTotalCount(response.count || 0);
    } catch (error: any) {
      showError(error.message || 'Failed to load deferred payments');
    } finally {
      setLoading(false);
    }
  }, [search, page, pageSize, showError]);

  useEffect(() => {
    setPage(1);
  }, [search]);

  useEffect(() => {
    if (user?.role === 'RECEPTIONIST') {
      loadItems();
    }
  }, [loadItems, user?.role]);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  const openSettle = (item: DeferredLegacyPayment) => {
    setSelected(item);
    setPaymentMethod('CASH');
    setAmount(defaultSettlementAmount(item));
    setTransactionReference('');
    setNotes('');
  };

  const closeSettle = () => {
    if (!submitting) {
      setSelected(null);
    }
  };

  const handleSettle = async () => {
    if (!selected) return;
    if (!isValidAmount(amount) || parseFloat(amount) <= 0) {
      showError('Enter a valid settlement amount greater than zero');
      return;
    }
    if (paymentMethod === 'TRANSFER' && !transactionReference.trim()) {
      showError('Transaction reference is required for transfer payments');
      return;
    }

    try {
      setSubmitting(true);
      await settleDeferredLegacyPayment(selected.charge_id, {
        amount,
        payment_method: paymentMethod,
        transaction_reference: transactionReference || undefined,
        notes: notes || undefined,
      });
      showSuccess('Deferred service settled successfully');
      setSelected(null);
      await loadItems();
    } catch (error: any) {
      showError(error.message || 'Failed to settle deferred payment');
    } finally {
      setSubmitting(false);
    }
  };

  if (user?.role !== 'RECEPTIONIST') {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. This page is for Receptionists only.</p>
      </div>
    );
  }

  return (
    <div className={styles.paymentProcessingPage}>
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Deferred Legacy Payments</h1>
        <p>
          Flexible-payment services from LIFEWAY (rendered without upfront payment). Settle here using
          the same payment flow as visit billing.
        </p>
      </header>

      <div className={styles.formGroup} style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search patient, service, visit..."
        />
        <button type="button" className={styles.newPaymentButton} onClick={loadItems}>
          Refresh
        </button>
      </div>

      <div className={styles.paymentSummary}>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Unsettled</span>
          <span className={styles.summaryValuePending}>{totalCount.toLocaleString()}</span>
        </div>
        {totalPages > 1 && (
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Page</span>
            <span className={styles.summaryValuePending}>
              {page} / {totalPages}
            </span>
          </div>
        )}
      </div>

      {loading ? (
        <LoadingSkeleton />
      ) : items.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No unsettled deferred legacy services.</p>
        </div>
      ) : (
        <div className={styles.paymentsList}>
          {items.map((item) => (
            <article key={item.charge_id} className={`${styles.paymentCard} ${styles.deferredCard}`}>
              <div className={styles.paymentHeader}>
                <div>
                  <h3>{item.patient.name}</h3>
                  <p className={styles.deferredMeta}>
                    {item.patient.patient_id} · Visit #{item.visit_id}
                  </p>
                </div>
                <span className={styles.badgePending}>Deferred</span>
              </div>
              <div className={styles.deferredDetails}>
                <p className={styles.deferredDue}>
                  <span>Due</span>
                  <strong>
                    {item.needs_price ? 'Enter amount' : formatCurrency(item.amount_due)}
                  </strong>
                </p>
                {item.price_source && item.price_source !== 'unknown' && (
                  <p className={styles.deferredSource}>{priceSourceLabel(item.price_source)}</p>
                )}
                <p>
                  <strong>Service:</strong> {item.service_line || 'Legacy service'}
                </p>
              </div>
              <div className={`${styles.paymentActions} ${styles.inlineActions}`}>
                <button type="button" className={styles.clearButton} onClick={() => openSettle(item)}>
                  Settle payment
                </button>
                <button
                  type="button"
                  className={styles.cancelButton}
                  onClick={() => navigate(`/visits/${item.visit_id}#billing-section`)}
                >
                  Visit billing
                </button>
              </div>
            </article>
          ))}
        </div>
      )}

      {!loading && totalPages > 1 && (
        <div className={styles.paginationBar}>
          <button
            type="button"
            className={styles.cancelButton}
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </button>
          <span>
            Page {page} of {totalPages}
          </span>
          <button
            type="button"
            className={styles.cancelButton}
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          >
            Next
          </button>
        </div>
      )}

      {selected && (
        <div
          className={styles.modalOverlay}
          role="dialog"
          aria-modal="true"
          aria-labelledby="settle-deferred-title"
          onClick={closeSettle}
        >
          <div className={styles.modalPanel} onClick={(e) => e.stopPropagation()}>
            <h3 id="settle-deferred-title">Settle deferred service</h3>
            <p className={styles.modalSubtitle}>
              {selected.patient.name} — {selected.service_line || 'Legacy service'}
            </p>

            {!selected.needs_price && (
              <p className={styles.balanceHint}>
                Suggested due: {formatCurrency(selected.amount_due)}
                {selected.price_source && selected.price_source !== 'unknown'
                  ? ` (${priceSourceLabel(selected.price_source)})`
                  : ''}
              </p>
            )}

            {selected.needs_price && (
              <p className={styles.balanceHint}>
                No price could be resolved automatically. Enter the amount manually before confirming.
              </p>
            )}

            <div className={styles.formGroup}>
              <label htmlFor="settle-method">Payment method</label>
              <select
                id="settle-method"
                value={paymentMethod}
                onChange={(e) => setPaymentMethod(e.target.value as PaymentMethod)}
              >
                <option value="CASH">Cash</option>
                <option value="POS">POS</option>
                <option value="TRANSFER">Transfer</option>
              </select>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="settle-amount">Amount (₦)</label>
              <input
                id="settle-amount"
                type="number"
                min="0"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                autoFocus
              />
            </div>

            {paymentMethod === 'TRANSFER' && (
              <div className={styles.formGroup}>
                <label htmlFor="settle-ref">Transaction reference</label>
                <input
                  id="settle-ref"
                  type="text"
                  value={transactionReference}
                  onChange={(e) => setTransactionReference(e.target.value)}
                />
              </div>
            )}

            <div className={styles.formGroup}>
              <label htmlFor="settle-notes">Notes (optional)</label>
              <textarea
                id="settle-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
              />
            </div>

            <div className={styles.formActions}>
              <button type="button" className={styles.cancelButton} onClick={closeSettle} disabled={submitting}>
                Cancel
              </button>
              <button type="button" className={styles.submitButton} onClick={handleSettle} disabled={submitting}>
                {submitting ? 'Processing...' : 'Confirm settlement'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
