/**
 * Nursing Notes Section Component
 * 
 * Allows Nurse to create and view nursing notes.
 * Visit-scoped and permission-aware.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { fetchNursingNotes, createNursingNote, updateNursingNote } from '../../api/nursing';
import { NursingNote, NursingNoteCreate } from '../../types/nursing';
import SpeechToTextButton from '../common/SpeechToTextButton';
import styles from '../../styles/NurseVisit.module.css';

interface NursingNotesSectionProps {
  visitId: string;
  canCreate: boolean;
}

export default function NursingNotesSection({ visitId, canCreate }: NursingNotesSectionProps) {
  const { showSuccess, showError } = useToast();
  const [notes, setNotes] = useState<NursingNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  
  const [editingNote, setEditingNote] = useState<NursingNote | null>(null);
  const [formData, setFormData] = useState<NursingNoteCreate>({
    note_type: 'GENERAL',
    note_content: '',
    patient_condition: '',
    care_provided: '',
    patient_response: '',
    merge_with_patient_record: false,
  });

  useEffect(() => {
    loadNotes();
  }, [visitId]);

  const loadNotes = async () => {
    try {
      setLoading(true);
      const data = await fetchNursingNotes(parseInt(visitId));
      setNotes(Array.isArray(data) ? data : []);
    } catch (error: any) {
      showError(error.message || 'Failed to load nursing notes');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (note: NursingNote) => {
    setEditingNote(note);
    setFormData({
      note_type: note.note_type,
      note_content: note.note_content,
      patient_condition: note.patient_condition || '',
      care_provided: note.care_provided || '',
      patient_response: note.patient_response || '',
      merge_with_patient_record: false,
    });
    setShowForm(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingNote(null);
    setFormData({
      note_type: 'GENERAL',
      note_content: '',
      patient_condition: '',
      care_provided: '',
      patient_response: '',
      merge_with_patient_record: false,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!canCreate) {
      showError('Cannot create or update nursing note. Visit must be OPEN and payment cleared.');
      return;
    }
    
    if (!formData.note_content.trim()) {
      showError('Note content is required');
      return;
    }
    
    try {
      setSaving(true);
      if (editingNote) {
        // Update existing note
        await updateNursingNote(parseInt(visitId), editingNote.id, formData);
        showSuccess('Nursing note updated successfully');
      } else {
        // Create new note
        await createNursingNote(parseInt(visitId), formData);
        showSuccess('Nursing note created successfully');
      }
      handleCancel();
      loadNotes();
    } catch (error: any) {
      showError(error.message || `Failed to ${editingNote ? 'update' : 'create'} nursing note`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.section}>
      <div className={styles.sectionHeader}>
        <h3>📝 Nursing Notes</h3>
        {canCreate && (
          <button
            type="button"
            className={styles.addButton}
            onClick={() => {
              if (showForm) {
                handleCancel();
              } else {
                setShowForm(true);
              }
            }}
            disabled={saving}
          >
            {showForm ? 'Cancel' : editingNote ? 'Edit Note' : '+ Add Nursing Note'}
          </button>
        )}
      </div>

      {showForm && canCreate && (
        <form onSubmit={handleSubmit} className={styles.nursingNoteForm}>
          <div className={styles.formField}>
            <label>Note Type *</label>
            <select
              value={formData.note_type}
              onChange={(e) => setFormData({ ...formData, note_type: e.target.value as NursingNoteCreate['note_type'] })}
              required
            >
              <option value="GENERAL">General Nursing Note</option>
              <option value="ADMISSION">Admission Note</option>
              <option value="SHIFT_HANDOVER">Shift Handover Note</option>
              <option value="PROCEDURE">Procedure Note</option>
              <option value="WOUND_CARE">Wound Care Note</option>
              <option value="PATIENT_EDUCATION">Patient Education Note</option>
              <option value="ANTENATAL">Antenatal Monitoring Note</option>
              <option value="INPATIENT">Inpatient Monitoring Note</option>
              <option value="OTHER">Other</option>
            </select>
          </div>
          <div className={styles.formField}>
            <label>Note Content *</label>
            <div style={{ position: 'relative', paddingTop: '2rem' }}>
              <textarea
                value={formData.note_content}
                onChange={(e) => setFormData({ ...formData, note_content: e.target.value })}
                rows={6}
                required
                placeholder="Enter nursing note content..."
              />
              <SpeechToTextButton
                value={formData.note_content}
                onTranscribe={(text) => setFormData((prev) => ({ ...prev, note_content: text }))}
                appendMode={true}
                position="top-right"
                showPreview={true}
              />
            </div>
          </div>
          <div className={styles.formField}>
            <label>Patient Condition</label>
            <div style={{ position: 'relative', paddingTop: '2rem' }}>
              <textarea
                value={formData.patient_condition}
                onChange={(e) => setFormData({ ...formData, patient_condition: e.target.value })}
                rows={3}
                placeholder="Describe patient's condition..."
              />
              <SpeechToTextButton
                value={formData.patient_condition}
                onTranscribe={(text) => setFormData((prev) => ({ ...prev, patient_condition: text }))}
                appendMode={true}
                position="top-right"
                showPreview={true}
              />
            </div>
          </div>
          <div className={styles.formField}>
            <label>Care Provided</label>
            <div style={{ position: 'relative', paddingTop: '2rem' }}>
              <textarea
                value={formData.care_provided}
                onChange={(e) => setFormData({ ...formData, care_provided: e.target.value })}
                rows={3}
                placeholder="Describe care provided..."
              />
              <SpeechToTextButton
                value={formData.care_provided}
                onTranscribe={(text) => setFormData({ ...formData, care_provided: text })}
                appendMode={true}
                position="top-right"
                showPreview={true}
              />
            </div>
          </div>
          <div className={styles.formField}>
            <label>Patient Response</label>
            <div style={{ position: 'relative', paddingTop: '2rem' }}>
              <textarea
                value={formData.patient_response}
                onChange={(e) => setFormData({ ...formData, patient_response: e.target.value })}
                rows={3}
                placeholder="Describe patient's response..."
              />
              <SpeechToTextButton
                value={formData.patient_response}
                onTranscribe={(text) => setFormData((prev) => ({ ...prev, patient_response: text }))}
                appendMode={true}
                position="top-right"
                showPreview={true}
              />
            </div>
          </div>
          <div className={styles.formField}>
            <label>
              <input
                type="checkbox"
                checked={formData.merge_with_patient_record || false}
                onChange={(e) => setFormData({ ...formData, merge_with_patient_record: e.target.checked })}
              />
              Merge with patient's medical record
            </label>
            <p className={styles.helpText}>
              If checked, this nursing note will be added to the patient's cumulative medical history.
            </p>
          </div>
          <div className={styles.formActions}>
            <button type="submit" disabled={saving} className={styles.saveButton}>
              {saving ? 'Saving...' : editingNote ? 'Update Note' : 'Save Note'}
            </button>
            <button type="button" onClick={handleCancel} className={styles.cancelButton}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className={styles.loading}>Loading nursing notes...</div>
      ) : notes.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No nursing notes recorded yet.</p>
          {canCreate && <p>Click "Add Nursing Note" to create the first entry.</p>}
        </div>
      ) : (
        <div className={styles.notesList}>
          {notes.map((note) => (
            <div key={note.id} className={styles.noteCard}>
              <div className={styles.noteHeader}>
                <div>
                  <span className={styles.noteType}>
                    {note.note_type === 'GENERAL' ? 'General' :
                     note.note_type === 'ADMISSION' ? 'Admission' :
                     note.note_type === 'SHIFT_HANDOVER' ? 'Shift Handover' :
                     note.note_type === 'PROCEDURE' ? 'Procedure' :
                     note.note_type === 'WOUND_CARE' ? 'Wound Care' :
                     note.note_type === 'PATIENT_EDUCATION' ? 'Patient Education' :
                     note.note_type === 'ANTENATAL' ? 'Antenatal' :
                     note.note_type === 'INPATIENT' ? 'Inpatient' :
                     note.note_type === 'OTHER' ? 'Other' :
                     note.note_type}
                  </span>
                  <span className={styles.noteDate}>
                    {new Date(note.recorded_at).toLocaleString()} by {note.recorded_by_name || 'Nurse'}
                  </span>
                </div>
                {canCreate && (
                  <button
                    type="button"
                    className={styles.editButton}
                    onClick={() => handleEdit(note)}
                    title="Edit nursing note"
                  >
                    ✏️ Edit
                  </button>
                )}
              </div>
              <div className={styles.noteContent}>
                <p>{note.note_content}</p>
              </div>
              {(note.patient_condition || note.care_provided || note.patient_response) && (
                <div className={styles.noteDetails}>
                  {note.patient_condition && (
                    <div className={styles.noteDetailItem}>
                      <strong>Patient Condition:</strong>
                      <p>{note.patient_condition}</p>
                    </div>
                  )}
                  {note.care_provided && (
                    <div className={styles.noteDetailItem}>
                      <strong>Care Provided:</strong>
                      <p>{note.care_provided}</p>
                    </div>
                  )}
                  {note.patient_response && (
                    <div className={styles.noteDetailItem}>
                      <strong>Patient Response:</strong>
                      <p>{note.patient_response}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
