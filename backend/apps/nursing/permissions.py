"""
Nursing Permissions - strict role enforcement.

Per EMR Rules:
- Nurse: Can create nursing notes, medication administration, lab sample collection
- All records are visit-scoped
- No diagnosis fields allowed
- Records are immutable after creation
- Visit must be OPEN (ACTIVE) - returns 409 Conflict if closed
- Visit payment must be CLEARED
"""
from rest_framework import permissions
from rest_framework.permissions import BasePermission
from rest_framework import status
from rest_framework.response import Response


class IsNurse(BasePermission):
    """
    Permission: Only Nurses can create nursing records.
    """
    
    def has_permission(self, request, view):
        """Check if user is a nurse."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'NURSE'


class CanViewNursingRecords(BasePermission):
    """
    Permission: Doctor and Nurse can view nursing records.
    """
    
    def has_permission(self, request, view):
        """Check if user can view nursing records."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read operations only
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['DOCTOR', 'NURSE']


class IsVisitActiveAndPaid(BasePermission):
    """
    Permission: Visit must be OPEN (ACTIVE) and payment must be CLEARED.
    Returns 409 Conflict for closed visits.
    """
    
    def has_permission(self, request, view):
        """Check if visit is OPEN and payment is cleared."""
        from rest_framework.exceptions import APIException
        
        visit = getattr(request, 'visit', None)
        if not visit:
            return False
        
        # Check if visit is closed - return 409 Conflict
        if visit.status == 'CLOSED':
            from rest_framework.exceptions import APIException
            exception = APIException(
                detail="Cannot perform action on a CLOSED visit. Closed visits are immutable.",
                code='visit_closed'
            )
            exception.status_code = status.HTTP_409_CONFLICT
            raise exception
        
        # Check if visit is OPEN (ACTIVE)
        if visit.status != 'OPEN':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                detail=f"Visit must be OPEN (ACTIVE) to perform this action. Current status: {visit.status}",
                code='visit_not_active'
            )
        
        # Check if payment is cleared
        if not visit.is_payment_cleared():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                detail=f"Payment must be cleared before performing this action. Current payment status: {visit.payment_status}",
                code='payment_not_cleared'
            )
        
        return True

