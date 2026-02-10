"""
Radiology Request Permissions - strict role enforcement.

Per EMR Rules:
- Doctor: Can create requests, view all (including reports)
- Radiology Tech: Can only update reports, cannot create requests
- No role overlap allowed
"""
from rest_framework import permissions


class IsDoctorOrRadiologyTech(permissions.BasePermission):
    """
    Permission class for radiology request endpoints.
    Allows both Doctor and Radiology Tech, but with different actions.
    """
    
    def has_permission(self, request, view):
        """Check if user is a doctor or radiology tech."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['DOCTOR', 'RADIOLOGY_TECH']


class CanCreateRadiologyRequest(permissions.BasePermission):
    """
    Permission: Only doctors can create radiology requests.
    Radiology Tech and Nurse cannot create requests.
    """
    
    def has_permission(self, request, view):
        """Check if user is a doctor. Explicitly deny Nurse."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Explicit guard: Deny Nurse
        if user_role == 'NURSE':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                detail="Nurses are not permitted to create radiology orders. "
                       "This action requires Doctor role.",
                code='nurse_prohibited'
            )
        
        return user_role == 'DOCTOR'


class CanUpdateRadiologyReport(permissions.BasePermission):
    """
    Permission: Only Radiology Tech can update radiology reports.
    Doctor cannot update reports (only view).
    """
    
    def has_permission(self, request, view):
        """Check if user is a radiology tech."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'RADIOLOGY_TECH'


class CanViewRadiologyRequest(permissions.BasePermission):
    """
    Permission: Doctor can view all fields, Radiology Tech can view limited fields.
    """
    
    def has_permission(self, request, view):
        """Check if user is a doctor or radiology tech."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['DOCTOR', 'RADIOLOGY_TECH']
