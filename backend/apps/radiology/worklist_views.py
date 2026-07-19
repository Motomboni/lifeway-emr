"""Radiology worklist for imaging staff."""

from django.db.models import Prefetch, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.radiology.models import RadiologyRequest
from apps.radiology.permissions import CanUpdateRadiologyReport
from apps.visits.models import Visit
from core.tenant import filter_by_organization, get_request_organization


@api_view(["GET"])
@permission_classes([IsAuthenticated, CanUpdateRadiologyReport])
def radiology_worklist(request):
    """
    GET /api/v1/radiology/requests/worklist/
    Visits with radiology requests for the imaging worklist.
    """
    status_filter = (request.query_params.get("status") or "all").lower()
    org = get_request_organization(request)

    req_qs = RadiologyRequest.objects.select_related(
        "visit", "visit__patient", "ordered_by"
    ).order_by("-created_at")

    if org:
        req_qs = req_qs.filter(visit__organization=org)

    if status_filter == "pending":
        req_qs = req_qs.filter(status="PENDING")
    elif status_filter == "completed":
        req_qs = req_qs.filter(status="COMPLETED")

    visit_ids = req_qs.values_list("visit_id", flat=True).distinct()
    visits = (
        Visit.objects.filter(id__in=visit_ids)
        .select_related("patient")
        .prefetch_related(
            Prefetch("radiology_requests", queryset=req_qs),
        )
    )
    visits = filter_by_organization(visits, request)

    results = []
    for visit in visits:
        patient = visit.patient
        results.append(
            {
                "id": visit.id,
                "status": visit.status,
                "payment_status": visit.payment_status,
                "created_at": visit.created_at,
                "patient": patient.id if patient else None,
                "patient_name": patient.get_full_name() if patient else "",
                "patient_id_display": getattr(patient, "patient_id", "") or "",
                "radiology_requests": [
                    {
                        "id": r.id,
                        "study_type": r.study_type,
                        "status": r.status,
                        "clinical_indication": r.clinical_indication,
                        "image_count": r.image_count,
                        "ordered_by_name": (
                            f"{r.ordered_by.first_name} {r.ordered_by.last_name}".strip()
                            if r.ordered_by
                            else ""
                        ),
                        "created_at": r.created_at,
                        "pacs_study_id": getattr(
                            getattr(r, "pacs_study", None), "id", None
                        ),
                    }
                    for r in visit.radiology_requests.all()
                ],
            }
        )

    return Response({"count": len(results), "results": results})
