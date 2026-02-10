/**
 * Patient Portal - Radiology Results Page
 * 
 * Shows all patient's radiology results.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPatientRadiologyResults } from '../api/patientPortal';
import { RadiologyResult } from '../types/patientPortal';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalRadiologyResultsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();

  const [radiologyResults, setRadiologyResults] = useState<RadiologyResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/patient-portal/dashboard', { replace: true });
      return;
    }
    loadRadiologyResults();
  }, [user, navigate]);

  const loadRadiologyResults = async () => {
    try {
      setLoading(true);
      const data = await getPatientRadiologyResults();
      setRadiologyResults(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load radiology results';
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

  const getFindingFlagBadgeClass = (flag: string) => {
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
            <h1>My Radiology Results</h1>
            <p>View all your radiology test results</p>
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
          {radiologyResults.length === 0 ? (
            <p className={styles.emptyText}>No radiology results found.</p>
          ) : (
            <div className={styles.list}>
              {radiologyResults.map((result) => (
                <div key={result.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>Radiology Result #{result.id}</h3>
                    <span className={`${styles.badge} ${getFindingFlagBadgeClass(result.finding_flag)}`}>
                      {result.finding_flag}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    <p><strong>Radiology Request ID:</strong> {result.radiology_request_id}</p>
                    <p><strong>Reported:</strong> {formatDateTime(result.reported_at)}</p>
                    <p><strong>Image Count:</strong> {result.image_count}</p>
                    {result.report && (
                      <div style={{ marginTop: '1rem', padding: '1rem', background: '#f8f9fa', borderRadius: '4px' }}>
                        <strong>Report:</strong>
                        <p style={{ marginTop: '0.5rem', whiteSpace: 'pre-wrap' }}>
                          {result.report}
                        </p>
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
