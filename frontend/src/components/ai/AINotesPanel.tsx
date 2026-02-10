/**
 * AI Clinical Notes Panel - generate SOAP/summary/discharge; doctor approves before save.
 */
import React, { useState } from 'react';
import { apiRequest } from '../../utils/apiClient';
import { useToast } from '../../hooks/useToast';

interface AINotesPanelProps {
  patientId: number;
  appointmentId?: number | null;
  onSaved?: () => void;
}

export default function AINotesPanel(props: AINotesPanelProps) {
  const { patientId, appointmentId, onSaved } = props;
  const { showSuccess, showError } = useToast();
  const [transcript, setTranscript] = useState('');
  const [noteType, setNoteType] = useState<'SOAP' | 'summary' | 'discharge'>('summary');
  const [structuredNote, setStructuredNote] = useState('');
  const [editedNote, setEditedNote] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleGenerate = async () => {
    if (!transcript.trim()) {
      showError('Enter transcript or bullet notes');
      return;
    }
    setLoading(true);
    setStructuredNote('');
    setEditedNote('');
    try {
      const body: Record<string, unknown> = { transcript: transcript.trim(), note_type: noteType };
      if (appointmentId) body.appointment_id = appointmentId;
      const data = await apiRequest<{ structured_note: string }>('/ai/generate-note/', {
        method: 'POST',
        body: JSON.stringify(body),
      });
      setStructuredNote(data.structured_note);
      setEditedNote(data.structured_note);
      showSuccess('Note generated. Edit if needed, then save.');
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
      await apiRequest('/ai/notes/', {
        method: 'POST',
        body: JSON.stringify({
          patient_id: patientId,
          appointment_id: appointmentId || null,
          note_type: noteType,
          raw_transcript: transcript,
          ai_generated_note: structuredNote,
          doctor_edited_note: final,
        }),
      });
      showSuccess('Clinical note saved.');
      setTranscript('');
      setStructuredNote('');
      setEditedNote('');
      onSaved?.();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to save note');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">AI Clinical Notes</h3>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Note type</label>
          <select
            value={noteType}
            onChange={(e) => setNoteType(e.target.value as 'SOAP' | 'summary' | 'discharge')}
            className="w-full max-w-xs rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="SOAP">SOAP</option>
            <option value="summary">Summary</option>
            <option value="discharge">Discharge</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Transcript</label>
          <textarea
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Paste transcript or bullet points..."
            rows={4}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <button
          type="button"
          onClick={handleGenerate}
          disabled={loading || !transcript.trim()}
          className="min-h-[44px] px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? 'Generating...' : 'Generate note'}
        </button>
        {structuredNote ? (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Structured note (editable)</label>
              <textarea
                value={editedNote}
                onChange={(e) => setEditedNote(e.target.value)}
                rows={10}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="min-h-[44px] px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save approved note'}
            </button>
          </>
        ) : null}
      </div>
    </div>
  );
}
