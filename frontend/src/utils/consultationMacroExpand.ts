import { CONSULTATION_MACROS, findMacroByTrigger } from '../data/consultationMacros';
import { ConsultationData } from '../types/consultation';

export type MacroField = 'history' | 'examination' | 'diagnosis' | 'clinical_notes';

export function detectMacroTrigger(value: string): string | null {
  const trimmed = value.trimEnd();
  for (const macro of CONSULTATION_MACROS) {
    if (trimmed.endsWith(macro.trigger)) {
      return macro.trigger;
    }
  }
  return null;
}

function mergeFieldValue(existing: string, incoming: string): string {
  const base = existing.trim();
  if (!base) return incoming;
  return `${base}\n\n${incoming}`.trim();
}

/** Build form updates when user types a macro trigger and presses Tab. */
export function buildMacroExpansion(
  field: MacroField,
  value: string,
  formData: Pick<ConsultationData, MacroField>
): Partial<ConsultationData> | null {
  const trigger = detectMacroTrigger(value);
  if (!trigger) return null;

  const macro = findMacroByTrigger(trigger);
  if (!macro) return null;

  const trimmed = value.trimEnd();
  const fieldValue = trimmed.slice(0, trimmed.length - trigger.length).trimEnd();
  const updates: Partial<ConsultationData> = {
    [field]: fieldValue,
  };

  for (const [key, text] of Object.entries(macro.expansion)) {
    if (!text) continue;
    const macroField = key as MacroField;
    updates[macroField] = mergeFieldValue(formData[macroField] || '', text);
  }

  return updates;
}

/** Apply a macro by trigger (command palette / guide). */
export function applyMacroTrigger(
  trigger: string,
  formData: Pick<ConsultationData, MacroField>
): Partial<ConsultationData> | null {
  const macro = findMacroByTrigger(trigger);
  if (!macro) return null;

  const updates: Partial<ConsultationData> = {};
  for (const [key, text] of Object.entries(macro.expansion)) {
    if (!text) continue;
    const macroField = key as MacroField;
    updates[macroField] = mergeFieldValue(formData[macroField] || '', text);
  }
  return updates;
}
