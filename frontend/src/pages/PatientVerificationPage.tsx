/**
 * Patient Verification Page
 * 
 * Allows Receptionists to verify patient accounts that registered via the Patient Portal.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPendingVerificationPatients, verifyPatient } from '../api/patient';
import { Patient } from '../types/patient';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/PatientVerification.module.css';

export default function PatientVerificationPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();

  const [patients, setPatients] = useState<Patient[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState<number | null>(null);

  useEffect(() => {
    // Only Receptionists can access this page
    if (user?.role !== 'RECEPTIONIST') {
      navigate('/dashboard', { replace: true });
      return;
    }
    loadPendingPatients();
  }, [user, navigate]);

  const loadPendingPatients = async () => {
    try {
      setLoading(true);
      const data = await getPendingVerificationPatients();
      setPatients(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load pending verifications';
      showError(errorMessage);
      setPatients([]);
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (patientId: number) => {
    if (!window.confirm('Are you sure you want to verify this patient account? This will allow them to access the Patient Portal.')) {
      return;
    }

    try {
      setVerifying(patientId);
      await verifyPatient(patientId);
      showSuccess('Patient account verified successfully');
      // Remove verified patient from list
      setPatients(patients.filter(p => p.id !== patientId));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to verify patient account';
      showError(errorMessage);
    } finally {
      setVerifying(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <BackToDashboard />
        <div className={styles.header}>
          <h1>Patient Account Verification</h1>
        </div>
        <LoadingSkeleton count={5} />
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <BackToDashboard />
      <div className={styles.header}>
        <h1>Patient Account Verification</h1>
        <p className={styles.subtitle}>
          Review and verify patient accounts that registered via the Patient Portal
        </p>
      </div>

      {patients.length === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>✓</div>
          <h2>No Pending Verifications</h2>
          <p>All patient accounts have been verified.</p>
        </div>
      ) : (
        <>
          <div className={styles.stats}>
            <span className={styles.statBadge}>
              {patients.length} {patients.length === 1 ? 'account' : 'accounts'} pending verification
            </span>
          </div>

          <div className={styles.patientsList}>
            {patients.map((patient) => (
              <div key={patient.id} className={styles.patientCard}>
                <div className={styles.patientHeader}>
                  <div className={styles.patientInfo}>
                    <h3>{patient.full_name}</h3>
                    <p className={styles.patientId}>Patient ID: {patient.patient_id}</p>
                  </div>
                  <button
                    className={styles.verifyButton}
                    onClick={() => handleVerify(patient.id)}
                    disabled={verifying === patient.id}
                  >
                    {verifying === patient.id ? 'Verifying...' : 'Verify Account'}
                  </button>
                </div>

                <div className={styles.patientDetails}>
                  <div className={styles.detailRow}>
                    <span className={styles.label}>Email:</span>
                    <span>{patient.email || patient.user_email || 'N/A'}</span>
                  </div>
                  <div className={styles.detailRow}>
                    <span className={styles.label}>Phone:</span>
                    <span>{patient.phone || 'N/A'}</span>
                  </div>
                  <div className={styles.detailRow}>
                    <span className={styles.label}>Username:</span>
                    <span>{patient.user_username || 'N/A'}</span>
                  </div>
                  {patient.date_of_birth && (
                    <div className={styles.detailRow}>
                      <span className={styles.label}>Date of Birth:</span>
                      <span>{new Date(patient.date_of_birth).toLocaleDateString()}</span>
                    </div>
                  )}
                  <div className={styles.detailRow}>
                    <span className={styles.label}>Registered:</span>
                    <span>{formatDate(patient.created_at)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
