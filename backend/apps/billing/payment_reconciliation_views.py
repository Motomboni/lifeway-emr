"""Bank transfer / USSD payment reconciliation API."""

from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.visits.models import Visit
from core.permissions import IsStaffOrAdminRole

from .permissions import CanProcessPayment

from .payment_reconciliation_models import PaymentReconciliation


def _serialize(rec: PaymentReconciliation) -> dict:
    return {
        "id": rec.id,
        "visit_id": rec.visit_id,
        "payment_id": rec.payment_id,
        "method": rec.method,
        "reference": rec.reference,
        "amount_ngn": str(rec.amount_ngn),
        "payer_name": rec.payer_name,
        "bank_name": rec.bank_name,
        "status": rec.status,
        "notes": rec.notes,
        "recorded_by": rec.recorded_by_id,
        "matched_at": rec.matched_at,
        "created_at": rec.created_at,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsStaffOrAdminRole])
def payment_reconciliation_list(request):
    qs = PaymentReconciliation.objects.select_related("visit", "recorded_by").order_by(
        "-created_at"
    )
    status_filter = request.query_params.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter.upper())
    if request.method == "GET":
        return Response([_serialize(r) for r in qs[:200]])

    visit_id = request.data.get("visit_id")
    visit = None
    if visit_id:
        visit = get_object_or_404(Visit, id=visit_id)
    try:
        amount = Decimal(str(request.data.get("amount_ngn") or "0"))
    except InvalidOperation:
        return Response(
            {"detail": "Invalid amount_ngn."}, status=status.HTTP_400_BAD_REQUEST
        )
    reference = (request.data.get("reference") or "").strip()
    if not reference:
        return Response(
            {"detail": "reference is required."}, status=status.HTTP_400_BAD_REQUEST
        )
    rec = PaymentReconciliation.objects.create(
        visit=visit,
        method=request.data.get("method") or "BANK_TRANSFER",
        reference=reference,
        amount_ngn=amount,
        payer_name=request.data.get("payer_name") or "",
        bank_name=request.data.get("bank_name") or "",
        notes=request.data.get("notes") or "",
        recorded_by=request.user,
    )
    return Response(_serialize(rec), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanProcessPayment])
def payment_reconciliation_match(request, rec_id: int):
    rec = get_object_or_404(PaymentReconciliation, id=rec_id)
    rec.status = "MATCHED"
    rec.matched_at = timezone.now()
    if request.data.get("notes"):
        rec.notes = request.data["notes"]
    payment_id = request.data.get("payment_id")
    if payment_id:
        rec.payment_id = payment_id
    rec.save()
    return Response(_serialize(rec))


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanProcessPayment])
def payment_reconciliation_dispute(request, rec_id: int):
    rec = get_object_or_404(PaymentReconciliation, id=rec_id)
    rec.status = "DISPUTED"
    rec.notes = request.data.get("notes") or rec.notes
    rec.save(update_fields=["status", "notes"])
    return Response(_serialize(rec))
