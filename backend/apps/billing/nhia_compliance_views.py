"""NHIA compliance dashboard API."""

from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .nhia_compliance_service import get_nhia_compliance_summary
from .permissions import CanExportClaimPack


class NHIAComplianceDashboardView(APIView):
    """
    GET /api/v1/billing/nhia-compliance/?start_date=&end_date=
    Admin / billing staff NHIA claim readiness dashboard.
    """

    permission_classes = [IsAuthenticated, CanExportClaimPack]

    def get(self, request):
        start_raw = request.query_params.get("start_date")
        end_raw = request.query_params.get("end_date")
        start_date = parse_date(start_raw) if start_raw else None
        end_date = parse_date(end_raw) if end_raw else None
        org = getattr(request, "organization", None)
        summary = get_nhia_compliance_summary(
            start_date=start_date,
            end_date=end_date,
            organization=org,
        )
        return Response(summary)
