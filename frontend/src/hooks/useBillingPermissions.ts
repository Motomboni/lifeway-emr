/**
 * Billing Permissions Hook
 * 
 * Provides role-based permission checks for billing operations.
 * Per EMR Rules: Only Receptionist can view/edit billing.
 */
import { useAuth } from '../contexts/AuthContext';

export interface BillingPermissions {
  canViewBilling: boolean;
  canEditBilling: boolean;
  canProcessPayments: boolean;
  canAddCharges: boolean;
  canViewInsurance: boolean;
  canManageInsurance: boolean;
  isReceptionist: boolean;
  isDoctor: boolean;
  isAdmin: boolean;
}

export function useBillingPermissions(): BillingPermissions {
  const { user } = useAuth();
  
  const isReceptionist = user?.role === 'RECEPTIONIST';
  const isDoctor = user?.role === 'DOCTOR';
  const isAdmin = user?.is_superuser === true;
  
  // Only Receptionist and Admin can view billing
  const canViewBilling = isReceptionist || isAdmin;
  
  // Only Receptionist can edit billing
  const canEditBilling = isReceptionist;
  
  // Only Receptionist can process payments
  const canProcessPayments = isReceptionist;
  
  // Doctors can request consultation charges and add post-consultation services; Receptionist and departments can add charges
  const canAddCharges = isReceptionist || 
    isDoctor ||
    user?.role === 'LAB_TECH' || 
    user?.role === 'PHARMACIST' || 
    user?.role === 'RADIOLOGY_TECH';
  
  // All authenticated users can view insurance info
  const canViewInsurance = !!user;
  
  // Only Receptionist can manage insurance
  const canManageInsurance = isReceptionist;
  
  return {
    canViewBilling,
    canEditBilling,
    canProcessPayments,
    canAddCharges,
    canViewInsurance,
    canManageInsurance,
    isReceptionist,
    isDoctor,
    isAdmin,
  };
}

