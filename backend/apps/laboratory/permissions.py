"""
Lab Order Permissions - strict role enforcement.

Per EMR Rules:
- Doctor: Can create orders, view all (including results)
- Lab Tech: Can only update results, cannot create orders
- No role overlap allowed
"""
from rest_framework import permissions


class IsDoctorOrLabTech(permissions.BasePermission):
    """
    Permission class for lab order endpoints.
    Allows both Doctor and Lab Tech, but with different actions.
    """
    
    def has_permission(self, request, view):
        """Check if user is a doctor or lab tech."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['DOCTOR', 'LAB_TECH']


class CanCreateLabOrder(permissions.BasePermission):
    """
    Permission: Only doctors can create lab orders.
    Lab Tech and Nurse cannot create orders.
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
                detail="Nurses are not permitted to create lab orders. "
                       "This action requires Doctor role.",
                code='nurse_prohibited'
            )
        
        return user_role == 'DOCTOR'


class CanUpdateLabResult(permissions.BasePermission):
    """
    Permission: Only Lab Tech can update lab results.
    Doctor cannot update results (only view).
    """
    
    def has_permission(self, request, view):
        """Check if user is a lab tech."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'LAB_TECH'


class CanViewLabOrder(permissions.BasePermission):
    """
    Permission: Doctor can view all fields, Lab Tech can view limited fields.
    """
    
    def has_permission(self, request, view):
        """Check if user is a doctor or lab tech."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['DOCTOR', 'LAB_TECH']
