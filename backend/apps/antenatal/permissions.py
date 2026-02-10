"""
Antenatal Module Permissions

Role-based access control for antenatal clinic management.
Antenatal care is accessible to:
- DOCTOR: Full access to create and manage antenatal records
- NURSE: Can view and record antenatal visits, vitals, medications
- ADMIN: Full access for oversight
"""
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class CanManageAntenatalRecords(permissions.BasePermission):
    """
    Permission class for managing antenatal records.
    
    Allows:
    - DOCTOR: Full access to create and manage antenatal records
    - ADMIN: Full access
    - NURSE: Read-only access
    
    Denies:
    - All other roles
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Admin always has access
        if user_role == 'ADMIN':
            return True
        
        # Doctor has full access
        if user_role == 'DOCTOR':
            return True
        
        # Nurse has read-only access
        if user_role == 'NURSE':
            return request.method in permissions.SAFE_METHODS
        
        # Deny all others
        return False


class CanRecordAntenatalVisits(permissions.BasePermission):
    """
    Permission for recording antenatal visits.
    
    Allows:
    - DOCTOR: Full access
    - NURSE: Can record visits and vitals
    - ADMIN: Full access
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Full access roles
        if user_role in ['ADMIN', 'DOCTOR', 'NURSE']:
            return True
        
        return False


class CanManageAntenatalOutcomes(permissions.BasePermission):
    """
    Permission for recording delivery outcomes.
    
    Requires DOCTOR or ADMIN role.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Only Doctor and Admin can record outcomes
        if user_role in ['ADMIN', 'DOCTOR']:
            return True
        
        # Others have read-only access
        if user_role == 'NURSE':
            return request.method in permissions.SAFE_METHODS
        
        return False
