/**
 * AI Clinical Scribe — Nigerian EMR documentation from transcripts.
 * SOAP / Antenatal auto-detection, NHIA + ICD-11 coding, doctor approval before save.
 */
import React, { useState } from 'react';
import { apiRequest } from '../../utils/apiClient';
import { useToast } from '../../hooks/useToast';
import SpeechToTextButton from '../common/SpeechToTextButton';
import styles from '../../styles/AIComponents.module.css';

export type ClinicalNoteType = 'auto' | 'SOAP' | 'antenatal' | 'summary' | 'discharge';

interface GenerateNoteResponse {
  structured_note: string;
  note_type: string;
  template_used?: string;
}

interface AINotesPanelProps {
  patientId: number;
  appointmentId?: number | null;
  onSaved?: () => void;
}

export default function AINotesPanel(props: AINotesPanelProps) {
  const { patientId, appointmentId, onSaved } = props;
  const { showSuccess, showError } = useToast();
  const [transcript, setTranscript] = useState('');
  const [noteType, setNoteType] = useState<ClinicalNoteType>('auto');
  const [resolvedType, setResolvedType] = useState<string | null>(null);
  const [structuredNote, setStructuredNote] = useState('');
  const [editedNote, setEditedNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleGenerate = async () => {
    if (!transcript.trim()) {
      showError('Enter transcript, dialogue, or shorthand dictate');
      return;
    }
    setLoading(true);
    setStructuredNote('');
    setEditedNote('');
    setResolvedType(null);
    try {
      const body: Record<string, unknown> = {
        transcript: transcript.trim(),
        note_type: noteType,
      };
      if (appointmentId) body.appointment_id = appointmentId;
      const data = await apiRequest<GenerateNoteResponse>('/ai/generate-note/', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      setStructuredNote(data.structured_note);
      setEditedNote(data.structured_note);
      setResolvedType(data.template_used || data.note_type);
      showSuccess(
        `Note generated (${data.note_type}). Review, edit, and save to the record.`
      );
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to generate note');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    const final = (editedNote || structuredNote).trim();
    if (!final) {
      showError('Nothing to save');
      return;
    }
    setSaving(true);
    try {
      const saveNoteType =
        resolvedType === 'antenatal'
          ? 'Antenatal'
          : noteType === 'auto'
            ? 'SOAP'
            : noteType === 'antenatal'
              ? 'Antenatal'
              : noteType;
      await apiRequest('/ai/notes/', {
        method: 'POST',
        body: JSON.stringify({
          patient_id: patientId,
          appointment_id: appointmentId || null,
          note_type: saveNoteType,
          raw_transcript: transcript,
          ai_generated_note: structuredNote,
          doctor_edited_note: final,
        }),
      });
      showSuccess('Clinical note saved.');
      setTranscript('');
      setStructuredNote('');
      setEditedNote('');
      setResolvedType(null);
      onSaved?.();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to save note');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.panel}>
      <h3 className={styles.panelTitle}>Clinical AI Scribe</h3>
      <p className={styles.panelHint}>
        Paste audio transcript, doctor–patient dialogue, or shorthand. Supports Nigerian
        English/Pidgin, auto SOAP vs antenatal templates, and NHIA/ICD-11 coding.
      </p>
      <div className={styles.panelBody}>
        <div className={styles.field}>
          <label htmlFor="scribe-note-type">Documentation template</label>
          <select
            id="scribe-note-type"
            value={noteType}
            onChange={(e) => setNoteType(e.target.value as ClinicalNoteType)}
            className={styles.select}
          >
            <option value="auto">Auto (SOAP or Antenatal)</option>
            <option value="SOAP">General consultation (SOAP)</option>
            <option value="antenatal">Antenatal / maternity card</option>
            <option value="summary">Brief summary</option>
            <option value="discharge">Discharge summary</option>
          </select>
        </div>
        <div className={styles.field} style={{ position: 'relative' }}>
          <label htmlFor="scribe-transcript">Transcript or dictate</label>
          <SpeechToTextButton
            value={transcript}
            onTranscribe={setTranscript}
            appendMode
            position="top-right"
          />
          <textarea
            id="scribe-transcript"
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="e.g. Patient say body dey hot since 3 days, purging small small. LMP 01/10/2025. G2P1..."
            rows={5}
            className={styles.textarea}
          />
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={loading || !transcript.trim()}
          className={styles.primaryButton}
        >
          {loading ? 'Generating…' : 'Generate clinical note'}
        </button>
        {resolvedType ? (
          <p className={styles.resolvedBadge}>Template applied: {resolvedType}</p>
        ) : null}
        {structuredNote ? (
          <>
            <div className={styles.field}>
              <label htmlFor="scribe-output">Structured note (editable)</label>
              <textarea
                id="scribe-output"
                value={editedNote}
                onChange={(e) => setEditedNote(e.target.value)}
                rows={14}
                className={styles.textarea}
              />
            </div>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className={styles.successButton}
            >
              {saving ? 'Saving…' : 'Save approved note'}
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
}
