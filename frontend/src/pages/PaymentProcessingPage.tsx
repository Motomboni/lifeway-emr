/**
 * Payment Processing Page
 *
 * Read-only payment history across visits, with visit-scoped navigation for
 * collecting or adjusting payments.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import { getPaymentHistory, GlobalPayment, PaymentHistoryResponse } from '../api/billing';
import { formatCurrency } from '../utils/currency';
import styles from '../styles/PaymentProcessing.module.css';

export default function PaymentProcessingPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();
  const [payments, setPayments] = useState<GlobalPayment[]>([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [legacyOnly, setLegacyOnly] = useState(true);
  const [loading, setLoading] = useState(true);

  const loadPayments = useCallback(async () => {
    try {
      setLoading(true);
      const response: PaymentHistoryResponse = await getPaymentHistory({
        search,
        status,
        legacyOnly,
        page,
        pageSize: 50,
      });
      setPayments(response.results || []);
      setCount(response.count || 0);
    } catch (error: any) {
      showError(error.message || 'Failed to load payments');
    } finally {
      setLoading(false);
    }
  }, [legacyOnly, page, search, showError, status]);

  useEffect(() => {
    if (user?.role === 'RECEPTIONIST') {
      loadPayments();
    }
  }, [loadPayments, user?.role]);

  if (user?.role !== 'RECEPTIONIST') {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. This page is for Receptionists only.</p>
      </div>
    );
  }

  return (
    <div className={styles.paymentProcessingPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Billing & Payments</h1>
        <p>Review migrated legacy payments and current visit-scoped payments.</p>
      </header>

      <div className={styles.paymentSummary}>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Records</span>
          <span className={styles.summaryValue}>{count.toLocaleString()}</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Showing</span>
          <span className={styles.summaryValue}>{payments.length.toLocaleString()}</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Filter</span>
          <span className={styles.summaryValue}>{legacyOnly ? 'Legacy payments' : 'All payments'}</span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        <input
          type="text"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }}
          placeholder="Search patient, visit, receipt, notes..."
          style={{ minWidth: 280, padding: '0.75rem', border: '1px solid #ddd', borderRadius: 4 }}
        />
        <select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
          style={{ padding: '0.75rem', border: '1px solid #ddd', borderRadius: 4 }}
        >
          <option value="">All statuses</option>
          <option value="CLEARED">Cleared</option>
          <option value="PENDING">Pending</option>
          <option value="PARTIAL">Partial</option>
          <option value="REFUNDED">Refunded</option>
          <option value="FAILED">Failed</option>
        </select>
        <label style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={legacyOnly}
            onChange={(event) => {
              setLegacyOnly(event.target.checked);
              setPage(1);
            }}
          />
          Legacy only
        </label>
      </div>

      {loading ? (
        <LoadingSkeleton count={5} />
      ) : payments.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No payments found for the current filters.</p>
        </div>
      ) : (
        <div className={styles.paymentsList}>
          {payments.map((payment) => (
            <div key={payment.id} className={styles.paymentCard}>
              <div className={styles.paymentHeader}>
                <h3>
                  {formatCurrency(payment.amount)}
                  {payment.is_legacy ? ' | Legacy' : ''}
                </h3>
                <span className={payment.status === 'CLEARED' ? styles.badgeCleared : styles.badgePending}>
                  {payment.status}
                </span>
              </div>
              <div className={styles.paymentDetails}>
                <p><strong>Patient:</strong> {payment.patient.name} ({payment.patient.patient_id})</p>
                <p><strong>Visit:</strong> #{payment.visit_id} ({payment.visit_status})</p>
                <p><strong>Method:</strong> {payment.payment_method}</p>
                {payment.transaction_reference && (
                  <p><strong>Reference:</strong> {payment.transaction_reference}</p>
                )}
                <p><strong>Created:</strong> {new Date(payment.created_at).toLocaleString()}</p>
                {payment.notes && <p><strong>Notes:</strong> {payment.notes}</p>}
              </div>
              <div className={styles.paymentActions}>
                <button
                  type="button"
                  onClick={() => navigate(`/visits/${payment.visit_id}#billing-section`)}
                  className={styles.clearButton}
                >
                  Open Visit Billing
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem' }}>
        <button
          type="button"
          disabled={page <= 1 || loading}
          onClick={() => setPage((current) => Math.max(current - 1, 1))}
          className={styles.cancelButton}
        >
          Previous
        </button>
        <span>Page {page}</span>
        <button
          type="button"
          disabled={page * 50 >= count || loading}
          onClick={() => setPage((current) => current + 1)}
          className={styles.submitButton}
        >
          Next
        </button>
      </div>
    </div>
  );
}
