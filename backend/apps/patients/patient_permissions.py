"""
Patient Portal RBAC - Role-Based Access Control

Custom permission classes for patient portal access.
Ensures PATIENT role users can only access their own data.

Per EMR Rules:
- PATIENT role users can only view their own records
- PATIENT role users cannot access other patients' data
- All access attempts are logged for security audit
"""
from rest_framework import permissions
import logging

logger = logging.getLogger(__name__)


class IsPatientOwner(permissions.BasePermission):
    """
    Permission class for patient-scoped access control.
    
    Rules:
    - PATIENT role users can only access their own data
    - Compares request.user.patient.id to object.patient.id
    - Works for any model with a 'patient' foreign key
    - Non-PATIENT roles pass through (handled by other permissions)
    
    Usage:
        class VisitViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, IsPatientOwner]
    
    Compatible Models:
    - Visit (visit.patient)
    - Prescription (prescription.patient via visit)
    - LabOrder (laborder.patient via visit)
    - RadiologyOrder (radiologyorder.patient via visit)
    - Bill/Payment (bill.patient via visit)
    - Appointment (appointment.patient)
    """
    
    def has_permission(self, request, view):
        """
        Check if user has general permission to access this view.
        
        For PATIENT role:
        - Allow list/retrieve actions (object-level check happens in has_object_permission)
        - Deny create/update/delete actions (patients are read-only)
        
        For other roles:
        - Pass through (let other permission classes decide)
        """
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get user role
        user_role = getattr(request.user, 'role', None)
        
        # If user is PATIENT role
        if user_role == 'PATIENT':
            # PATIENT users must have a linked patient record
            if not hasattr(request.user, 'patient') or not request.user.patient:
                logger.warning(
                    f"PATIENT role user {request.user.username} has no linked patient record"
                )
                return False
            
            # PATIENT role is read-only
            # Allow: GET (list, retrieve), HEAD, OPTIONS
            # Deny: POST (create), PUT/PATCH (update), DELETE (destroy)
            if request.method in permissions.SAFE_METHODS:
                return True
            else:
                logger.warning(
                    f"PATIENT user {request.user.username} attempted {request.method} "
                    f"on {view.__class__.__name__}"
                )
                return False
        
        # For non-PATIENT roles, pass through
        # (other permission classes will handle authorization)
        return True
    
    def has_object_permission(self, request, view, obj):
        """
        Check if user has permission to access this specific object.
        
        For PATIENT role:
        - Compare request.user.patient.id to object.patient.id
        - Only allow if they match (user's own data)
        
        For other roles:
        - Pass through (let other permission classes decide)
        """
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Get user role
        user_role = getattr(request.user, 'role', None)
        
        # If user is not PATIENT, pass through
        if user_role != 'PATIENT':
            return True
        
        # For PATIENT users, enforce patient-scoped access
        # User must have a linked patient
        if not hasattr(request.user, 'patient') or not request.user.patient:
            logger.warning(
                f"PATIENT user {request.user.username} has no linked patient"
            )
            return False
        
        user_patient_id = request.user.patient.id
        
        # Get patient from object
        object_patient_id = self._get_patient_id_from_object(obj)
        
        if object_patient_id is None:
            logger.error(
                f"Could not determine patient_id from object {obj.__class__.__name__} "
                f"for PATIENT user {request.user.username}"
            )
            return False
        
        # Compare patient IDs
        if user_patient_id == object_patient_id:
            # User is accessing their own data
            return True
        else:
            # User is trying to access another patient's data
            logger.warning(
                f"PATIENT user {request.user.username} (patient_id={user_patient_id}) "
                f"attempted to access object with patient_id={object_patient_id}"
            )
            return False
    
    def _get_patient_id_from_object(self, obj):
        """
        Extract patient_id from object.
        
        Supports multiple model types:
        - Direct: obj.patient.id (Visit, Appointment, Patient)
        - Via visit: obj.visit.patient.id (Prescription, LabOrder, RadiologyOrder)
        - Via bill: obj.visit.patient.id (Payment, Charge)
        
        Returns:
            patient_id (int) or None if cannot determine
        """
        # Direct patient attribute
        if hasattr(obj, 'patient') and obj.patient:
            return obj.patient.id
        
        # Via visit attribute (common for clinical models)
        if hasattr(obj, 'visit') and obj.visit:
            if hasattr(obj.visit, 'patient') and obj.visit.patient:
                return obj.visit.patient.id
        
        # Object is Patient itself
        if obj.__class__.__name__ == 'Patient':
            return obj.id
        
        # Could not determine patient
        return None


