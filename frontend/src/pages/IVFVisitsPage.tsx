/**
 * IVF Patient Visits Page
 *
 * Lists visits for patients who have at least one IVF cycle only.
 * Used from the IVF Specialist Dashboard.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchIVFVisits } from '../api/ivf';
import styles from '../styles/CyclesList.module.css';

interface IVFVisitItem {
  id: number;
  patient: number;
  patient_name?: string;
  patient_id?: string;
  status: string;
  payment_status?: string;
  created_at: string;
  visit_type?: string;
}

export default function IVFVisitsPage() {
  const navigate = useNavigate();
  const [visits, setVisits] = useState<IVFVisitItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    loadVisits();
  }, [statusFilter]);

  const loadVisits = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchIVFVisits(statusFilter ? { status: statusFilter } : undefined);
      setVisits(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load IVF patient visits');
    } finally {
      setLoading(false);
    }
  };

  const handleVisitClick = (visitId: number) => {
    navigate(`/visits/${visitId}`);
  };

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <button className={styles.backButton} onClick={() => navigate('/ivf')}>
            ← IVF Dashboard
          </button>
          <h1>IVF Patient Visits</h1>
        </div>
        <p style={{ margin: 0, color: 'var(--text-secondary, #6c757d)', fontSize: '0.95rem' }}>
          Visits for patients with at least one IVF cycle
        </p>
      </header>

      <div className={styles.filters}>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className={styles.filterSelect}
        >
          <option value="">All statuses</option>
          <option value="OPEN">Open</option>
          <option value="CLOSED">Closed</option>
        </select>
      </div>

      {error && (
        <div className={styles.errorBanner} style={{ marginBottom: 16 }}>
          {error}
          <button onClick={loadVisits}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className={styles.loading}>Loading IVF patient visits...</div>
      ) : visits.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No visits found for IVF patients</p>
          <p style={{ marginTop: 8, fontSize: '0.9rem' }}>
            Visits will appear here when they belong to patients with an IVF cycle.
          </p>
          <button className={styles.primaryButton} onClick={() => navigate('/ivf')}>
            Back to IVF Dashboard
          </button>
        </div>
      ) : (
        <div className={styles.tableContainer}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Visit #</th>
                <th>Patient</th>
                <th>Status</th>
                <th>Payment</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {visits.map((v) => (
                <tr key={v.id}>
                  <td>
                    <strong>#{v.id}</strong>
                  </td>
                  <td>
                    {v.patient_name || `Patient ${v.patient}`}
                    {v.patient_id && (
                      <small style={{ display: 'block', color: '#6c757d' }}>{v.patient_id}</small>
                    )}
                  </td>
                  <td>
                    <span
                      className={styles.statusBadge}
                      style={{
                        backgroundColor: v.status === 'OPEN' ? '#17a2b8' : '#6c757d',
                        color: '#fff',
                      }}
                    >
                      {v.status}
                    </span>
                  </td>
                  <td>{v.payment_status || '–'}</td>
                  <td>{v.created_at ? new Date(v.created_at).toLocaleDateString() : '–'}</td>
                  <td>
                    <button
                      type="button"
                      className={styles.viewButton}
                      onClick={() => handleVisitClick(v.id)}
                    >
                      View visit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
