"""
Prescription Permissions - strict role enforcement.

Per EMR Rules:
- Doctor: Can create prescriptions, view all
- Pharmacist: Can only dispense, cannot create prescriptions
- No role overlap allowed
"""
from rest_framework import permissions


class IsDoctor(permissions.BasePermission):
    """
    Permission: Only doctors can create prescriptions.
    Nurse explicitly denied.
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
                detail="Nurses are not permitted to create prescriptions. "
                       "This action requires Doctor role.",
                code='nurse_prohibited'
            )
        
        return user_role == 'DOCTOR'


class CanViewPrescription(permissions.BasePermission):
    """
    Permission: Doctor and Pharmacist can view prescriptions (with different fields).
    """
    
    def has_permission(self, request, view):
        """Check if user is a doctor or pharmacist."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['DOCTOR', 'PHARMACIST']


class CanDispensePrescription(permissions.BasePermission):
    """
    Permission: Only Pharmacist can dispense prescriptions.
    Doctor cannot dispense (only view).
    """
    
    def has_permission(self, request, view):
        """Check if user is a pharmacist."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'PHARMACIST'


class CanManageDrugs(permissions.BasePermission):
    """
    Permission: Only Pharmacist can create and manage drugs.
    """
    
    def has_permission(self, request, view):
        """Check if user is a pharmacist."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'PHARMACIST'
