/**
 * Operation Notes Component
 * 
 * Manages surgical operation notes and procedures.
 * Per EMR Rules: Doctor-only creation, visit-scoped, consultation-dependent
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import {
  getOperationNotes,
  createOperationNote,
  updateOperationNote,
  deleteOperationNote,
} from '../../api/operation';
import {
  OperationNote,
  OperationNoteCreateData,
  OperationNoteUpdateData,
  OPERATION_TYPE_OPTIONS,
  ANESTHESIA_TYPE_OPTIONS,
} from '../../types/operation';
import { fetchConsultation } from '../../api/consultation';
import { Consultation } from '../../types/consultation';
import LoadingSpinner from '../common/LoadingSpinner';
import SpeechToTextButton from '../common/SpeechToTextButton';
import styles from '../../styles/OperationNotes.module.css';

interface OperationNotesProps {
  visitId: number;
  visitStatus: string;
  consultationId?: number;
  /** When false, consultation API is not called (avoids 403 when registration not paid). */
  registrationPaid?: boolean;
}

export default function OperationNotes({
  visitId,
  visitStatus,
  consultationId,
  registrationPaid = true,
}: OperationNotesProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [operationNotes, setOperationNotes] = useState<OperationNote[]>([]);
  const [consultations, setConsultations] = useState<Consultation[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingNote, setEditingNote] = useState<OperationNote | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [formData, setFormData] = useState<Partial<OperationNoteCreateData>>({
    consultation: consultationId || 0,
    operation_type: 'OTHER',
    operation_name: '',
    preoperative_diagnosis: '',
    postoperative_diagnosis: '',
    indication: '',
    anesthesia_type: 'GENERAL',
    anesthesia_notes: '',
    procedure_description: '',
    findings: '',
    technique: '',
    complications: '',
    estimated_blood_loss: '',
    specimens_sent: '',
    postoperative_plan: '',
    postoperative_instructions: '',
    operation_date: new Date().toISOString().slice(0, 16),
    operation_duration_minutes: null,
  });

  useEffect(() => {
    loadData();
  }, [visitId, registrationPaid]);

  const loadData = async () => {
    try {
      setLoading(true);
      const notes = await getOperationNotes(visitId);
      setOperationNotes(notes);
      
      // Only call consultation API when registration is paid (avoids 403)
      if (registrationPaid) {
        try {
          const consult = await fetchConsultation(visitId.toString());
          setConsultations([consult]);
        } catch (error: any) {
          const isExpectedError =
            error?.status === 404 ||
            error?.message === '404' ||
            (error?.status === 403 && error?.message?.includes('Payment'));
          if (!isExpectedError) {
            console.warn('Failed to load consultation for operation notes:', error);
          }
          setConsultations([]);
        }
      } else {
        setConsultations([]);
      }
    } catch (error: any) {
      showError(error?.message || 'Failed to load operation notes');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!formData.consultation || !formData.operation_name || !formData.preoperative_diagnosis || !formData.indication || !formData.procedure_description || !formData.operation_date) {
      showError('Please fill in all required fields');
      return;
    }

    try {
      setSubmitting(true);
      const data: OperationNoteCreateData = {
        consultation: formData.consultation,
        assistant_surgeon: formData.assistant_surgeon || null,
        anesthetist: formData.anesthetist || null,
        operation_type: formData.operation_type || 'OTHER',
        operation_name: formData.operation_name,
        preoperative_diagnosis: formData.preoperative_diagnosis,
        postoperative_diagnosis: formData.postoperative_diagnosis || undefined,
        indication: formData.indication,
        anesthesia_type: formData.anesthesia_type || 'GENERAL',
        anesthesia_notes: formData.anesthesia_notes || undefined,
        procedure_description: formData.procedure_description,
        findings: formData.findings || undefined,
        technique: formData.technique || undefined,
        complications: formData.complications || undefined,
        estimated_blood_loss: formData.estimated_blood_loss || undefined,
        specimens_sent: formData.specimens_sent || undefined,
        postoperative_plan: formData.postoperative_plan || undefined,
        postoperative_instructions: formData.postoperative_instructions || undefined,
        operation_date: formData.operation_date,
        operation_duration_minutes: formData.operation_duration_minutes || null,
      };

      await createOperationNote(visitId, data);
      showSuccess('Operation note created successfully');
      setShowCreateForm(false);
      resetForm();
      await loadData();
    } catch (error: any) {
      showError(error?.responseData?.detail || error?.message || 'Failed to create operation note');
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async () => {
    if (!editingNote) return;

    if (!formData.operation_name || !formData.preoperative_diagnosis || !formData.indication || !formData.procedure_description || !formData.operation_date) {
      showError('Please fill in all required fields');
      return;
    }

    try {
      setSubmitting(true);
      const data: OperationNoteUpdateData = {
        consultation: formData.consultation || editingNote.consultation,
        assistant_surgeon: formData.assistant_surgeon || null,
        anesthetist: formData.anesthetist || null,
        operation_type: formData.operation_type || editingNote.operation_type,
        operation_name: formData.operation_name,
        preoperative_diagnosis: formData.preoperative_diagnosis,
        postoperative_diagnosis: formData.postoperative_diagnosis || undefined,
        indication: formData.indication,
        anesthesia_type: formData.anesthesia_type || editingNote.anesthesia_type,
        anesthesia_notes: formData.anesthesia_notes || undefined,
        procedure_description: formData.procedure_description,
        findings: formData.findings || undefined,
        technique: formData.technique || undefined,
        complications: formData.complications || undefined,
        estimated_blood_loss: formData.estimated_blood_loss || undefined,
        specimens_sent: formData.specimens_sent || undefined,
        postoperative_plan: formData.postoperative_plan || undefined,
        postoperative_instructions: formData.postoperative_instructions || undefined,
        operation_date: formData.operation_date,
        operation_duration_minutes: formData.operation_duration_minutes || null,
      };

      await updateOperationNote(visitId, editingNote.id, data);
      showSuccess('Operation note updated successfully');
      setEditingNote(null);
      resetForm();
      await loadData();
    } catch (error: any) {
      showError(error?.responseData?.detail || error?.message || 'Failed to update operation note');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (noteId: number) => {
    if (!window.confirm('Are you sure you want to delete this operation note?')) {
      return;
    }

    try {
      await deleteOperationNote(visitId, noteId);
      showSuccess('Operation note deleted successfully');
      await loadData();
    } catch (error: any) {
      showError(error?.responseData?.detail || error?.message || 'Failed to delete operation note');
    }
  };

  const resetForm = () => {
    setFormData({
      consultation: consultationId || 0,
      operation_type: 'OTHER',
      operation_name: '',
      preoperative_diagnosis: '',
      postoperative_diagnosis: '',
      indication: '',
      anesthesia_type: 'GENERAL',
      anesthesia_notes: '',
      procedure_description: '',
      findings: '',
      technique: '',
      complications: '',
      estimated_blood_loss: '',
      specimens_sent: '',
      postoperative_plan: '',
      postoperative_instructions: '',
      operation_date: new Date().toISOString().slice(0, 16),
      operation_duration_minutes: null,
    });
  };

  const startEdit = (note: OperationNote) => {
    setEditingNote(note);
    setFormData({
      consultation: note.consultation,
      assistant_surgeon: note.assistant_surgeon || null,
      anesthetist: note.anesthetist || null,
      operation_type: note.operation_type,
      operation_name: note.operation_name,
      preoperative_diagnosis: note.preoperative_diagnosis,
      postoperative_diagnosis: note.postoperative_diagnosis || '',
      indication: note.indication,
      anesthesia_type: note.anesthesia_type,
      anesthesia_notes: note.anesthesia_notes || '',
      procedure_description: note.procedure_description,
      findings: note.findings || '',
      technique: note.technique || '',
      complications: note.complications || '',
      estimated_blood_loss: note.estimated_blood_loss || '',
      specimens_sent: note.specimens_sent || '',
      postoperative_plan: note.postoperative_plan || '',
      postoperative_instructions: note.postoperative_instructions || '',
      operation_date: new Date(note.operation_date).toISOString().slice(0, 16),
      operation_duration_minutes: note.operation_duration_minutes || null,
    });
  };

  const cancelEdit = () => {
    setEditingNote(null);
    resetForm();
  };

  const canEdit = user?.role === 'DOCTOR' && visitStatus === 'OPEN';

  if (loading) {
    return (
      <section className={styles.section}>
        <h2>Operation Notes</h2>
        <LoadingSpinner message="Loading operation notes..." />
      </section>
    );
  }

  return (
    <section className={styles.section}>
      <div className={styles.header}>
        <h2>Operation Notes ({operationNotes.length})</h2>
        {canEdit && !showCreateForm && !editingNote && (
          <button
            onClick={() => setShowCreateForm(true)}
            className={styles.createButton}
          >
            + Add Operation Note
          </button>
        )}
      </div>

      {/* Create Form */}
      {showCreateForm && canEdit && (
        <div className={styles.formCard}>
          <h3>Create Operation Note</h3>
          <OperationNoteForm
            formData={formData}
            setFormData={setFormData}
            consultations={consultations}
            onSubmit={handleCreate}
            onCancel={() => {
              setShowCreateForm(false);
              resetForm();
            }}
            submitting={submitting}
            isEdit={false}
          />
        </div>
      )}

      {/* Edit Form */}
      {editingNote && canEdit && (
        <div className={styles.formCard}>
          <h3>Edit Operation Note</h3>
          <OperationNoteForm
            formData={formData}
            setFormData={setFormData}
            consultations={consultations}
            onSubmit={handleUpdate}
            onCancel={cancelEdit}
            submitting={submitting}
            isEdit={true}
          />
        </div>
      )}

      {/* Operation Notes List */}
      {operationNotes.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No operation notes recorded for this visit</p>
        </div>
      ) : (
        <div className={styles.notesList}>
          {operationNotes.map((note) => (
            <div key={note.id} className={styles.noteCard}>
              <div className={styles.noteHeader}>
                <div>
                  <h3>{note.operation_name}</h3>
                  <p className={styles.noteMeta}>
                    {OPERATION_TYPE_OPTIONS.find((o: { value: string; label: string }) => o.value === note.operation_type)?.label || note.operation_type}
                    {' • '}
                    {new Date(note.operation_date).toLocaleString()}
                    {note.operation_duration_minutes && ` • Duration: ${note.operation_duration_minutes} minutes`}
                  </p>
                </div>
                {canEdit && (
                  <div className={styles.noteActions}>
                    <button
                      onClick={() => startEdit(note)}
                      className={styles.editButton}
                    >
                      Edit
                    </button>
                    <button
                      onClick={() => handleDelete(note.id)}
                      className={styles.deleteButton}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>

              <div className={styles.noteContent}>
                <div className={styles.noteSection}>
                  <h4>Surgeons & Anesthesia</h4>
                  <p><strong>Surgeon:</strong> {note.surgeon_name || 'Unknown'}</p>
                  {note.assistant_surgeon_name && (
                    <p><strong>Assistant Surgeon:</strong> {note.assistant_surgeon_name}</p>
                  )}
                  {note.anesthetist_name && (
                    <p><strong>Anesthetist:</strong> {note.anesthetist_name}</p>
                  )}
                  <p><strong>Anesthesia Type:</strong> {ANESTHESIA_TYPE_OPTIONS.find((a: { value: string; label: string }) => a.value === note.anesthesia_type)?.label || note.anesthesia_type}</p>
                  {note.anesthesia_notes && (
                    <p><strong>Anesthesia Notes:</strong> {note.anesthesia_notes}</p>
                  )}
                </div>

                <div className={styles.noteSection}>
                  <h4>Diagnosis</h4>
                  <p><strong>Preoperative:</strong> {note.preoperative_diagnosis}</p>
                  {note.postoperative_diagnosis && (
                    <p><strong>Postoperative:</strong> {note.postoperative_diagnosis}</p>
                  )}
                  <p><strong>Indication:</strong> {note.indication}</p>
                </div>

                <div className={styles.noteSection}>
                  <h4>Procedure</h4>
                  <p>{note.procedure_description}</p>
                  {note.findings && (
                    <div>
                      <strong>Findings:</strong>
                      <p>{note.findings}</p>
                    </div>
                  )}
                  {note.technique && (
                    <div>
                      <strong>Technique:</strong>
                      <p>{note.technique}</p>
                    </div>
                  )}
                  {note.complications && (
                    <div>
                      <strong>Complications:</strong>
                      <p>{note.complications}</p>
                    </div>
                  )}
                  {note.estimated_blood_loss && (
                    <p><strong>Estimated Blood Loss:</strong> {note.estimated_blood_loss}</p>
                  )}
                  {note.specimens_sent && (
                    <p><strong>Specimens Sent:</strong> {note.specimens_sent}</p>
                  )}
                </div>

                {(note.postoperative_plan || note.postoperative_instructions) && (
                  <div className={styles.noteSection}>
                    <h4>Postoperative</h4>
                    {note.postoperative_plan && (
                      <div>
                        <strong>Plan:</strong>
                        <p>{note.postoperative_plan}</p>
                      </div>
                    )}
                    {note.postoperative_instructions && (
                      <div>
                        <strong>Instructions:</strong>
                        <p>{note.postoperative_instructions}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

interface OperationNoteFormProps {
  formData: Partial<OperationNoteCreateData>;
  setFormData: React.Dispatch<React.SetStateAction<Partial<OperationNoteCreateData>>>;
  consultations: Consultation[];
  onSubmit: () => void;
  onCancel: () => void;
  submitting: boolean;
  isEdit?: boolean;
}

function OperationNoteForm({
  formData,
  setFormData,
  consultations,
  onSubmit,
  onCancel,
  submitting,
  isEdit = false,
}: OperationNoteFormProps) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className={styles.form}
    >
      <div className={styles.formGrid}>
        <div className={styles.formGroup}>
          <label>Consultation *</label>
          <select
            value={formData.consultation || 0}
            onChange={(e) => setFormData({ ...formData, consultation: parseInt(e.target.value) })}
            required
            disabled={submitting}
          >
            <option value={0}>Select Consultation</option>
            {consultations.map((consult) => (
              <option key={consult.id} value={consult.id}>
                Consultation #{consult.id} - {new Date(consult.created_at).toLocaleDateString()}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.formGroup}>
          <label>Operation Type *</label>
          <select
            value={formData.operation_type || 'OTHER'}
            onChange={(e) => setFormData({ ...formData, operation_type: e.target.value as any })}
            required
            disabled={submitting}
          >
            {OPERATION_TYPE_OPTIONS.map((option: { value: string; label: string }) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className={styles.formGroup}>
          <label>Operation Name *</label>
          <input
            type="text"
            value={formData.operation_name || ''}
            onChange={(e) => setFormData({ ...formData, operation_name: e.target.value })}
            required
            disabled={submitting}
            placeholder="e.g., Appendectomy, Cholecystectomy"
          />
        </div>

        <div className={styles.formGroup}>
          <label>Operation Date & Time *</label>
          <input
            type="datetime-local"
            value={formData.operation_date || ''}
            onChange={(e) => setFormData({ ...formData, operation_date: e.target.value })}
            required
            disabled={submitting}
          />
        </div>

        <div className={styles.formGroup}>
          <label>Duration (minutes)</label>
          <input
            type="number"
            min="0"
            value={formData.operation_duration_minutes || ''}
            onChange={(e) => setFormData({ ...formData, operation_duration_minutes: parseInt(e.target.value) || null })}
            disabled={submitting}
            placeholder="e.g., 120"
          />
        </div>

        <div className={styles.formGroup}>
          <label>Anesthesia Type *</label>
          <select
            value={formData.anesthesia_type || 'GENERAL'}
            onChange={(e) => setFormData({ ...formData, anesthesia_type: e.target.value as any })}
            required
            disabled={submitting}
          >
            {ANESTHESIA_TYPE_OPTIONS.map((option: { value: string; label: string }) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Preoperative Diagnosis *</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.preoperative_diagnosis || ''}
            onChange={(e) => setFormData({ ...formData, preoperative_diagnosis: e.target.value })}
            required
            disabled={submitting}
            rows={3}
            placeholder="Preoperative diagnosis"
          />
          <SpeechToTextButton
            value={formData.preoperative_diagnosis || ''}
            onTranscribe={(text) => setFormData((prev) => ({ ...prev, preoperative_diagnosis: text }))}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Postoperative Diagnosis</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.postoperative_diagnosis || ''}
            onChange={(e) => setFormData({ ...formData, postoperative_diagnosis: e.target.value })}
            disabled={submitting}
            rows={3}
            placeholder="Postoperative diagnosis (if different)"
          />
          <SpeechToTextButton
            value={formData.postoperative_diagnosis || ''}
            onTranscribe={(text) => setFormData((prev) => ({ ...prev, postoperative_diagnosis: text }))}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Indication *</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.indication || ''}
            onChange={(e) => setFormData({ ...formData, indication: e.target.value })}
            required
            disabled={submitting}
            rows={3}
            placeholder="Clinical indication for the operation"
          />
          <SpeechToTextButton
            value={formData.indication || ''}
            onTranscribe={(text) => setFormData({ ...formData, indication: text })}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Anesthesia Notes</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.anesthesia_notes || ''}
            onChange={(e) => setFormData({ ...formData, anesthesia_notes: e.target.value })}
            disabled={submitting}
            rows={2}
            placeholder="Additional anesthesia notes"
          />
          <SpeechToTextButton
            value={formData.anesthesia_notes || ''}
            onTranscribe={(text) => setFormData((prev) => ({ ...prev, anesthesia_notes: text }))}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Procedure Description *</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.procedure_description || ''}
            onChange={(e) => setFormData({ ...formData, procedure_description: e.target.value })}
            required
            disabled={submitting}
            rows={5}
            placeholder="Detailed description of the procedure performed"
          />
          <SpeechToTextButton
            value={formData.procedure_description || ''}
            onTranscribe={(text) => setFormData({ ...formData, procedure_description: text })}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Intraoperative Findings</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.findings || ''}
            onChange={(e) => setFormData({ ...formData, findings: e.target.value })}
            disabled={submitting}
            rows={3}
            placeholder="Intraoperative findings"
          />
          <SpeechToTextButton
            value={formData.findings || ''}
            onTranscribe={(text) => setFormData((prev) => ({ ...prev, findings: text }))}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Surgical Technique</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.technique || ''}
            onChange={(e) => setFormData({ ...formData, technique: e.target.value })}
            disabled={submitting}
            rows={3}
            placeholder="Surgical technique used"
          />
          <SpeechToTextButton
            value={formData.technique || ''}
            onTranscribe={(text) => setFormData({ ...formData, technique: text })}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Complications</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.complications || ''}
            onChange={(e) => setFormData({ ...formData, complications: e.target.value })}
            disabled={submitting}
            rows={3}
            placeholder="Any complications encountered"
          />
          <SpeechToTextButton
            value={formData.complications || ''}
            onTranscribe={(text) => setFormData((prev) => ({ ...prev, complications: text }))}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formGrid}>
        <div className={styles.formGroup}>
          <label>Estimated Blood Loss</label>
          <input
            type="text"
            value={formData.estimated_blood_loss || ''}
            onChange={(e) => setFormData({ ...formData, estimated_blood_loss: e.target.value })}
            disabled={submitting}
            placeholder="e.g., 200ml, Minimal"
          />
        </div>

        <div className={styles.formGroup}>
          <label>Specimens Sent</label>
          <input
            type="text"
            value={formData.specimens_sent || ''}
            onChange={(e) => setFormData({ ...formData, specimens_sent: e.target.value })}
            disabled={submitting}
            placeholder="Specimens sent for pathology"
          />
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Postoperative Plan</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.postoperative_plan || ''}
            onChange={(e) => setFormData({ ...formData, postoperative_plan: e.target.value })}
            disabled={submitting}
            rows={3}
            placeholder="Postoperative care plan"
          />
          <SpeechToTextButton
            value={formData.postoperative_plan || ''}
            onTranscribe={(text) => setFormData({ ...formData, postoperative_plan: text })}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formGroup}>
        <label>Postoperative Instructions</label>
        <div style={{ position: 'relative', paddingTop: '2rem' }}>
          <textarea
            value={formData.postoperative_instructions || ''}
            onChange={(e) => setFormData({ ...formData, postoperative_instructions: e.target.value })}
            disabled={submitting}
            rows={3}
            placeholder="Postoperative instructions for patient"
          />
          <SpeechToTextButton
            value={formData.postoperative_instructions || ''}
            onTranscribe={(text) => setFormData((prev) => ({ ...prev, postoperative_instructions: text }))}
            appendMode={true}
            position="top-right"
            showPreview={true}
          />
        </div>
      </div>

      <div className={styles.formActions}>
        <button
          type="button"
          onClick={onCancel}
          className={styles.cancelButton}
          disabled={submitting}
        >
          Cancel
        </button>
        <button
          type="submit"
          className={styles.submitButton}
          disabled={submitting}
        >
          {submitting ? 'Saving...' : (isEdit ? 'Update' : 'Create')} Operation Note
        </button>
      </div>
    </form>
  );
}
