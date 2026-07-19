import { GUIDE_COMMANDS } from '../data/guideCommands';
import type { GuideCommand } from '../types/guide';
import type { GuideModules } from '../data/guideModules';
import { isGuideModuleEnabled, normalizeGuideModules } from '../data/guideModules';

export function filterGuideCommands(
  query: string,
  role: string | undefined,
  modules?: Partial<GuideModules> | null
): GuideCommand[] {
  const q = query.trim().toLowerCase();
  const enabled = normalizeGuideModules(modules ?? undefined);

  return GUIDE_COMMANDS.filter((command) => {
    if (command.roles && role && role !== 'ADMIN' && !command.roles.includes(role)) {
      return false;
    }
    if (command.module && !isGuideModuleEnabled(command.module as keyof GuideModules, enabled)) {
      return false;
    }
    if (!q) return true;
    if (command.label.toLowerCase().includes(q)) return true;
    if (command.id.toLowerCase().includes(q)) return true;
    return command.keywords.some(
      (keyword) => keyword.includes(q) || q.includes(keyword)
    );
  });
}
