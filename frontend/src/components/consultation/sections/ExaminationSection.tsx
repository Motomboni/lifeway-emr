/**
 * ExaminationSection Component
 * 
 * Physical examination findings and clinical observations.
 */
import React from 'react';
import SpeechToTextButton from '../../common/SpeechToTextButton';
import styles from '../../../styles/ConsultationWorkspace.module.css';

interface ExaminationSectionProps {
  value: string;
  onChange: (value: string) => void;
}

export default function ExaminationSection({ value, onChange }: ExaminationSectionProps) {
  return (
    <div className={styles.consultationSection}>
      <label htmlFor="examination">
        <h3>Examination</h3>
        <span className={styles.sectionDescription}>
          Physical examination findings and clinical observations
        </span>
      </label>
      <div style={{ position: 'relative', paddingTop: '2rem' }}>
        <textarea
          id="examination"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter physical examination findings and clinical observations..."
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
