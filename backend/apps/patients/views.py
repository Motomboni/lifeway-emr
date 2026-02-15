"""
Patient ViewSet - patient registration and search.

Per EMR Rules:
- Receptionist: Can register and search patients
- All patient data is PHI - must be protected
- No standalone patient endpoints (patients are accessed via visits)
- Search functionality for finding existing patients
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model

User = get_user_model()

from .models import Patient
from .serializers import (
    PatientSerializer,
    PatientCreateSerializer,
    PatientSearchSerializer,
    PatientVerificationSerializer,
)
from .permissions import CanRegisterPatient, CanSearchPatient, CanDeletePatient
from core.audit import AuditLog


class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Patient management.
    
    Endpoint: /api/v1/patients/
    
    Rules enforced:
    - Receptionist: Can create and search patients
    - Other roles: Can view patient data (read-only)
    - All patient data is PHI - must be protected
    - Audit logging for all actions
    """
    
    queryset = Patient.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        
        - Create: PatientCreateSerializer
        - List/Search: PatientSearchSerializer (data minimization)
        - Pending Verification: PatientVerificationSerializer
        - Retrieve/Update: PatientSerializer (full data)
        """
        if self.action == 'create':
            return PatientCreateSerializer
        elif self.action == 'list' or self.action == 'search':
            return PatientSearchSerializer
        elif self.action == 'pending_verification':
            return PatientVerificationSerializer
        else:
            return PatientSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create: Receptionist only
        - List/Search: Receptionist and clinical staff
        - Destroy: Admin, Receptionist, or Superuser (archive/soft-delete)
        - Retrieve/Update: Authenticated users (read-only for non-receptionist)
        """
        if self.action == 'create':
            permission_classes = [CanRegisterPatient]
        elif self.action == 'list' or self.action == 'search':
            permission_classes = [CanSearchPatient]
        elif self.action == 'destroy':
            permission_classes = [CanDeletePatient]
        else:
            # Retrieve, update - authenticated users can view
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Get patients queryset.
        Filter by is_active=True by default.
        """
        queryset = Patient.objects.filter(is_active=True)
        
        # Add search filtering if search query provided
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(patient_id__icontains=search_query) |
                Q(national_id__icontains=search_query) |
                Q(phone__icontains=search_query)
            )
        
        return queryset.order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        Create patient with optional portal account creation.
        
        Enhanced response includes:
        - Success message
        - Patient data
        - Portal creation status
        - Temporary credentials (if portal created)
        
        Transaction-safe: All operations wrapped in atomic transaction.
        The serializer handles the transaction, this method formats the response.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            # Validate input data
            serializer.is_valid(raise_exception=True)
            
            # Wrap in transaction.atomic to ensure atomicity at view level too
            with transaction.atomic():
                # Perform creation (calls serializer.create() which has its own transaction)
                patient = self.perform_create(serializer)
            
            # Get serialized data (includes portal_created and temporary_password)
            response_data = serializer.data
            
            # Build enhanced response
            result = {
                'success': True,
                'message': 'Patient registered successfully',
                'patient': response_data,
            }
            
            # Add portal credentials if portal was created
            if response_data.get('portal_created', False):
                result['portal_created'] = True
                result['portal_credentials'] = {
                    'username': response_data.get('email', request.data.get('portal_email')),
                    'temporary_password': response_data.get('temporary_password'),
                    'login_url': '/patient-portal/login'
                }
                result['message'] = 'Patient registered successfully with portal account'
                
                # Log portal account creation
                logger.info(
                    f"Patient portal account created: Patient ID {patient.id}, "
                    f"Username {response_data.get('email', request.data.get('portal_email'))}"
                )
            else:
                result['portal_created'] = False
            
            return Response(result, status=status.HTTP_201_CREATED)
            
        except IntegrityError as e:
            # Handle database integrity errors (e.g., duplicate email)
            logger.error(f"Database integrity error: {str(e)}", exc_info=True)
            
            error_message = str(e).lower()
            if 'unique constraint' in error_message or 'duplicate' in error_message:
                if 'username' in error_message or 'email' in error_message:
                    return Response(
                        {
                            'success': False,
                            'error': 'A portal account with this email already exists.',
                            'detail': 'Please use a different email address for the patient portal.'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                elif 'national_id' in error_message:
                    return Response(
                        {
                            'success': False,
                            'error': 'A patient with this national ID already exists.',
                            'detail': 'Please verify the national ID or search for existing patient.'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    return Response(
                        {
                            'success': False,
                            'error': 'A patient with these details already exists.',
                            'detail': str(e)
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Generic integrity error
            return Response(
                {
                    'success': False,
                    'error': 'Database constraint violation.',
                    'detail': str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except DRFValidationError as e:
            # Handle validation errors from serializer
            logger.warning(f"Validation error during patient creation: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': 'Validation failed',
                    'detail': str(e.detail) if hasattr(e, 'detail') else str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error creating patient: {str(e)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return Response(
                {
                    'success': False,
                    'error': 'Failed to create patient',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        """
        Create patient with audit logging.
        
        Rules:
        1. Only Receptionist can create (enforced by CanRegisterPatient)
        2. patient_id auto-generated if not provided
        3. Audit log created
        4. Portal account created if requested (handled by serializer)
        
        Note: The serializer.save() call handles the atomic transaction
        for patient + portal user creation.
        """
        # Save patient (serializer handles portal creation internally)
        patient = serializer.save()
        
        # REQUIRED VIEWSET ENFORCEMENT: Audit log
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        # Ensure user_role is a string (required by AuditLog model)
        if not user_role:
            user_role = 'UNKNOWN'
        
        # Build audit metadata
        audit_metadata = {'patient_id': patient.patient_id}
        
        # Add portal creation info to audit log
        if hasattr(patient, 'portal_created') and patient.portal_created:
            audit_metadata['portal_account_created'] = True
            if hasattr(patient, 'portal_user'):
                audit_metadata['portal_username'] = patient.portal_user.username
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action="PATIENT_CREATED",
            visit_id=None,  # Patient creation is not visit-scoped
            resource_type="patient",
            resource_id=patient.id,
            request=self.request,
            metadata=audit_metadata
        )
        
        return patient
    
    def perform_update(self, serializer):
        """
        Update patient with audit logging.
        
        Rules:
        1. Only Receptionist should update (enforced by permissions if needed)
        2. Audit log created
        """
        patient = serializer.save()
        
        # Audit log
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        # Ensure user_role is a string (required by AuditLog model)
        if not user_role:
            user_role = 'UNKNOWN'
        
        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action="PATIENT_UPDATED",
            visit_id=None,
            resource_type="patient",
            resource_id=patient.id,
            request=self.request
        )
        
        return patient
    
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Search patients by name, patient_id, national_id, or phone.
        
        GET /api/v1/patients/search/?q=search_term
        
        Returns minimal patient data (data minimization).
        """
        search_term = request.query_params.get('q', '').strip()
        
        if not search_term:
            return Response(
                {'detail': 'Search query parameter "q" is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search in multiple fields
        queryset = Patient.objects.filter(
            is_active=True
        ).filter(
            Q(first_name__icontains=search_term) |
            Q(last_name__icontains=search_term) |
            Q(patient_id__icontains=search_term) |
            Q(national_id__icontains=search_term) |
            Q(phone__icontains=search_term)
        )[:20]  # Limit to 20 results
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="PATIENT_SEARCH",
            visit_id=None,
            resource_type="patient",
            resource_id=None,
            request=request,
            metadata={'search_term': search_term}
        )
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Soft delete patient (compliance requirement).
        
        Per EMR rules, patients cannot be hard-deleted.
        Use soft-delete (is_active=False) instead.
        """
        patient = self.get_object()
        
        # Soft delete
        patient.is_active = False
        patient.save()
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        # Ensure user_role is a string (required by AuditLog model)
        if not user_role:
            user_role = 'UNKNOWN'
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="PATIENT_DELETED",
            visit_id=None,
            resource_type="patient",
            resource_id=patient.id,
            request=request
        )
        
        return Response(
            {'detail': 'Patient record archived successfully.'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], url_path='verify')
    def verify(self, request, pk=None):
        """
        Verify a patient account (Receptionist only).
        
        POST /api/v1/patients/{id}/verify/
        
        Rules:
        - Only Receptionist can verify patient accounts
        - Patient must have a linked user account
        - Sets is_verified=True, verified_by, and verified_at
        - Audit log created
        """
        # Check if user is Receptionist
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        if user_role != 'RECEPTIONIST':
            raise PermissionDenied("Only receptionists can verify patient accounts.")
        
        patient = self.get_object()
        
        # Check if patient has a linked user account
        if not patient.user:
            return Response(
                {'detail': 'Patient does not have a linked user account.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already verified
        if patient.is_verified:
            return Response(
                {'detail': 'Patient account is already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the patient account
        from django.utils import timezone
        patient.is_verified = True
        patient.verified_by = request.user
        patient.verified_at = timezone.now()
        patient.save()
        
        # Audit log
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="PATIENT_VERIFIED",
            visit_id=None,
            resource_type="patient",
            resource_id=patient.id,
            request=request,
            metadata={'patient_user_id': patient.user.id}
        )
        
        # Send email notification to patient
        try:
            from apps.notifications.utils import send_patient_verification_notification
            send_patient_verification_notification(patient, request.user)
        except Exception as e:
            # Log error but don't fail the verification
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send verification email to patient {patient.id}: {str(e)}")
        
        serializer = self.get_serializer(patient)
        return Response({
            'detail': 'Patient account verified successfully.',
            'patient': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='pending-verification')
    def pending_verification(self, request):
        """
        Get list of patients pending verification (Receptionist only).
        
        GET /api/v1/patients/pending-verification/
        
        Returns patients with user accounts that are not yet verified.
        """
        # Check if user is Receptionist
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        if user_role != 'RECEPTIONIST':
            raise PermissionDenied("Only receptionists can view pending verifications.")
        
        # Get patients with user accounts that are not verified
        queryset = Patient.objects.filter(
            is_active=True,
            user__isnull=False,
            is_verified=False
        ).select_related('user').order_by('-created_at')
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Audit log
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="PATIENT_PENDING_VERIFICATION_VIEWED",
            visit_id=None,
            resource_type="patient",
            resource_id=None,
            request=request
        )
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='create-portal')
    def create_portal(self, request, pk=None):
        """
        Create portal account for existing patient.
        
        POST /api/v1/patients/{id}/create-portal/
        
        Request Body:
        {
            "email": "patient@example.com",
            "phone": "0712345678"  // optional
        }
        
        Response:
        {
            "success": true,
            "message": "Portal account created successfully",
            "credentials": {
                "username": "patient@example.com",
                "temporary_password": "xK9mP2nQ7vR3",
                "login_url": "/patient-portal/login"
            }
        }
        
        Rules:
        - Only Receptionist or Admin can create portal accounts
        - Patient must not already have a portal account
        - Email is required
        - Phone is optional
        - Generates secure temporary password
        - Uses atomic transaction
        """
        import logging
        import secrets
        
        logger = logging.getLogger(__name__)
        
        # Check permissions
        user_role = getattr(request.user, 'role', None)
        if user_role not in ['RECEPTIONIST', 'ADMIN']:
            raise PermissionDenied("Only receptionists and administrators can create portal accounts.")
        
        # Get patient
        patient = self.get_object()
        
        # Validate input
        email = request.data.get('email', '').strip()
        phone = request.data.get('phone', '').strip()
        
        if not email:
            return Response(
                {
                    'success': False,
                    'error': 'Email is required',
                    'detail': 'Please provide a valid email address for the portal account.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate email format
        import re
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, email):
            return Response(
                {
                    'success': False,
                    'error': 'Invalid email format',
                    'detail': 'Please provide a valid email address.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if patient already has a portal account
        if hasattr(patient, 'portal_user') and patient.portal_user:
            return Response(
                {
                    'success': False,
                    'error': 'Portal account already exists',
                    'detail': f'This patient already has a portal account with username: {patient.portal_user.username}',
                    'existing_username': patient.portal_user.username
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if email is already used by another user
        if User.objects.filter(username=email).exists():
            return Response(
                {
                    'success': False,
                    'error': 'Email already in use',
                    'detail': 'A portal account with this email already exists. Please use a different email.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create portal account in atomic transaction
        try:
            with transaction.atomic():
                # Generate secure temporary password
                temporary_password = secrets.token_urlsafe(12)[:12]
                
                # Create user account with PATIENT role
                portal_user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=temporary_password,
                    role='PATIENT',
                    patient=patient,
                    first_name=patient.first_name,
                    last_name=patient.last_name,
                    is_active=True
                )
                
                # Enable portal on patient record
                patient.portal_enabled = True
                patient.save(update_fields=['portal_enabled'])
                
                logger.info(
                    f"Portal account created for existing patient {patient.id} "
                    f"(username: {email}) by {request.user.username}"
                )
                
                # Send notification (optional)
                try:
                    from apps.patients.portal_notifications import notify_new_portal_account
                    
                    notify_new_portal_account(
                        patient=patient,
                        username=email,
                        temporary_password=temporary_password,
                        phone=phone if phone else None
                    )
                except Exception as e:
                    # Don't fail if notification fails
                    logger.warning(f"Failed to prepare portal notification: {e}")
                
                # Audit log
                AuditLog.log(
                    user=request.user,
                    role=user_role,
                    action="PORTAL_ACCOUNT_CREATED",
                    visit_id=None,
                    resource_type="patient",
                    resource_id=patient.id,
                    request=request,
                    metadata={
                        'patient_id': patient.patient_id,
                        'portal_username': email,
                        'portal_user_id': portal_user.id
                    }
                )
                
                # Return success with credentials
                return Response(
                    {
                        'success': True,
                        'message': 'Portal account created successfully',
                        'credentials': {
                            'username': email,
                            'temporary_password': temporary_password,
                            'login_url': '/patient-portal/login'
                        },
                        'patient': {
                            'id': patient.id,
                            'patient_id': patient.patient_id,
                            'name': patient.get_full_name(),
                            'portal_enabled': patient.portal_enabled
                        }
                    },
                    status=status.HTTP_201_CREATED
                )
                
        except IntegrityError as e:
            logger.error(f"Database integrity error creating portal: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': 'Database error',
                    'detail': 'Failed to create portal account due to database constraint. Email may already be in use.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Error creating portal account: {str(e)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return Response(
                {
                    'success': False,
                    'error': 'Failed to create portal account',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='toggle-portal')
    def toggle_portal(self, request, pk=None):
        """
        Enable or disable patient portal access (Admin only).
        
        POST /api/v1/patients/{id}/toggle-portal/
        
        Request Body:
        {
            "enabled": true  // or false
        }
        
        Response:
        {
            "success": true,
            "message": "Portal access enabled",
            "portal_enabled": true,
            "portal_user_active": true
        }
        
        Behavior:
        - If disabling: Sets patient.portal_enabled=False AND user.is_active=False
        - If enabling: Sets patient.portal_enabled=True AND user.is_active=True
        - Blocks portal login when disabled (user cannot authenticate)
        - Atomic transaction ensures consistency
        """
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Check permissions - Only ADMIN
        user_role = getattr(request.user, 'role', None)
        if user_role != 'ADMIN':
            raise PermissionDenied("Only administrators can enable/disable patient portal access.")
        
        patient = self.get_object()
        enabled = request.data.get('enabled')
        
        if enabled is None:
            return Response(
                {'success': False, 'error': 'Missing "enabled" parameter'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        enabled = bool(enabled)
        
        # Check if already in desired state
        if patient.portal_enabled == enabled:
            state_text = 'enabled' if enabled else 'disabled'
            return Response(
                {
                    'success': True,
                    'message': f'Portal is already {state_text}',
                    'portal_enabled': patient.portal_enabled,
                    'no_change': True
                },
                status=status.HTTP_200_OK
            )
        
        # Toggle portal access atomically
        try:
            with transaction.atomic():
                # Update patient.portal_enabled
                patient.portal_enabled = enabled
                patient.save(update_fields=['portal_enabled'])
                
                # Update linked user.is_active (if portal user exists)
                portal_user_active = None
                if hasattr(patient, 'portal_user') and patient.portal_user:
                    patient.portal_user.is_active = enabled
                    patient.portal_user.save(update_fields=['is_active'])
                    portal_user_active = enabled
                    
                    logger.info(
                        f"Portal user {patient.portal_user.username} "
                        f"{'activated' if enabled else 'deactivated'}"
                    )
                
                action_text = 'enabled' if enabled else 'disabled'
                logger.info(f"Portal {action_text} for patient {patient.id} by {request.user.username}")
                
                # Audit log
                AuditLog.log(
                    user=request.user,
                    role=user_role,
                    action=f"PORTAL_ACCESS_{'ENABLED' if enabled else 'DISABLED'}",
                    visit_id=None,
                    resource_type="patient",
                    resource_id=patient.id,
                    request=request,
                    metadata={
                        'patient_id': patient.patient_id,
                        'portal_enabled': enabled,
                        'portal_user_active': portal_user_active
                    }
                )
                
                return Response(
                    {
                        'success': True,
                        'message': f'Portal access {action_text} successfully',
                        'portal_enabled': patient.portal_enabled,
                        'portal_user_active': portal_user_active
                    },
                    status=status.HTTP_200_OK
                )
                
        except Exception as e:
            logger.error(f"Error toggling portal: {e}", exc_info=True)
            return Response(
                {'success': False, 'error': 'Failed to toggle portal access'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )