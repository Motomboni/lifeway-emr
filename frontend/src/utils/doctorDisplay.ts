import { User } from '../types/auth';

export function formatDoctorDisplayName(user: Pick<User, 'role' | 'first_name' | 'last_name' | 'username' | 'specialization'>): string {
  const baseName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim() || user.username;
  if (user.role !== 'DOCTOR') return baseName;
  const prefixed = /^dr\./i.test(baseName) ? baseName : `Dr. ${baseName}`;
  const specialization = (user.specialization || '').trim();
  return specialization ? `${prefixed} (${specialization})` : prefixed;
}
