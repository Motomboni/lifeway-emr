"""
Appointment ViewSet - appointment management.

Endpoint: /api/v1/appointments/

Enforcement:
1. Receptionist: Can create/manage all appointments
2. Doctor: Can view their own appointments, update status/notes
3. Audit logging mandatory
4. Data minimization: Doctors see only their appointments
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from django.utils import timezone
from django.db.models import Q

from .models import Appointment
from .serializers import (
    AppointmentSerializer,
    AppointmentCreateSerializer,
    AppointmentUpdateSerializer,
)
from .permissions import CanManageAppointments, CanCreateAppointments
from core.audit import AuditLog
from apps.notifications.utils import (
    send_appointment_confirmation,
    send_appointment_reminder,
)


def log_appointment_action(
    user,
    action,
    appointment_id,
    request=None,
    metadata=None
):
    """
    Log an appointment action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'create', 'update', 'cancel')
        appointment_id: Appointment ID (required)
        request: Django request object (for IP/user agent)
        metadata: Additional metadata dict (no PHI)
    """
    user_role = getattr(user, 'role', None)
    if not user_role:
        user_role = getattr(user, 'get_role', lambda: None)()
    if not user_role:
        user_role = 'UNKNOWN'
    
    ip_address = None
    user_agent = ''
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    AuditLog.objects.create(
        user=user,
        user_role=user_role,
        action=f'appointment.{action}',
        resource_type='appointment',
        resource_id=appointment_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )


class AppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Appointment management.
    
    Rules enforced:
    - Receptionist: Full access (create, update, delete, list all)
    - Doctor: View own appointments, update status/notes
    - Audit logging
    - Data minimization
    """
    
    queryset = Appointment.objects.all().select_related(
        'patient', 'doctor', 'visit', 'created_by', 'cancelled_by'
    )
    permission_classes = [CanManageAppointments]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return AppointmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AppointmentUpdateSerializer
        return AppointmentSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action == 'create':
            return [CanCreateAppointments()]
        return [CanManageAppointments()]
    
    def get_queryset(self):
        """
        Filter queryset based on user role.
        
        Receptionist: See all appointments
        Doctor: See only their own appointments
        """
        queryset = super().get_queryset()
        
        user_role = getattr(self.request.user, 'role', None)
        if not user_role:
            user_role = getattr(self.request.user, 'get_role', lambda: None)()
        
        # Doctor: Filter to own appointments
        if user_role == 'DOCTOR':
            queryset = queryset.filter(doctor=self.request.user)
        
        # Apply filters
        patient_id = self.request.query_params.get('patient', None)
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        
        doctor_id = self.request.query_params.get('doctor', None)
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        date_from = self.request.query_params.get('date_from', None)
        if date_from:
            queryset = queryset.filter(appointment_date__gte=date_from)
        
        date_to = self.request.query_params.get('date_to', None)
        if date_to:
            queryset = queryset.filter(appointment_date__lte=date_to)
        
        # Search by patient name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(patient__first_name__icontains=search) |
                Q(patient__last_name__icontains=search) |
                Q(patient__patient_id__icontains=search)
            )
        
        return queryset.order_by('appointment_date')
    
    def perform_create(self, serializer):
        """Create appointment with audit logging."""
        appointment = serializer.save()
        
        log_appointment_action(
            user=self.request.user,
            action='create',
            appointment_id=appointment.id,
            request=self.request,
            metadata={
                'patient_id': appointment.patient_id,
                'doctor_id': appointment.doctor_id,
                'appointment_date': appointment.appointment_date.isoformat(),
                'status': appointment.status,
            }
        )
        
        return appointment
    
    def perform_update(self, serializer):
        """Update appointment with audit logging."""
        old_status = serializer.instance.status
        appointment = serializer.save()
        
        log_appointment_action(
            user=self.request.user,
            action='update',
            appointment_id=appointment.id,
            request=self.request,
            metadata={
                'old_status': old_status,
                'new_status': appointment.status,
                'patient_id': appointment.patient_id,
                'doctor_id': appointment.doctor_id,
            }
        )
        
        return appointment
    
    def perform_destroy(self, instance):
        """Cancel appointment instead of deleting (soft delete)."""
        if instance.status != 'CANCELLED':
            instance.status = 'CANCELLED'
            instance.cancelled_at = timezone.now()
            instance.cancelled_by = self.request.user
            instance.save()
            
            log_appointment_action(
                user=self.request.user,
                action='cancel',
                appointment_id=instance.id,
                request=self.request,
                metadata={
                    'patient_id': instance.patient_id,
                    'doctor_id': instance.doctor_id,
                }
            )
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm an appointment."""
        appointment = self.get_object()
        
        if appointment.status != 'SCHEDULED':
            raise DRFValidationError(
                f"Cannot confirm appointment with status {appointment.status}."
            )
        
        appointment.status = 'CONFIRMED'
        appointment.save()
        
        log_appointment_action(
            user=request.user,
            action='confirm',
            appointment_id=appointment.id,
            request=request,
            metadata={
                'patient_id': appointment.patient_id,
                'doctor_id': appointment.doctor_id,
            }
        )
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark appointment as completed."""
        appointment = self.get_object()
        
        if appointment.status not in ['SCHEDULED', 'CONFIRMED']:
            raise DRFValidationError(
                f"Cannot complete appointment with status {appointment.status}."
            )
        
        appointment.status = 'COMPLETED'
        appointment.save()
        
        log_appointment_action(
            user=request.user,
            action='complete',
            appointment_id=appointment.id,
            request=request,
            metadata={
                'patient_id': appointment.patient_id,
                'doctor_id': appointment.doctor_id,
            }
        )
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an appointment."""
        appointment = self.get_object()
        
        if appointment.status == 'CANCELLED':
            raise DRFValidationError("Appointment is already cancelled.")
        
        cancellation_reason = request.data.get('cancellation_reason', '')
        
        appointment.status = 'CANCELLED'
        appointment.cancelled_at = timezone.now()
        appointment.cancelled_by = request.user
        appointment.cancellation_reason = cancellation_reason
        appointment.save()
        
        log_appointment_action(
            user=request.user,
            action='cancel',
            appointment_id=appointment.id,
            request=request,
            metadata={
                'patient_id': appointment.patient_id,
                'doctor_id': appointment.doctor_id,
                'cancellation_reason': cancellation_reason[:100] if cancellation_reason else '',
            }
        )
        
        # Send cancellation email
        try:
            if appointment.patient and appointment.patient.email:
                from apps.notifications.utils import send_email_notification
                from django.utils import timezone
                patient = appointment.patient
                patient_name = patient.get_full_name()
                send_email_notification(
                    notification_type='APPOINTMENT_CANCELLED',
                    recipient_email=patient.email,
                    recipient_name=patient_name,
                    subject=f'Appointment Cancelled - {appointment.appointment_date.strftime("%B %d, %Y")}',
                    template_name='notifications/appointment_cancelled.html',
                    context={
                        'patient_name': patient_name,
                        'appointment_date': appointment.appointment_date.strftime('%B %d, %Y'),
                        'appointment_time': appointment.appointment_date.strftime('%I:%M %p'),
                        'cancellation_reason': cancellation_reason or 'No reason provided',
                        'current_year': timezone.now().year,
                    },
                    appointment=appointment,
                    created_by=request.user,
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send appointment cancellation email: {e}")
        
        serializer = self.get_serializer(appointment)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming appointments for the user."""
        queryset = self.get_queryset().filter(
            appointment_date__gte=timezone.now(),
            status__in=['SCHEDULED', 'CONFIRMED']
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's appointments for the user."""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59)
        
        queryset = self.get_queryset().filter(
            appointment_date__gte=today_start,
            appointment_date__lte=today_end
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
