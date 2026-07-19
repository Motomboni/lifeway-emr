/**
 * ClinicalNotesSection Component
 */
import React from 'react';
import SpeechToTextButton from '../../common/SpeechToTextButton';
import MacroAwareTextarea from '../MacroAwareTextarea';
import { ConsultationData } from '../../../types/consultation';
import styles from '../../../styles/ConsultationWorkspace.module.css';

interface ClinicalNotesSectionProps {
  value: string;
  formData: Pick<ConsultationData, 'history' | 'examination' | 'diagnosis' | 'clinical_notes'>;
  onChange: (value: string) => void;
  onMacroExpand: (updates: Partial<ConsultationData>) => void;
}

export default function ClinicalNotesSection({
  value,
  formData,
  onChange,
  onMacroExpand,
}: ClinicalNotesSectionProps) {
  return (
    <div className={styles.consultationSection}>
      <label htmlFor="clinical_notes">
        <h3>Clinical Notes</h3>
        <span className={styles.sectionDescription}>
          Treatment plan, prescriptions, follow-up instructions, and additional notes
        </span>
      </label>
      <div style={{ position: 'relative', paddingTop: '2rem' }}>
        <MacroAwareTextarea
          id="clinical_notes"
          field="clinical_notes"
          value={value}
          formData={formData}
          onChange={onChange}
          onMacroExpand={onMacroExpand}
          placeholder="Enter clinical notes… Type .htn + Tab for macros"
          rows={6}
          className={styles.consultationTextarea}
        />
        <SpeechToTextButton
          value={value}
          onTranscribe={onChange}
          appendMode={true}
          position="top-right"
          showPreview={true}
        />
      </div>
    </div>
  );
}
