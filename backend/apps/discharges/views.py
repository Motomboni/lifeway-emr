"""
Views for DischargeSummary model.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from .models import DischargeSummary
from .serializers import (
    DischargeSummarySerializer,
    DischargeSummaryCreateSerializer,
)
from .permissions import CanCreateDischargeSummary, CanViewDischargeSummary
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from core.permissions import IsVisitAccessible
from core.audit import AuditLog


def log_discharge_action(
    user,
    action,
    visit_id,
    discharge_summary_id=None,
    request=None,
    metadata=None
):
    """
    Log a discharge summary action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'create', 'read', 'export')
        visit_id: Visit ID (required)
        discharge_summary_id: Discharge Summary ID if applicable
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
        action=f'discharge_summary.{action}',
        visit_id=visit_id,
        resource_type='discharge_summary',
        resource_id=discharge_summary_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


class DischargeSummaryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Discharge Summary management - visit-scoped.
    
    Rules enforced:
    - Visit-scoped architecture
    - Visit must be CLOSED
    - Doctor-only creation
    - Immutable once created
    - Exportable in multiple formats
    - Audit logging
    """
    
    def get_queryset(self):
        """Get discharge summary for the specific visit."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return DischargeSummary.objects.none()
        
        return DischargeSummary.objects.filter(visit_id=visit_id).select_related(
            'visit',
            'consultation',
            'created_by',
            'visit__patient'
        )
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return DischargeSummaryCreateSerializer
        else:
            return DischargeSummarySerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create: Doctor only + Visit Accessible (must be CLOSED)
        - Read: All authenticated users + Visit Accessible
        """
        if self.action == 'create':
            permission_classes = [
                CanCreateDischargeSummary,
                IsVisitAccessible,
            ]
        else:
            # Read operations: All authenticated users, visit accessible
            permission_classes = [
                CanViewDischargeSummary,
                IsVisitAccessible,
            ]
        
        return [permission() for permission in permission_classes]
    
    def get_visit(self):
        """Get and validate visit from URL parameter."""
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        visit = get_object_or_404(Visit, pk=visit_id)
        self.request.visit = visit
        return visit
    
    def get_consultation(self, visit):
        """
        Get consultation for the visit.
        Discharge summaries REQUIRE consultation.
        """
        consultation = Consultation.objects.filter(visit=visit).first()
        
        if not consultation:
            raise DRFValidationError(
                "Consultation must exist before creating discharge summary. "
                "Please create a consultation first."
            )
        
        return consultation
    
    def perform_create(self, serializer):
        """Create discharge summary with validation and audit logging."""
        visit = self.get_visit()
        consultation = self.get_consultation(visit)
        
        # Ensure visit is CLOSED
        if visit.status != 'CLOSED':
            raise DRFValidationError(
                "Discharge summary can only be created for CLOSED visits."
            )
        
        # Check if discharge summary already exists
        if DischargeSummary.objects.filter(visit=visit).exists():
            raise DRFValidationError(
                "Discharge summary already exists for this visit."
            )
        
        # Create discharge summary
        discharge_summary = serializer.save()
        
        # Link to admission if visit has an admission
        if hasattr(visit, 'admission') and visit.admission:
            discharge_summary.admission = visit.admission
            discharge_summary.save(update_fields=['admission'])
            
            # Update admission's discharge_summary link
            visit.admission.discharge_summary = discharge_summary
            visit.admission.save(update_fields=['discharge_summary'])
        
        # Audit log
        log_discharge_action(
            user=self.request.user,
            action='create',
            visit_id=visit.id,
            discharge_summary_id=discharge_summary.id,
            request=self.request,
            metadata={
                'condition_at_discharge': discharge_summary.condition_at_discharge,
                'discharge_disposition': discharge_summary.discharge_disposition,
            }
        )
        
        return discharge_summary
    
    def retrieve(self, request, *args, **kwargs):
        """Retrieve a discharge summary."""
        discharge_summary = self.get_object()
        
        # Audit log
        log_discharge_action(
            user=request.user,
            action='read',
            visit_id=discharge_summary.visit_id,
            discharge_summary_id=discharge_summary.id,
            request=request,
        )
        
        serializer = self.get_serializer(discharge_summary)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """Disable UPDATE - discharge summaries are immutable."""
        return Response(
            {'error': 'Discharge summaries cannot be modified once created.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def partial_update(self, request, *args, **kwargs):
        """Disable PATCH - discharge summaries are immutable."""
        return Response(
            {'error': 'Discharge summaries cannot be modified once created.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """Disable DELETE - discharge summaries cannot be deleted."""
        return Response(
            {'error': 'Discharge summaries cannot be deleted.'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    @action(detail=True, methods=['get'], url_path='export/text')
    def export_text(self, request, visit_id=None, pk=None):
        """Export discharge summary as plain text."""
        discharge_summary = self.get_object()
        
        # Audit log
        log_discharge_action(
            user=request.user,
            action='export',
            visit_id=discharge_summary.visit_id,
            discharge_summary_id=discharge_summary.id,
            request=request,
            metadata={'format': 'text'}
        )
        
        text_content = discharge_summary.get_formatted_summary()
        
        response = HttpResponse(text_content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="discharge_summary_{discharge_summary.visit_id}.txt"'
        return response
    
    @action(detail=True, methods=['get'], url_path='export/html')
    def export_html(self, request, visit_id=None, pk=None):
        """Export discharge summary as HTML."""
        discharge_summary = self.get_object()
        
        # Audit log
        log_discharge_action(
            user=request.user,
            action='export',
            visit_id=discharge_summary.visit_id,
            discharge_summary_id=discharge_summary.id,
            request=request,
            metadata={'format': 'html'}
        )
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Discharge Summary - Visit {discharge_summary.visit_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
        .section {{ margin: 20px 0; }}
        .label {{ font-weight: bold; color: #555; }}
        .value {{ margin-left: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>DISCHARGE SUMMARY</h1>
    
    <div class="section">
        <p><span class="label">Visit ID:</span> <span class="value">{discharge_summary.visit_id}</span></p>
        <p><span class="label">Patient:</span> <span class="value">{discharge_summary.visit.patient.get_full_name()}</span></p>
        <p><span class="label">Admission Date:</span> <span class="value">{discharge_summary.admission_date.strftime('%Y-%m-%d %H:%M')}</span></p>
        <p><span class="label">Discharge Date:</span> <span class="value">{discharge_summary.discharge_date.strftime('%Y-%m-%d %H:%M')}</span></p>
    </div>
    
    <div class="section">
        <h2>Chief Complaint</h2>
        <p>{discharge_summary.chief_complaint}</p>
    </div>
    
    <div class="section">
        <h2>Diagnosis</h2>
        <p>{discharge_summary.diagnosis}</p>
    </div>
    
    {f'<div class="section"><h2>Procedures Performed</h2><p>{discharge_summary.procedures_performed}</p></div>' if discharge_summary.procedures_performed else ''}
    
    <div class="section">
        <h2>Treatment Summary</h2>
        <p>{discharge_summary.treatment_summary}</p>
    </div>
    
    {f'<div class="section"><h2>Medications on Discharge</h2><p>{discharge_summary.medications_on_discharge}</p></div>' if discharge_summary.medications_on_discharge else ''}
    
    <div class="section">
        <h2>Follow-up Instructions</h2>
        <p>{discharge_summary.follow_up_instructions}</p>
    </div>
    
    <div class="section">
        <p><span class="label">Condition at Discharge:</span> <span class="value">{discharge_summary.get_condition_at_discharge_display()}</span></p>
        <p><span class="label">Discharge Disposition:</span> <span class="value">{discharge_summary.get_discharge_disposition_display()}</span></p>
    </div>
    
    <div class="section">
        <p><span class="label">Prepared by:</span> <span class="value">{discharge_summary.created_by.get_full_name()}</span></p>
        <p><span class="label">Date:</span> <span class="value">{discharge_summary.created_at.strftime('%Y-%m-%d %H:%M')}</span></p>
    </div>
</body>
</html>
        """
        
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="discharge_summary_{discharge_summary.visit_id}.html"'
        return response
