"""Insurance claims API: create claim, submit, list. Billing staff only."""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .claim_service import generate_claim, submit_claim
from .insurance_models import Claim, ClaimPolicy

logger = logging.getLogger(__name__)


def _is_billing_staff(user):
    return getattr(user, "role", None) in ("RECEPTIONIST", "ADMIN")


from core.tenant import filter_by_patient_organization, get_org_scoped_patient


class InsurancePolicyViewSet(viewsets.ModelViewSet):
    """CRUD insurance policies. Billing staff."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not _is_billing_staff(self.request.user):
            return ClaimPolicy.objects.none()
        return filter_by_patient_organization(
            ClaimPolicy.objects.all()
            .select_related("patient", "provider")
            .order_by("-created_at"),
            self.request,
        )

    def get_serializer_class(self):
        from .claims_serializers import ClaimPolicySerializer

        return ClaimPolicySerializer

    def perform_create(self, serializer):
        if not _is_billing_staff(self.request.user):
            raise PermissionDenied("Only billing staff can manage policies.")
        serializer.save()

    def list(self, request, *args, **kwargs):
        if not _is_billing_staff(request.user):
            return Response(
                {"detail": "Only billing staff can view policies."}, status=403
            )
        return super().list(request, *args, **kwargs)


class ClaimViewSet(viewsets.ModelViewSet):
    """Create claim, submit, list. Billing staff only."""

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if not _is_billing_staff(self.request.user):
            return Claim.objects.none()
        return filter_by_patient_organization(
            Claim.objects.all()
            .select_related("patient", "policy__provider")
            .order_by("-created_at"),
            self.request,
        )

    def list(self, request, *args, **kwargs):
        if not _is_billing_staff(request.user):
            return Response(
                {"detail": "Only billing staff can view claims."}, status=403
            )
        qs = self.get_queryset()
        provider_id = request.query_params.get("provider_id")
        if provider_id:
            qs = qs.filter(policy__provider_id=provider_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        from .claims_serializers import ClaimSerializer

        serializer = ClaimSerializer(qs, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        if not _is_billing_staff(request.user):
            raise PermissionDenied("Only billing staff can create claims.")
        patient_id = request.data.get("patient_id")
        policy_id = request.data.get("policy_id")
        services = request.data.get("services")
        if not patient_id and not policy_id:
            return Response(
                {"detail": "Provide patient_id or policy_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.patients.models import Patient

        if policy_id:
            policy = get_object_or_404(ClaimPolicy, id=policy_id)
            if hasattr(request, "organization") and request.organization:
                if policy.patient.organization_id != request.organization.id:
                    raise PermissionDenied("Policy does not belong to your organization.")
            patient = policy.patient
        else:
            patient = get_org_scoped_patient(request, patient_id)
            policy = None
        try:
            claim = generate_claim(patient, services=services, policy=policy)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        from .claims_serializers import ClaimSerializer

        return Response(ClaimSerializer(claim).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        if not _is_billing_staff(request.user):
            raise PermissionDenied("Only billing staff can submit claims.")
        claim = get_object_or_404(Claim, pk=pk)
        try:
            ok, new_status, payload = submit_claim(claim.id)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        from .claims_serializers import ClaimSerializer

        claim.refresh_from_db()
        return Response(ClaimSerializer(claim).data)
