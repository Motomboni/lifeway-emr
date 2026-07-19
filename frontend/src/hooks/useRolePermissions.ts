/**
 * Centralized role-based permission checks for the frontend.
 */
import { useAuth } from '../contexts/AuthContext';
import {
  isAdminUser,
  isSuperuser,
  isPatientUser,
  isStaffUser,
  hasRole,
  canViewAppointments,
  canManageAppointments,
  canAccessWallet,
  canManageLabCatalog,
  canViewLabCatalog,
  canManageRadiologyCatalog,
  canViewRadiologyCatalog,
  canCreateVisit,
  canManagePatients,
  canArchivePatients,
  StaffRole,
} from '../utils/roleUtils';

export function useRolePermissions() {
  const { user } = useAuth();

  return {
    user,
    role: user?.role,
    isAdmin: isAdminUser(user),
    isSuperuser: isSuperuser(user),
    isPatient: isPatientUser(user),
    isStaff: isStaffUser(user),
    isReceptionist: user?.role === 'RECEPTIONIST',
    isDoctor: user?.role === 'DOCTOR',
    isNurse: user?.role === 'NURSE',
    hasRole: (roles: StaffRole | StaffRole[]) => hasRole(user, roles),
    canViewAppointments: canViewAppointments(user),
    canManageAppointments: canManageAppointments(user),
    canAccessWallet: canAccessWallet(user),
    canManageLabCatalog: canManageLabCatalog(user),
    canViewLabCatalog: canViewLabCatalog(user),
    canManageRadiologyCatalog: canManageRadiologyCatalog(user),
    canViewRadiologyCatalog: canViewRadiologyCatalog(user),
    canCreateVisit: canCreateVisit(user),
    canManagePatients: canManagePatients(user),
    canArchivePatients: canArchivePatients(user),
    canHardDeleteRecords: isSuperuser(user),
  };
}
