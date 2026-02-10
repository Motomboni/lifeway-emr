/**
 * Patient Portal - Lab Results Page
 * 
 * Shows all patient's lab results.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPatientLabResults } from '../api/patientPortal';
import { LabResult } from '../types/lab';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalLabResultsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();

  const [labResults, setLabResults] = useState<LabResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/patient-portal/dashboard', { replace: true });
      return;
    }
    loadLabResults();
  }, [user, navigate]);

  const loadLabResults = async () => {
    try {
      setLoading(true);
      const data = await getPatientLabResults();
      setLabResults(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load lab results';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getAbnormalFlagBadgeClass = (flag: string) => {
    switch (flag) {
      case 'CRITICAL':
        return styles.critical;
      case 'ABNORMAL':
        return styles.abnormal;
      case 'NORMAL':
      default:
        return styles.normal;
    }
  };

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
            <h1>My Lab Results</h1>
            <p>View all your laboratory test results</p>
          </div>
          <button
            className={styles.viewAllButton}
            onClick={() => navigate('/patient-portal/dashboard')}
          >
            Back to Dashboard
          </button>
        </div>
      </header>

      <div className={styles.content}>
        <section className={styles.section}>
          {labResults.length === 0 ? (
            <p className={styles.emptyText}>No lab results found.</p>
          ) : (
            <div className={styles.list}>
              {labResults.map((result) => (
                <div key={result.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>Lab Result #{result.id}</h3>
                    <span className={`${styles.badge} ${getAbnormalFlagBadgeClass(result.abnormal_flag)}`}>
                      {result.abnormal_flag}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    <p><strong>Lab Order ID:</strong> {result.lab_order_id}</p>
                    <p><strong>Recorded:</strong> {formatDateTime(result.recorded_at)}</p>
                    {result.result_data && (
                      <div style={{ marginTop: '1rem', padding: '1rem', background: '#f8f9fa', borderRadius: '4px' }}>
                        <strong>Results:</strong>
                        <pre style={{ marginTop: '0.5rem', whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                          {typeof result.result_data === 'string' 
                            ? result.result_data 
                            : JSON.stringify(result.result_data, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
