/**
 * JitHintChip — subtle just-in-time help chip (non-modal).
 */
import React from 'react';
import { createPortal } from 'react-dom';
import type { JitHint } from '../../types/guide';
import styles from '../../styles/Guide.module.css';

interface JitHintChipProps {
  hint: JitHint;
  onAction: () => void;
  onDismiss: () => void;
}

export default function JitHintChip({ hint, onAction, onDismiss }: JitHintChipProps) {
  return createPortal(
    <div className={styles.jitHintContainer} role="status" aria-live="polite">
      <div className={styles.jitHintChip}>
        <p className={styles.jitHintMessage}>{hint.message}</p>
        <div className={styles.jitHintActions}>
          {hint.actionLabel && (
            <button type="button" className={styles.jitHintAction} onClick={onAction}>
              {hint.actionLabel}
            </button>
          )}
          <button type="button" className={styles.jitHintDismiss} onClick={onDismiss} aria-label="Dismiss hint">
            ×
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}
