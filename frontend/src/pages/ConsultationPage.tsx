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
 *   ├── ServiceCatalogInline (doctor — after clinical notes)
 *   └── ConsultationActions (save, cancel)
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import ConsultationForm from '../components/consultation/ConsultationForm';
import ConsultationHeader from '../components/consultation/ConsultationHeader';
import WorkflowRail from '../components/guide/WorkflowRail';
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
import { useRegisterGuidePage, useGuidePage } from '../contexts/GuidePageContext';
import { applyMacroTrigger } from '../utils/consultationMacroExpand';
import ServiceCatalogInline from '../components/inline/ServiceCatalogInline';
import VisitChargesReadOnly from '../components/billing/VisitChargesReadOnly';
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
import ConsultationScribePanel from '../components/ai/ConsultationScribePanel';
import styles from '../styles/ConsultationWorkspace.module.css';

interface ConsultationPageProps {
  visitId: string;
}

export default function ConsultationPage({ visitId }: ConsultationPageProps) {
  const location = useLocation();
  const telemedicineTranscript = (
    location.state as { telemedicineTranscript?: string } | null
  )?.telemedicineTranscript;
  const [registrationPaid, setRegistrationPaid] = useState<boolean | null>(null);
  const [gatesLoading, setGatesLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const loadGates = async () => {
      setGatesLoading(true);
      try {
        const summary = await getBillingSummary(parseInt(visitId, 10));
        if (!cancelled) {
          setRegistrationPaid(summary.payment_gates?.registration_paid === true);
        }
      } catch {
        if (!cancelled) {
          setRegistrationPaid(false);
        }
      } finally {
        if (!cancelled) {
          setGatesLoading(false);
        }
      }
    };
    loadGates();
    return () => {
      cancelled = true;
    };
  }, [visitId]);

  const consultationEnabled = registrationPaid === true;

  const {
    consultation,
    loading,
    error,
    saveConsultation,
    updateConsultation,
    isSaving
  } = useConsultation(visitId, { enabled: consultationEnabled });

  const { user } = useAuth();
  const navigate = useNavigate();
  const { toasts, showSuccess, showError, removeToast } = useToast();
  const isOffline = useOffline();
  const { registerMacroHandler } = useGuidePage();

  const [visitStatus, setVisitStatus] = useState<'OPEN' | 'CLOSED'>('OPEN');
  const [visitType, setVisitType] = useState<string | undefined>();
  const [paymentStatus, setPaymentStatus] = useState<string | undefined>();
  const [paymentBlocked, setPaymentBlocked] = useState(false);
  const [isClosingVisit, setIsClosingVisit] = useState(false);
  /** Bumps after catalog orders so doctor-facing charge list refetches */
  const [orderedChargesRefresh, setOrderedChargesRefresh] = useState(0);
  /** Refetch diagnosis codes after scribe apply */
  const [diagnosisCodesRefresh, setDiagnosisCodesRefresh] = useState(0);

  const [formData, setFormData] = useState<ConsultationData>({
    history: '',
    examination: '',
    diagnosis: '',
    clinical_notes: '',
    merge_with_patient_record: false
  });

  const [originalData, setOriginalData] = useState<ConsultationData | null>(null);
  const [mergeWithPatientRecord, setMergeWithPatientRecord] = useState(false);

  useRegisterGuidePage({
    visitId,
    visitStatus,
    paymentStatus,
    hasConsultation: !!consultation,
    paymentBlocked,
  });

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

  // Track dirty state by comparing current form data with original.
  // Compare only the consultation fields plus the merge_with_patient_record flag.
  const isDirty = originalData
    ? (
        formData.history !== originalData.history ||
        formData.examination !== originalData.examination ||
        formData.diagnosis !== originalData.diagnosis ||
        formData.clinical_notes !== originalData.clinical_notes ||
        mergeWithPatientRecord
      )
    : (
        Object.values({
          history: formData.history,
          examination: formData.examination,
          diagnosis: formData.diagnosis,
          clinical_notes: formData.clinical_notes
        }).some(value => typeof value === 'string' && value.trim() !== '') ||
        mergeWithPatientRecord
      );

  const handleFieldChange = (field: keyof ConsultationData, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleApplyFormPatch = useCallback((patch: Partial<ConsultationData>) => {
    setFormData((prev) => ({ ...prev, ...patch }));
  }, []);

  const handleMacroFromGuide = useCallback(
    (trigger: string) => {
      const updates = applyMacroTrigger(trigger, formData);
      if (!updates) return false;
      handleApplyFormPatch(updates);
      showSuccess(`Macro ${trigger} inserted`);
      return true;
    },
    [formData, handleApplyFormPatch, showSuccess]
  );

  useEffect(() => {
    registerMacroHandler(handleMacroFromGuide);
    return () => registerMacroHandler(null);
  }, [handleMacroFromGuide, registerMacroHandler]);

  const handleScribeApply = (sections: Partial<ConsultationData>) => {
    setFormData(prev => ({
      ...prev,
      history: sections.history ?? prev.history,
      examination: sections.examination ?? prev.examination,
      diagnosis: sections.diagnosis ?? prev.diagnosis,
      clinical_notes: sections.clinical_notes ?? prev.clinical_notes,
    }));
  };

  /** Create consultation if needed so lab/radiology/prescription orders can be placed. */
  const ensureConsultation = useCallback(async (): Promise<number> => {
    if (consultation?.id) {
      return consultation.id;
    }
    const saved = await saveConsultation(visitId, {
      ...formData,
      merge_with_patient_record: false,
    });
    setOriginalData({
      history: formData.history,
      examination: formData.examination,
      diagnosis: formData.diagnosis,
      clinical_notes: formData.clinical_notes,
    });
    return saved.id;
  }, [consultation?.id, formData, saveConsultation, visitId]);

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
      // Update original data after successful save and reset merge flag
      setOriginalData({
        history: formData.history,
        examination: formData.examination,
        diagnosis: formData.diagnosis,
        clinical_notes: formData.clinical_notes
      });
      setMergeWithPatientRecord(false);
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
    setMergeWithPatientRecord(false);
  };

  const handleCloseVisit = async () => {
    if (!consultation) {
      showError('Cannot close visit without a consultation');
      return;
    }

    const paymentCleared =
      paymentStatus === 'PAID' ||
      paymentStatus === 'SETTLED' ||
      paymentStatus === 'PARTIALLY_PAID';

    if (paymentStatus && !paymentCleared) {
      setPaymentBlocked(true);
      showError('Payment must be cleared before closing this visit. Ask reception to clear billing.');
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
        setPaymentStatus(visit.payment_status);
        setVisitType(visit.visit_type);
        const cleared =
          visit.payment_status === 'PAID' ||
          visit.payment_status === 'SETTLED' ||
          visit.payment_status === 'PARTIALLY_PAID';
        if (cleared) {
          setPaymentBlocked(false);
        }
      } catch (error) {
        console.error('Failed to load visit status:', error);
      }
    };
    loadVisitStatus();
  }, [visitId]);

  // Show loading skeleton while payment gates or consultation loads
  if (gatesLoading || (consultationEnabled && loading)) {
    return <ConsultationSkeleton />;
  }

  if (registrationPaid === false) {
    return (
      <div className={styles.consultationWorkspace}>
        <BackToDashboard />
        <ConsultationHeader visitId={visitId} />
        <div className={styles.errorContainer}>
          <div className={styles.errorMessage}>Registration payment required</div>
          <div className={styles.errorDetails}>
            Collect registration payment at reception before opening the consultation workspace.
          </div>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={() => navigate(`/visits/${visitId}`)}
          >
            Go to visit billing
          </button>
        </div>
      </div>
    );
  }

  // Show error state when consultation API fails
  if (error && !consultation) {
    return (
      <div className={styles.errorContainer}>
        <div className={styles.errorMessage}>Error loading consultation</div>
        <div className={styles.errorDetails}>{error}</div>
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
      <WorkflowRail visitId={visitId} />
      
      {/* Scrollable content area - form and inline components */}
      <div className={styles.consultationContent}>
        {/* Clinical Alerts - show first if any */}
        <div data-guide-id="clinical-alerts">
          <ClinicalAlertsInline visitId={visitId} />
        </div>
        
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
          onApplyFormPatch={handleApplyFormPatch}
          visitId={visitId}
          isNewConsultation={!consultation}
          visitType={visitType}
        />

        {/* Service Catalog — immediately after clinical notes */}
        {user?.role === 'DOCTOR' && (
          <ServiceCatalogInline
            visitId={visitId}
            onServiceAdded={() => setOrderedChargesRefresh((n) => n + 1)}
          />
        )}

        {/* Lab → Radiology → Prescriptions → Ordered services → Referrals */}
        <LabInline
          visitId={visitId}
          consultationId={consultation?.id}
          ensureConsultation={ensureConsultation}
        />
        <RadiologyInline
          visitId={visitId}
          consultationId={consultation?.id}
          ensureConsultation={ensureConsultation}
        />
        <PrescriptionInline
          visitId={visitId}
          consultationId={consultation?.id}
          ensureConsultation={ensureConsultation}
        />
        {user?.role === 'DOCTOR' && (
          <div className={styles.inlineComponent}>
            <VisitChargesReadOnly
              visitId={parseInt(visitId, 10)}
              refreshTrigger={orderedChargesRefresh}
              embedded
            />
          </div>
        )}
        {consultation && (
          <ReferralsInline visitId={visitId} consultationId={consultation.id} />
        )}
        
        {/* Diagnosis Codes - show after consultation is saved */}
        {consultation && (
          <DiagnosisCodes
            key={diagnosisCodesRefresh}
            visitId={visitId}
            consultationId={consultation.id}
          />
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

        {/* Clinical AI Scribe — after AI-Powered Features */}
        {user?.role === 'DOCTOR' && (
          <ConsultationScribePanel
            visitId={visitId}
            consultationId={consultation?.id}
            initialTranscript={telemedicineTranscript}
            onApplySections={handleScribeApply}
            onCodesApplied={() => setDiagnosisCodesRefresh((n) => n + 1)}
            onNhiaBilled={() => setOrderedChargesRefresh((n) => n + 1)}
          />
        )}
        
        {/* Documents - can be uploaded anytime */}
        <DocumentsInline visitId={visitId} />
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
