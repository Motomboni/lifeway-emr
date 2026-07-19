"""
NHIA/HMO claim pack export API.
"""

from datetime import datetime

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import AuditLog
from core.tenant import get_org_scoped_visit

from .claim_pack_service import (
    build_batch_claim_pack,
    build_visit_claim_pack,
    claim_pack_to_csv,
)
from .permissions import CanExportClaimPack


class VisitClaimPackView(APIView):
    """
    GET /api/v1/visits/{visit_id}/billing/claim-pack/
    GET /api/v1/visits/{visit_id}/billing/claim-pack/?format=csv
    """

    permission_classes = [IsAuthenticated, CanExportClaimPack]

    def get(self, request, visit_id):
        visit = get_org_scoped_visit(request, int(visit_id))
        pack = build_visit_claim_pack(visit)
        export_format = (request.query_params.get("format") or "json").lower()

        if export_format == "csv":
            csv_body = claim_pack_to_csv([pack])
            response = HttpResponse(csv_body, content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="claim_pack_visit_{visit_id}.csv"'
            )
            return response

        return Response(pack, status=status.HTTP_200_OK)


class BatchClaimPackView(APIView):
    """
    GET /api/v1/billing/claim-pack/?start_date=&end_date=
    POST /api/v1/billing/claim-pack/  { "visit_ids": [1, 2] }
    """

    permission_classes = [IsAuthenticated, CanExportClaimPack]

    def _parse_dates(self, request):
        start_raw = request.query_params.get("start_date") or request.data.get(
            "start_date"
        )
        end_raw = request.query_params.get("end_date") or request.data.get("end_date")
        start_date = parse_date(start_raw) if start_raw else None
        end_date = parse_date(end_raw) if end_raw else None
        return start_date, end_date

    def get(self, request):
        start_date, end_date = self._parse_dates(request)
        org = getattr(request, "organization", None)
        batch = build_batch_claim_pack(
            start_date=start_date,
            end_date=end_date,
            organization=org,
        )
        export_format = (request.query_params.get("format") or "json").lower()
        if export_format == "csv":
            csv_body = claim_pack_to_csv(batch["packs"])
            response = HttpResponse(csv_body, content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="claim_pack_{datetime.now():%Y%m%d}.csv"'
            )
            return response
        return Response(batch, status=status.HTTP_200_OK)

    def post(self, request):
        visit_ids = request.data.get("visit_ids")
        if not isinstance(visit_ids, list) or not visit_ids:
            raise DRFValidationError({"visit_ids": ["Required list of visit IDs."]})
        start_date, end_date = self._parse_dates(request)
        org = getattr(request, "organization", None)
        batch = build_batch_claim_pack(
            start_date=start_date,
            end_date=end_date,
            visit_ids=[int(v) for v in visit_ids],
            organization=org,
        )

        user_role = (
            getattr(request.user, "role", None)
            or getattr(request.user, "get_role", lambda: None)()
        )
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="NHIA_CLAIM_PACK_EXPORT",
            visit_id=None,
            resource_type="claim_pack",
            resource_id=0,
            request=request,
            metadata={
                "visit_count": batch["visit_count"],
                "claim_ready_count": batch["claim_ready_count"],
            },
        )

        export_format = (request.data.get("format") or "json").lower()
        if export_format == "csv":
            csv_body = claim_pack_to_csv(batch["packs"])
            response = HttpResponse(csv_body, content_type="text/csv")
            response["Content-Disposition"] = (
                f'attachment; filename="claim_pack_batch_{datetime.now():%Y%m%d}.csv"'
            )
            return response
        return Response(batch, status=status.HTTP_200_OK)
