/**
 * Previous Consultations Panel Component
 * 
 * Displays previous consultations for the same patient, allowing doctors to:
 * - View previous consultation history
 * - Copy data from previous consultations into the current form
 */
import React, { useState, useEffect } from 'react';
import { fetchPatientConsultations } from '../../api/consultation';
import { Consultation } from '../../types/consultation';
import { useToast } from '../../hooks/useToast';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface PreviousConsultationsPanelProps {
  visitId: string;
  onCopyData: (consultation: Consultation) => void;
}

export default function PreviousConsultationsPanel({
  visitId,
  onCopyData
}: PreviousConsultationsPanelProps) {
  const { showError } = useToast();
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showPanel, setShowPanel] = useState(false);

  useEffect(() => {
    if (showPanel) {
      loadConsultations();
    }
  }, [visitId, showPanel]);

  const loadConsultations = async () => {
    try {
      setLoading(true);
      const data = await fetchPatientConsultations(visitId);
      setConsultations(Array.isArray(data) ? data : []);
    } catch (error: any) {
      console.error('Failed to load previous consultations:', error);
      // Don't show error if it's just "no consultations found" (empty array is valid)
      if (error.status !== 404 && error.status !== 200) {
        showError(error.message || 'Failed to load previous consultations');
      }
      setConsultations([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleCopyField = (consultation: Consultation, field: keyof Consultation) => {
    const value = consultation[field] as string;
    if (value && value.trim()) {
      // Create a partial consultation object with just this field
      const partialConsultation = {
        ...consultation,
        [field]: value
      } as Consultation;
      onCopyData(partialConsultation);
    }
  };

  const handleCopyAll = (consultation: Consultation) => {
    onCopyData(consultation);
  };

  if (!showPanel) {
    return (
      <div className={styles.previousConsultationsToggle}>
        <button
          type="button"
          className={styles.toggleButton}
          onClick={() => setShowPanel(true)}
        >
          📋 View Previous Consultations
        </button>
      </div>
    );
  }

  return (
    <div className={styles.previousConsultationsPanel}>
      <div className={styles.panelHeader}>
        <h3>Previous Consultations</h3>
        <button
          type="button"
          className={styles.closeButton}
          onClick={() => setShowPanel(false)}
        >
          ✕
        </button>
      </div>

      {loading ? (
        <div className={styles.loadingState}>
          <p>Loading previous consultations...</p>
        </div>
      ) : consultations.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No previous consultations found for this patient.</p>
        </div>
      ) : (
        <div className={styles.consultationsList}>
          {consultations.map((consultation) => (
            <div
              key={consultation.id}
              className={styles.consultationCard}
            >
              <div
                className={styles.consultationHeader}
                onClick={() => setExpandedId(expandedId === consultation.id ? null : consultation.id)}
              >
                <div className={styles.consultationInfo}>
                  <strong>Visit #{consultation.visit_id}</strong>
                  <span className={styles.consultationDate}>
                    {formatDate(consultation.created_at)}
                  </span>
                  {consultation.created_by_name && (
                    <span className={styles.consultationDoctor}>
                      Dr. {consultation.created_by_name}
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  className={styles.copyAllButton}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCopyAll(consultation);
                  }}
                >
                  Copy All
                </button>
              </div>

              {expandedId === consultation.id && (
                <div className={styles.consultationDetails}>
                  {consultation.history && (
                    <div className={styles.consultationField}>
                      <div className={styles.fieldHeader}>
                        <strong>History</strong>
                        <button
                          type="button"
                          className={styles.copyFieldButton}
                          onClick={() => handleCopyField(consultation, 'history')}
                        >
                          Copy
                        </button>
                      </div>
                      <p className={styles.fieldContent}>{consultation.history}</p>
                    </div>
                  )}

                  {consultation.examination && (
                    <div className={styles.consultationField}>
                      <div className={styles.fieldHeader}>
                        <strong>Examination</strong>
                        <button
                          type="button"
                          className={styles.copyFieldButton}
                          onClick={() => handleCopyField(consultation, 'examination')}
                        >
                          Copy
                        </button>
                      </div>
                      <p className={styles.fieldContent}>{consultation.examination}</p>
                    </div>
                  )}

                  {consultation.diagnosis && (
                    <div className={styles.consultationField}>
                      <div className={styles.fieldHeader}>
                        <strong>Diagnosis</strong>
                        <button
                          type="button"
                          className={styles.copyFieldButton}
                          onClick={() => handleCopyField(consultation, 'diagnosis')}
                        >
                          Copy
                        </button>
                      </div>
                      <p className={styles.fieldContent}>{consultation.diagnosis}</p>
                    </div>
                  )}

                  {consultation.clinical_notes && (
                    <div className={styles.consultationField}>
                      <div className={styles.fieldHeader}>
                        <strong>Clinical Notes</strong>
                        <button
                          type="button"
                          className={styles.copyFieldButton}
                          onClick={() => handleCopyField(consultation, 'clinical_notes')}
                        >
                          Copy
                        </button>
                      </div>
                      <p className={styles.fieldContent}>{consultation.clinical_notes}</p>
                    </div>
                  )}

                  {(!consultation.history && !consultation.examination && 
                    !consultation.diagnosis && !consultation.clinical_notes) && (
                    <p className={styles.emptyConsultation}>No data in this consultation.</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
