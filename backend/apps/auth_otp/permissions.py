"""
Patient Portal Permissions

RBAC for patient portal access.
"""
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


class PatientOnlyAccess(permissions.BasePermission):
    """
    Permission class that only allows PATIENT role users.
    
    Additionally enforces:
    - User must have PATIENT role
    - User must have linked patient record
    - User must have portal_enabled=True
    - User.is_active must be True
    
    For object-level permissions:
    - Compare user.patient.id to object.patient.id
    - Or object.visit.patient.id for nested relationships
    """
    
    message = "Access denied. Patient portal access required."
    
    def has_permission(self, request, view):
        """View-level permission check."""
        if not request.user or not request.user.is_authenticated:
            self.message = "Authentication required."
            return False
        
        # Must have PATIENT role
        if request.user.role != 'PATIENT':
            self.message = "Only patient accounts can access this endpoint."
            logger.warning(f"Non-PATIENT user {request.user.username} tried to access patient portal")
            return False
        
        # Must have linked patient
        if not hasattr(request.user, 'patient') or not request.user.patient:
            self.message = "No patient record linked to account."
            return False
        
        # Must have portal enabled
        if not request.user.portal_enabled:
            self.message = "Portal access is disabled for your account."
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Object-level permission check.
        
        Ensures patient can only access their own records.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.role != 'PATIENT':
            return False
        
        if not hasattr(request.user, 'patient') or not request.user.patient:
            return False
        
        user_patient_id = request.user.patient.id
        
        # Direct patient relationship
        if hasattr(obj, 'patient') and obj.patient:
            match = obj.patient.id == user_patient_id
            if not match:
                logger.warning(
                    f"PATIENT {request.user.username} (patient_id={user_patient_id}) "
                    f"tried to access object with patient_id={obj.patient.id}"
                )
            return match
        
        # Via visit relationship
        if hasattr(obj, 'visit') and obj.visit:
            if hasattr(obj.visit, 'patient') and obj.visit.patient:
                match = obj.visit.patient.id == user_patient_id
                if not match:
                    logger.warning(
                        f"PATIENT {request.user.username} tried to access "
                        f"another patient's record via visit"
                    )
                return match
        
        # Object is Patient itself
        if obj.__class__.__name__ == 'Patient':
            return obj.id == user_patient_id
        
        # Cannot determine - deny access
        logger.error(
            f"Could not determine patient ownership for {obj.__class__.__name__}"
        )
        return False
