/**
 * Bank transfer / USSD payment reconciliation.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import {
  createPaymentReconciliation,
  disputePaymentReconciliation,
  fetchPaymentReconciliations,
  matchPaymentReconciliation,
  PaymentReconciliation,
} from '../api/paymentReconciliation';
import styles from '../styles/RevenueLeakDashboard.module.css';

export default function BankTransferReconciliationPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();
  const [records, setRecords] = useState<PaymentReconciliation[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    visit_id: '',
    method: 'BANK_TRANSFER',
    reference: '',
    amount_ngn: '',
    payer_name: '',
    bank_name: '',
  });

  useEffect(() => {
    if (!user) navigate('/login');
  }, [user, navigate]);

  const load = async () => {
    try {
      setLoading(true);
      setRecords(await fetchPaymentReconciliations());
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to load reconciliations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) load();
  }, [user]);

  const handleCreate = async () => {
    if (!form.reference || !form.amount_ngn) {
      showError('Reference and amount are required');
      return;
    }
    try {
      await createPaymentReconciliation({
        visit_id: form.visit_id ? parseInt(form.visit_id, 10) : undefined,
        method: form.method,
        reference: form.reference,
        amount_ngn: form.amount_ngn,
        payer_name: form.payer_name,
        bank_name: form.bank_name,
      });
      showSuccess('Payment recorded for reconciliation');
      setForm({ visit_id: '', method: 'BANK_TRANSFER', reference: '', amount_ngn: '', payer_name: '', bank_name: '' });
      load();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to record payment');
    }
  };

  if (loading && records.length === 0) {
    return (
      <div className={styles.page}>
        <LoadingSkeleton lines={6} />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Bank Transfer / USSD Reconciliation</h1>
        <p className={styles.subtitle}>Match incoming transfers to visits and payments</p>
      </header>

      <div className={styles.filters} style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
        <input placeholder="Visit ID (optional)" value={form.visit_id} onChange={(e) => setForm({ ...form, visit_id: e.target.value })} />
        <select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>
          <option value="BANK_TRANSFER">Bank Transfer</option>
          <option value="USSD">USSD</option>
          <option value="POS">POS</option>
          <option value="CASH">Cash</option>
        </select>
        <input placeholder="Reference *" value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} />
        <input placeholder="Amount ₦ *" value={form.amount_ngn} onChange={(e) => setForm({ ...form, amount_ngn: e.target.value })} />
        <input placeholder="Payer name" value={form.payer_name} onChange={(e) => setForm({ ...form, payer_name: e.target.value })} />
        <input placeholder="Bank" value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} />
        <button type="button" onClick={handleCreate}>Record</button>
      </div>

      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Ref</th>
              <th>Method</th>
              <th>Amount</th>
              <th>Visit</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr><td colSpan={6}>No reconciliation records yet</td></tr>
            ) : (
              records.map((r) => (
                <tr key={r.id}>
                  <td>{r.reference}</td>
                  <td>{r.method}</td>
                  <td>₦{r.amount_ngn}</td>
                  <td>{r.visit_id ? `#${r.visit_id}` : '—'}</td>
                  <td>{r.status}</td>
                  <td>
                    {r.status === 'PENDING' && (
                      <>
                        <button type="button" onClick={() => matchPaymentReconciliation(r.id).then(load)}>Match</button>
                        {' '}
                        <button type="button" onClick={() => disputePaymentReconciliation(r.id, 'Disputed').then(load)}>Dispute</button>
                      </>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
