/**
 * DiagnosisSection Component
 * 
 * Clinical diagnosis, differential diagnosis, and assessment.
 */
import React from 'react';
import SpeechToTextButton from '../../common/SpeechToTextButton';
import styles from '../../../styles/ConsultationWorkspace.module.css';

interface DiagnosisSectionProps {
  value: string;
  onChange: (value: string) => void;
}

export default function DiagnosisSection({ value, onChange }: DiagnosisSectionProps) {
  return (
    <div className={styles.consultationSection}>
      <label htmlFor="diagnosis">
        <h3>Diagnosis</h3>
        <span className={styles.sectionDescription}>
          Clinical diagnosis, differential diagnosis, and assessment
        </span>
      </label>
      <div style={{ position: 'relative', paddingTop: '2rem' }}>
        <textarea
          id="diagnosis"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter clinical diagnosis, differential diagnosis, and assessment..."
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
