/**
 * HistorySection Component
 * 
 * Patient history, chief complaint, and presenting symptoms.
 */
import React from 'react';
import SpeechToTextButton from '../../common/SpeechToTextButton';
import styles from '../../../styles/ConsultationWorkspace.module.css';

interface HistorySectionProps {
  value: string;
  onChange: (value: string) => void;
}

export default function HistorySection({ value, onChange }: HistorySectionProps) {
  return (
    <div className={styles.consultationSection}>
      <label htmlFor="history">
        <h3>History</h3>
        <span className={styles.sectionDescription}>
          Patient history, chief complaint, and presenting symptoms
        </span>
      </label>
      <div style={{ position: 'relative', paddingTop: '2rem' }}>
        <textarea
          id="history"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter patient history, chief complaint, and presenting symptoms..."
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
