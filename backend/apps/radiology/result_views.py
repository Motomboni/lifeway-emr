"""
LEGACY: RadiologyOrder + RadiologyResult path (quarantined).

Endpoint: /api/v1/visits/{visit_id}/radiology/results/

Service Catalog flow uses RadiologyRequest only; report via PATCH on the request.
This ViewSet is disabled by default (LEGACY_RADIOLOGY_RESULTS_ENABLED = False).
Set to True only if you need to support legacy RadiologyOrder/RadiologyResult data.
"""

from rest_framework import status, viewsets

# Set True only to support legacy RadiologyOrder/RadiologyResult; Service Catalog uses RadiologyRequest.
LEGACY_RADIOLOGY_RESULTS_ENABLED = False
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import (
    PermissionDenied,
)
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
)
from rest_framework.response import Response

from apps.notifications.utils import send_radiology_result_notification
from apps.visits.models import Visit
from core.audit import AuditLog
from core.permissions import IsPaymentCleared, IsVisitAccessible, IsVisitOpen
from core.superuser_purge import try_superuser_destroy
from core.tenant import get_org_scoped_visit

from .models import RadiologyOrder, RadiologyRequest, RadiologyResult
from .permissions import CanUpdateRadiologyReport
from .result_serializers import (
    RadiologyResultCreateSerializer,
    RadiologyResultReadSerializer,
)


class RadiologyResultViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Radiology Results - visit-scoped.

    Rules enforced:
    - Visit-scoped architecture
    - Radiology Tech: Create results (immutable once created)
    - Doctor: View results (read-only)
    - Payment must be CLEARED
    - Visit must be OPEN
    - Audit logging
    """

    def initial(self, request, *args, **kwargs):
        """
        Ensure request.visit is set early for permission checks.
        """
        # Support visit_id from router kwargs or middleware (request.visit_id)
        visit_id = kwargs.get("visit_id") or getattr(request, "visit_id", None)
        if visit_id and not hasattr(request, "visit"):
            try:
                visit = get_org_scoped_visit(self.request, visit_id)
                request.visit = visit
            except Visit.DoesNotExist:
                # Let permissions/views handle missing visit
                pass
        # Ensure kwargs also has visit_id for downstream methods
        if visit_id and "visit_id" not in kwargs:
            kwargs["visit_id"] = visit_id
        super().initial(request, *args, **kwargs)

    def get_queryset(self):
        """
        Get radiology results for the specific visit.
        Filter by radiology orders that belong to the visit.
        """
        visit_id = self.kwargs.get("visit_id") or getattr(
            self.request, "visit_id", None
        )
        if not visit_id:
            return RadiologyResult.objects.none()

        # Get all radiology orders for this visit
        radiology_orders = RadiologyOrder.objects.filter(visit_id=visit_id)
        radiology_order_ids = radiology_orders.values_list("id", flat=True)

        return RadiologyResult.objects.filter(
            radiology_order_id__in=radiology_order_ids
        ).select_related("radiology_order", "reported_by")

    def list(self, request, *args, **kwargs):
        """List radiology results for a visit. Returns 410 if legacy path is disabled."""
        if not LEGACY_RADIOLOGY_RESULTS_ENABLED:
            return Response(
                {
                    "detail": "Legacy RadiologyResult API is disabled. Use GET /visits/{id}/radiology/ and PATCH to post reports."
                },
                status=status.HTTP_410_GONE,
            )
        import logging

        logger = logging.getLogger(__name__)
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data)
        except Exception as exc:
            logger.error("Error listing radiology results", exc_info=True)
            raise DRFValidationError(f"Error listing radiology results: {exc}")

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.

        - Create: RadiologyResultCreateSerializer (Radiology Tech only)
        - Read: RadiologyResultReadSerializer (both roles)
        """
        if self.action == "create":
            return RadiologyResultCreateSerializer
        else:
            return RadiologyResultReadSerializer

    def get_permissions(self):
        """
        Return appropriate permissions based on action.

        - Create: Radiology Tech only + Payment + Visit Open
        - Read: Both roles (Doctor and Radiology Tech) - no payment/status check for reads
        """
        if self.action == "create":
            permission_classes = [
                CanUpdateRadiologyReport,  # Radiology Tech only
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

    def _check_legacy_enabled(self):
        """Reject if legacy RadiologyResult path is disabled."""
        if not LEGACY_RADIOLOGY_RESULTS_ENABLED:
            raise PermissionDenied(
                detail="Legacy RadiologyResult API is disabled. Use PATCH on /visits/{id}/radiology/{request_id}/ to post reports."
            )

    def reject_service_catalog_order_id(self):
        """
        Reject POST when radiology_order id refers to a Service Catalog order (RadiologyRequest).
        RadiologyResult (POST /radiology/results/) is legacy-only; Service Catalog uses PATCH on the request.
        """
        order_id = self.request.data.get("radiology_order")
        if order_id is None:
            return
        if RadiologyRequest.objects.filter(pk=order_id).exists():
            raise DRFValidationError(
                "Service Catalog radiology orders (RadiologyRequest) must not use POST /radiology/results/. "
                "Use PATCH on the radiology request to post the report."
            )

    def get_visit(self):
        """Get and validate visit from URL parameter."""
        visit_id = self.kwargs.get("visit_id") or getattr(
            self.request, "visit_id", None
        )
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")

        visit = get_org_scoped_visit(self.request, visit_id)
        self.request.visit = visit
        # Ensure kwargs consistency for downstream uses
        if "visit_id" not in self.kwargs:
            self.kwargs["visit_id"] = visit_id
        return visit

    def check_visit_status(self, visit):
        """Ensure visit is OPEN before allowing mutations."""
        if visit.status == "CLOSED":
            raise PermissionDenied(
                detail="Cannot create radiology results for a CLOSED visit. "
                "Closed visits are immutable per EMR rules.",
                code="visit_closed",
            )

    def check_payment_status(self, visit):
        """Registration must be paid; radiology fees are collected post-consultation."""
        from apps.billing.payment_gates_service import is_registration_paid

        if not is_registration_paid(visit):
            raise PermissionDenied(
                detail="Registration payment is required before radiology results. "
                "Please collect registration payment at reception.",
                code="registration_payment_required",
            )

    def check_user_role(self, request):
        """Ensure user is a Radiology Tech for creating results."""
        user_role = (
            getattr(request.user, "role", None)
            or getattr(request.user, "get_role", lambda: None)()
        )

        if user_role != "RADIOLOGY_TECH":
            raise PermissionDenied(
                detail="Only Radiology Technicians can create radiology results.",
                code="role_forbidden",
            )

    def perform_create(self, serializer):
        """
        Create radiology result with strict enforcement.
        Legacy path: disabled when LEGACY_RADIOLOGY_RESULTS_ENABLED is False.
        """
        self._check_legacy_enabled()
        self.reject_service_catalog_order_id()
        visit = self.get_visit()

        # Enforce visit status
        self.check_visit_status(visit)

        # Enforce payment status
        self.check_payment_status(visit)

        # Enforce user role
        self.check_user_role(self.request)

        # Add visit to context for serializer validation
        serializer.context["visit"] = visit
        serializer.context["request"] = self.request

        # Create radiology result
        radiology_result = serializer.save()

        # Update radiology order status to PERFORMED if it was ORDERED
        if radiology_result.radiology_order.status == "ORDERED":
            radiology_result.radiology_order.status = "PERFORMED"
            radiology_result.radiology_order.save()

        # REQUIRED VIEWSET ENFORCEMENT: Audit log
        user_role = (
            getattr(self.request.user, "role", None)
            or getattr(self.request.user, "get_role", lambda: None)()
        )

        # Ensure user_role is a string (required by AuditLog model)
        if not user_role:
            user_role = "UNKNOWN"

        AuditLog.log(
            user=self.request.user,
            role=user_role,
            action="RADIOLOGY_RESULT_CREATED",
            visit_id=self.kwargs["visit_id"],
            resource_type="radiology_result",
            resource_id=radiology_result.id,
            request=self.request,
        )

        # Send email notification
        try:
            patient = visit.patient
            if patient and patient.email:
                send_radiology_result_notification(radiology_result)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send radiology result notification email: {e}")

        # Send SMS notification
        try:
            patient = visit.patient
            if patient and patient.phone:
                from apps.notifications.sms_utils import send_radiology_result_sms

                send_radiology_result_sms(radiology_result)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send radiology result notification SMS: {e}")

        return radiology_result

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve radiology result.

        Both Doctor and Radiology Tech can view results.
        """
        radiology_result = self.get_object()
        visit = radiology_result.radiology_order.visit

        # Audit log
        user_role = (
            getattr(request.user, "role", None)
            or getattr(request.user, "get_role", lambda: None)()
        )

        AuditLog.log(
            user=request.user,
            role=user_role,
            action="RADIOLOGY_RESULT_READ",
            visit_id=visit.id,
            resource_type="radiology_result",
            resource_id=radiology_result.id,
            request=request,
        )

        serializer = self.get_serializer(radiology_result)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        """
        List radiology results for visit.
        """
        try:
            visit = self.get_visit()

            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)

            return Response(serializer.data)
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error listing radiology results: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error listing radiology results: {str(e)}")

    def update(self, request, *args, **kwargs):
        """
        Update radiology result.

        Per EMR rules, radiology results are immutable once created.
        """
        raise PermissionDenied(
            detail="Radiology results are immutable once created. "
            "Cannot modify existing results.",
            code="immutable",
        )

    def partial_update(self, request, *args, **kwargs):
        """
        Partially update radiology result.

        Per EMR rules, radiology results are immutable once created.
        """
        raise PermissionDenied(
            detail="Radiology results are immutable once created. "
            "Cannot modify existing results.",
            code="immutable",
        )

    def destroy(self, request, *args, **kwargs):
        """Superusers may hard-delete for test-data cleanup."""
        response = try_superuser_destroy(self, request, *args, **kwargs)
        if response is not None:
            return response
        raise PermissionDenied(
            detail="Radiology results cannot be deleted. "
            "Results are immutable per EMR rules.",
            code="delete_forbidden",
        )
