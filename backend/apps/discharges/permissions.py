"""
Permissions for Discharge Summaries.
"""
from rest_framework.permissions import BasePermission


class CanCreateDischargeSummary(BasePermission):
    """Permission to create discharge summaries (Doctors only). Nurse explicitly denied."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # Explicit guard: Deny Nurse
        if user_role == 'NURSE':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                detail="Nurses are not permitted to create discharge summaries. "
                       "This action requires Doctor role.",
                code='nurse_prohibited'
            )
        
        return user_role == 'DOCTOR'


class CanViewDischargeSummary(BasePermission):
    """Permission to view discharge summaries (All authenticated users)."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
