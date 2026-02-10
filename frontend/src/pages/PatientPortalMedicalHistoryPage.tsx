/**
 * Patient Portal - Medical History Page
 * 
 * Shows comprehensive medical history for the patient.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getPatientMedicalHistory } from '../api/patientPortal';
import { PatientPortalMedicalHistory } from '../types/patientPortal';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/PatientPortal.module.css';

export default function PatientPortalMedicalHistoryPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError } = useToast();

  const [history, setHistory] = useState<PatientPortalMedicalHistory | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (user?.role !== 'PATIENT') {
      navigate('/patient-portal/dashboard', { replace: true });
      return;
    }
    loadMedicalHistory();
  }, [user, navigate]);

  const loadMedicalHistory = async () => {
    try {
      setLoading(true);
      const data = await getPatientMedicalHistory();
      setHistory(data);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load medical history';
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

  if (!history) {
    return (
      <div className={styles.dashboard}>
        <p className={styles.emptyText}>Medical history not found.</p>
      </div>
    );
  }

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <div>
            <h1>My Medical History</h1>
            <p>Comprehensive view of all your medical records</p>
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
        {/* Patient Information */}
        <section className={styles.section}>
          <h2>Patient Information</h2>
          <div className={styles.infoCard}>
            <div className={styles.infoRow}>
              <strong>Name:</strong> {history.patient.first_name} {history.patient.last_name}
            </div>
            <div className={styles.infoRow}>
              <strong>Patient ID:</strong> {history.patient.patient_id}
            </div>
            {history.patient.date_of_birth && (
              <div className={styles.infoRow}>
                <strong>Date of Birth:</strong> {formatDate(history.patient.date_of_birth)}
              </div>
            )}
            {history.patient.blood_group && (
              <div className={styles.infoRow}>
                <strong>Blood Group:</strong> {history.patient.blood_group}
              </div>
            )}
            {history.patient.allergies && (
              <div className={styles.infoRow}>
                <strong>Allergies:</strong> {history.patient.allergies}
              </div>
            )}
          </div>
        </section>

        {/* Visits Summary */}
        <section className={styles.section}>
          <h2>Visits ({history.visits.length})</h2>
          {history.visits.length === 0 ? (
            <p className={styles.emptyText}>No visits found.</p>
          ) : (
            <div className={styles.list}>
              {history.visits.slice(0, 10).map((visit) => (
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
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Consultations Summary */}
        <section className={styles.section}>
          <h2>Consultations ({history.consultations.length})</h2>
          {history.consultations.length === 0 ? (
            <p className={styles.emptyText}>No consultations found.</p>
          ) : (
            <div className={styles.list}>
              {history.consultations.slice(0, 10).map((consultation) => (
                <div key={consultation.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>Consultation #{consultation.id}</h3>
                  </div>
                  <div className={styles.cardDetails}>
                    <p><strong>Date:</strong> {formatDateTime(consultation.created_at)}</p>
                    {consultation.diagnosis && (
                      <p><strong>Diagnosis:</strong> {consultation.diagnosis.substring(0, 100)}...</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Lab Results Summary */}
        <section className={styles.section}>
          <h2>Lab Results ({history.lab_results.length})</h2>
          {history.lab_results.length === 0 ? (
            <p className={styles.emptyText}>No lab results found.</p>
          ) : (
            <div className={styles.list}>
              {history.lab_results.slice(0, 10).map((result) => (
                <div key={result.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>Lab Result #{result.id}</h3>
                    <span className={`${styles.badge} ${
                      result.abnormal_flag === 'CRITICAL' ? styles.critical :
                      result.abnormal_flag === 'ABNORMAL' ? styles.abnormal :
                      styles.normal
                    }`}>
                      {result.abnormal_flag}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    <p><strong>Date:</strong> {formatDateTime(result.recorded_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Prescriptions Summary */}
        <section className={styles.section}>
          <h2>Prescriptions ({history.prescriptions.length})</h2>
          {history.prescriptions.length === 0 ? (
            <p className={styles.emptyText}>No prescriptions found.</p>
          ) : (
            <div className={styles.list}>
              {history.prescriptions.slice(0, 10).map((prescription) => (
                <div key={prescription.id} className={styles.card}>
                  <div className={styles.cardHeader}>
                    <h3>{prescription.drug || 'Prescription'}</h3>
                    <span className={`${styles.badge} ${prescription.status === 'DISPENSED' ? styles.open : styles.scheduled}`}>
                      {prescription.status}
                    </span>
                  </div>
                  <div className={styles.cardDetails}>
                    <p><strong>Dosage:</strong> {prescription.dosage}</p>
                    <p><strong>Date:</strong> {formatDateTime(prescription.created_at)}</p>
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
