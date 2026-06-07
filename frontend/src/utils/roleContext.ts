/**
 * Helpers for admin view-as-role and effective role checks.
 */
import { User, UserRole } from '../types/auth';

export const ROLE_LABELS: Record<string, string> = {
  ADMIN: 'Administrator',
  DOCTOR: 'Doctor',
  NURSE: 'Nurse',
  LAB_TECH: 'Lab Scientist',
  RADIOLOGY_TECH: 'Radiology Technician',
  PHARMACIST: 'Pharmacist',
  RECEPTIONIST: 'Receptionist',
  IVF_SPECIALIST: 'IVF Specialist',
  EMBRYOLOGIST: 'Embryologist',
  PATIENT: 'Patient',
};

export function getActualRole(user: User | null | undefined): UserRole | undefined {
  if (!user) return undefined;
  return user.actual_role ?? user.role;
}

export function getEffectiveRole(user: User | null | undefined): UserRole | undefined {
  return user?.role;
}

export function isAdminUser(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser === true) return true;
  const actual = getActualRole(user);
  if (actual === 'ADMIN') return true;
  // Fallback when /me has not yet populated actual_role
  if (user.role === 'ADMIN' && !user.viewing_as_role) return true;
  return false;
}

export function isViewingAsRole(user: User | null | undefined): boolean {
  return Boolean(user?.viewing_as_role);
}

export function formatRoleLabel(role: string | undefined): string {
  if (!role) return '';
  return ROLE_LABELS[role] ?? role.replace(/_/g, ' ');
}
