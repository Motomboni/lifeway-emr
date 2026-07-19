import type { ConsultationMacro } from '../types/guide';

/** Local documentation macros — expand into consultation sections. */
export const CONSULTATION_MACROS: ConsultationMacro[] = [
  {
    trigger: '.dm2',
    label: 'Type 2 DM — controlled',
    expansion: {
      diagnosis: 'Type 2 diabetes mellitus, controlled on current regimen.',
      clinical_notes: 'Continue current medications. Counsel on diet and exercise. Fasting glucose and HbA1c at next visit.',
    },
  },
  {
    trigger: '.htn',
    label: 'Hypertension — stable',
    expansion: {
      diagnosis: 'Essential hypertension, well controlled.',
      clinical_notes: 'Continue antihypertensive therapy. Home BP monitoring advised. Review renal function annually.',
    },
  },
  {
    trigger: '.uri',
    label: 'Upper respiratory infection',
    expansion: {
      history: 'C/o cough, nasal congestion, and sore throat × 3 days. No dyspnoea or chest pain. No known sick contacts.',
      examination: 'Afebrile. Oropharynx mildly erythematous. Chest clear. No lymphadenopathy.',
      diagnosis: 'Acute upper respiratory tract infection, likely viral.',
      clinical_notes: 'Symptomatic care. Return if fever >38.5°C, dyspnoea, or symptoms worsen after 5 days.',
    },
  },
  {
    trigger: '.anc',
    label: 'Routine ANC visit',
    expansion: {
      history: 'Routine antenatal visit. No bleeding, leakage of liquor, or reduced fetal movements.',
      examination: 'Vitals within normal limits. Fundal height appropriate for gestational age. FHR present.',
      clinical_notes: 'Continue iron and folate. Next ANC visit scheduled. Danger signs counselled.',
    },
  },
  {
    trigger: '.well',
    label: 'Well adult review',
    expansion: {
      history: 'Presenting for routine review. No acute complaints.',
      examination: 'General condition satisfactory. Systems review unremarkable.',
      clinical_notes: 'Health maintenance discussed. Follow up as needed.',
    },
  },
];

export function findMacroByTrigger(trigger: string): ConsultationMacro | undefined {
  const normalized = trigger.trim().toLowerCase();
  return CONSULTATION_MACROS.find((m) => m.trigger.toLowerCase() === normalized);
}
