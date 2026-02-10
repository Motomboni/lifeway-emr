"""
Permissions for Lab Test Catalog.
"""
from rest_framework.permissions import BasePermission


class CanManageLabTestCatalog(BasePermission):
    """Permission to manage lab test catalog (Doctors and Lab Techs)."""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # Doctors and Lab Techs can manage the catalog
        return user_role in ['DOCTOR', 'LAB_TECH']


class CanViewLabTestCatalog(BasePermission):
    """Permission to view lab test catalog (All authenticated users)."""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