class IsPatientOwnerOrStaff(permissions.BasePermission):
    """
    Permission class that allows:
    - PATIENT role: Only their own data (read-only)
    - Staff (DOCTOR, NURSE, etc.): All data (read/write based on other permissions)
    
    Use this when you want staff to have full access but patients to be restricted.
    
    Usage:
        class PrescriptionViewSet(viewsets.ModelViewSet):
            permission_classes = [IsAuthenticated, IsPatientOwnerOrStaff]
    """
    
    def has_permission(self, request, view):
        """General permission check."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        
        # PATIENT role: read-only, must have linked patient
        if user_role == 'PATIENT':
            if not hasattr(request.user, 'patient') or not request.user.patient:
                return False
            return request.method in permissions.READONLY_METHODS
        
        # Staff roles: pass through
        return True
    
    def has_object_permission(self, request, view, obj):
        """Object-level permission check."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        
        # Staff roles: allow all access
        if user_role != 'PATIENT':
            return True
        
        # PATIENT role: check ownership
        if not hasattr(request.user, 'patient') or not request.user.patient:
            return False
        
        user_patient_id = request.user.patient.id
        
        # Get patient from object
        if hasattr(obj, 'patient') and obj.patient:
            return obj.patient.id == user_patient_id
        
        if hasattr(obj, 'visit') and obj.visit and hasattr(obj.visit, 'patient'):
            return obj.visit.patient.id == user_patient_id
        
        if obj.__class__.__name__ == 'Patient':
            return obj.id == user_patient_id
        
        return False


class PatientPortalAccess(permissions.BasePermission):
    """
    Specific permission for patient portal endpoints.
    
    Enforces:
    - User must be authenticated
    - User must have PATIENT role
    - User must have linked patient record
    
    Use for patient portal-specific views/viewsets.
    
    Usage:
        class PatientPortalDashboardView(APIView):
            permission_classes = [PatientPortalAccess]
    """
    
    message = "Access denied. Patient portal access requires a verified patient account."
    
    def has_permission(self, request, view):
        """Check if user can access patient portal."""
        # Must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must have PATIENT role
        user_role = getattr(request.user, 'role', None)
        if user_role != 'PATIENT':
            self.message = "Access denied. Only patient accounts can access the patient portal."
            return False
        
        # Must have linked patient record
        if not hasattr(request.user, 'patient') or not request.user.patient:
            self.message = "Access denied. No patient record linked to this account."
            return False
        
        # Optional: Check if patient account is verified
        patient = request.user.patient
        if hasattr(patient, 'is_verified') and not patient.is_verified:
            self.message = "Access denied. Your patient account is pending verification."
            logger.warning(f"Unverified patient {patient.id} attempted portal access")
            return False
        
        return True


class IsPatientOrStaffReadOnly(permissions.BasePermission):
    """
    Permission that allows:
    - PATIENT: Read-only access to their own data
    - Staff: Read-only access to all data
    
    Use for sensitive data that should be read-only even for staff.
    
    Usage:
        class MedicalHistoryViewSet(viewsets.ReadOnlyModelViewSet):
            permission_classes = [IsPatientOrStaffReadOnly]
    """
    
    def has_permission(self, request, view):
        """General permission - allow read-only."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Only allow read methods
        if request.method not in permissions.SAFE_METHODS:
            return False
        
        # PATIENT must have linked patient
        user_role = getattr(request.user, 'role', None)
        if user_role == 'PATIENT':
            return hasattr(request.user, 'patient') and request.user.patient is not None
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Object-level permission - PATIENT sees only their data."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        
        # Staff can read all
        if user_role != 'PATIENT':
            return True
        
        # PATIENT can only read their own
        if not hasattr(request.user, 'patient'):
            return False
        
        user_patient_id = request.user.patient.id
        
        # Check patient match
        if hasattr(obj, 'patient') and obj.patient:
            return obj.patient.id == user_patient_id
        
        if hasattr(obj, 'visit') and obj.visit and hasattr(obj.visit, 'patient'):
            return obj.visit.patient.id == user_patient_id
        
        if obj.__class__.__name__ == 'Patient':
            return obj.id == user_patient_id
        
        return False


# Utility function for filtering querysets by patient
def filter_queryset_for_patient(queryset, user):
    """
    Filter queryset to only include records for a specific patient.
    
    Use in ViewSet.get_queryset() to automatically filter for PATIENT users.
    
    Args:
        queryset: Django QuerySet to filter
        user: Request user
    
    Returns:
        Filtered queryset for PATIENT users, original queryset for others
    
    Example:
        def get_queryset(self):
            queryset = Visit.objects.all()
            return filter_queryset_for_patient(queryset, self.request.user)
    """
    # Only filter for PATIENT role
    user_role = getattr(user, 'role', None)
    if user_role != 'PATIENT':
        return queryset
    
    # User must have linked patient
    if not hasattr(user, 'patient') or not user.patient:
        return queryset.none()
    
    patient_id = user.patient.id
    
    # Determine how to filter based on model
    model_name = queryset.model.__name__
    
    # Direct patient relationship
    if hasattr(queryset.model, 'patient'):
        return queryset.filter(patient_id=patient_id)
    
    # Via visit relationship
    if hasattr(queryset.model, 'visit'):
        return queryset.filter(visit__patient_id=patient_id)
    
    # Model is Patient itself
    if model_name == 'Patient':
        return queryset.filter(id=patient_id)
    
    # Could not determine - deny all (safe default)
    logger.warning(
        f"Could not determine patient filter for model {model_name} "
        f"for PATIENT user {user.username}"
    )
    return queryset.none()
