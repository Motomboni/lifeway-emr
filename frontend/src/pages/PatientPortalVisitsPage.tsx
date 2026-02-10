/**
 * Patient Portal - Visits List Page
 * 
 * Shows all patient's visits in a list format.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPatientVisits } from '../api/patientPortal';
import { Visit } from '../types/visit';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalVisitsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();

  const [visits, setVisits] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/patient-portal/dashboard', { replace: true });
      return;
    }
    loadVisits();
  }, [user, navigate]);

  const loadVisits = async () => {
    try {
      setLoading(true);
      const data = await getPatientVisits();
      setVisits(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load visits';
      showError(errorMessage);
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

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div>
            <h1>My Visits</h1>
            <p>View all your medical visits</p>
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
          {visits.length === 0 ? (
            <p className={styles.emptyText}>No visits found.</p>
          ) : (
            <div className={styles.list}>
              {visits.map((visit) => (
                <div key={visit.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>Visit #{visit.id}</h3>
                    <span className={`${styles.badge} ${visit.status === 'CLOSED' ? styles.closed : styles.open}`}>
                      {visit.status}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    <p><strong>Date:</strong> {formatDateTime(visit.created_at)}</p>
                    <p><strong>Payment Status:</strong> {visit.payment_status}</p>
                    {visit.closed_at && (
                      <p><strong>Closed:</strong> {formatDateTime(visit.closed_at)}</p>
                    )}
                  </div>
                  <button
                    className={styles.viewButton}
                    onClick={() => navigate(`/patient-portal/visits/${visit.id}`)}
                  >
                    View Details
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
