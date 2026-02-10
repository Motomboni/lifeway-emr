/**
 * Patient Portal - Visit Detail Page
 * 
 * Shows detailed information about a specific visit.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPatientVisitDetail } from '../api/patientPortal';
import { Visit } from '../types/visit';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalVisitDetailPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { visitId } = useParams<{ visitId: string }>();
  const { showError } = useToast();

  const [visit, setVisit] = useState<Visit | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/patient-portal/dashboard', { replace: true });
      return;
    }
    if (visitId) {
      loadVisit();
    }
  }, [user, visitId, navigate]);

  const loadVisit = async () => {
    if (!visitId) return;
    try {
      setLoading(true);
      const data = await getPatientVisitDetail(parseInt(visitId));
      setVisit(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load visit details';
      showError(errorMessage);
      navigate('/patient-portal/visits');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
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

  if (loading) {
    return (
      <div className={styles.dashboard}>
        <LoadingSkeleton count={5} />
      </div>
    );
  }

  if (!visit) {
    return (
      <div className={styles.dashboard}>
        <p className={styles.emptyText}>Visit not found.</p>
      </div>
    );
  }

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div>
            <h1>Visit #{visit.id}</h1>
            <p>Visit Details</p>
          </div>
          <button
            className={styles.viewAllButton}
            onClick={() => navigate('/patient-portal/visits')}
          >
            Back to Visits
          </button>
        </div>
      </header>

      <div className={styles.content}>
        <section className={styles.section}>
          <h2>Visit Information</h2>
          <div className={styles.infoCard}>
            <div className={styles.infoRow}>
              <strong>Visit ID:</strong> {visit.id}
            </div>
            <div className={styles.infoRow}>
              <strong>Status:</strong>{' '}
              <span className={`${styles.badge} ${visit.status === 'CLOSED' ? styles.closed : styles.open}`}>
                {visit.status}
              </span>
            </div>
            <div className={styles.infoRow}>
              <strong>Payment Status:</strong> {visit.payment_status}
            </div>
            <div className={styles.infoRow}>
              <strong>Created:</strong> {formatDateTime(visit.created_at)}
            </div>
            {visit.closed_at && (
              <div className={styles.infoRow}>
                <strong>Closed:</strong> {formatDateTime(visit.closed_at)}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
