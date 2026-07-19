import type { RoleLaunchStep } from '../types/guide';
import type { GuideModuleKey, GuideModules } from './guideModules';
import { isGuideModuleEnabled, normalizeGuideModules } from './guideModules';

/** Role Launch tour steps — learn-by-doing on live UI targets. */
export const ROLE_LAUNCH_STEPS: Record<string, RoleLaunchStep[]> = {
  DOCTOR: [
    {
      id: 'doctor-launch:open-visits',
      title: 'Your patient queue',
      body: 'Open Visits shows every active encounter. Start here each shift.',
      guide_target: 'dashboard-open-visits',
      route: '/dashboard',
    },
    {
      id: 'doctor-launch:consultation',
      title: 'Consultation workspace',
      body: 'Chart, order labs, and prescribe — all on one scrollable screen tied to the visit.',
      guide_target: 'consultation-form',
      requiresSandbox: true,
      sandboxPath: 'consultation',
    },
    {
      id: 'doctor-launch:service-catalog',
      title: 'Service Catalog & billing',
      body: 'Add NHIA-validated services and charges right after your clinical notes.',
      guide_target: 'service-catalog',
      module: 'nhia',
      requiresSandbox: true,
      sandboxPath: 'consultation',
    },
    {
      id: 'doctor-launch:close-visit',
      title: 'Save & close',
      body: 'Save consultation, confirm payment is cleared, then close the visit from the bottom bar.',
      guide_target: 'consultation-actions',
      requiresSandbox: true,
      sandboxPath: 'consultation',
    },
  ],
  RECEPTIONIST: [
    {
      id: 'reception-launch:register',
      title: 'Register patients',
      body: 'Add new patients from quick actions — demographics and NHIA details live here.',
      guide_target: 'register-patient',
      route: '/dashboard',
    },
    {
      id: 'reception-launch:create-visit',
      title: 'Create a visit',
      body: 'Every clinical action is visit-scoped. Create a visit before sending the patient to the doctor.',
      guide_target: 'dashboard-create-visit',
      route: '/dashboard',
    },
    {
      id: 'reception-launch:billing',
      title: 'Clear payment',
      body: 'Process Cash, POS, Transfer, or Paystack on Visit Details → Billing.',
      guide_target: 'billing-dashboard',
      requiresSandbox: true,
      sandboxPath: 'visit-details',
    },
    {
      id: 'reception-launch:appointments',
      title: 'Appointments',
      body: 'Doctors can self-schedule; you see and manage the full clinic calendar.',
      guide_target: 'appointments',
      route: '/appointments',
    },
  ],
  NURSE: [
    {
      id: 'nurse-launch:vitals',
      title: 'Record vitals first',
      body: 'Vital signs sit at the top of the nursing visit page.',
      guide_target: 'vitals-inline',
      requiresSandbox: true,
      sandboxPath: 'nursing',
    },
    {
      id: 'nurse-launch:intake',
      title: 'Intake checklist',
      body: 'Follow the workflow rail on each visit — verify patient, vitals, triage, then queue for doctor.',
      guide_target: 'workflow-rail',
      requiresSandbox: true,
      sandboxPath: 'nursing',
    },
  ],
  LAB_TECH: [
    {
      id: 'labtech-launch:worklist',
      title: 'Lab worklist',
      body: 'Your queue shows every visit with pending lab orders. Select a visit to begin.',
      guide_target: 'lab-worklist',
      route: '/lab-orders',
    },
    {
      id: 'labtech-launch:result',
      title: 'Record results',
      body: 'Enter findings for each order and flag abnormal or critical values.',
      guide_target: 'lab-result-form',
      route: '/lab-orders',
    },
  ],
  PHARMACIST: [
    {
      id: 'pharm-launch:worklist',
      title: 'Prescription queue',
      body: 'Open Prescriptions to see visits with pending medication orders.',
      guide_target: 'pharmacy-worklist',
      route: '/prescriptions',
    },
    {
      id: 'pharm-launch:dispense',
      title: 'Dispense medication',
      body: 'Verify payment is cleared, enter dispensed quantity, then dispense.',
      guide_target: 'pharmacy-dispense',
      route: '/prescriptions',
    },
  ],
};

export function getRoleLaunchSteps(
  role: string | undefined,
  modules?: Partial<GuideModules> | null
): RoleLaunchStep[] {
  if (!role) return [];
  const steps = ROLE_LAUNCH_STEPS[role] ?? [];
  const enabled = normalizeGuideModules(modules ?? undefined);
  return steps.filter((step) =>
    isGuideModuleEnabled(step.module as GuideModuleKey | undefined, enabled)
  );
}
