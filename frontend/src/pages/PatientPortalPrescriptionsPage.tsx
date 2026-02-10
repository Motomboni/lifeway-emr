/**
 * Patient Portal - Prescriptions Page
 * 
 * Shows all patient's prescriptions.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPatientPrescriptions } from '../api/patientPortal';
import { Prescription } from '../types/prescription';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalPrescriptionsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();

  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/patient-portal/dashboard', { replace: true });
      return;
    }
    loadPrescriptions();
  }, [user, navigate]);

  const loadPrescriptions = async () => {
    try {
      setLoading(true);
      const data = await getPatientPrescriptions();
      setPrescriptions(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load prescriptions';
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
            <h1>My Prescriptions</h1>
            <p>View all your prescriptions</p>
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
          {prescriptions.length === 0 ? (
            <p className={styles.emptyText}>No prescriptions found.</p>
          ) : (
            <div className={styles.list}>
              {prescriptions.map((prescription) => (
                <div key={prescription.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>{prescription.drug || 'Prescription'}</h3>
                    <span className={`${styles.badge} ${prescription.status === 'DISPENSED' ? styles.open : styles.scheduled}`}>
                      {prescription.status}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    <p><strong>Dosage:</strong> {prescription.dosage}</p>
                    {prescription.frequency && (
                      <p><strong>Frequency:</strong> {prescription.frequency}</p>
                    )}
                    {prescription.duration && (
                      <p><strong>Duration:</strong> {prescription.duration}</p>
                    )}
                    {prescription.instructions && (
                      <p><strong>Instructions:</strong> {prescription.instructions}</p>
                    )}
                    <p><strong>Prescribed:</strong> {formatDateTime(prescription.created_at)}</p>
                    {prescription.dispensed_date && (
                      <p><strong>Dispensed:</strong> {formatDateTime(prescription.dispensed_date)}</p>
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
