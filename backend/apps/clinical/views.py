"""
Views for clinical features - Vital signs, templates, alerts.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError as DRFValidationError
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import VitalSigns, ClinicalTemplate, ClinicalAlert
from .operation_models import OperationNote
from .serializers import (
    VitalSignsSerializer,
    VitalSignsCreateSerializer,
    ClinicalTemplateSerializer,
    ClinicalTemplateCreateSerializer,
    ClinicalAlertSerializer,
    OperationNoteSerializer,
    OperationNoteCreateSerializer,
)
from .permissions import (
    CanRecordVitalSigns,
    CanManageTemplates,
    CanViewAlerts,
    CanAcknowledgeAlerts,
    CanManageOperationNotes,
)
from apps.visits.models import Visit
from core.permissions import IsVisitOpen, IsVisitAccessible
from core.audit import AuditLog


def log_clinical_action(user, action, visit_id, resource_type, resource_id, request=None):
    """Log clinical action to audit log."""
    user_role = getattr(user, 'role', None) or \
               getattr(user, 'get_role', lambda: None)()
    if not user_role:
        user_role = 'UNKNOWN'
    
    AuditLog.log(
        user=user,
        role=user_role,
        action=f"CLINICAL_{action}",
        visit_id=visit_id,
        resource_type=resource_type,
        resource_id=resource_id,
        request=request,
    )


class VitalSignsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vital Signs.
    
    Rules enforced:
    - Visit-scoped
    - Doctor/Nurse can record
    - Payment enforcement for clinical actions
    """
    serializer_class = VitalSignsSerializer
    permission_classes = [CanRecordVitalSigns]
    pagination_class = None
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        from rest_framework.permissions import IsAuthenticated
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanRecordVitalSigns(), IsVisitOpen()]
        else:
            # Read operations: Just require authentication
            # Role and visit checks are handled elsewhere
            return [IsAuthenticated()]
    
    def get_visit(self):
        """Get visit from middleware or URL parameter."""
        # First try to get from request.visit set by middleware
        if hasattr(self.request, 'visit') and self.request.visit:
            return self.request.visit
        
        # Fallback to kwargs (from URL pattern)
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(detail=f"Visit with id {visit_id} not found.")
        
        # Set on request for permissions
        self.request.visit = visit
        return visit
    
    def get_queryset(self):
        """Get vital signs for the visit."""
        # Use visit_id from kwargs directly to avoid exceptions in get_queryset
        # get_visit() will be called by permissions/perform_create if needed
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return VitalSigns.objects.none()
        
        return VitalSigns.objects.filter(visit_id=visit_id).select_related(
            'visit', 'recorded_by'
        )
    
    def list(self, request, *args, **kwargs):
        """List vital signs for the visit with error handling."""
        import logging
        logger = logging.getLogger(__name__)
        try:
            queryset = self.get_queryset()
            
            # Serialize with per-record error handling
            vital_signs_data = []
            for vs in queryset:
                try:
                    serializer = self.get_serializer(vs)
                    vital_signs_data.append(serializer.data)
                except Exception as e:
                    # Log error for this specific record but continue with others
                    logger.warning(f"Error serializing vital signs {vs.id}: {str(e)}", exc_info=True)
                    # Add a basic record without computed fields
                    vital_signs_data.append({
                        'id': vs.id,
                        'visit': vs.visit_id,
                        'recorded_by': vs.recorded_by_id if vs.recorded_by else None,
                        'recorded_by_name': getattr(vs.recorded_by, 'username', 'Unknown') if vs.recorded_by else 'Unknown',
                        'temperature': str(vs.temperature) if vs.temperature else None,
                        'systolic_bp': vs.systolic_bp,
                        'diastolic_bp': vs.diastolic_bp,
                        'pulse': vs.pulse,
                        'respiratory_rate': vs.respiratory_rate,
                        'oxygen_saturation': str(vs.oxygen_saturation) if vs.oxygen_saturation else None,
                        'weight': str(vs.weight) if vs.weight else None,
                        'height': str(vs.height) if vs.height else None,
                        'bmi': str(vs.bmi) if vs.bmi else None,
                        'notes': vs.notes,
                        'recorded_at': vs.recorded_at.isoformat() if vs.recorded_at else None,
                        'abnormal_flags': [],
                    })
            
            return Response(vital_signs_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error listing vital signs: {str(e)}", exc_info=True)
            return Response(
                {"detail": f"Error retrieving vital signs: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return VitalSignsCreateSerializer
        return VitalSignsSerializer
    
    def perform_create(self, serializer):
        """Create vital signs record."""
        visit = self.get_visit()
        
        # Ensure visit is OPEN
        if visit.status == 'CLOSED':
            raise PermissionDenied("Cannot record vital signs for a CLOSED visit.")
        
        vital_signs = serializer.save(
            visit=visit,
            recorded_by=self.request.user
        )
        
        # Check for abnormal values and create alerts
        abnormal_flags = vital_signs.get_abnormal_flags()
        if abnormal_flags:
            for flag in abnormal_flags:
                severity = 'CRITICAL' if flag in ['HYPOTENSION', 'HYPOXIA', 'FEVER'] else 'HIGH'
                ClinicalAlert.objects.create(
                    visit=visit,
                    alert_type='VITAL_SIGNS',
                    severity=severity,
                    title=f"Abnormal Vital Sign: {flag}",
                    message=f"Vital signs recorded show {flag}. Please review.",
                    related_resource_type='vital_signs',
                    related_resource_id=vital_signs.id,
                )
        
        # Audit log
        log_clinical_action(
            user=self.request.user,
            action='VITAL_SIGNS_RECORDED',
            visit_id=visit.id,
            resource_type='vital_signs',
            resource_id=vital_signs.id,
            request=self.request,
        )
        
        return vital_signs


class ClinicalTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Clinical Templates.
    
    Rules enforced:
    - Doctor-only access
    - Templates can be used by all doctors
    """
    queryset = ClinicalTemplate.objects.filter(is_active=True).select_related('created_by')
    serializer_class = ClinicalTemplateSerializer
    permission_classes = [CanManageTemplates]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return ClinicalTemplateCreateSerializer
        return ClinicalTemplateSerializer
    
    def perform_create(self, serializer):
        """Create clinical template."""
        template = serializer.save(created_by=self.request.user)
        
        # Audit log
        AuditLog.log(
            user=self.request.user,
            role=getattr(self.request.user, 'role', 'UNKNOWN'),
            action='CLINICAL_TEMPLATE_CREATED',
            resource_type='clinical_template',
            resource_id=template.id,
            request=self.request,
        )
        
        return template
    
    @action(detail=True, methods=['post'], url_path='use')
    def use_template(self, request, pk=None):
        """Use a template and increment usage count."""
        template = self.get_object()
        template.increment_usage()
        
        return Response({
            'history': template.history_template or '',
            'examination': template.examination_template or '',
            'diagnosis': template.diagnosis_template or '',
            'clinical_notes': template.clinical_notes_template or '',
        })


class ClinicalAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Clinical Alerts.
    
    Rules enforced:
    - Visit-scoped
    - All authenticated users can view
    - Doctors can acknowledge
    """
    serializer_class = ClinicalAlertSerializer
    permission_classes = [CanViewAlerts]
    pagination_class = None
    
    def get_visit(self):
        """Get visit from URL parameter."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return None
        
        try:
            return Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            raise NotFound(detail=f"Visit with id {visit_id} not found.")
    
    def get_queryset(self):
        """Get alerts for the visit or all unresolved alerts."""
        # Use visit_id from kwargs directly to avoid exceptions in get_queryset
        visit_id = self.kwargs.get('visit_id')
        user = self.request.user
        
        queryset = ClinicalAlert.objects.all().select_related(
            'visit', 'acknowledged_by'
        )
        
        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)
        
        # Filter by resolved status if provided
        is_resolved = self.request.query_params.get('is_resolved')
        if is_resolved is not None:
            queryset = queryset.filter(is_resolved=is_resolved.lower() == 'true')
        else:
            # Default: show unresolved alerts
            queryset = queryset.filter(is_resolved=False)
        
        return queryset
    
    
    @action(detail=True, methods=['post'], url_path='acknowledge')
    def acknowledge_alert(self, request, visit_id=None, pk=None):
        """Acknowledge an alert (Doctor only)."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            alert = self.get_object()
            logger.info(f"Acknowledging alert {alert.id} for visit {alert.visit_id}")
        except Exception as e:
            logger.error(f"Failed to retrieve alert {pk}: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Failed to retrieve alert: {str(e)}")
        
        # Ensure visit is set on request for permissions
        if not hasattr(request, 'visit') or not request.visit:
            try:
                visit = self.get_visit()
                if visit:
                    request.visit = visit
            except Exception as e:
                logger.warning(f"Visit lookup failed for alert {alert.id}: {str(e)}")
                # If visit lookup fails, continue - alert.visit_id should still work
                pass
        
        # Check permission
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can acknowledge alerts.")
        
        try:
            alert.acknowledge(request.user)
            # Refresh from DB to get updated acknowledged_by and acknowledged_at
            alert.refresh_from_db()
            logger.info(f"Alert {alert.id} acknowledged successfully")
        except Exception as e:
            logger.error(f"Failed to acknowledge alert {alert.id}: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Failed to acknowledge alert: {str(e)}")
        
        # Audit log
        try:
            log_clinical_action(
                user=request.user,
                action='ALERT_ACKNOWLEDGED',
                visit_id=alert.visit_id,
                resource_type='clinical_alert',
                resource_id=alert.id,
                request=request,
            )
        except Exception as e:
            # Log audit failure but don't fail the request
            logger.warning(f"Audit log failed for alert {alert.id}: {str(e)}")
            pass
        
        try:
            serializer = ClinicalAlertSerializer(alert)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Serialization failed for alert {alert.id}: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Failed to serialize alert: {str(e)}")
    
    @action(detail=True, methods=['post'], url_path='resolve')
    def resolve_alert(self, request, visit_id=None, pk=None):
        """Resolve an alert (Doctor only)."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            alert = self.get_object()
            logger.info(f"Resolving alert {alert.id} for visit {alert.visit_id}")
        except Exception as e:
            logger.error(f"Failed to retrieve alert {pk}: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Failed to retrieve alert: {str(e)}")
        
        # Ensure visit is set on request for permissions
        if not hasattr(request, 'visit') or not request.visit:
            try:
                visit = self.get_visit()
                if visit:
                    request.visit = visit
            except Exception as e:
                logger.warning(f"Visit lookup failed for alert {alert.id}: {str(e)}")
                # If visit lookup fails, continue - alert.visit_id should still work
                pass
        
        # Check permission
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        if user_role != 'DOCTOR':
            raise PermissionDenied("Only doctors can resolve alerts.")
        
        try:
            alert.resolve()
            # Refresh from DB to get updated is_resolved
            alert.refresh_from_db()
            logger.info(f"Alert {alert.id} resolved successfully")
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert.id}: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Failed to resolve alert: {str(e)}")
        
        # Audit log
        try:
            log_clinical_action(
                user=request.user,
                action='ALERT_RESOLVED',
                visit_id=alert.visit_id,
                resource_type='clinical_alert',
                resource_id=alert.id,
                request=request,
            )
        except Exception as e:
            # Log audit failure but don't fail the request
            logger.warning(f"Audit log failed for alert {alert.id}: {str(e)}")
            pass
        
        try:
            serializer = ClinicalAlertSerializer(alert)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Serialization failed for alert {alert.id}: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Failed to serialize alert: {str(e)}")
