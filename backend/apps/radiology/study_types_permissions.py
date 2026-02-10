"""
Permissions for Radiology Study Types Catalog.
"""
from rest_framework.permissions import BasePermission


class CanManageRadiologyStudyTypes(BasePermission):
    """Permission to manage radiology study types catalog (Doctors and Radiology Techs)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # Doctors and Radiology Techs can manage the catalog
        return user_role in ['DOCTOR', 'RADIOLOGY_TECH']


class CanViewRadiologyStudyTypes(BasePermission):
    """Permission to view radiology study types catalog (All authenticated users)."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
