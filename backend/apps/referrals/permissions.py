"""
Permissions for Referrals.
"""
from rest_framework.permissions import BasePermission


class CanCreateReferral(BasePermission):
    """Permission to create referrals (Doctors only). Nurse explicitly denied."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # Explicit guard: Deny Nurse
        if user_role == 'NURSE':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                detail="Nurses are not permitted to create referrals. "
                       "This action requires Doctor role.",
                code='nurse_prohibited'
            )
        
        return user_role == 'DOCTOR'


class CanViewReferral(BasePermission):
    """Permission to view referrals (All authenticated users)."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanUpdateReferral(BasePermission):
    """Permission to update referrals (Doctors and Receptionists)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # Doctors and Receptionists can update referral status
        return user_role in ['DOCTOR', 'RECEPTIONIST']
