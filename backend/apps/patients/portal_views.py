"""
Patient Portal Views - Read-only access for patients to view their records.

Per EMR Rules:
- Patients can ONLY view their own data
- Read-only access (no modifications)
- Strict access control enforced
- Audit logging for all patient portal access
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from django.db.models import Q
from django.utils import timezone

from .models import Patient
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from apps.appointments.models import Appointment
from apps.laboratory.models import LabOrder, LabResult
from apps.radiology.models import RadiologyOrder, RadiologyResult
from apps.pharmacy.models import Prescription
from core.audit import AuditLog


def log_patient_portal_action(
    user,
    action,
    patient_id,
    request=None,
    metadata=None
):
    """
    Log a patient portal action to audit log.
    
    Args:
        user: User performing the action (patient)
        action: Action type (e.g., 'view_visits', 'view_lab_results')
        patient_id: Patient ID
        request: Django request object (for IP/user agent)
        metadata: Additional metadata dict (no PHI)
    
    Returns:
        AuditLog instance
    """
    user_role = getattr(user, 'role', None) or getattr(user, 'get_role', lambda: 'UNKNOWN')()
    
    ip_address = None
    user_agent = ''
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    audit_log = AuditLog(
        user=user,
        user_role=user_role,
        action=f'patient_portal.{action}',
        visit_id=None,  # Portal actions may not be visit-specific
        resource_type='patient_portal',
        resource_id=patient_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


def get_patient_from_user(user):
    """
    Get the Patient object associated with the authenticated user.
    Auto-creates Patient record if missing (same as wallet view).
    
    Raises:
        PermissionDenied: If user is not a patient
    """
    if user.role != 'PATIENT':
        raise PermissionDenied("This endpoint is only accessible to patients.")
    
    # Auto-create Patient record if missing (same logic as wallet view)
    try:
        patient = Patient.objects.get(user=user, is_active=True)
    except Patient.DoesNotExist:
        # Create Patient record if it doesn't exist
        from django.utils import timezone
        import random
        import secrets
        
        patient = Patient(
            first_name=user.first_name or 'Unknown',
            last_name=user.last_name or 'Patient',
            email=user.email or '',
            user=user,
            is_active=True,
            is_verified=False,
        )
        # Call clean() to generate patient_id, then save
        patient.clean()
        patient.save()
    
    # Check if patient account is verified
    if not patient.is_verified:
        raise PermissionDenied(
            "Your patient account has not been verified yet. "
            "Please contact the receptionist to verify your account."
        )
    
    return patient


class PatientPortalViewSet(viewsets.ViewSet):
    """
    Patient Portal ViewSet - Read-only access to patient's own records.
    
    Endpoint: /api/v1/patient-portal/
    
    Rules enforced:
    - Only PATIENT role can access
    - Patients can ONLY view their own data
    - All endpoints are read-only
    - Audit logging mandatory
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'], url_path='profile')
    def profile(self, request):
        """
        Get patient's own profile information.
        
        GET /api/v1/patient-portal/profile/
        """
        patient = get_patient_from_user(request.user)
        
        # Audit log
        log_patient_portal_action(
            user=request.user,
            action='view_profile',
            patient_id=patient.id,
            request=request,
        )
        
        from .serializers import PatientSerializer
        serializer = PatientSerializer(patient)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='visits')
    def visits(self, request):
        """
        Get patient's own visits.
        
        GET /api/v1/patient-portal/visits/
        """
        patient = get_patient_from_user(request.user)
        
        visits = Visit.objects.filter(
            patient=patient
        ).select_related('patient', 'closed_by').order_by('-created_at')
        
        # Audit log
        log_patient_portal_action(
            user=request.user,
            action='view_visits',
            patient_id=patient.id,
            request=request,
            metadata={'visit_count': visits.count()}
        )
        
        from apps.visits.serializers import VisitReadSerializer
        serializer = VisitReadSerializer(visits, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='visits/(?P<visit_id>[0-9]+)')
    def visit_detail(self, request, visit_id=None):
        """
        Get details of a specific visit (patient's own only).
        
        GET /api/v1/patient-portal/visits/{visit_id}/
        """
        patient = get_patient_from_user(request.user)
        
        try:
            visit = Visit.objects.get(id=visit_id, patient=patient)
        except Visit.DoesNotExist:
            raise NotFound("Visit not found or you don't have access to it.")
        
        # Audit log
        log_patient_portal_action(
            user=request.user,
            action='view_visit_detail',
            patient_id=patient.id,
            request=request,
            metadata={'visit_id': visit_id}
        )
        
        from apps.visits.serializers import VisitReadSerializer
        serializer = VisitReadSerializer(visit)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='appointments')
    def appointments(self, request):
        """
        Get patient's own appointments.
        
        GET /api/v1/patient-portal/appointments/
        """
        try:
            patient = get_patient_from_user(request.user)
            
            appointments = Appointment.objects.filter(
                patient=patient
            ).select_related('patient', 'doctor', 'visit').order_by('-appointment_date')
            
            # Audit log
            log_patient_portal_action(
                user=request.user,
                action='view_appointments',
                patient_id=patient.id,
                request=request,
                metadata={'appointment_count': appointments.count()}
            )
            
            from apps.appointments.serializers import AppointmentSerializer
            serializer = AppointmentSerializer(appointments, many=True)
            return Response(serializer.data)
        except Exception as e:
            import traceback
            error_detail = str(e)
            traceback.print_exc()
            return Response(
                {'error': f'Failed to load appointments: {error_detail}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='lab-results')
    def lab_results(self, request):
        """
        Get patient's own lab results.
        
        GET /api/v1/patient-portal/lab-results/
        """
        try:
            patient = get_patient_from_user(request.user)
            
            # Get lab results through visits
            lab_results = LabResult.objects.filter(
                lab_order__visit__patient=patient
            ).select_related(
                'lab_order',
                'lab_order__visit',
                'lab_order__consultation',
                'recorded_by'
            ).order_by('-recorded_at')
            
            # Audit log
            log_patient_portal_action(
                user=request.user,
                action='view_lab_results',
                patient_id=patient.id,
                request=request,
                metadata={'result_count': lab_results.count()}
            )
            
            from apps.laboratory.result_serializers import LabResultReadSerializer
            serializer = LabResultReadSerializer(lab_results, many=True)
            return Response(serializer.data)
        except Exception as e:
            import traceback
            error_detail = str(e)
            traceback.print_exc()
            return Response(
                {'error': f'Failed to load lab results: {error_detail}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='radiology-results')
    def radiology_results(self, request):
        """
        Get patient's own radiology results.
        
        GET /api/v1/patient-portal/radiology-results/
        """
        patient = get_patient_from_user(request.user)
        
        # Get radiology results through visits
        radiology_results = RadiologyResult.objects.filter(
            radiology_order__visit__patient=patient
        ).select_related(
            'radiology_order',
            'radiology_order__visit',
            'reported_by'
        ).order_by('-reported_at')
        
        # Audit log
        log_patient_portal_action(
            user=request.user,
            action='view_radiology_results',
            patient_id=patient.id,
            request=request,
            metadata={'result_count': radiology_results.count()}
        )
        
        from apps.radiology.result_serializers import RadiologyResultReadSerializer
        serializer = RadiologyResultReadSerializer(radiology_results, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='prescriptions')
    def prescriptions(self, request):
        """
        Get patient's own prescriptions.
        
        GET /api/v1/patient-portal/prescriptions/
        """
        try:
            patient = get_patient_from_user(request.user)
            
            # Get prescriptions through visits
            # Note: 'drug' is a CharField, not a ForeignKey, so it can't be in select_related
            prescriptions = Prescription.objects.filter(
                visit__patient=patient
            ).select_related(
                'visit',
                'consultation',
                'prescribed_by'
            ).order_by('-created_at')
            
            # Audit log
            log_patient_portal_action(
                user=request.user,
                action='view_prescriptions',
                patient_id=patient.id,
                request=request,
                metadata={'prescription_count': prescriptions.count()}
            )
            
            from apps.pharmacy.serializers import PrescriptionSerializer
            serializer = PrescriptionSerializer(prescriptions, many=True)
            return Response(serializer.data)
        except Exception as e:
            import traceback
            error_detail = str(e)
            traceback.print_exc()
            return Response(
                {'error': f'Failed to load prescriptions: {error_detail}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='medical-history')
    def medical_history(self, request):
        """
        Get patient's comprehensive medical history.
        
        GET /api/v1/patient-portal/medical-history/
        
        Returns:
        {
            "patient": {...},
            "visits": [...],
            "consultations": [...],
            "lab_results": [...],
            "radiology_results": [...],
            "prescriptions": [...],
            "appointments": [...]
        }
        """
        patient = get_patient_from_user(request.user)
        
        # Get all related data
        visits = Visit.objects.filter(patient=patient).select_related('patient', 'closed_by').order_by('-created_at')
        consultations = Consultation.objects.filter(visit__patient=patient).select_related('visit', 'created_by').order_by('-created_at')
        lab_results = LabResult.objects.filter(lab_order__visit__patient=patient).select_related('lab_order', 'recorded_by').order_by('-recorded_at')
        radiology_results = RadiologyResult.objects.filter(radiology_order__visit__patient=patient).select_related('radiology_order', 'reported_by').order_by('-reported_at')
        # Note: 'drug' is a CharField, not a ForeignKey, so it can't be in select_related
        prescriptions = Prescription.objects.filter(visit__patient=patient).select_related('visit', 'prescribed_by').order_by('-created_at')
        # Note: Appointment model only has 'appointment_date', not 'appointment_time'
        appointments = Appointment.objects.filter(patient=patient).select_related('patient', 'doctor', 'visit').order_by('-appointment_date')
        
        # Audit log
        log_patient_portal_action(
            user=request.user,
            action='view_medical_history',
            patient_id=patient.id,
            request=request,
        )
        
        # Serialize all data
        from .serializers import PatientSerializer
        from apps.visits.serializers import VisitReadSerializer
        from apps.consultations.serializers import ConsultationSerializer
        from apps.laboratory.serializers import LabResultSerializer
        from apps.radiology.serializers import RadiologyResultSerializer
        from apps.pharmacy.serializers import PrescriptionSerializer
        from apps.appointments.serializers import AppointmentSerializer
        
        return Response({
            'patient': PatientSerializer(patient).data,
            'visits': VisitReadSerializer(visits, many=True).data,
            'consultations': ConsultationSerializer(consultations, many=True).data,
            'lab_results': LabResultReadSerializer(lab_results, many=True).data,
            'radiology_results': RadiologyResultSerializer(radiology_results, many=True).data,
            'prescriptions': PrescriptionSerializer(prescriptions, many=True).data,
            'appointments': AppointmentSerializer(appointments, many=True).data,
        })
