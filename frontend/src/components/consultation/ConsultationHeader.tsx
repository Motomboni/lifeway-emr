/**
 * ConsultationHeader Component
 * 
 * Displays visit context and patient summary (read-only).
 * Ensures visit context is never lost - always visible at top.
 */
import React, { useEffect, useState } from 'react';
import { fetchVisitDetails } from '../../api/visits';
import { HeaderSkeleton } from '../common/LoadingSkeleton';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface VisitDetails {
  id: number;
  patient: number;
  patient_name?: string;
  patient_id?: string;
  patient_details?: {
    name: string;
    age?: number;
    gender?: string;
    phone?: string;
  };
  status: string;
  payment_status: string;
  created_at: string;
}

interface ConsultationHeaderProps {
  visitId: string;
}

export default function ConsultationHeader({ visitId }: ConsultationHeaderProps) {
  const [visitDetails, setVisitDetails] = useState<VisitDetails | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadVisitDetails = async () => {
      try {
        const details = await fetchVisitDetails(visitId);
        setVisitDetails(details);
      } catch (error) {
        console.error('Failed to load visit details:', error);
      } finally {
        setLoading(false);
      }
    };

    loadVisitDetails();
  }, [visitId]);

  if (loading) {
    return <HeaderSkeleton />;
  }

  if (!visitDetails) {
    return (
      <div className={styles.consultationHeader}>
        <div className={styles.errorMessage}>Visit not found</div>
      </div>
    );
  }

  return (
    <div className={styles.consultationHeader}>
      <div className={styles.visitContext}>
        <h2>Visit #{visitDetails.id}</h2>
        <div className={styles.visitStatus}>
          <span className={`${styles.statusBadge} ${visitDetails.status === 'OPEN' ? styles.statusOpen : styles.statusClosed}`}>
            {visitDetails.status}
          </span>
          <span className={`${styles.paymentBadge} ${visitDetails.payment_status === 'PAID' || visitDetails.payment_status === 'SETTLED' ? styles.paymentCleared : styles.paymentPending}`}>
            Payment: {visitDetails.payment_status}
          </span>
        </div>
      </div>
      
      <div className={styles.patientSummary}>
        <h3>Patient Information</h3>
        <div className={styles.patientDetails}>
          {visitDetails.patient_details ? (
            <>
              <div className={styles.patientField}>
                <label>Name:</label>
                <span>{visitDetails.patient_details.name}</span>
              </div>
              {visitDetails.patient_details.age && (
                <div className={styles.patientField}>
                  <label>Age:</label>
                  <span>{visitDetails.patient_details.age} years</span>
                </div>
              )}
              {visitDetails.patient_details.gender && (
                <div className={styles.patientField}>
                  <label>Gender:</label>
                  <span>
                    {visitDetails.patient_details.gender === 'MALE' ? 'Male' :
                     visitDetails.patient_details.gender === 'FEMALE' ? 'Female' :
                     visitDetails.patient_details.gender === 'OTHER' ? 'Other' :
                     visitDetails.patient_details.gender === 'PREFER_NOT_TO_SAY' ? 'Prefer not to say' :
                     visitDetails.patient_details.gender}
                  </span>
                </div>
              )}
              {visitDetails.patient_details.phone && (
                <div className={styles.patientField}>
                  <label>Phone:</label>
                  <span>{visitDetails.patient_details.phone}</span>
                </div>
              )}
            </>
          ) : (
            <>
              {visitDetails.patient_name && (
                <div className={styles.patientField}>
                  <label>Name:</label>
                  <span>{visitDetails.patient_name}</span>
                </div>
              )}
              {visitDetails.patient_id && (
                <div className={styles.patientField}>
                  <label>Patient ID:</label>
                  <span>{visitDetails.patient_id}</span>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
