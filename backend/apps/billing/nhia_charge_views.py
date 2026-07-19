"""
Visit-scoped NHIA billing endpoints (scribe → bill).
"""

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.audit import AuditLog
from core.permissions import IsVisitOpen

from .billing_endpoints import BillingEndpointView
from .nhia_charge_service import add_nhia_charges_from_scribe
from .permissions import CanAddServicesFromCatalog


class NHIAScribeChargesView(BillingEndpointView):
    """
    POST /api/v1/visits/{visit_id}/billing/nhia-charges/

    Add validated NHIA tariff items from Clinical AI Scribe to the visit bill.
    Doctor or Receptionist; visit must be OPEN.
    """

    permission_classes = [IsAuthenticated, CanAddServicesFromCatalog, IsVisitOpen]

    def post(self, request, visit_id):
        visit = self.get_visit(visit_id)
        codes = request.data.get("codes")
        if not isinstance(codes, list) or not codes:
            raise DRFValidationError(
                {"codes": ["Required list of {nhia, icd11, diagnosis} objects."]}
            )

        only_matched = request.data.get("only_matched", True)
        try:
            result = add_nhia_charges_from_scribe(
                visit,
                codes,
                only_matched=bool(only_matched),
            )
        except ValidationError as exc:
            raise DRFValidationError(str(exc)) from exc

        user_role = (
            getattr(request.user, "role", None)
            or getattr(request.user, "get_role", lambda: None)()
        )
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="NHIA_SCRIBE_CHARGES_ADDED",
            visit_id=visit_id,
            resource_type="visit",
            resource_id=visit_id,
            request=request,
            metadata={
                "created_count": result["created_count"],
                "skipped_count": result["skipped_count"],
            },
        )

        return Response(result, status=status.HTTP_201_CREATED)
