"""
Telemedicine Permissions.

Per EMR Rules:
- Doctor: Can create and manage telemedicine sessions
- Patient access: Via visit context
- All sessions must be visit-scoped
"""
from rest_framework import permissions


class CanManageTelemedicine(permissions.BasePermission):
    """
    Permission: Only Doctors can create and manage telemedicine sessions.
    """
    
    def has_permission(self, request, view):
        """Check if user is a doctor."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'DOCTOR'


class CanJoinTelemedicineSession(permissions.BasePermission):
    """
    Permission: Doctor or patient can join their own telemedicine session.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user can join this session."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Doctor can join if they are the assigned doctor
        if user_role == 'DOCTOR':
            return obj.doctor == request.user
        
        # Patient can join if they are the patient for this session's visit
        if user_role == 'PATIENT':
            # Get patient from user
            try:
                from apps.patients.models import Patient
                patient = Patient.objects.get(user=request.user, is_active=True)
                # Check if this session's patient matches the logged-in patient
                return obj.patient == patient
            except Patient.DoesNotExist:
                return False
        
        return False
