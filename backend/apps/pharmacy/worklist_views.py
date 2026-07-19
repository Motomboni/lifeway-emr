"""Pharmacy prescription worklist for dispensing staff."""

from django.db.models import Prefetch
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.pharmacy.models import Prescription
from apps.pharmacy.permissions import CanViewPrescription
from apps.visits.models import Visit
from core.tenant import filter_by_organization, get_request_organization


@api_view(["GET"])
@permission_classes([IsAuthenticated, CanViewPrescription])
def prescription_worklist(request):
    """
    GET /api/v1/drugs/prescriptions/worklist/
    Visits with prescriptions for pharmacy fulfillment.
    """
    status_filter = (request.query_params.get("status") or "all").lower()
    org = get_request_organization(request)

    rx_qs = Prescription.objects.select_related(
        "visit", "visit__patient", "prescribed_by"
    ).order_by("-created_at")

    if org:
        rx_qs = rx_qs.filter(visit__organization=org)

    if status_filter == "pending":
        rx_qs = rx_qs.filter(status="PENDING", dispensed=False)
    elif status_filter == "dispensed":
        rx_qs = rx_qs.filter(status="DISPENSED", dispensed=True)

    visit_ids = rx_qs.values_list("visit_id", flat=True).distinct()
    visits = Visit.objects.filter(id__in=visit_ids).select_related("patient").prefetch_related(
        Prefetch("prescriptions", queryset=rx_qs),
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
                "prescriptions": [
                    {
                        "id": rx.id,
                        "drug": rx.drug,
                        "status": rx.status,
                        "dispensed": rx.dispensed,
                        "dosage": rx.dosage,
                        "quantity": rx.quantity,
                        "created_at": rx.created_at,
                    }
                    for rx in visit.prescriptions.all()
                ],
            }
        )

    return Response({"count": len(results), "page": 1, "page_size": 500, "results": results})
