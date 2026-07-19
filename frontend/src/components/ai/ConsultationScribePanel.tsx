/**
 * Consultation workspace Clinical AI Scribe — ambient capture, generate,
 * validate NHIA/ICD-11, and one-click apply into consultation fields.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { addNhiaScribeCharges } from '../../api/billing';
import { generateScribeNote } from '../../api/scribe';
import { applyAIDiagnosisCodes } from '../../api/diagnosisCodes';
import { useToast } from '../../hooks/useToast';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import type { ConsultationData } from '../../types/consultation';
import {
  matchStatusLabel,
  parseScribeSections,
  type CodeValidation,
  type GenerateScribeNoteResponse,
} from '../../utils/scribeParser';
import { VOICE_SCRIBE_EVENTS, consumePendingScribeAction } from '../../utils/voiceIntents';
import type { ClinicalNoteType } from './AINotesPanel';
import styles from '../../styles/AIComponents.module.css';

interface ConsultationScribePanelProps {
  visitId: string;
  consultationId?: number;
  initialTranscript?: string;
  onApplySections: (sections: Partial<ConsultationData>) => void;
  onCodesApplied?: () => void;
  onNhiaBilled?: () => void;
}

export default function ConsultationScribePanel({
  visitId,
  consultationId,
  initialTranscript,
  onApplySections,
  onCodesApplied,
  onNhiaBilled,
}: ConsultationScribePanelProps) {
  const { showSuccess, showError } = useToast();
  const [transcript, setTranscript] = useState('');
  const [noteType, setNoteType] = useState<ClinicalNoteType>('auto');
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [billing, setBilling] = useState(false);
  const [result, setResult] = useState<GenerateScribeNoteResponse | null>(null);
  const [editedNote, setEditedNote] = useState('');
  const [ambientActive, setAmbientActive] = useState(false);
  const [ambientSeconds, setAmbientSeconds] = useState(0);
  const transcriptRef = useRef(transcript);
  transcriptRef.current = transcript;
  const ambientActiveRef = useRef(false);
  ambientActiveRef.current = ambientActive;

  useEffect(() => {
    if (initialTranscript?.trim()) {
      setTranscript(initialTranscript.trim());
    }
  }, [initialTranscript]);

  const appendFinalChunk = useCallback((chunk: string) => {
    const clean = chunk.trim();
    if (!clean) return;
    setTranscript((prev) => {
      const base = prev.trim();
      if (!base) return clean;
      const needsSpace = !/[\s\n]$/.test(base);
      return `${base}${needsSpace ? ' ' : ''}${clean}`;
    });
  }, []);

  const speech = useSpeechRecognition({
    continuous: true,
    interimResults: true,
    lang: 'en-NG',
    onResult: (text, isFinal) => {
      if (isFinal) appendFinalChunk(text);
    },
    onError: (err) => {
      if (ambientActiveRef.current) {
        showError(err);
        setAmbientActive(false);
      }
    },
  });

  const startAmbient = useCallback(() => {
    if (!speech.isSupported) {
      showError('Speech recognition is not supported in this browser. Use Chrome.');
      return;
    }
    setAmbientActive(true);
    setAmbientSeconds(0);
    speech.clearTranscript();
    speech.startListening();
    showSuccess('Ambient scribe listening — speak the encounter');
  }, [showError, showSuccess, speech]);

  const stopAmbient = useCallback(() => {
    setAmbientActive(false);
    speech.stopListening();
    showSuccess('Ambient capture stopped');
  }, [showSuccess, speech]);

  useEffect(() => {
    if (!ambientActive) return undefined;
    const timer = window.setInterval(() => {
      setAmbientSeconds((s) => s + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [ambientActive]);

  useEffect(() => {
    if (ambientActive && speech.isSupported && !speech.isListening) {
      // Web Speech often ends sessions; restart while ambient mode is on
      const t = window.setTimeout(() => {
        if (ambientActiveRef.current) speech.startListening();
      }, 400);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [ambientActive, speech.isListening, speech.isSupported, speech]);

  const handleGenerate = useCallback(async () => {
    const text = transcriptRef.current.trim();
    if (!text) {
      showError('Enter transcript or start ambient scribe first');
      return;
    }
    if (ambientActiveRef.current) {
      setAmbientActive(false);
      speech.stopListening();
    }
    setLoading(true);
    setResult(null);
    setEditedNote('');
    try {
      const data = await generateScribeNote({
        transcript: text,
        note_type: noteType,
        visit_id: parseInt(visitId, 10),
      });
      setResult(data);
      setEditedNote(data.structured_note);
      const validation = data.code_validation;
      if (validation?.all_matched) {
        showSuccess(`Note generated — all ${validation.validated_codes.length} codes NHIA verified.`);
      } else if (validation?.validated_codes?.length) {
        showSuccess(
          `Note generated (${data.note_type}). Review validation badges before applying.`,
        );
      } else {
        showSuccess(`Note generated (${data.note_type}). Review and apply to consultation.`);
      }
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to generate note');
    } finally {
      setLoading(false);
    }
  }, [noteType, showError, showSuccess, speech, visitId]);

  const handleApply = useCallback(async () => {
    const noteText = (editedNote || result?.structured_note || '').trim();
    if (!noteText) {
      showError('Nothing to apply');
      return;
    }

    setApplying(true);
    try {
      const template = result?.template_used || 'soap';
      const sections =
        result?.parsed_sections || parseScribeSections(noteText, template);

      onApplySections({
        history: sections.history,
        examination: sections.examination,
        diagnosis: sections.diagnosis,
        clinical_notes: sections.clinical_notes,
      });

      const icdPayload = result?.icd11_apply_payload?.filter((c) => c.code);
      if (icdPayload?.length && consultationId) {
        await applyAIDiagnosisCodes(visitId, {
          icd11_codes: icdPayload,
          set_primary: true,
        });
        onCodesApplied?.();
        showSuccess('Scribe applied to consultation fields and ICD-11 codes.');
      } else if (icdPayload?.length && !consultationId) {
        showSuccess(
          'Consultation fields filled. Save the consultation to apply ICD-11 codes.',
        );
      } else {
        showSuccess('Scribe applied to consultation fields.');
      }
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to apply scribe output');
    } finally {
      setApplying(false);
    }
  }, [
    consultationId,
    editedNote,
    onApplySections,
    onCodesApplied,
    result,
    showError,
    showSuccess,
    visitId,
  ]);

  useEffect(() => {
    const onStart = () => startAmbient();
    const onStop = () => stopAmbient();
    const onGenerate = () => {
      void handleGenerate();
    };
    const onApply = () => {
      void handleApply();
    };
    window.addEventListener(VOICE_SCRIBE_EVENTS.start, onStart);
    window.addEventListener(VOICE_SCRIBE_EVENTS.stop, onStop);
    window.addEventListener(VOICE_SCRIBE_EVENTS.generate, onGenerate);
    window.addEventListener(VOICE_SCRIBE_EVENTS.apply, onApply);

    // Voice command may have navigated here with a queued action
    const pending = consumePendingScribeAction();
    let pendingTimer: number | undefined;
    if (pending) {
      pendingTimer = window.setTimeout(() => {
        window.dispatchEvent(new CustomEvent(VOICE_SCRIBE_EVENTS[pending]));
      }, 350);
    }

    return () => {
      if (pendingTimer) window.clearTimeout(pendingTimer);
      window.removeEventListener(VOICE_SCRIBE_EVENTS.start, onStart);
      window.removeEventListener(VOICE_SCRIBE_EVENTS.stop, onStop);
      window.removeEventListener(VOICE_SCRIBE_EVENTS.generate, onGenerate);
      window.removeEventListener(VOICE_SCRIBE_EVENTS.apply, onApply);
    };
  }, [handleApply, handleGenerate, startAmbient, stopAmbient]);

  useEffect(() => {
    return () => {
      speech.stopListening();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAddToBill = async () => {
    const codes = validation?.validated_codes?.filter(
      (c) => c.match_status === 'matched' && c.nhia && c.amount_ngn,
    );
    if (!codes?.length) {
      showError('No fully matched NHIA tariffs to bill. Generate a note with validated codes first.');
      return;
    }
    setBilling(true);
    try {
      const billResult = await addNhiaScribeCharges(
        parseInt(visitId, 10),
        codes.map((c) => ({
          nhia: c.nhia,
          icd11: c.icd11,
          diagnosis: c.diagnosis || c.tariff_name || undefined,
        })),
        true,
      );
      if (billResult.created_count > 0) {
        showSuccess(
          `Added ${billResult.created_count} NHIA item(s) to visit bill` +
            (billResult.skipped_count ? ` (${billResult.skipped_count} skipped).` : '.'),
        );
        onNhiaBilled?.();
      } else {
        showError('All validated NHIA items are already on this visit bill.');
      }
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to add NHIA items to bill');
    } finally {
      setBilling(false);
    }
  };

  const validation: CodeValidation | undefined = result?.code_validation;
  const billableCount =
    validation?.validated_codes?.filter((c) => c.match_status === 'matched').length ?? 0;

  const formatTimer = (total: number) => {
    const m = Math.floor(total / 60)
      .toString()
      .padStart(2, '0');
    const s = (total % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className={styles.panel} data-ambient-scribe={ambientActive ? 'on' : 'off'}>
      <h3 className={styles.panelTitle}>Clinical AI Scribe</h3>
      <p className={styles.panelHint}>
        Use ambient capture to record the encounter, or paste notes. Generates SOAP or antenatal
        documentation with NHIA tariff validation. Review before applying to this consultation.
      </p>
      <div className={styles.panelBody}>
        <div className={styles.ambientBar}>
          <div className={styles.ambientStatus}>
            {ambientActive ? (
              <>
                <span className={styles.ambientDot} />
                <strong>Ambient listening</strong>
                <span className={styles.ambientTimer}>{formatTimer(ambientSeconds)}</span>
              </>
            ) : (
              <span>Ambient scribe idle</span>
            )}
          </div>
          <div className={styles.actions}>
            {!ambientActive ? (
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={startAmbient}
                disabled={loading || !speech.isSupported}
                title={
                  speech.isSupported
                    ? 'Continuously capture encounter speech into the transcript'
                    : 'Speech recognition unavailable'
                }
              >
                🎤 Start ambient
              </button>
            ) : (
              <button type="button" className={styles.dangerButton} onClick={stopAmbient}>
                ⏹ Stop ambient
              </button>
            )}
          </div>
        </div>

        {ambientActive && speech.interimTranscript && (
          <p className={styles.interimLine}>Live: {speech.interimTranscript}</p>
        )}

        <div className={styles.field}>
          <label htmlFor="consult-scribe-type">Documentation template</label>
          <select
            id="consult-scribe-type"
            value={noteType}
            onChange={(e) => setNoteType(e.target.value as ClinicalNoteType)}
            disabled={loading}
          >
            <option value="auto">Auto (SOAP or Antenatal)</option>
            <option value="SOAP">SOAP</option>
            <option value="antenatal">Antenatal / Maternity</option>
            <option value="summary">Summary</option>
            <option value="discharge">Discharge</option>
          </select>
        </div>
        <div className={styles.field}>
          <label htmlFor="consult-scribe-transcript">Transcript / ambient capture</label>
          <textarea
            id="consult-scribe-transcript"
            rows={5}
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder="Start ambient scribe, or paste encounter notes…"
            disabled={loading}
          />
        </div>
        <div className={styles.actions}>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={() => void handleGenerate()}
            disabled={loading || !transcript.trim()}
          >
            {loading ? 'Generating…' : 'Generate note'}
          </button>
        </div>

        {(result || editedNote) && (
          <>
            {result?.template_used && (
              <p className={styles.panelHint}>
                Template: <strong>{result.note_type}</strong> ({result.template_used})
              </p>
            )}

            {validation && validation.validated_codes.length > 0 && (
              <div className={styles.validationList}>
                <h4>NHIA / ICD-11 validation</h4>
                <ul>
                  {validation.validated_codes.map((code) => (
                    <li
                      key={`${code.icd11}-${code.nhia}`}
                      className={
                        code.match_status === 'matched'
                          ? styles.validationOk
                          : styles.validationWarn
                      }
                    >
                      <span>
                        {code.diagnosis || code.tariff_name || code.icd11} — ICD-11:{' '}
                        <strong>{code.icd11}</strong> / NHIA: <strong>{code.nhia}</strong>
                      </span>
                      <span className={styles.validationBadge}>
                        {matchStatusLabel(code.match_status)}
                        {code.amount_ngn ? ` · ₦${code.amount_ngn}` : ''}
                      </span>
                    </li>
                  ))}
                </ul>
                {validation.suggested_tariffs.length > 0 && (
                  <div className={styles.suggestions}>
                    <p>Suggested NHIA tariffs for unmatched codes:</p>
                    <ul>
                      {validation.suggested_tariffs.map((t) => (
                        <li key={t.nhia_code}>
                          {t.name} ({t.nhia_code}) — ₦{t.amount_ngn} for ICD-11 {t.icd11}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <div className={styles.field}>
              <label htmlFor="consult-scribe-output">Generated note (editable)</label>
              <textarea
                id="consult-scribe-output"
                rows={12}
                value={editedNote}
                onChange={(e) => setEditedNote(e.target.value)}
              />
            </div>
            <div className={styles.actions}>
              <button
                type="button"
                className={styles.primaryButton}
                onClick={() => void handleApply()}
                disabled={applying || !editedNote.trim()}
              >
                {applying ? 'Applying…' : 'Apply to consultation'}
              </button>
              {billableCount > 0 && (
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={handleAddToBill}
                  disabled={billing}
                  title="Add validated NHIA tariff amounts to this visit bill"
                >
                  {billing ? 'Adding to bill…' : `Add ${billableCount} NHIA item(s) to bill`}
                </button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
