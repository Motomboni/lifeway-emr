/**
 * Shared role / permission helpers (pure functions — no React dependency).
 */
import { User } from '../types/auth';

export type StaffRole =
  | 'ADMIN'
  | 'DOCTOR'
  | 'NURSE'
  | 'LAB_TECH'
  | 'RADIOLOGY_TECH'
  | 'PHARMACIST'
  | 'RECEPTIONIST'
  | 'IVF_SPECIALIST'
  | 'EMBRYOLOGIST';

export function getUserRole(user: User | null | undefined): string | undefined {
  return user?.role;
}

export function isSuperuser(user: User | null | undefined): boolean {
  return user?.is_superuser === true;
}

/** Platform admin: superuser or ADMIN role */
export function isAdminUser(user: User | null | undefined): boolean {
  return isSuperuser(user) || user?.role === 'ADMIN';
}

export function isPatientUser(user: User | null | undefined): boolean {
  return user?.role === 'PATIENT';
}

export function isStaffUser(user: User | null | undefined): boolean {
  return !!user && !isPatientUser(user);
}

export function hasRole(
  user: User | null | undefined,
  roles: StaffRole | StaffRole[]
): boolean {
  if (!user?.role) return false;
  if (isAdminUser(user)) return true;
  const allowed = Array.isArray(roles) ? roles : [roles];
  return allowed.includes(user.role as StaffRole);
}

export function canViewAppointments(user: User | null | undefined): boolean {
  return hasRole(user, [
    'RECEPTIONIST',
    'DOCTOR',
    'NURSE',
    'IVF_SPECIALIST',
    'EMBRYOLOGIST',
    'ADMIN',
  ]);
}

export function canManageAppointments(user: User | null | undefined): boolean {
  return hasRole(user, ['RECEPTIONIST', 'DOCTOR', 'IVF_SPECIALIST', 'ADMIN']);
}

export function canAccessWallet(user: User | null | undefined): boolean {
  return user?.role === 'PATIENT' || user?.role === 'RECEPTIONIST' || isAdminUser(user);
}

export function canManageLabCatalog(user: User | null | undefined): boolean {
  return hasRole(user, ['DOCTOR', 'LAB_TECH', 'ADMIN']);
}

export function canViewLabCatalog(user: User | null | undefined): boolean {
  return hasRole(user, ['DOCTOR', 'LAB_TECH', 'ADMIN']);
}

export function canManageRadiologyCatalog(user: User | null | undefined): boolean {
  return hasRole(user, ['DOCTOR', 'RADIOLOGY_TECH', 'ADMIN']);
}

export function canViewRadiologyCatalog(user: User | null | undefined): boolean {
  return hasRole(user, ['DOCTOR', 'RADIOLOGY_TECH', 'ADMIN']);
}

export function canCreateVisit(user: User | null | undefined): boolean {
  return hasRole(user, ['RECEPTIONIST', 'ADMIN']);
}

export function canManagePatients(user: User | null | undefined): boolean {
  return hasRole(user, ['RECEPTIONIST', 'ADMIN']);
}

export function canArchivePatients(user: User | null | undefined): boolean {
  return isSuperuser(user) || hasRole(user, ['RECEPTIONIST', 'ADMIN']);
}
