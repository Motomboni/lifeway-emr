/** Guide module keys aligned with backend guide_modules.py */

export type GuideModuleKey =
  | 'core'
  | 'laboratory'
  | 'pharmacy'
  | 'radiology'
  | 'nhia'
  | 'anc'
  | 'telemedicine';

export type GuideModules = Record<GuideModuleKey, boolean>;

export const DEFAULT_GUIDE_MODULES: GuideModules = {
  core: true,
  laboratory: true,
  pharmacy: true,
  radiology: true,
  nhia: true,
  anc: true,
  telemedicine: true,
};

export const GUIDE_MODULE_LABELS: Record<GuideModuleKey, string> = {
  core: 'Core workflows (register, vitals, billing)',
  laboratory: 'Laboratory',
  pharmacy: 'Pharmacy & prescriptions',
  radiology: 'Radiology / imaging',
  nhia: 'NHIA billing & claims',
  anc: 'Antenatal (ANC)',
  telemedicine: 'Telemedicine',
};

/** Admin-configurable modules (core always on). */
export const GUIDE_MODULE_TOGGLES: GuideModuleKey[] = [
  'laboratory',
  'pharmacy',
  'radiology',
  'nhia',
  'anc',
  'telemedicine',
];

export function normalizeGuideModules(raw?: Partial<GuideModules> | null): GuideModules {
  const result = { ...DEFAULT_GUIDE_MODULES };
  if (raw) {
    for (const key of Object.keys(DEFAULT_GUIDE_MODULES) as GuideModuleKey[]) {
      if (key in raw) {
        result[key] = Boolean(raw[key]);
      }
    }
  }
  return result;
}

export function isGuideModuleEnabled(
  module: GuideModuleKey | undefined,
  modules: GuideModules
): boolean {
  if (!module || module === 'core') {
    return modules.core;
  }
  return modules[module] ?? true;
}
