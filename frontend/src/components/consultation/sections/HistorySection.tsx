/**
 * HistorySection Component
 */
import React from 'react';
import SpeechToTextButton from '../../common/SpeechToTextButton';
import MacroAwareTextarea from '../MacroAwareTextarea';
import { ConsultationData } from '../../../types/consultation';
import styles from '../../../styles/ConsultationWorkspace.module.css';

interface HistorySectionProps {
  value: string;
  formData: Pick<ConsultationData, 'history' | 'examination' | 'diagnosis' | 'clinical_notes'>;
  onChange: (value: string) => void;
  onMacroExpand: (updates: Partial<ConsultationData>) => void;
}

export default function HistorySection({
  value,
  formData,
  onChange,
  onMacroExpand,
}: HistorySectionProps) {
  return (
    <div className={styles.consultationSection}>
      <label htmlFor="history">
        <h3>History</h3>
        <span className={styles.sectionDescription}>
          Patient history, chief complaint, and presenting symptoms
        </span>
      </label>
      <div style={{ position: 'relative', paddingTop: '2rem' }}>
        <MacroAwareTextarea
          id="history"
          field="history"
          value={value}
          formData={formData}
          onChange={onChange}
          onMacroExpand={onMacroExpand}
          placeholder="Enter patient history… Type .uri + Tab for macros"
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
