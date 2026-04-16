"""
Role-based permissions for EMR system.

Per EMR rules:
- Doctor → Consultation, Orders, Prescriptions
- Nurse → Vital Signs, Nursing Notes, Medication Administration (from existing prescriptions), Lab Sample Collection (from existing orders)
- Lab Tech → Lab results ONLY
- Radiology Tech → Imaging results ONLY
- Pharmacist → Dispense ONLY
- Receptionist → Registration, Payment ONLY

Nurse STRICT prohibitions:
- Diagnosis creation/editing
- Prescriptions creation
- Lab/Radiology orders creation
- Lab/Radiology results entry
- Visit closure/discharge
- Billing/payments
- Editing doctor consultation notes
"""
from rest_framework import permissions


class IsDoctor(permissions.BasePermission):
    """
    Permission class to ensure only doctors can access consultation endpoints.
    
    Explicitly denies Nurse and all other roles.
    Assumes User model has a 'role' field or method that returns 'DOCTOR'.
    """
    
    def has_permission(self, request, view):
        """Check if user is a doctor. Explicitly deny Nurse."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get user role (assumes role field or get_role method)
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            # Try method if field doesn't exist
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Explicit guard: Deny Nurse explicitly
        if user_role == 'NURSE':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                detail="Nurses are not permitted to perform this action. "
                       "This action requires Doctor role.",
                code='nurse_prohibited'
            )
        
        return user_role == 'DOCTOR'


class IsVisitOpen(permissions.BasePermission):
    """
    Permission class to ensure visit is OPEN before allowing mutations.
    
    This should be used in conjunction with visit lookup middleware.
    For read operations, use IsVisitAccessible instead.
    """
    
    def has_permission(self, request, view):
        """Check if visit exists and is OPEN."""
        from rest_framework.exceptions import PermissionDenied
        
        visit = getattr(request, 'visit', None)
        if not visit:
            return False
        
        if visit.status != 'OPEN':
            raise PermissionDenied(
                detail="Cannot create or modify consultation for a CLOSED visit. "
                       "Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
        
        return True


class IsVisitAccessible(permissions.BasePermission):
    """
    Permission class to ensure visit exists and is accessible.
    
    Allows reads on both OPEN and CLOSED visits (read-only access for closed).
    Used for read operations where closed visits should be accessible.
    """
    
    def has_permission(self, request, view):
        """Check if visit exists (OPEN or CLOSED)."""
        # Try to get visit from request (set by get_visit() in viewset)
        visit = getattr(request, 'visit', None)
        
        # If not on request, try to get from view kwargs (for nested viewsets)
        if not visit:
            visit_id = view.kwargs.get('visit_id')
            if visit_id:
                try:
                    from apps.visits.models import Visit
                    visit = Visit.objects.get(pk=visit_id)
                except Visit.DoesNotExist:
                    return False
        
        if not visit:
            return False
        
        # Allow access to both OPEN and CLOSED visits
        return visit.status in ['OPEN', 'CLOSED']


class IsPaymentCleared(permissions.BasePermission):
    """
    Permission class to ensure payment is cleared before clinical actions.
    
    This should be used in conjunction with payment guard middleware.
    For read operations, payment check may not be required.
    """
    
    def has_permission(self, request, view):
        """Check if visit payment is cleared."""
        from rest_framework.exceptions import PermissionDenied
        
        visit = getattr(request, 'visit', None)
        if not visit:
            return False
        try:
            visit.refresh_from_db()
        except Exception:
            pass
        
        if not visit.is_payment_cleared():
            raise PermissionDenied(
                detail="Payment must be cleared before this clinical action. "
                       f"Current payment status: {visit.payment_status}",
                code='payment_not_cleared'
            )
        
        return True


class IsRegistrationPaymentCleared(permissions.BasePermission):
    """
    Kept for backwards compatibility with older URL/view wiring.

    Consultation and related clinical flows are not gated on registration payment.
    """

    def has_permission(self, request, view):
        return True


class IsConsultationPaymentCleared(permissions.BasePermission):
    """
    Kept for backwards compatibility with older URL/view wiring.

    Consultation is not gated on consultation-line-item payment.
    """

    def has_permission(self, request, view):
        return True


class IsNurse(permissions.BasePermission):
    """
    Permission class to ensure user is a Nurse.
    
    Used for operations explicitly allowed for Nurses.
    Default behavior: DENY-ALL unless explicitly allowed.
    """
    
    def has_permission(self, request, view):
        """Check if user is a nurse."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'NURSE'


class DenyNurse(permissions.BasePermission):
    """
    Permission class to explicitly deny Nurse access.
    
    Used to prevent privilege escalation and enforce strict role boundaries.
    This should be combined with other permission classes using AND logic.
    """
    
    def has_permission(self, request, view):
        """Explicitly deny if user is a nurse."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Explicitly deny Nurse
        if user_role == 'NURSE':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                detail="Nurses are not permitted to perform this action. "
                       "This action requires a different role.",
                code='nurse_prohibited'
            )
        
        return True


class IsStaffOrAdminRole(permissions.BasePermission):
    """
    Allow access if user is staff (is_staff) OR has role ADMIN.
    Used for admin-only endpoints (e.g. Revenue Leak Dashboard, Service Catalog write).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'is_staff', False):
            return True
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        return user_role == 'ADMIN'


class CanViewVisits(permissions.BasePermission):
    """
    Permission to view visits (read-only).
    
    Allows: Doctor, Nurse, Receptionist, and other clinical staff.
    """
    
    def has_permission(self, request, view):
        """Check if user can view visits."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read operations only
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Allow read access for clinical and administrative roles
        return user_role in [
            'DOCTOR', 'NURSE', 'RECEPTIONIST', 
            'LAB_TECH', 'RADIOLOGY_TECH', 'PHARMACIST'
        ]


class CanViewAppointments(permissions.BasePermission):
    """
    Permission to view appointments (read-only).
    
    Allows: Doctor, Nurse, Receptionist.
    """
    
    def has_permission(self, request, view):
        """Check if user can view appointments."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Read operations only
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role in ['DOCTOR', 'NURSE', 'RECEPTIONIST']


class IsGOPDConsultationAccessible(permissions.BasePermission):
    """
    Permission class for GOPD Consultation workflow driven by ServiceCatalog.
    
    Rules:
    - Consultation access is not blocked by payment status
    - Consultation status and doctor assignment are enforced
    - CLOSED consultations: Read-only access
    """
    
    def has_permission(self, request, view):
        """Check if doctor can access consultation based on ServiceCatalog workflow."""
        from rest_framework.exceptions import PermissionDenied
        
        visit = getattr(request, 'visit', None)
        if not visit:
            return False
        try:
            visit.refresh_from_db()
        except Exception:
            pass
        
        # Get consultation if it exists
        from apps.consultations.models import Consultation
        consultation = Consultation.objects.filter(visit=visit).first()
        
        # If no consultation exists, allow creation path
        if not consultation:
            return True
        
        # Consultation exists - check status and payment
        if consultation.status == 'CLOSED':
            # Closed consultations are read-only
            return request.method in permissions.SAFE_METHODS
        
        if consultation.status == 'PENDING':
            # PENDING consultations can be activated/accessed per workflow.
            return True
        
        if consultation.status == 'ACTIVE':
            # ACTIVE consultations - check doctor assignment
            if consultation.created_by and consultation.created_by != request.user:
                raise PermissionDenied(
                    detail="Only the assigned doctor can access this consultation.",
                    code='doctor_not_assigned'
                )
            return True
        
        return False