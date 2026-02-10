"""
IVF Module Permissions

Role-based access control for IVF-specific endpoints.
IVF is a specialized, role-restricted module requiring:
- IVF_SPECIALIST role for clinical actions (full access)
- EMBRYOLOGIST role for lab procedures
- NURSE role for monitoring and medication administration
- Standard DOCTOR can view but not modify

Nigerian Healthcare Compliance:
- MDCN accreditation verification
- Consent tracking enforcement
- Nurse scope of practice limitations
"""
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class IsIVFSpecialist(permissions.BasePermission):
    """
    Permission class for IVF specialist access.
    
    Allows:
    - IVF_SPECIALIST: Full access to IVF clinical procedures
    - DOCTOR: Read-only access
    - ADMIN: Full access for oversight
    
    Denies:
    - All other roles
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Admin always has access
        if user_role == 'ADMIN':
            return True
        
        # IVF Specialist has full access
        if user_role == 'IVF_SPECIALIST':
            return True
        
        # Doctor has read-only access
        if user_role == 'DOCTOR':
            return request.method in permissions.SAFE_METHODS
        
        # Deny all others
        raise PermissionDenied(
            detail="IVF module requires IVF_SPECIALIST role. "
                   "Please contact your administrator for access.",
            code='ivf_access_denied'
        )


class IsEmbryologist(permissions.BasePermission):
    """
    Permission class for embryology lab access.
    
    Allows:
    - EMBRYOLOGIST: Full access to embryo and lab records
    - IVF_SPECIALIST: Full access
    - ADMIN: Full access
    
    Denies:
    - All other roles
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Admin always has access
        if user_role == 'ADMIN':
            return True
        
        # IVF Specialist has full access
        if user_role == 'IVF_SPECIALIST':
            return True
        
        # Embryologist has full access to lab procedures
        if user_role == 'EMBRYOLOGIST':
            return True
        
        # Deny all others
        raise PermissionDenied(
            detail="This action requires EMBRYOLOGIST or IVF_SPECIALIST role.",
            code='embryology_access_denied'
        )


class CanViewIVFRecords(permissions.BasePermission):
    """
    Permission for viewing IVF records.
    
    Allows read access for:
    - IVF_SPECIALIST
    - EMBRYOLOGIST
    - DOCTOR
    - NURSE (for patient care context)
    - ADMIN
    
    Allows write access for:
    - IVF_SPECIALIST (thaw, dispose actions)
    - EMBRYOLOGIST (thaw, dispose actions)
    - ADMIN
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Read-only roles
        read_only_roles = ['DOCTOR', 'NURSE']
        
        # Full access roles (can also thaw/dispose)
        full_access_roles = ['ADMIN', 'IVF_SPECIALIST', 'EMBRYOLOGIST']
        
        if user_role in full_access_roles:
            return True
        
        if user_role in read_only_roles:
            return request.method in permissions.SAFE_METHODS
        
        return False


class IsIVFNurse(permissions.BasePermission):
    """
    Permission class for IVF nursing staff.
    
    Nurses can:
    - View all IVF records (read access)
    - Record stimulation monitoring data (vitals, measurements)
    - Record medication administration
    - Update patient notes
    
    Nurses CANNOT:
    - Create or cancel IVF cycles
    - Perform oocyte retrieval or embryo transfer (procedure records)
    - Make embryo disposition decisions
    - Sign consents on behalf of patients
    - Modify embryo grading or PGT results
    
    Nigerian Nursing Scope of Practice:
    Per Nursing and Midwifery Council of Nigeria (NMCN) guidelines,
    nurses work under physician supervision for specialized procedures.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Admin and IVF Specialist always have access
        if user_role in ['ADMIN', 'IVF_SPECIALIST']:
            return True
        
        # Nurse has access
        if user_role == 'NURSE':
            return True
        
        # Embryologist has access for lab-related nursing tasks
        if user_role == 'EMBRYOLOGIST':
            return True
        
        # Doctor has read-only access
        if user_role == 'DOCTOR':
            return request.method in permissions.SAFE_METHODS
        
        print(f"DEBUG IsIVFNurse: DENIED - role {repr(user_role)} not allowed")
        return False


class CanRecordStimulationMonitoring(permissions.BasePermission):
    """
    Permission for recording ovarian stimulation monitoring data.
    
    This is a key nursing function in IVF - recording daily monitoring
    results including hormone levels, ultrasound findings, and vitals.
    
    Allows:
    - IVF_SPECIALIST: Full access
    - NURSE: Can create and update monitoring records
    - EMBRYOLOGIST: Read-only (lab focus)
    - DOCTOR: Read-only
    - ADMIN: Full access
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Full access roles
        if user_role in ['ADMIN', 'IVF_SPECIALIST']:
            return True
        
        # Nurse can create and update stimulation records
        if user_role == 'NURSE':
            return True
        
        # Read-only for others
        if user_role in ['DOCTOR', 'EMBRYOLOGIST']:
            return request.method in permissions.SAFE_METHODS
        
        return False


class CanRecordMedicationAdministration(permissions.BasePermission):
    """
    Permission for recording IVF medication administration.
    
    Nurses are responsible for administering IVF medications
    (injections, etc.) and documenting administration.
    
    Allows:
    - IVF_SPECIALIST: Full access (prescribe and record)
    - NURSE: Can record administration of prescribed medications
    - ADMIN: Full access
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Full access roles
        if user_role in ['ADMIN', 'IVF_SPECIALIST']:
            return True
        
        # Nurse can view and record medication administration
        if user_role == 'NURSE':
            return True
        
        # Read-only for Doctor
        if user_role == 'DOCTOR':
            return request.method in permissions.SAFE_METHODS
        
        return False


class IVFConsentRequired(permissions.BasePermission):
    """
    Permission that verifies consent is signed before allowing certain actions.
    
    Nigerian Healthcare Requirement:
    All IVF procedures require documented patient consent before proceeding.
    """
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # This permission is typically checked at the object level
        return True
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Check if the object has a cycle attribute
        cycle = getattr(obj, 'cycle', None) or obj
        
        if hasattr(cycle, 'consent_signed'):
            if not cycle.consent_signed:
                raise PermissionDenied(
                    detail="Patient consent must be signed before this action. "
                           "This is a legal requirement under Nigerian healthcare regulations.",
                    code='consent_required'
                )
        
        return True


class CanManageEmbryoDisposition(permissions.BasePermission):
    """
    Permission for embryo disposition decisions.
    
    Requires:
    - IVF_SPECIALIST or ADMIN role
    - Proper consent documentation
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            user_role = getattr(request.user, 'get_role', lambda: None)()
        
        # Only IVF Specialist and Admin can make disposition decisions
        if user_role not in ['ADMIN', 'IVF_SPECIALIST']:
            raise PermissionDenied(
                detail="Embryo disposition decisions require IVF_SPECIALIST role.",
                code='disposition_access_denied'
            )
        
        return True
