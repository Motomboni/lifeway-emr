/**
 * Consultation Workspace - Single Screen UI
 * 
 * EMR Rule Compliance:
 * - Visit-scoped: All actions require visitId
 * - No sidebar navigation: Single screen only
 * - Context preservation: Visit context never lost
 * - Service Catalog: Doctors order services from catalog (unified ordering system)
 * 
 * Component Hierarchy:
 * ConsultationPage (container)
 *   ├── ConsultationHeader (visit context, patient summary)
 *   ├── ConsultationForm (main form)
 *   │   ├── HistorySection
 *   │   ├── ExaminationSection
 *   │   ├── DiagnosisSection
 *   │   └── ClinicalNotesSection
 *   └── ConsultationActions (save, cancel)
 */
import React, { useState, useEffect } from 'react';
import ConsultationHeader from '../components/consultation/ConsultationHeader';
import ConsultationForm from '../components/consultation/ConsultationForm';
import ConsultationActions from '../components/consultation/ConsultationActions';
import ToastContainer from '../components/common/ToastContainer';
import OfflineIndicator from '../components/common/OfflineIndicator';
import { ConsultationSkeleton } from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import { useConsultation } from '../hooks/useConsultation';
import { useToast } from '../hooks/useToast';
import { useOffline } from '../hooks/useOffline';
import { ConsultationData, Consultation } from '../types/consultation';
import { closeVisit } from '../api/visits';
import { getBillingSummary } from '../api/billing';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import ServiceCatalogInline from '../components/inline/ServiceCatalogInline';
import VitalSignsInline from '../components/clinical/VitalSignsInline';
import ClinicalAlertsInline from '../components/clinical/ClinicalAlertsInline';
import DocumentsInline from '../components/documents/DocumentsInline';
import ReferralsInline from '../components/referrals/ReferralsInline';
import AIInline from '../components/ai/AIInline';
import LabInline from '../components/inline/LabInline';
import PreviousConsultationsPanel from '../components/consultation/PreviousConsultationsPanel';
import PrescriptionInline from '../components/inline/PrescriptionInline';
import RadiologyInline from '../components/inline/RadiologyInline';
import DiagnosisCodes from '../components/consultation/DiagnosisCodes';
import styles from '../styles/ConsultationWorkspace.module.css';

interface ConsultationPageProps {
  visitId: string;
}

