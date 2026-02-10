/**
 * Nurse Visit Header Component
 * 
 * Displays visit context and patient summary (read-only).
 * Ensures visit context is never lost - always visible at top.
 * NO diagnosis, billing, or insurance information shown.
 */
import React, { useEffect, useState } from 'react';
import { fetchVisitDetails, VisitDetails } from '../../api/visits';
import { HeaderSkeleton } from '../common/LoadingSkeleton';
import styles from '../../styles/NurseVisit.module.css';

interface NurseVisitHeaderProps {
  visitId: string;
  visit: any; // Visit from parent, but we'll use fetchVisitDetails for full details
}

export default function NurseVisitHeader({ visitId, visit: visitProp }: NurseVisitHeaderProps) {
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

  const visit = visitDetails || visitProp;

  if (!visit) {
    return (
      <div className={styles.nurseVisitHeader}>
        <div className={styles.errorMessage}>Visit not found</div>
      </div>
    );
  }

  return (
    <div className={styles.nurseVisitHeader}>
      <div className={styles.visitContext}>
        <h2>Visit #{visitId} - Nursing Care</h2>
        <div className={styles.visitStatus}>
          <span className={`${styles.statusBadge} ${visit.status === 'OPEN' ? styles.statusOpen : styles.statusClosed}`}>
            {visit.status}
          </span>
          <span className={`${styles.paymentBadge} ${visit.payment_status === 'PAID' || visit.payment_status === 'SETTLED' ? styles.paymentCleared : styles.paymentPending}`}>
            Payment: {visit.payment_status}
          </span>
        </div>
      </div>
      
      <div className={styles.patientSummary}>
        <h3>Patient Information</h3>
        <div className={styles.patientDetails}>
          {(visit as VisitDetails).patient_details ? (
            <>
              <div className={styles.patientField}>
                <label>Name:</label>
                <span>{(visit as VisitDetails).patient_details!.name}</span>
              </div>
              {(visit as VisitDetails).patient_details!.age && (
                <div className={styles.patientField}>
                  <label>Age:</label>
                  <span>{(visit as VisitDetails).patient_details!.age} years</span>
                </div>
              )}
              {(visit as VisitDetails).patient_details!.gender && (
                <div className={styles.patientField}>
                  <label>Gender:</label>
                  <span>
                    {(visit as VisitDetails).patient_details!.gender === 'MALE' ? 'Male' :
                     (visit as VisitDetails).patient_details!.gender === 'FEMALE' ? 'Female' :
                     (visit as VisitDetails).patient_details!.gender === 'OTHER' ? 'Other' :
                     (visit as VisitDetails).patient_details!.gender === 'PREFER_NOT_TO_SAY' ? 'Prefer not to say' :
                     (visit as VisitDetails).patient_details!.gender}
                  </span>
                </div>
              )}
              {(visit as VisitDetails).patient_details!.phone && (
                <div className={styles.patientField}>
                  <label>Phone:</label>
                  <span>{(visit as VisitDetails).patient_details!.phone}</span>
                </div>
              )}
            </>
          ) : (
            <>
              {visit.patient_name && (
                <div className={styles.patientField}>
                  <label>Name:</label>
                  <span>{visit.patient_name}</span>
                </div>
              )}
              {visit.patient_id && (
                <div className={styles.patientField}>
                  <label>Patient ID:</label>
                  <span>{visit.patient_id}</span>
                </div>
              )}
            </>
          )}
        </div>
        <div className={styles.contextNote}>
          <p>📋 Visit Context: All actions are scoped to this visit. Context is preserved throughout.</p>
        </div>
      </div>
    </div>
  );
}
