"""
Appointment Permissions - role-based access control.

Per EMR Rules:
- Receptionist: Can create/manage all appointments
- Doctor: Can create appointments (with themselves as doctor) and view their own appointments, update status/notes
"""
from rest_framework import permissions


class CanManageAppointments(permissions.BasePermission):
    """
    Permission for managing appointments.
    
    Receptionist: Full access (create, update, delete)
    Doctor/IVF_SPECIALIST: Can create appointments and view their own appointments, update status/notes
    Admin: Full access
    """
    
    def has_permission(self, request, view):
        """Check if user has permission for the action."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Receptionist, Doctor, Admin, and IVF staff can access appointments
        return user_role in [
            'RECEPTIONIST', 'DOCTOR', 'ADMIN',
            'IVF_SPECIALIST', 'EMBRYOLOGIST', 'NURSE'
        ]
    
    def has_object_permission(self, request, view, obj):
        """Check if user can perform action on specific appointment."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Receptionist and Admin: Full access
        if user_role in ['RECEPTIONIST', 'ADMIN']:
            return True
        
        # Doctor/IVF_SPECIALIST: Can only access their own appointments
        if user_role in ['DOCTOR', 'IVF_SPECIALIST']:
            return obj.doctor_id == request.user.id
        
        # Nurse/Embryologist: Read-only access
        if user_role in ['NURSE', 'EMBRYOLOGIST']:
            return request.method in permissions.SAFE_METHODS
        
        return False


class CanCreateAppointments(permissions.BasePermission):
    """
    Permission for creating appointments.
    
    Receptionist, Doctor, Admin, and IVF Specialist can create appointments.
    """
    
    def has_permission(self, request, view):
        """Check if user can create appointments."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['RECEPTIONIST', 'DOCTOR', 'ADMIN', 'IVF_SPECIALIST']
