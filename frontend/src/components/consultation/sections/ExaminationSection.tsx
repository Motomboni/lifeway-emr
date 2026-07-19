/**
 * ExaminationSection Component
 */
import React from 'react';
import SpeechToTextButton from '../../common/SpeechToTextButton';
import MacroAwareTextarea from '../MacroAwareTextarea';
import { ConsultationData } from '../../../types/consultation';
import styles from '../../../styles/ConsultationWorkspace.module.css';

interface ExaminationSectionProps {
  value: string;
  formData: Pick<ConsultationData, 'history' | 'examination' | 'diagnosis' | 'clinical_notes'>;
  onChange: (value: string) => void;
  onMacroExpand: (updates: Partial<ConsultationData>) => void;
}

export default function ExaminationSection({
  value,
  formData,
  onChange,
  onMacroExpand,
}: ExaminationSectionProps) {
  return (
    <div className={styles.consultationSection}>
      <label htmlFor="examination">
        <h3>Examination</h3>
        <span className={styles.sectionDescription}>
          Physical examination findings and clinical observations
        </span>
      </label>
      <div style={{ position: 'relative', paddingTop: '2rem' }}>
        <MacroAwareTextarea
          id="examination"
          field="examination"
          value={value}
          formData={formData}
          onChange={onChange}
          onMacroExpand={onMacroExpand}
          placeholder="Enter examination findings… Type .uri + Tab for macros"
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
