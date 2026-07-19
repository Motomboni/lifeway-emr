"""Laboratory order worklist for lab scientists."""

from django.db.models import Prefetch
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.laboratory.models import LabOrder
from apps.laboratory.permissions import IsDoctorOrLabTech
from apps.visits.models import Visit
from core.tenant import filter_by_organization, get_request_organization


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsDoctorOrLabTech])
def lab_order_worklist(request):
    """
    GET /api/v1/laboratory/orders/worklist/
    Visits with lab orders for the lab fulfillment queue.
    """
    status_filter = (request.query_params.get("status") or "all").lower()
    org = get_request_organization(request)

    order_qs = LabOrder.objects.select_related(
        "visit", "visit__patient", "ordered_by"
    ).order_by("-created_at")

    if org:
        order_qs = order_qs.filter(visit__organization=org)

    if status_filter == "pending":
        order_qs = order_qs.exclude(status=LabOrder.Status.RESULT_READY)
    elif status_filter == "completed":
        order_qs = order_qs.filter(status=LabOrder.Status.RESULT_READY)

    visit_ids = order_qs.values_list("visit_id", flat=True).distinct()
    visits = Visit.objects.filter(id__in=visit_ids).select_related("patient").prefetch_related(
        Prefetch("lab_orders", queryset=order_qs),
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
                "lab_orders": [
                    {
                        "id": order.id,
                        "status": order.status,
                        "tests_requested": order.tests_requested,
                        "clinical_indication": order.clinical_indication,
                        "created_at": order.created_at,
                        "ordered_by_name": (
                            f"{order.ordered_by.first_name} {order.ordered_by.last_name}".strip()
                            if order.ordered_by
                            else ""
                        ),
                    }
                    for order in visit.lab_orders.all()
                ],
            }
        )

    return Response({"count": len(results), "page": 1, "page_size": 500, "results": results})
