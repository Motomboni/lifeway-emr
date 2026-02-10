/**
 * ClinicalNotesSection Component
 * 
 * Additional clinical notes, treatment plan, and follow-up instructions.
 */
import React from 'react';
import SpeechToTextButton from '../../common/SpeechToTextButton';
import styles from '../../../styles/ConsultationWorkspace.module.css';

interface ClinicalNotesSectionProps {
  value: string;
  onChange: (value: string) => void;
}

export default function ClinicalNotesSection({ value, onChange }: ClinicalNotesSectionProps) {
  return (
    <div className={styles.consultationSection}>
      <label htmlFor="clinical_notes">
        <h3>Clinical Notes</h3>
        <span className={styles.sectionDescription}>
          Additional clinical notes, treatment plan, and follow-up instructions
        </span>
      </label>
      <div style={{ position: 'relative', paddingTop: '2rem' }}>
        <textarea
          id="clinical_notes"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter additional clinical notes, treatment plan, and follow-up instructions..."
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
