/**
 * Patient Education Section Component
 * 
 * Allows Nurse to record patient education provided.
 * Visit-scoped and permission-aware.
 * 
 * Note: This is a simplified implementation. In a full system, this might
 * be a separate model or integrated into nursing notes.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import SpeechToTextButton from '../common/SpeechToTextButton';
import styles from '../../styles/NurseVisit.module.css';

interface PatientEducationSectionProps {
  visitId: string;
  canCreate: boolean;
}

interface PatientEducationRecord {
  id: number;
  topic: string;
  content: string;
  provided_by: string;
  provided_at: string;
  patient_understood?: boolean;
  notes?: string;
}

export default function PatientEducationSection({ visitId, canCreate }: PatientEducationSectionProps) {
  const { showSuccess, showError } = useToast();
  const [educationRecords, setEducationRecords] = useState<PatientEducationRecord[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [formData, setFormData] = useState({
    topic: '',
    content: '',
    patient_understood: false,
    notes: '',
  });

  // For now, we'll use nursing notes with type "Patient Education"
  // In a full implementation, this would be a separate API endpoint
  useEffect(() => {
    // This would load patient education records
    // For now, it's a placeholder
  }, [visitId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!canCreate) {
      showError('Cannot record patient education. Visit must be OPEN and payment cleared.');
      return;
    }
    
    if (!formData.topic.trim() || !formData.content.trim()) {
      showError('Topic and content are required');
      return;
    }
    
    try {
      setSaving(true);
      // For now, create a nursing note with type "Patient Education"
      // In a full implementation, this would call a dedicated patient education API
      const { createNursingNote } = await import('../../api/nursing');
      await createNursingNote(parseInt(visitId), {
        note_type: 'PATIENT_EDUCATION',
        note_content: `Topic: ${formData.topic}\n\nContent: ${formData.content}${formData.patient_understood ? '\n\nPatient understood: Yes' : ''}${formData.notes ? `\n\nNotes: ${formData.notes}` : ''}`,
        patient_condition: '',
        care_provided: '',
        patient_response: formData.patient_understood ? 'Patient understood the education provided' : '',
      });
      showSuccess('Patient education recorded successfully');
      setShowForm(false);
      setFormData({
        topic: '',
        content: '',
        patient_understood: false,
        notes: '',
      });
      // Reload would happen via parent component
    } catch (error: any) {
      showError(error.message || 'Failed to record patient education');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <h3>📚 Patient Education</h3>
        {canCreate && (
          <button
            type="button"
            className={styles.addButton}
            onClick={() => setShowForm(!showForm)}
            disabled={saving}
          >
            {showForm ? 'Cancel' : '+ Record Patient Education'}
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <form onSubmit={handleSubmit} className={styles.patientEducationForm}>
          <div className={styles.formField}>
            <label>Topic *</label>
            <input
              type="text"
              value={formData.topic}
              onChange={(e) => setFormData({ ...formData, topic: e.target.value })}
              required
              placeholder="e.g., Medication administration, Wound care, Diet instructions"
            />
          </div>
          <div className={styles.formField}>
            <label>Content *</label>
            <textarea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              rows={6}
              required
              placeholder="Describe the education provided to the patient..."
            />
          </div>
          <div className={styles.formField}>
            <label>
              <input
                type="checkbox"
                checked={formData.patient_understood}
                onChange={(e) => setFormData({ ...formData, patient_understood: e.target.checked })}
              />
              Patient understood the education
            </label>
          </div>
          <div className={styles.formField}>
            <label>Additional Notes</label>
            <div style={{ position: 'relative', paddingTop: '2rem' }}>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                rows={3}
                placeholder="Any additional notes about the education session..."
              />
              <SpeechToTextButton
                value={formData.notes}
                onTranscribe={(text) => setFormData((prev) => ({ ...prev, notes: text }))}
                appendMode={true}
                position="top-right"
                showPreview={true}
              />
            </div>
          </div>
          <div className={styles.formActions}>
            <button type="submit" disabled={saving} className={styles.saveButton}>
              {saving ? 'Saving...' : 'Record Education'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className={styles.cancelButton}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {educationRecords.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No patient education records yet.</p>
          {canCreate && <p>Click "Record Patient Education" to add the first entry.</p>}
          <p className={styles.infoNote}>
            Note: Patient education records are stored as nursing notes with type "Patient Education".
            Check the Nursing Notes section to view all education records.
          </p>
        </div>
      ) : (
        <div className={styles.educationList}>
          {educationRecords.map((record) => (
            <div key={record.id} className={styles.educationCard}>
              <div className={styles.educationHeader}>
                <strong>{record.topic}</strong>
                <span className={styles.educationDate}>
                  {new Date(record.provided_at).toLocaleString()} by {record.provided_by}
                </span>
              </div>
              <div className={styles.educationContent}>
                <p>{record.content}</p>
              </div>
              {record.patient_understood !== undefined && (
                <div className={styles.educationDetail}>
                  <label>Patient Understood:</label>
                  <span>{record.patient_understood ? 'Yes' : 'No'}</span>
                </div>
              )}
              {record.notes && (
                <div className={styles.educationNotes}>
                  <label>Notes:</label>
                  <p>{record.notes}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
