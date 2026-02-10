/**
 * IVF Patients Page
 *
 * Lists only patients who have at least one IVF cycle (IVF patients).
 * Used from the IVF Specialist Dashboard.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchIVFPatients, IVFPatientListItem } from '../api/ivf';
import styles from '../styles/CyclesList.module.css';

export default function IVFPatientsPage() {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<IVFPatientListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPatients();
  }, []);

  const loadPatients = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchIVFPatients();
      setPatients(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load IVF patients');
    } finally {
      setLoading(false);
    }
  };

  const handlePatientClick = (patientId: number) => {
    navigate(`/patients/${patientId}/history`);
  };

  const handleViewCycles = (patientId: number) => {
    navigate(`/ivf/cycles?patient=${patientId}`);
  };

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <button className={styles.backButton} onClick={() => navigate('/ivf')}>
            ← IVF Dashboard
          </button>
          <h1>IVF Patients</h1>
        </div>
        <p style={{ margin: 0, color: 'var(--text-secondary, #6c757d)', fontSize: '0.95rem' }}>
          Patients with at least one IVF cycle
        </p>
      </header>

      {error && (
        <div className={styles.errorBanner} style={{ marginBottom: 16 }}>
          {error}
          <button onClick={loadPatients}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className={styles.loading}>Loading IVF patients...</div>
      ) : patients.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No IVF patients found</p>
          <p style={{ marginTop: 8, fontSize: '0.9rem' }}>
            Patients will appear here once they have at least one IVF cycle.
          </p>
          <button className={styles.primaryButton} onClick={() => navigate('/ivf/cycles/new')}>
            Start New IVF Cycle
          </button>
        </div>
      ) : (
        <div className={styles.tableContainer}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Name</th>
                <th>IVF Cycles</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {patients.map((p) => (
                <tr key={p.id}>
                  <td>{p.patient_id}</td>
                  <td>
                    <strong>
                      {p.first_name} {p.last_name}
                    </strong>
                  </td>
                  <td>{p.cycle_count}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className={styles.viewButton}
                        onClick={() => handlePatientClick(p.id)}
                      >
                        View patient
                      </button>
                      <button
                        type="button"
                        className={styles.viewButton}
                        onClick={() => handleViewCycles(p.id)}
                      >
                        View cycles
                      </button>
                    </div>
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
