/**
 * VoiceCommandBar — floating staff voice control.
 * Opens common clinical workflows + ambient scribe + virtual clinic invites.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import { isStaffUser } from '../../utils/roleUtils';
import {
  getVoiceCommandExamplesForRole,
  dispatchScribeVoiceEvent,
  parseVoiceIntent,
  queuePendingClinicInvite,
  queuePendingScribeAction,
  type PendingScribeAction,
  type VoiceIntent,
  type VoiceParseContext,
} from '../../utils/voiceIntents';
import styles from '../../styles/VoiceCommandBar.module.css';

type PanelMode = 'collapsed' | 'listening' | 'confirm' | 'help';

function consultationVisitId(pathname: string): string | null {
  const m = pathname.match(/^\/visits\/(\d+)\/consultation\/?$/);
  return m ? m[1] : null;
}

function anyVisitId(pathname: string): string | null {
  const m = pathname.match(/^\/visits\/(\d+)(?:\/|$)/);
  return m ? m[1] : null;
}

function roomSessionId(pathname: string): string | null {
  const m = pathname.match(/^\/telemedicine\/room\/(\d+)\/?$/);
  return m ? m[1] : null;
}

export default function VoiceCommandBar() {
  const { isAuthenticated, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { showSuccess, showError } = useToast();
  const [mode, setMode] = useState<PanelMode>('collapsed');
  const [pending, setPending] = useState<VoiceIntent | null>(null);
  const [lastHeard, setLastHeard] = useState('');
  const [statusLine, setStatusLine] = useState('Say a command…');

  const parseContext: VoiceParseContext = useMemo(
    () => ({
      visitId: anyVisitId(location.pathname),
      sessionId: roomSessionId(location.pathname),
      role: user?.role,
    }),
    [location.pathname, user?.role],
  );

  const helpExamples = useMemo(
    () => getVoiceCommandExamplesForRole(user?.role),
    [user?.role],
  );

  const runScribeAction = useCallback(
    (action: PendingScribeAction) => {
      const onConsult = consultationVisitId(location.pathname);
      if (onConsult) {
        dispatchScribeVoiceEvent(action);
        const labels: Record<PendingScribeAction, string> = {
          start: 'Ambient scribe started',
          stop: 'Ambient scribe stopped',
          generate: 'Generating clinical note…',
          apply: 'Applying scribe to consultation…',
        };
        showSuccess(labels[action]);
        return;
      }

      const visitId = anyVisitId(location.pathname);
      if (visitId && (action === 'start' || action === 'generate' || action === 'apply')) {
        queuePendingScribeAction(action);
        navigate(`/visits/${visitId}/consultation`);
        showSuccess(
          action === 'start'
            ? 'Opening consultation to start ambient scribe…'
            : 'Opening consultation for scribe…',
        );
        return;
      }

      if (action === 'stop') {
        showError('Ambient scribe is only active on a consultation page.');
        return;
      }

      showError('Open a consultation first, then try the scribe command again.');
      navigate('/visits?status=OPEN');
    },
    [location.pathname, navigate, showError, showSuccess],
  );

  const runClinicInvite = useCallback(
    (intent: VoiceIntent) => {
      const role = intent.inviteRole || 'NURSE';
      queuePendingClinicInvite(role);
      if (intent.path) {
        navigate(intent.path);
      } else {
        navigate('/telemedicine');
      }
      showSuccess(`${intent.label} — opening invite panel`);
    },
    [navigate, showSuccess],
  );

  const executeIntent = useCallback(
    (intent: VoiceIntent) => {
      switch (intent.type) {
        case 'navigate':
          if (intent.path) {
            navigate(intent.path);
            showSuccess(intent.label);
          }
          break;
        case 'clinic_invite':
          runClinicInvite(intent);
          break;
        case 'scribe_start':
          runScribeAction('start');
          break;
        case 'scribe_stop':
          runScribeAction('stop');
          break;
        case 'scribe_generate':
          runScribeAction('generate');
          break;
        case 'scribe_apply':
          runScribeAction('apply');
          break;
        case 'help':
          setMode('help');
          return;
        default:
          showError(intent.label);
          setStatusLine(intent.label);
          setMode('collapsed');
          return;
      }
      setMode('collapsed');
      setPending(null);
      setStatusLine(intent.label);
    },
    [navigate, runClinicInvite, runScribeAction, showError, showSuccess],
  );

  const handleFinalUtterance = useCallback(
    (transcript: string) => {
      const text = transcript.trim();
      if (!text) return;
      setLastHeard(text);
      const intent = parseVoiceIntent(text, parseContext);
      if (intent.type === 'unknown') {
        setStatusLine(intent.label);
        showError(`Voice: ${intent.label}`);
        setMode('collapsed');
        return;
      }
      if (intent.type === 'help') {
        setMode('help');
        return;
      }
      if (intent.requiresConfirm) {
        setPending(intent);
        setMode('confirm');
        setStatusLine(`Confirm: ${intent.label}?`);
        return;
      }
      executeIntent(intent);
    },
    [executeIntent, parseContext, showError],
  );

  const speech = useSpeechRecognition({
    continuous: false,
    interimResults: true,
    lang: 'en-NG',
    onResult: (text, isFinal) => {
      if (!isFinal) {
        setStatusLine(text || 'Listening…');
        return;
      }
      if (text.trim()) {
        handleFinalUtterance(text);
      }
    },
    onError: (err) => {
      showError(err);
      setMode('collapsed');
      setStatusLine(err);
    },
  });

  useEffect(() => {
    if (mode === 'listening' && speech.isSupported && !speech.isListening) {
      speech.clearTranscript();
      speech.startListening();
    }
    if (mode !== 'listening' && speech.isListening) {
      speech.stopListening();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, speech.isSupported]);

  if (!isAuthenticated || !isStaffUser(user)) {
    return null;
  }

  if (!speech.isSupported) {
    return createPortal(
      <div className={styles.shell} aria-live="polite">
        <button type="button" className={styles.fabDisabled} title="Voice not supported in this browser" disabled>
          🎤
        </button>
      </div>,
      document.body,
    );
  }

  const startListening = () => {
    setPending(null);
    setStatusLine('Listening…');
    setMode('listening');
  };

  const cancel = () => {
    speech.stopListening();
    setPending(null);
    setMode('collapsed');
    setStatusLine('Cancelled');
  };

  return createPortal(
    <div className={styles.shell} aria-live="polite">
      {mode !== 'collapsed' && (
        <div className={styles.panel} role="dialog" aria-label="Voice commands">
          <div className={styles.panelHeader}>
            <strong>Voice control</strong>
            <button type="button" className={styles.closeBtn} onClick={cancel} aria-label="Close">
              ×
            </button>
          </div>

          {mode === 'listening' && (
            <>
              <p className={styles.listeningBadge}>Listening…</p>
              <p className={styles.heard}>{speech.interimTranscript || statusLine}</p>
              <button type="button" className={styles.secondary} onClick={cancel}>
                Cancel
              </button>
            </>
          )}

          {mode === 'confirm' && pending && (
            <>
              <p className={styles.confirmText}>{pending.label}</p>
              {lastHeard && <p className={styles.heardMuted}>Heard: “{lastHeard}”</p>}
              <div className={styles.row}>
                <button type="button" className={styles.secondary} onClick={cancel}>
                  Cancel
                </button>
                <button
                  type="button"
                  className={styles.primary}
                  onClick={() => executeIntent(pending)}
                >
                  Confirm
                </button>
              </div>
            </>
          )}

          {mode === 'help' && (
            <>
              <p className={styles.helpIntro}>
                Try saying{user?.role ? ` (${user.role.toLowerCase()})` : ''}:
              </p>
              <ul className={styles.helpList}>
                {helpExamples.map((ex) => (
                  <li key={ex}>{ex}</li>
                ))}
              </ul>
              <button type="button" className={styles.secondary} onClick={() => setMode('collapsed')}>
                Close
              </button>
            </>
          )}
        </div>
      )}

      <div className={styles.fabRow}>
        {mode === 'collapsed' && lastHeard && (
          <span className={styles.lastHint} title={lastHeard}>
            {statusLine}
          </span>
        )}
        <button
          type="button"
          className={`${styles.fab} ${mode === 'listening' ? styles.fabActive : ''}`}
          onClick={() => (mode === 'listening' ? cancel() : startListening())}
          aria-label={mode === 'listening' ? 'Stop listening' : 'Start voice command'}
          title="Voice commands (say Help for list)"
        >
          {mode === 'listening' ? '⏹' : '🎤'}
        </button>
        {mode === 'collapsed' && (
          <button
            type="button"
            className={styles.helpFab}
            onClick={() => setMode('help')}
            aria-label="Voice command help"
            title="Voice command help"
          >
            ?
          </button>
        )}
      </div>
    </div>,
    document.body,
  );
}
