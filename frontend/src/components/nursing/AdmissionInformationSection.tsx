/**
 * Admission Information Section Component
 * 
 * Displays comprehensive admission information for nurses.
 * Shows all clinical data collected during admission.
 */
import React, { useState, useEffect } from 'react';
import { fetchAdmission, Admission } from '../../api/admissions';
import { useToast } from '../../hooks/useToast';
import LoadingSkeleton from '../common/LoadingSkeleton';
import styles from '../../styles/NurseVisit.module.css';

interface AdmissionInformationSectionProps {
  visitId: string;
}

interface ParsedAdmissionNotes {
  clinical_data?: {
    history_of_present_illness?: string;
    past_medical_history?: string;
    allergies?: string;
    current_medications?: string;
    vital_signs_at_admission?: string;
    physical_examination?: string;
    provisional_diagnosis?: string;
    plan_of_care?: string;
  };
  additional_notes?: string;
  formatted_text?: string;
}

export default function AdmissionInformationSection({ visitId }: AdmissionInformationSectionProps) {
  const { showError } = useToast();
  const [admission, setAdmission] = useState<Admission | null>(null);
  const [loading, setLoading] = useState(true);
  const [parsedNotes, setParsedNotes] = useState<ParsedAdmissionNotes | null>(null);

  useEffect(() => {
    loadAdmission();
  }, [visitId]);

  const loadAdmission = async () => {
    try {
      setLoading(true);
      const data = await fetchAdmission(parseInt(visitId));
      setAdmission(data);
      
      // Parse admission notes if available
      if (data?.admission_notes) {
        try {
          const parsed = JSON.parse(data.admission_notes);
          setParsedNotes(parsed);
        } catch (e) {
          // If not JSON, treat as plain text
          setParsedNotes({ additional_notes: data.admission_notes });
        }
      } else {
        setParsedNotes(null);
      }
    } catch (error: any) {
      console.error('Failed to load admission:', error);
      if (error.status !== 404) {
        showError('Failed to load admission information.');
      }
      setAdmission(null);
      setParsedNotes(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Admission Information</h3>
        <LoadingSkeleton count={3} />
      </div>
    );
  }

  if (!admission) {
    return (
      <div className={styles.section}>
        <h3 className={styles.sectionTitle}>Admission Information</h3>
        <div className={styles.emptyState}>
          <p>No admission record for this visit.</p>
        </div>
      </div>
    );
  }

  const clinicalData = parsedNotes?.clinical_data || {};

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>Admission Information</h3>
        <span className={`${styles.statusBadge} ${admission.admission_status === 'ADMITTED' ? styles.statusActive : styles.statusInactive}`}>
          {admission.admission_status}
        </span>
      </div>

      <div className={styles.admissionInfoCard}>
        {/* Basic Admission Details */}
        <div className={styles.infoGroup}>
          <h4>Location & Admission Details</h4>
          <div className={styles.infoGrid}>
            <div className={styles.infoItem}>
              <label>Ward:</label>
              <span>{admission.ward_name} ({admission.ward_code})</span>
            </div>
            <div className={styles.infoItem}>
              <label>Bed:</label>
              <span>{admission.bed_number}</span>
            </div>
            <div className={styles.infoItem}>
              <label>Admission Type:</label>
              <span>{admission.admission_type}</span>
            </div>
            <div className={styles.infoItem}>
              <label>Admission Source:</label>
              <span>{admission.admission_source}</span>
            </div>
            <div className={styles.infoItem}>
              <label>Admission Date:</label>
              <span>{new Date(admission.admission_date).toLocaleString()}</span>
            </div>
            <div className={styles.infoItem}>
              <label>Length of Stay:</label>
              <span>{admission.length_of_stay_days} day(s)</span>
            </div>
            <div className={styles.infoItem}>
              <label>Admitted By:</label>
              <span>{admission.admitting_doctor_name}</span>
            </div>
          </div>
        </div>

        {/* Chief Complaint */}
        <div className={styles.infoGroup}>
          <h4>Chief Complaint</h4>
          <div className={styles.infoText}>
            {admission.chief_complaint || 'Not specified'}
          </div>
        </div>

        {/* History of Present Illness */}
        {clinicalData.history_of_present_illness && (
          <div className={styles.infoGroup}>
            <h4>History of Present Illness</h4>
            <div className={styles.infoText}>
              {clinicalData.history_of_present_illness}
            </div>
          </div>
        )}

        {/* Past Medical History */}
        {clinicalData.past_medical_history && (
          <div className={styles.infoGroup}>
            <h4>Past Medical History</h4>
            <div className={styles.infoText}>
              {clinicalData.past_medical_history}
            </div>
          </div>
        )}

        {/* Allergies */}
        {clinicalData.allergies && (
          <div className={styles.infoGroup}>
            <h4>Allergies</h4>
            <div className={`${styles.infoText} ${styles.allergyWarning}`}>
              ⚠️ {clinicalData.allergies}
            </div>
          </div>
        )}

        {/* Current Medications */}
        {clinicalData.current_medications && (
          <div className={styles.infoGroup}>
            <h4>Current Medications</h4>
            <div className={styles.infoText}>
              {clinicalData.current_medications}
            </div>
          </div>
        )}

        {/* Vital Signs at Admission */}
        {clinicalData.vital_signs_at_admission && (
          <div className={styles.infoGroup}>
            <h4>Vital Signs at Admission</h4>
            <div className={styles.infoText}>
              {clinicalData.vital_signs_at_admission}
            </div>
          </div>
        )}

        {/* Physical Examination */}
        {clinicalData.physical_examination && (
          <div className={styles.infoGroup}>
            <h4>Physical Examination Findings</h4>
            <div className={styles.infoText}>
              {clinicalData.physical_examination}
            </div>
          </div>
        )}

        {/* Provisional Diagnosis */}
        {clinicalData.provisional_diagnosis && (
          <div className={styles.infoGroup}>
            <h4>Provisional Diagnosis</h4>
            <div className={styles.infoText}>
              {clinicalData.provisional_diagnosis}
            </div>
          </div>
        )}

        {/* Plan of Care */}
        {clinicalData.plan_of_care && (
          <div className={styles.infoGroup}>
            <h4>Plan of Care</h4>
            <div className={styles.infoText}>
              {clinicalData.plan_of_care}
            </div>
          </div>
        )}

        {/* Additional Notes */}
        {parsedNotes?.additional_notes && (
          <div className={styles.infoGroup}>
            <h4>Additional Notes</h4>
            <div className={styles.infoText}>
              {parsedNotes.additional_notes}
            </div>
          </div>
        )}

        {/* Fallback: Display formatted text if available but no structured data */}
        {parsedNotes?.formatted_text && !Object.keys(clinicalData).length && (
          <div className={styles.infoGroup}>
            <h4>Admission Notes</h4>
            <div className={styles.infoText} style={{ whiteSpace: 'pre-wrap' }}>
              {parsedNotes.formatted_text}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
