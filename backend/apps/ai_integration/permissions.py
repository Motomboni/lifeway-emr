"""
Permissions for AI Integration app.

Per EMR Rules:
- Doctor-only access for clinical AI features
- Visit-scoped access control
"""
from rest_framework import permissions
from core.permissions import IsDoctor


class IsDoctorForAI(IsDoctor):
    """
    Permission class for AI clinical features.
    
    Only doctors can use AI clinical features.
    """
    pass
