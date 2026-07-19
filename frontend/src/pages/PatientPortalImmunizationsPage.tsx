/**
 * Patient Portal - Immunization Schedule (read-only)
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPatientImmunizations } from '../api/patientPortal';
import { ImmunizationRecord } from '../api/clinical';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

const VACCINE_LABELS: Record<string, string> = {
  BCG: 'BCG',
  HEP_B: 'Hepatitis B birth dose',
  OPV: 'Oral Polio Vaccine (OPV)',
  IPV: 'Inactivated Polio Vaccine (IPV)',
  PENTA: 'Pentavalent',
  PCV: 'Pneumococcal (PCV)',
  ROTA: 'Rotavirus',
  MEASLES: 'Measles-containing vaccine',
  YELLOW_FEVER: 'Yellow Fever',
  MEN_A: 'Meningococcal A',
  MALARIA: 'Malaria vaccine',
  HPV: 'Human Papillomavirus (HPV)',
  TD: 'Tetanus-Diphtheria (Td)',
};

const today = () => new Date().toISOString().slice(0, 10);

const formatDate = (value: string | null) => {
  if (!value) return 'Not recorded';
  return new Intl.DateTimeFormat('en-NG', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`));
};

const getStatus = (record: ImmunizationRecord) => {
  if (record.administered_date) return 'administered';
  if (record.scheduled_date && record.scheduled_date < today()) return 'overdue';
  return 'scheduled';
};

const statusLabel: Record<string, string> = {
  administered: 'Completed',
  scheduled: 'Upcoming',
  overdue: 'Overdue',
};

export default function PatientPortalImmunizationsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();
  const [records, setRecords] = useState<ImmunizationRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/patient-portal/dashboard', { replace: true });
      return;
    }
    void loadImmunizations();
  }, [user, navigate]);

  const loadImmunizations = async () => {
    try {
      setLoading(true);
      setRecords(await getPatientImmunizations());
    } catch (error) {
      showError(error instanceof Error ? error.message : 'Failed to load immunizations');
    } finally {
      setLoading(false);
    }
  };

  const summary = useMemo(
    () =>
      records.reduce(
        (counts, record) => {
          counts[getStatus(record)] += 1;
          return counts;
        },
        { administered: 0, scheduled: 0, overdue: 0 },
      ),
    [records],
  );

  if (loading) {
    return (
      <div className={styles.dashboard}>
        <LoadingSkeleton count={5} />
      </div>
    );
  }

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div>
            <h1>My Immunization Schedule</h1>
            <p>View your vaccination history and upcoming doses</p>
          </div>
          <button
            className={styles.viewAllButton}
            type="button"
            onClick={() => navigate('/patient-portal/dashboard')}
          >
            Back to Dashboard
          </button>
        </div>
      </header>

      <div className={styles.content}>
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statIcon}>✅</div>
            <div className={styles.statInfo}>
              <h3>{summary.administered}</h3>
              <p>Completed</p>
            </div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statIcon}>📅</div>
            <div className={styles.statInfo}>
              <h3>{summary.scheduled}</h3>
              <p>Upcoming</p>
            </div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statIcon}>⚠️</div>
            <div className={styles.statInfo}>
              <h3>{summary.overdue}</h3>
              <p>Overdue</p>
            </div>
          </div>
        </div>

        <section className={styles.section}>
          {records.length === 0 ? (
            <p className={styles.emptyText}>
              No immunization records yet. Your clinic will add vaccinations here after they are
              scheduled or administered.
            </p>
          ) : (
            <div className={styles.list}>
              {records.map((record) => {
                const status = getStatus(record);
                return (
                  <div key={record.id} className={styles.card}>
                    <div className={styles.cardHeader}>
                      <h3>
                        {VACCINE_LABELS[record.vaccine] || record.vaccine} · Dose {record.dose_number}
                      </h3>
                      <span
                        className={`${styles.badge} ${
                          status === 'administered'
                            ? styles.normal
                            : status === 'overdue'
                              ? styles.critical
                              : styles.scheduled
                        }`}
                      >
                        {statusLabel[status]}
                      </span>
                    </div>
                    <div className={styles.cardDetails}>
                      <p>
                        <strong>Scheduled:</strong> {formatDate(record.scheduled_date)}
                      </p>
                      <p>
                        <strong>Administered:</strong> {formatDate(record.administered_date)}
                      </p>
                      {record.batch_number && (
                        <p>
                          <strong>Batch number:</strong> {record.batch_number}
                        </p>
                      )}
                      {record.notes && (
                        <p>
                          <strong>Notes:</strong> {record.notes}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
