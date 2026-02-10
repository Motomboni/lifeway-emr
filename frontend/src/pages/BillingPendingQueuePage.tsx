/**
 * Central Billing Queue - Receptionist dashboard.
 *
 * Shows all visits with pending (unpaid or partially paid) bills.
 * Receptionist can view itemized charges and navigate to visit billing to collect payment.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getBillingPendingQueue, PendingQueueVisit } from '../api/billing';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import { formatCurrency } from '../utils/currency';
import styles from '../styles/VisitDetails.module.css';

export default function BillingPendingQueuePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();
  const [visits, setVisits] = useState<PendingQueueVisit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'RECEPTIONIST') return;
    getBillingPendingQueue()
      .then((res) => setVisits(res.visits))
      .catch((err) => showError(err.message || 'Failed to load pending queue'))
      .finally(() => setLoading(false));
  }, [user?.role, showError]);

  if (user?.role !== 'RECEPTIONIST') {
    return (
      <div style={{ padding: '2rem' }}>
        <p>Access denied. This page is for Receptionists only.</p>
      </div>
    );
  }

  return (
    <div className={styles.visitDetailsPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Central Billing Queue</h1>
        <p>Pending payments from all departments. Collect payment from Visit Details → Billing.</p>
      </header>
      {loading ? (
        <p>Loading...</p>
      ) : visits.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No pending bills.</p>
        </div>
      ) : (
        <div className={styles.content} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {visits.map((v) => (
            <div
              key={v.visit_id}
              style={{
                border: '1px solid #e5e7eb',
                borderRadius: 8,
                padding: '1rem',
                background: '#fff',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div>
                  <strong>{v.patient.name}</strong>
                  <span style={{ marginLeft: '0.5rem', color: '#6b7280' }}>Visit #{v.visit_id}</span>
                </div>
                <div>
                  <span style={{ fontWeight: 600, marginRight: '0.5rem' }}>{formatCurrency(v.total_pending)}</span>
                  <button
                    type="button"
                    onClick={() => navigate(`/visits/${v.visit_id}#billing-section`)}
                    style={{ padding: '0.25rem 0.75rem', borderRadius: 6, background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer' }}
                  >
                    Collect payment
                  </button>
                </div>
              </div>
              <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.875rem', color: '#374151' }}>
                {v.items.map((item) => (
                  <li key={item.id}>
                    [{item.department}] {item.description} — {formatCurrency(item.amount)} ({item.status})
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
