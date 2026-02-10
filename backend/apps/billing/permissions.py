"""
Payment Permissions - Receptionist can process payments.

Per EMR Rules:
- Receptionist: Can process payments
- Other roles: Can view payment information (read-only)
"""
from rest_framework import permissions


class CanProcessPayment(permissions.BasePermission):
    """
    Permission: Only Receptionist can process payments.
    """
    
    def has_permission(self, request, view):
        """Check if user is a receptionist."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'RECEPTIONIST'


class CanAddServicesFromCatalog(permissions.BasePermission):
    """
    Permission: Receptionist and Doctor can add services from catalog to bills.
    
    Per EMR Rules:
    - Receptionist: Can add services from catalog (billing workflow)
    - Doctor: Can order services from catalog (clinical workflow)
    - Both roles can add services, which will reflect in patient's account
    """
    
    def has_permission(self, request, view):
        """Check if user is a receptionist or doctor."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['RECEPTIONIST', 'DOCTOR']