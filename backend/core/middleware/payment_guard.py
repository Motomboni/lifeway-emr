"""
PaymentClearedGuard middleware - enforces payment must be cleared for clinical actions.

Per EMR Rules:
- Payment must be CLEARED before clinical actions
- Enforced at middleware level
- Payment endpoints are excluded (users need to access payments to clear them)
- Receptionists can access visit details to process payments
"""
from rest_framework.exceptions import PermissionDenied
from django.http import JsonResponse


class PaymentClearedGuard:
    """
    Middleware to enforce payment clearance for clinical actions.
    
    Requires VisitLookupMiddleware to set request.visit.
    
    Rules:
    - Receptionists can access visit details regardless of payment status (to process payments)
    - Payment/billing endpoints are always accessible
    - Visit retrieve/list endpoints are accessible (needed to view visit details)
    - Only clinical action endpoints are blocked when payment is PENDING
    """
    
    # Endpoints that should be accessible even when payment is PENDING
    # These are payment-related endpoints that users need to access to clear payment
    EXCLUDED_PATHS = [
        '/payments/',  # Payment CRUD endpoints
        '/billing/',   # Billing endpoints
        '/payment-intents/',  # Paystack payment intents
        '/insurance/',  # Insurance endpoints
    ]
    
    # Clinical action endpoints that require payment to be cleared
    CLINICAL_ACTION_PATHS = [
        '/consultation/',
        '/laboratory/',
        '/radiology/',
        '/prescriptions/',
        '/pharmacy/dispense/',
        '/vitals/',
        '/nursing-notes/',
        '/medication-administration/',
        '/lab-samples/',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response

    def _is_receptionist(self, request):
        """Check if the user is a Receptionist."""
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            # Try method if field doesn't exist
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        return user_role == 'RECEPTIONIST'
    
    def _is_visit_retrieve_or_list(self, path):
        """Check if this is a visit retrieve or list endpoint."""
        # Pattern: /api/v1/visits/{id}/ or /api/v1/visits/
        # Should match /visits/{id}/ (retrieve) or /visits/ (list)
        import re
        # Match /visits/{id}/ (exact match, no sub-path)
        if re.match(r'.*/visits/\d+/$', path):
            return True
        # Match /visits/ (list endpoint)
        if re.match(r'.*/visits/$', path):
            return True
        return False
    
    def _is_clinical_action(self, path):
        """Check if this is a clinical action endpoint."""
        return any(
            clinical_path in path for clinical_path in self.CLINICAL_ACTION_PATHS
        )
    
    def _is_payment_endpoint(self, path):
        """Check if this is a payment/billing endpoint."""
        return any(
            excluded_path in path for excluded_path in self.EXCLUDED_PATHS
        )

    def __call__(self, request):
        visit = getattr(request, 'visit', None)
        if visit:
            # Refresh visit and bill from database to ensure we have latest payment status
            # This is important because bill status might have been updated in a recent transaction
            try:
                visit.refresh_from_db()
                # Also refresh the bill if it exists
                if hasattr(visit, 'bill') and visit.bill:
                    visit.bill.refresh_from_db()
            except Exception:
                # If refresh fails, continue with existing visit instance
                pass
        
        # If visit has INSURANCE_PENDING but approved insurance exists, sync payment_status so clinical actions are allowed
        if visit and getattr(visit, 'payment_status', None) == 'INSURANCE_PENDING':
            try:
                from apps.billing.insurance_models import VisitInsurance
                if VisitInsurance.objects.filter(visit_id=visit.pk, approval_status='APPROVED').exists():
                    visit.__class__.objects.filter(pk=visit.pk).update(payment_status='SETTLED')
                    visit.payment_status = 'SETTLED'
            except Exception:
                pass
        
        if visit and not visit.is_payment_cleared():
            path = getattr(request, 'path', '')
            
            # Always allow Receptionists to access visit details (they need to process payments)
            if self._is_receptionist(request):
                # Receptionists can access visit details and billing endpoints
                if self._is_visit_retrieve_or_list(path) or self._is_payment_endpoint(path):
                    return self.get_response(request)
                # But still block clinical actions for Receptionists
                if self._is_clinical_action(path):
                    return JsonResponse(
                        {'detail': 'Receptionists cannot perform clinical actions. '
                                  'Payment must be cleared and clinical actions must be performed by authorized clinical staff.'},
                        status=403
                    )
            
            # Allow access to payment/billing endpoints (all users need this to clear payment)
            if self._is_payment_endpoint(path):
                return self.get_response(request)
            
            # Allow access to visit retrieve/list endpoints (needed to view visit details)
            if self._is_visit_retrieve_or_list(path):
                return self.get_response(request)
            
            # Block access to clinical action endpoints when payment is PENDING
            if self._is_clinical_action(path):
                # Allow GET requests (read-only) for prescriptions - pharmacists need to view them
                # Block POST/PUT/PATCH (create/update) - these require payment clearance
                if '/prescriptions/' in path and request.method == 'GET':
                    # Allow read-only access to prescriptions even when payment is pending
                    # This allows pharmacists to view prescriptions for dispensation planning
                    # The view-level permissions will still enforce role-based access
                    return self.get_response(request)
                
                # Check if this is an API request (DRF)
                if hasattr(request, 'path') and '/api/' in request.path:
                    # Return proper JSON response for API requests
                    return JsonResponse(
                        {'detail': 'Payment must be cleared before consultation. '
                                  f'Current payment status: {visit.payment_status}'},
                        status=403
                    )
                else:
                    # For non-API requests, raise exception (will be handled by Django)
                    raise PermissionDenied('Payment not cleared for this visit')
        
        return self.get_response(request)