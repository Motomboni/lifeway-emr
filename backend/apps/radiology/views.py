"""
Radiology Request ViewSet - strictly visit-scoped and consultation-dependent.

Endpoint: /api/v1/visits/{visit_id}/radiology/

Enforcement:
1. Visit-scoped: All operations require visit_id in URL
2. Consultation-dependent: Consultation must exist before radiology requests
3. Doctor: Can create requests, view all (including reports)
4. Radiology Tech: Can only update reports, cannot create requests
5. Payment must be CLEARED
6. Visit must be OPEN
7. Audit logging required
8. No standalone radiology flow allowed
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    NotFound,
    ValidationError as DRFValidationError,
)
from django.shortcuts import get_object_or_404

from .models import RadiologyRequest, RadiologyOrder
from .serializers import (
    RadiologyRequestSerializer,
    RadiologyRequestCreateSerializer,
    RadiologyRequestReportSerializer,
    RadiologyRequestReadSerializer,
    RadiologyOrderSerializer,
    RadiologyOrderCreateSerializer,
)
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from core.permissions import IsVisitOpen, IsPaymentCleared, IsVisitAccessible
from .permissions import (
    IsDoctorOrRadiologyTech,
    CanCreateRadiologyRequest,
    CanUpdateRadiologyReport,
    CanViewRadiologyRequest,
)
from core.audit import AuditLog


def _ensure_radiology_billing_for_visit(visit, created_by=None):
    """
    Ensure at least one RADIOLOGY_STUDY BillingLineItem exists for the visit (post-report billing).
    If none exists, create one using the first active RADIOLOGY_STUDY service.
    """
    from apps.billing.billing_line_item_models import BillingLineItem
    from apps.billing.billing_line_item_service import get_or_create_billing_line_item
    from apps.billing.service_catalog_models import ServiceCatalog

    if BillingLineItem.objects.filter(
        visit=visit,
        service_catalog__workflow_type='RADIOLOGY_STUDY',
    ).exists():
        return
    radiology_service = ServiceCatalog.objects.filter(
        workflow_type='RADIOLOGY_STUDY',
        is_active=True,
    ).order_by('id').first()
    if radiology_service:
        get_or_create_billing_line_item(
            service=radiology_service,
            visit=visit,
            consultation=None,
            created_by=created_by,
        )


def _template_report_draft(study_type: str, clinical_indication: str) -> str:
    """Fallback template when LLM is unavailable or fails."""
    indication = clinical_indication.strip() or 'Clinical indication not specified.'
    return (
        f"EXAMINATION: {study_type}\n\n"
        f"CLINICAL INDICATION: {indication}\n\n"
        "TECHNIQUE: Standard imaging protocol.\n\n"
        "FINDINGS:\n"
        "[Describe findings here.]\n\n"
        "IMPRESSION:\n"
        "[Summarize impression here.]"
    )


def _generate_report_draft(
    study_type: str,
    clinical_indication: str,
    request=None,
    radiology_request=None,
) -> str:
    """
    Generate a radiology report draft using LLM when configured, else template.
    Uses apps.ai_integration (OpenAI/Anthropic). Set OPENAI_API_KEY or ANTHROPIC_API_KEY
    and optionally RADIOLOGY_DRAFT_LLM_PROVIDER / RADIOLOGY_DRAFT_LLM_MODEL in settings.
    """
    import os
    from django.conf import settings

    indication = (clinical_indication or '').strip() or 'Clinical indication not specified.'
    system_prompt = (
        "You are a radiology report assistant. Generate a concise, professional "
        "radiology report draft in plain text. Use sections: EXAMINATION, CLINICAL INDICATION, "
        "TECHNIQUE, FINDINGS, and IMPRESSION. Do not invent specific findings; use placeholder "
        "text like '[Describe findings here.]' and '[Summarize impression here.]' where the "
        "radiologist will fill in. Do not include patient identifiers or PHI."
    )
    user_prompt = (
        f"Study type: {study_type}\n"
        f"Clinical indication: {indication}\n\n"
        "Generate a short draft report (template-style, no invented findings)."
    )

    provider_name = getattr(settings, 'RADIOLOGY_DRAFT_LLM_PROVIDER', 'openai').lower()
    model = getattr(settings, 'RADIOLOGY_DRAFT_LLM_MODEL', 'gpt-4o-mini')
    if provider_name == 'anthropic':
        model = getattr(settings, 'RADIOLOGY_DRAFT_LLM_MODEL', 'claude-3-haiku-20240307')
    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('ANTHROPIC_API_KEY') or ''
    if provider_name == 'anthropic':
        api_key = os.environ.get('ANTHROPIC_API_KEY') or ''
    else:
        api_key = os.environ.get('OPENAI_API_KEY') or ''

    if not api_key:
        return _template_report_draft(study_type, clinical_indication)

    try:
        from apps.ai_integration.models import AIProvider
        from apps.ai_integration.services import AIServiceFactory, AIServiceError

        provider = AIProvider.ANTHROPIC if provider_name == 'anthropic' else AIProvider.OPENAI
        service = AIServiceFactory.create_service(provider=provider, model=model, api_key=api_key)
        result = service.generate(
            user_prompt,
            system_prompt=system_prompt,
            max_tokens=1500,
            temperature=0.3,
        )
        return (result.get('content') or '').strip() or _template_report_draft(study_type, clinical_indication)
    except Exception:
        return _template_report_draft(study_type, clinical_indication)


def log_radiology_request_action(
    user,
    action,
    visit_id,
    radiology_request_id=None,
    request=None,
    metadata=None
):
    """
    Log a radiology request action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'create', 'update_report', 'read')
        visit_id: Visit ID (required)
        radiology_request_id: Radiology Request ID if applicable
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
        action=f'radiology_request.{action}',
        visit_id=visit_id,
        resource_type='radiology_request',
        resource_id=radiology_request_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


class RadiologyRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Radiology Requests - visit-scoped and consultation-dependent.
    
    Rules enforced:
    - Visit-scoped architecture
    - Consultation-dependent (consultation must exist)
    - Doctor: Create requests, view all
    - Radiology Tech: Update reports only, cannot create
    - Payment must be CLEARED
    - Visit must be OPEN
    - Audit logging
    """
    # Restrict lookup to numeric IDs so nested paths (e.g., results/) are not
    # misinterpreted as a detail lookup for this viewset.
    lookup_value_regex = r'\d+'
    
    def get_queryset(self):
        """
        Get radiology requests for the specific visit.
        Role-based filtering:
        - Doctor: Sees all radiology requests
        - Radiology Tech: Sees all radiology requests (but limited fields in serializer)
        """
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return RadiologyRequest.objects.none()
        
        return RadiologyRequest.objects.filter(visit_id=visit_id).select_related(
            'consultation',
            'ordered_by',
            'reported_by'
        )
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action and user role.
        
        - Create: RadiologyRequestCreateSerializer (Doctor only)
        - Update (report): RadiologyRequestReportSerializer (Radiology Tech only)
        - Read: RadiologyRequestReadSerializer (role-based fields)
        """
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if self.action == 'create':
            return RadiologyRequestCreateSerializer
        elif self.action in ['update', 'partial_update']:
            # Check if Radiology Tech is updating report
            if user_role == 'RADIOLOGY_TECH':
                return RadiologyRequestReportSerializer
            # Doctor cannot update (only view)
            return RadiologyRequestReadSerializer
        else:
            return RadiologyRequestReadSerializer
    
    def get_permissions(self):
        """
        Return appropriate permissions based on action.
        
        - Create: Doctor only (CanCreateRadiologyRequest) + Payment + Visit Open
        - Update: Radiology Tech only (CanUpdateRadiologyReport) + Payment + Visit Open
        - Read: Both roles (CanViewRadiologyRequest) - no payment/status check for reads
        """
        if self.action == 'create':
            permission_classes = [
                CanCreateRadiologyRequest,
                IsVisitOpen,
                IsPaymentCleared,
            ]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [
                CanUpdateRadiologyReport,
                IsVisitOpen,
                IsPaymentCleared,
            ]
        else:
            # Read operations: Allow authenticated users (for billing/audit purposes)
            from rest_framework.permissions import IsAuthenticated
            permission_classes = [
                IsAuthenticated,
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
        Radiology requests REQUIRE consultation context.
        """
        consultation = Consultation.objects.filter(visit=visit).first()
        
        if not consultation:
            raise DRFValidationError(
                "Consultation must exist before creating radiology requests. "
                "Please create a consultation first."
            )
        
        return consultation
    
    def check_visit_status(self, visit):
        """Ensure visit is OPEN before allowing mutations."""
        if visit.status == 'CLOSED':
            raise PermissionDenied(
                detail="Cannot create or modify radiology requests for a CLOSED visit. "
                       "Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
    
    def check_payment_status(self, visit):
        """Ensure payment is cleared before allowing radiology requests."""
        if not visit.is_payment_cleared():
            raise PermissionDenied(
                detail="Payment must be cleared before creating radiology requests. "
                       "Current payment status: {status}".format(
                           status=visit.payment_status
                       ),
                code='payment_not_cleared'
            )
    
    def perform_create(self, serializer):
        """
        Create radiology request with strict enforcement.
        
        Rules:
        1. Only Doctor can create (enforced by CanCreateRadiologyRequest)
        2. Visit must be OPEN
        3. Payment must be CLEARED
        4. Consultation must exist
        5. ordered_by set to authenticated user (doctor)
        6. Audit log created
        """
        visit = self.get_visit()
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # Get consultation (required)
        consultation = self.get_consultation(visit)
        
        # Check user role
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role != 'DOCTOR':
            raise PermissionDenied(
                detail="Only doctors can create radiology requests. "
                       "Radiology Tech can only update reports.",
                code='role_forbidden'
            )
        
        # Create radiology request
        radiology_request = serializer.save(
            visit=visit,
            consultation=consultation,
            ordered_by=self.request.user,
            status='PENDING'
        )
        
        # Audit log
        log_radiology_request_action(
            user=self.request.user,
            action='create',
            visit_id=visit.id,
            radiology_request_id=radiology_request.id,
            request=self.request
        )
        
        return radiology_request
    
    def perform_update(self, serializer):
        """
        Update radiology request with role-based enforcement.
        
        Rules:
        1. Radiology Tech can only update reports
        2. Doctor cannot update (only view)
        3. Visit must be OPEN
        4. Payment must be CLEARED
        5. Audit log created
        """
        radiology_request = self.get_object()
        visit = radiology_request.visit
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # Check user role
        user_role = getattr(self.request.user, 'role', None) or \
                   getattr(self.request.user, 'get_role', lambda: None)()
        
        if user_role == 'RADIOLOGY_TECH':
            # Radiology Tech can update reports; status is COMPLETED when report provided
            from django.utils import timezone
            updated_request = serializer.save(
                reported_by=self.request.user,
                report_date=timezone.now(),
                status='COMPLETED' if serializer.validated_data.get('report') else 'PENDING'
            )

            # Post-report billing: ensure a RADIOLOGY_STUDY BillingLineItem exists for this visit
            if serializer.validated_data.get('report') and updated_request.status == 'COMPLETED':
                _ensure_radiology_billing_for_visit(visit, created_by=self.request.user)

            # Audit log
            log_radiology_request_action(
                user=self.request.user,
                action='update_report',
                visit_id=visit.id,
                radiology_request_id=updated_request.id,
                request=self.request
            )

            return updated_request
        else:
            # Doctor cannot update radiology requests (only view)
            raise PermissionDenied(
                detail="Doctors cannot update radiology requests. "
                       "Only Radiology Tech can post reports.",
                code='role_forbidden'
            )

    @action(detail=True, methods=['post'], url_path='draft-report')
    def draft_report(self, request, visit_id=None, pk=None):
        """
        AI-assisted draft for radiology report (Service Catalog).
        POST body: { study_type: string, clinical_indication: string }.
        Returns: { draft: string }. Replace with LLM when integrated.
        """
        radiology_request = self.get_object()
        study_type = (request.data.get('study_type') or radiology_request.study_type) or 'Imaging'
        clinical_indication = (request.data.get('clinical_indication') or radiology_request.clinical_indication) or ''
        draft = _generate_report_draft(
            study_type=study_type,
            clinical_indication=clinical_indication,
            request=request,
            radiology_request=radiology_request,
        )
        return Response({'draft': draft})

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve radiology request with role-based field visibility.
        
        Doctor: Sees all fields
        Radiology Tech: Sees limited fields (no consultation details)
        """
        radiology_request = self.get_object()
        visit = radiology_request.visit
        
        # Audit log
        log_radiology_request_action(
            user=request.user,
            action='read',
            visit_id=visit.id,
            radiology_request_id=radiology_request.id,
            request=request
        )
        
        serializer = self.get_serializer(radiology_request)
        return Response(serializer.data)
    
    def list(self, request, *args, **kwargs):
        """
        List radiology requests for visit.
        Role-based field visibility applied via serializer.
        """
        visit = self.get_visit()
        
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete radiology request.
        Per EMR rules, radiology requests should not be deleted (soft-delete only).
        This endpoint is disabled for compliance.
        """
        raise PermissionDenied(
            detail="Radiology requests cannot be deleted. "
                   "Use status CANCELLED instead for compliance.",
            code='delete_forbidden'
        )


# === Radiology Orders API (aligned with frontend expectations) ===
class RadiologyOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Radiology Orders - visit-scoped.
    Doctor creates orders; Doctor and Radiology Tech can view.
    """

    lookup_value_regex = r'\d+'

    def initial(self, request, *args, **kwargs):
        """Ensure visit is attached to request for permission checks."""
        visit_id = kwargs.get("visit_id") or getattr(request, "visit_id", None)
        if visit_id and not hasattr(request, "visit"):
            try:
                visit = Visit.objects.get(pk=visit_id)
                request.visit = visit
            except Visit.DoesNotExist:
                pass
        if visit_id and "visit_id" not in kwargs:
            kwargs["visit_id"] = visit_id
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        visit_id = self.kwargs.get('visit_id') or getattr(self.request, "visit_id", None)
        if not visit_id:
            return RadiologyOrder.objects.none()
        return RadiologyOrder.objects.filter(visit_id=visit_id).select_related('ordered_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return RadiologyOrderCreateSerializer
        return RadiologyOrderSerializer

    def get_permissions(self):
        if self.action == 'create':
            perms = [CanCreateRadiologyRequest, IsVisitOpen, IsPaymentCleared]
        else:
            # Read operations: Allow viewing for authenticated users (for billing/audit)
            from rest_framework.permissions import IsAuthenticated
            perms = [IsAuthenticated]
        return [perm() for perm in perms]

    def get_visit(self):
        visit_id = self.kwargs.get('visit_id') or getattr(self.request, "visit_id", None)
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        visit = get_object_or_404(Visit, pk=visit_id)
        self.request.visit = visit
        if "visit_id" not in self.kwargs:
            self.kwargs["visit_id"] = visit_id
        return visit

    def perform_create(self, serializer):
        visit = self.get_visit()
        serializer.context['visit'] = visit
        serializer.context['request'] = self.request
        return serializer.save()
