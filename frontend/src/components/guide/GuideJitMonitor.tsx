/**
 * GuideJitMonitor — runs JIT rule evaluation and renders the hint chip.
 */
import React from 'react';
import { useGuideJitActions, useGuideJitHints } from '../../hooks/useGuideJitHints';
import JitHintChip from './JitHintChip';

export default function GuideJitMonitor() {
  const activeHint = useGuideJitHints();
  const { executeHintAction, dismissJitHint } = useGuideJitActions();

  if (!activeHint) {
    return null;
  }

  return (
    <JitHintChip
      hint={activeHint}
      onAction={() => void executeHintAction(activeHint)}
      onDismiss={() => void dismissJitHint(activeHint)}
    />
  );
}
