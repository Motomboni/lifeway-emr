/**
 * ConsultationActions Component
 * 
 * Action buttons for saving/canceling consultation and closing visit.
 * Fixed at bottom of screen to ensure visibility.
 */
import React from 'react';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface ConsultationActionsProps {
  onSave: () => void;
  onCancel: () => void;
  onCloseVisit?: () => void;
  isDirty: boolean;
  isSaving: boolean;
  hasConsultation: boolean;
  canCloseVisit: boolean;
  isClosingVisit: boolean;
  visitStatus: 'OPEN' | 'CLOSED';
  mergeWithPatientRecord: boolean;
  onMergeChange: (merge: boolean) => void;
}

export default function ConsultationActions({
  onSave,
  onCancel,
  onCloseVisit,
  isDirty,
  isSaving,
  hasConsultation,
  canCloseVisit,
  isClosingVisit,
  visitStatus,
  mergeWithPatientRecord,
  onMergeChange
}: ConsultationActionsProps) {
  const isClosed = visitStatus === 'CLOSED';
  
  return (
    <div className={styles.consultationActions}>
      {!isClosed && (
        <>
          <div className={styles.mergeOption}>
            <label className={styles.mergeCheckbox}>
              <input
                type="checkbox"
                checked={mergeWithPatientRecord}
                onChange={(e) => onMergeChange(e.target.checked)}
                disabled={isSaving || isClosingVisit}
              />
              <span>Merge with patient's medical history</span>
            </label>
            <span className={styles.mergeHint}>
              (Adds this consultation to the patient's ongoing medical record)
            </span>
          </div>
          
          <button
            type="button"
            onClick={onCancel}
            disabled={!isDirty || isSaving || isClosingVisit}
            className={styles.btnCancel}
          >
            Cancel
          </button>
          
          <button
            type="button"
            onClick={onSave}
            disabled={!isDirty || isSaving || isClosingVisit}
            className={styles.btnSave}
          >
            {isSaving ? 'Saving...' : hasConsultation ? 'Update Consultation' : 'Save Consultation'}
          </button>
        </>
      )}
      
      {canCloseVisit && onCloseVisit && !isClosed && (
        <button
          type="button"
          onClick={onCloseVisit}
          disabled={isSaving || isDirty || isClosingVisit}
          className={styles.btnCloseVisit}
          title="Close this visit. Once closed, no further changes can be made."
        >
          {isClosingVisit ? 'Closing...' : 'Close Visit'}
        </button>
      )}
      
      {isClosed && (
        <div className={styles.closedNotice}>
          <span>This visit is closed and cannot be modified.</span>
        </div>
      )}
    </div>
  );
}
