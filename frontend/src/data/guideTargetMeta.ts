/** Default spotlight copy when only a guide_target id is known. */
export interface GuideTargetMeta {
  title: string;
  body: string;
}

export const GUIDE_TARGET_META: Record<string, GuideTargetMeta> = {
  'dashboard-open-visits': {
    title: 'Your patient queue',
    body: 'Open Visits lists every active encounter. Start here each shift.',
  },
  'dashboard-create-visit': {
    title: 'Create a visit',
    body: 'Every clinical action is visit-scoped. Create a visit before the patient sees the doctor.',
  },
  'register-patient': {
    title: 'Register patients',
    body: 'Add new patients with demographics and insurance details from here.',
  },
  'patient-summary': {
    title: 'Patient context',
    body: 'Confirm you have the right patient before documenting or ordering.',
  },
  'visit-status': {
    title: 'Visit status',
    body: 'Track whether the visit is open and if payment has been cleared.',
  },
  'clinical-alerts': {
    title: 'Clinical alerts',
    body: 'Review allergies and safety alerts before charting or prescribing.',
  },
  'vitals-inline': {
    title: 'Vital signs',
    body: 'Record vitals at the top of the visit — abnormal values are highlighted.',
  },
  'consultation-form': {
    title: 'Consultation chart',
    body: 'Document history, exam, diagnosis, and clinical notes in one scrollable form.',
  },
  'service-catalog': {
    title: 'Service Catalog',
    body: 'Add NHIA-validated services and billable items after your clinical notes.',
  },
  'lab-inline': {
    title: 'Lab orders',
    body: 'Order labs here — pick individual tests or apply a template.',
  },
  'radiology-inline': {
    title: 'Radiology orders',
    body: 'Order imaging studies and view reports in the consultation workspace.',
  },
  'prescription-inline': {
    title: 'Prescriptions',
    body: 'Write e-prescriptions inline during the consultation.',
  },
  'lab-worklist': {
    title: 'Lab worklist',
    body: 'Select a visit from the queue to process pending lab orders.',
  },
  'lab-result-form': {
    title: 'Record lab results',
    body: 'Enter findings and flag abnormal or critical values before saving.',
  },
  'pharmacy-worklist': {
    title: 'Prescription queue',
    body: 'Visits with pending prescriptions appear in this worklist.',
  },
  'pharmacy-dispense': {
    title: 'Dispense medication',
    body: 'Confirm payment, enter dispensed quantity, and complete dispensing.',
  },
  'consultation-actions': {
    title: 'Save & close',
    body: 'Save your consultation, confirm billing is cleared, then close the visit.',
  },
  'billing-dashboard': {
    title: 'Billing',
    body: 'Process Cash, POS, Transfer, or Paystack to clear the visit balance.',
  },
  appointments: {
    title: 'Appointments',
    body: 'Doctors can self-schedule; reception sees the full clinic calendar.',
  },
};

export function getGuideTargetMeta(targetId: string): GuideTargetMeta {
  return (
    GUIDE_TARGET_META[targetId] ?? {
      title: 'Guide',
      body: 'This is the area you were looking for.',
    }
  );
}
