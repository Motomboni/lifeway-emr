"""Regulatory export API endpoints."""

from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import IsPlatformAdmin

from .regulatory_export_service import (
    build_dhis2_style_export,
    build_moh_monthly_summary,
    moh_summary_to_csv,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def regulatory_moh_summary(request):
    org = getattr(request, "organization", None)
    start = parse_date(request.query_params.get("start_date") or "")
    end = parse_date(request.query_params.get("end_date") or "")
    summary = build_moh_monthly_summary(
        organization=org, start_date=start, end_date=end
    )
    if request.query_params.get("format") == "csv":
        csv_data = moh_summary_to_csv(summary)
        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="moh-summary.csv"'
        return response
    return Response(summary)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def regulatory_dhis2_export(request):
    org = getattr(request, "organization", None)
    start = parse_date(request.query_params.get("start_date") or "")
    end = parse_date(request.query_params.get("end_date") or "")
    csv_data = build_dhis2_style_export(
        organization=org, start_date=start, end_date=end
    )
    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="dhis2-export.csv"'
    return response
