"""
Permissions for clinical features.
"""
from rest_framework import permissions
from rest_framework.permissions import BasePermission


class CanRecordVitalSigns(BasePermission):
    """Permission to record vital signs (Doctors and Nurses)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # Doctors and Nurses can create/modify vital signs
        # For read operations, allow all authenticated clinical users
        if view.action in ['list', 'retrieve']:
            # Allow all authenticated users to view vital signs
            return user_role in ['DOCTOR', 'NURSE', 'RECEPTIONIST', 'LAB_TECH', 'PHARMACIST', 'RADIOLOGY_TECH']
        
        # For create/update/delete, only Doctors and Nurses
        return user_role in ['DOCTOR', 'NURSE']


class CanManageTemplates(BasePermission):
    """Permission to manage clinical templates (Doctors only)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'DOCTOR'


class CanViewAlerts(BasePermission):
    """Permission to view clinical alerts (All authenticated users)."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class CanAcknowledgeAlerts(BasePermission):
    """Permission to acknowledge alerts (Doctors only)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'DOCTOR'


class CanManageOperationNotes(BasePermission):
    """Permission to manage operation notes (Doctors only)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # For read operations, allow all authenticated clinical users
        if view.action in ['list', 'retrieve']:
            return user_role in ['DOCTOR', 'NURSE', 'ADMIN']
        
        # For create/update/delete, only Doctors
        return user_role == 'DOCTOR'
