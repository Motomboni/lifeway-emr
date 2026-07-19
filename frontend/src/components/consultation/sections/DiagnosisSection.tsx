/**
 * DiagnosisSection Component
 */
import React from 'react';
import SpeechToTextButton from '../../common/SpeechToTextButton';
import MacroAwareTextarea from '../MacroAwareTextarea';
import { ConsultationData } from '../../../types/consultation';
import styles from '../../../styles/ConsultationWorkspace.module.css';

interface DiagnosisSectionProps {
  value: string;
  formData: Pick<ConsultationData, 'history' | 'examination' | 'diagnosis' | 'clinical_notes'>;
  onChange: (value: string) => void;
  onMacroExpand: (updates: Partial<ConsultationData>) => void;
}

export default function DiagnosisSection({
  value,
  formData,
  onChange,
  onMacroExpand,
}: DiagnosisSectionProps) {
  return (
    <div className={styles.consultationSection}>
      <label htmlFor="diagnosis">
        <h3>Diagnosis</h3>
        <span className={styles.sectionDescription}>
          Clinical diagnosis, differential diagnosis, and assessment
        </span>
      </label>
      <div style={{ position: 'relative', paddingTop: '2rem' }}>
        <MacroAwareTextarea
          id="diagnosis"
          field="diagnosis"
          value={value}
          formData={formData}
          onChange={onChange}
          onMacroExpand={onMacroExpand}
          placeholder="Enter diagnosis… Type .dm2 + Tab for macros"
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
