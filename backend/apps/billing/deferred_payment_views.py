"""
Deferred legacy payment API — LIFEWAY flexible-payment settlement (Receptionist only).
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .legacy_deferred_service import (
    list_and_serialize_unsettled_deferred_charges,
    settle_deferred_charge,
)
from .permissions import CanProcessPayment


class DeferredPaymentsListView(APIView):
    """GET /api/v1/billing/deferred-payments/ — unsettled legacy deferred charges."""

    permission_classes = [IsAuthenticated, CanProcessPayment]

    def get(self, request):
        search = request.query_params.get("search", "")
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(100, max(1, int(request.query_params.get("page_size", 48))))
        except (TypeError, ValueError):
            page_size = 48

        total, results = list_and_serialize_unsettled_deferred_charges(
            search=search,
            page=page,
            page_size=page_size,
        )
        return Response(
            {
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )


class DeferredPaymentSettleView(APIView):
    """POST /api/v1/billing/deferred-payments/{charge_id}/settle/"""

    permission_classes = [IsAuthenticated, CanProcessPayment]

    def post(self, request, charge_id):
        amount_str = request.data.get("amount")
        payment_method = request.data.get("payment_method", "CASH")
        transaction_reference = request.data.get("transaction_reference", "")
        notes = request.data.get("notes", "")

        try:
            amount = Decimal(str(amount_str))
        except (InvalidOperation, TypeError):
            return Response(
                {"detail": "Invalid amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = settle_deferred_charge(
                charge_id,
                amount=amount,
                payment_method=payment_method,
                processed_by=request.user,
                transaction_reference=transaction_reference or "",
                notes=notes or "",
            )
        except ValidationError as exc:
            detail = exc.messages[0] if getattr(exc, "messages", None) else str(exc)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_201_CREATED)