export default function ConsultationPage({ visitId }: ConsultationPageProps) {
  const [billingSummary, setBillingSummary] = useState<{ payment_gates?: { registration_paid?: boolean } } | null>(null);
  const [billingSummaryLoading, setBillingSummaryLoading] = useState(true);
  const registrationPaid = billingSummary?.payment_gates?.registration_paid === true;

  const {
    consultation,
    loading,
    error,
    saveConsultation,
    updateConsultation,
    isSaving
  } = useConsultation(visitId, { enabled: registrationPaid });

  const { user } = useAuth();
  const navigate = useNavigate();
  const { toasts, showSuccess, showError, removeToast } = useToast();
  const isOffline = useOffline();

  const [visitStatus, setVisitStatus] = useState<'OPEN' | 'CLOSED'>('OPEN');
  const [isClosingVisit, setIsClosingVisit] = useState(false);

  // Load billing summary to check payment gate before calling consultation API (avoids 403)
  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setBillingSummaryLoading(true);
      try {
        const summary = await getBillingSummary(parseInt(visitId, 10));
        if (!cancelled) setBillingSummary(summary);
      } catch {
        if (!cancelled) setBillingSummary(null);
      } finally {
        if (!cancelled) setBillingSummaryLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [visitId]);

  const [formData, setFormData] = useState<ConsultationData>({
    history: '',
    examination: '',
    diagnosis: '',
    clinical_notes: '',
    merge_with_patient_record: false
  });

  const [originalData, setOriginalData] = useState<ConsultationData | null>(null);
  const [mergeWithPatientRecord, setMergeWithPatientRecord] = useState(false);

  // Clear form data when visitId changes (navigating to a different visit)
  useEffect(() => {
    setFormData({
      history: '',
      examination: '',
      diagnosis: '',
      clinical_notes: '',
      merge_with_patient_record: false
    });
    setOriginalData(null);
    setMergeWithPatientRecord(false);
  }, [visitId]);

  // Load existing consultation data
  useEffect(() => {
    if (consultation) {
      const data = {
        history: consultation.history || '',
        examination: consultation.examination || '',
        diagnosis: consultation.diagnosis || '',
        clinical_notes: consultation.clinical_notes || '',
        merge_with_patient_record: false // This field is separate from consultation data
      };
      setFormData(data);
      // Store original data without merge_with_patient_record for comparison
      setOriginalData({
        history: consultation.history || '',
        examination: consultation.examination || '',
        diagnosis: consultation.diagnosis || '',
        clinical_notes: consultation.clinical_notes || ''
      });
    } else {
      // Clear form data when there's no existing consultation (new consultation)
      setFormData({
        history: '',
        examination: '',
        diagnosis: '',
        clinical_notes: '',
        merge_with_patient_record: false
      });
      setOriginalData(null);
    }
  }, [consultation]);

  // Track dirty state by comparing current form data with original
  // Compare only the consultation fields, not merge_with_patient_record
  const isDirty = originalData
    ? (formData.history !== originalData.history ||
       formData.examination !== originalData.examination ||
       formData.diagnosis !== originalData.diagnosis ||
       formData.clinical_notes !== originalData.clinical_notes)
    : Object.values({
        history: formData.history,
        examination: formData.examination,
        diagnosis: formData.diagnosis,
        clinical_notes: formData.clinical_notes
      }).some(value => typeof value === 'string' && value.trim() !== '');

  const handleFieldChange = (field: keyof ConsultationData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleCopyFromPrevious = (previousConsultation: Consultation) => {
    // Copy data from previous consultation, appending to existing data if any
    setFormData(prev => ({
      history: previousConsultation.history 
        ? (prev.history ? `${prev.history}\n\n--- Previous Consultation ---\n${previousConsultation.history}` : previousConsultation.history)
        : prev.history,
      examination: previousConsultation.examination 
        ? (prev.examination ? `${prev.examination}\n\n--- Previous Consultation ---\n${previousConsultation.examination}` : previousConsultation.examination)
        : prev.examination,
      diagnosis: previousConsultation.diagnosis 
        ? (prev.diagnosis ? `${prev.diagnosis}\n\n--- Previous Consultation ---\n${previousConsultation.diagnosis}` : previousConsultation.diagnosis)
        : prev.diagnosis,
      clinical_notes: previousConsultation.clinical_notes 
        ? (prev.clinical_notes ? `${prev.clinical_notes}\n\n--- Previous Consultation ---\n${previousConsultation.clinical_notes}` : previousConsultation.clinical_notes)
        : prev.clinical_notes,
      merge_with_patient_record: prev.merge_with_patient_record
    }));
    showSuccess('Data copied from previous consultation');
  };

  const handleSave = async () => {
    try {
      const dataToSave = {
        ...formData,
        merge_with_patient_record: mergeWithPatientRecord
      };
      if (consultation) {
        await updateConsultation(visitId, dataToSave);
        showSuccess(mergeWithPatientRecord 
          ? 'Consultation updated and merged with patient record successfully'
          : 'Consultation updated successfully'
        );
      } else {
        await saveConsultation(visitId, dataToSave);
        showSuccess(mergeWithPatientRecord 
          ? 'Consultation saved and merged with patient record successfully'
          : 'Consultation saved successfully'
        );
      }
      // Update original data after successful save (exclude merge_with_patient_record from comparison)
      setOriginalData({
        history: formData.history,
        examination: formData.examination,
        diagnosis: formData.diagnosis,
        clinical_notes: formData.clinical_notes
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save consultation';
      showError(errorMessage);
    }
  };

  const handleCancel = () => {
    // Reset to original consultation data
    if (originalData) {
      setFormData({ ...originalData });
    } else {
      setFormData({
        history: '',
        examination: '',
        diagnosis: '',
        clinical_notes: ''
      });
    }
  };

  const handleCloseVisit = async () => {
    if (!consultation) {
      showError('Cannot close visit without a consultation');
      return;
    }

    if (!window.confirm('Are you sure you want to close this visit? Once closed, no further changes can be made.')) {
      return;
    }

    try {
      setIsClosingVisit(true);
      await closeVisit(parseInt(visitId));
      showSuccess('Visit closed successfully');
      setVisitStatus('CLOSED');
      // Optionally navigate away or refresh
      setTimeout(() => {
        navigate('/visits');
      }, 1500);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to close visit';
      showError(errorMessage);
    } finally {
      setIsClosingVisit(false);
    }
  };

  // Load visit status
  useEffect(() => {
    const loadVisitStatus = async () => {
      try {
        const { getVisit } = await import('../api/visits');
        const visit = await getVisit(parseInt(visitId));
        setVisitStatus(visit.status as 'OPEN' | 'CLOSED');
      } catch (error) {
        console.error('Failed to load visit status:', error);
      }
    };
    loadVisitStatus();
  }, [visitId]);

  // Wait for billing summary to know if we can access consultation
  if (billingSummaryLoading) {
    return <ConsultationSkeleton />;
  }

  // Block access when registration not paid (no consultation API call, so no 403)
  if (!registrationPaid) {
    return (
      <div className={styles.consultationWorkspace}>
        <BackToDashboard />
        <div className={styles.errorContainer}>
          <div className={styles.errorMessage}>Registration payment required</div>
          <div className={styles.errorDetails}>
            Registration must be paid before access to consultation. Please collect at reception.
          </div>
          <button
            type="button"
            onClick={() => navigate(`/visits/${visitId}#billing-section`)}
            style={{ marginTop: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}
          >
            Go to Visit Billing →
          </button>
        </div>
      </div>
    );
  }

  // Show loading skeleton while consultation loads
  if (loading) {
    return <ConsultationSkeleton />;
  }

  // Show error state (e.g. consultation payment required or other API error)
  if (error && !consultation) {
    const isPaymentError = /payment|registration|consultation/i.test(error);
    return (
      <div className={styles.errorContainer}>
        <div className={styles.errorMessage}>
          {isPaymentError ? 'Payment required' : 'Error loading consultation'}
        </div>
        <div className={styles.errorDetails}>{error}</div>
        {isPaymentError && (
          <button
            type="button"
            onClick={() => navigate(`/visits/${visitId}#billing-section`)}
            style={{ marginTop: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}
          >
            Go to Visit Billing →
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={styles.consultationWorkspace}>
      {/* Offline indicator */}
      {isOffline && <OfflineIndicator />}
      
      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
      
      {/* Back to Dashboard */}
      <BackToDashboard />
      
      {/* Visit context header - always visible */}
      <ConsultationHeader visitId={visitId} />
      
      {/* Scrollable content area - form and inline components */}
      <div className={styles.consultationContent}>
        {/* Clinical Alerts - show first if any */}
        <ClinicalAlertsInline visitId={visitId} />
        
        {/* Vital Signs - can be recorded anytime */}
        <VitalSignsInline visitId={visitId} />
        
        {/* Previous Consultations Panel - show before form for reference */}
        {user?.role === 'DOCTOR' && (
          <PreviousConsultationsPanel
            visitId={visitId}
            onCopyData={handleCopyFromPrevious}
          />
        )}
        
        {/* Main consultation form */}
        <ConsultationForm
          formData={formData}
          onFieldChange={handleFieldChange}
        />
        
        {/* Diagnosis Codes - show after consultation is saved */}
        {consultation && (
          <DiagnosisCodes visitId={visitId} consultationId={consultation.id} />
        )}
        
        {/* AI Features - available for doctors */}
        {user?.role === 'DOCTOR' && (
          <AIInline
            visitId={visitId}
            consultationId={consultation?.id}
            consultationData={consultation ? {
              history: consultation.history,
              examination: consultation.examination,
              diagnosis: consultation.diagnosis,
              clinical_notes: consultation.clinical_notes,
            } : {
              history: formData.history,
              examination: formData.examination,
              diagnosis: formData.diagnosis,
              clinical_notes: formData.clinical_notes,
            }}
          />
        )}
        
        {/* Documents - can be uploaded anytime */}
        <DocumentsInline visitId={visitId} />
        
        {/* Service Catalog - available for doctors to order services */}
        {user?.role === 'DOCTOR' && (
          <ServiceCatalogInline visitId={visitId} />
        )}
        
        {/* Lab Orders & Results - show orders and their results */}
        <LabInline visitId={visitId} consultationId={consultation?.id} />
        
        {/* Prescriptions - show prescribed medications */}
        <PrescriptionInline visitId={visitId} consultationId={consultation?.id} />
        
        {/* Radiology Orders & Results - show imaging orders and reports */}
        <RadiologyInline visitId={visitId} consultationId={consultation?.id} />
        
        {/* Referrals - requires consultation */}
        {consultation && (
          <ReferralsInline visitId={visitId} consultationId={consultation.id} />
        )}
      </div>
      
      {/* Action buttons - fixed at bottom */}
      <ConsultationActions
        onSave={handleSave}
        onCancel={handleCancel}
        onCloseVisit={user?.role === 'DOCTOR' ? handleCloseVisit : undefined}
        isDirty={isDirty}
        isSaving={isSaving}
        hasConsultation={!!consultation}
        canCloseVisit={user?.role === 'DOCTOR' && !!consultation && visitStatus === 'OPEN'}
        isClosingVisit={isClosingVisit}
        visitStatus={visitStatus}
        mergeWithPatientRecord={mergeWithPatientRecord}
        onMergeChange={setMergeWithPatientRecord}
      />
    </div>
  );
}
