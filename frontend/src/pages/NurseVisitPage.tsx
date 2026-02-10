/**
 * Nurse Visit Page - Visit-Scoped UI
 * 
 * EMR Rule Compliance:
 * - Visit-scoped: All actions require visitId from URL
 * - No sidebar navigation: Single screen only
 * - Context preservation: Visit context never lost
 * - Permission-aware: Only shows sections Nurse can access
 * - Read-only where appropriate: Diagnosis, billing, insurance hidden
 * 
 * Component Hierarchy:
 * NurseVisitPage (container)
 *   ├── NurseVisitHeader (visit context, patient summary)
 *   ├── VitalSignsSection (create/view vital signs)
 *   ├── NursingNotesSection (create/view nursing notes)
 *   ├── MedicationAdministrationSection (create/view medication administration)
 *   ├── LabSampleCollectionSection (create/view lab sample collection)
 *   └── PatientEducationSection (create/view patient education)
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { getVisit } from '../api/visits';
import { Visit } from '../types/visit';
import { useToast } from '../hooks/useToast';
import { useOffline } from '../hooks/useOffline';
import ToastContainer from '../components/common/ToastContainer';
import OfflineIndicator from '../components/common/OfflineIndicator';
import BackToDashboard from '../components/common/BackToDashboard';
import NurseVisitHeader from '../components/nursing/NurseVisitHeader';
import AdmissionInformationSection from '../components/nursing/AdmissionInformationSection';
import VitalSignsSection from '../components/nursing/VitalSignsSection';
import NursingNotesSection from '../components/nursing/NursingNotesSection';
import MedicationAdministrationSection from '../components/nursing/MedicationAdministrationSection';
import LabSampleCollectionSection from '../components/nursing/LabSampleCollectionSection';
import PatientEducationSection from '../components/nursing/PatientEducationSection';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/NurseVisit.module.css';

export default function NurseVisitPage() {
  const { visitId } = useParams<{ visitId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toasts, showError, removeToast } = useToast();
  const isOffline = useOffline();

  const [visit, setVisit] = useState<Visit | null>(null);
  const [loading, setLoading] = useState(true);
  const [visitStatus, setVisitStatus] = useState<'OPEN' | 'CLOSED'>('OPEN');
  const [paymentStatus, setPaymentStatus] = useState<'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'INSURANCE_PENDING' | 'INSURANCE_CLAIMED' | 'SETTLED'>('UNPAID');

  // Ensure user is a Nurse
  useEffect(() => {
    if (user && user.role !== 'NURSE') {
      navigate('/dashboard');
      return;
    }
  }, [user, navigate]);

  // Load visit details
  useEffect(() => {
    if (visitId) {
      loadVisitDetails();
    }
  }, [visitId]);

  const loadVisitDetails = async () => {
    if (!visitId) return;

    try {
      setLoading(true);
      const visitData = await getVisit(parseInt(visitId));
      setVisit(visitData);
      setVisitStatus(visitData.status as 'OPEN' | 'CLOSED');
      setPaymentStatus(visitData.payment_status as 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'INSURANCE_PENDING' | 'INSURANCE_CLAIMED' | 'SETTLED');
    } catch (error: any) {
      console.error('Failed to load visit details:', error);
      showError(error.message || 'Failed to load visit details');
    } finally {
      setLoading(false);
    }
  };

  // Show loading state
  if (loading || !visitId) {
    return (
      <div className={styles.nurseVisitPage}>
        <LoadingSkeleton count={5} />
      </div>
    );
  }

  // Show error if visit not found
  if (!visit) {
    return (
      <div className={styles.nurseVisitPage}>
        <div className={styles.errorContainer}>
          <div className={styles.errorMessage}>Visit not found</div>
          <button onClick={() => navigate('/dashboard')} className={styles.backButton}>
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  // Check if visit is accessible (OPEN and payment CLEARED for actions)
  // Include PARTIALLY_PAID as cleared payment status (allows clinical actions)
  const canPerformActions = visitStatus === 'OPEN' && (
    paymentStatus === 'PAID' || 
    paymentStatus === 'SETTLED' || 
    paymentStatus === 'PARTIALLY_PAID'
  );
  const isVisitClosed = visitStatus === 'CLOSED';

  return (
    <div className={styles.nurseVisitPage}>
      {/* Offline indicator */}
      {isOffline && <OfflineIndicator />}
      
      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      
      {/* Back to Dashboard */}
      <BackToDashboard />
      
      {/* Visit context header - always visible, visit context preserved */}
      {visitId && (
        <>
          <NurseVisitHeader visitId={visitId} visit={visit} />
          
          {/* Status warning banner */}
          {!canPerformActions && (
            <div className={styles.statusWarning}>
              {isVisitClosed ? (
                <div className={styles.warningMessage}>
                  ⚠️ This visit is CLOSED. You can view records but cannot create new ones.
                </div>
              ) : (
                <div className={styles.warningMessage}>
                  ⚠️ Payment is pending. Please wait for payment to be cleared before performing actions.
                </div>
              )}
            </div>
          )}
          
          {/* Scrollable content area - all sections */}
          <div className={styles.nurseVisitContent}>
            {/* Section 0: Admission Information */}
            <AdmissionInformationSection visitId={visitId} />
            
            {/* Section 1: Vital Signs */}
            <VitalSignsSection 
              visitId={visitId} 
              canCreate={canPerformActions}
            />
            
            {/* Section 2: Nursing Notes */}
            <NursingNotesSection 
              visitId={visitId} 
              canCreate={canPerformActions}
            />
            
            {/* Section 3: Medication Administration */}
            <MedicationAdministrationSection 
              visitId={visitId} 
              canCreate={canPerformActions}
            />
            
            {/* Section 4: Lab Sample Collection */}
            <LabSampleCollectionSection 
              visitId={visitId} 
              canCreate={canPerformActions}
            />
            
            {/* Section 5: Patient Education */}
            <PatientEducationSection 
              visitId={visitId} 
              canCreate={canPerformActions}
            />
          </div>
        </>
      )}
    </div>
  );
}
