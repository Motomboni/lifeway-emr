import { ClinicalTemplate } from '../types/clinical';

const GENERAL_PATTERN = /general|routine|consultation|default/i;

/** Pick a sensible default template for a new consultation. */
export function pickDefaultClinicalTemplate(
  templates: ClinicalTemplate[],
  visitType?: string
): ClinicalTemplate | undefined {
  if (templates.length === 0) return undefined;

  if (visitType) {
    const normalized = visitType.toLowerCase().replace(/_/g, ' ');
    const byCategory = templates.find(
      (template) =>
        template.category.toLowerCase() === visitType.toLowerCase() ||
        template.category.toLowerCase().replace(/_/g, ' ') === normalized ||
        template.name.toLowerCase().includes(normalized)
    );
    if (byCategory) return byCategory;
  }

  const general = templates.find(
    (template) => GENERAL_PATTERN.test(`${template.name} ${template.category}`)
  );
  return general ?? templates[0];
}
