"""
Central Billing Queue - Receptionist dashboard.

Per strict payment rules:
- Post-consultation bills (Lab, Pharmacy, Radiology, etc.) enter this queue
- Only Receptionist can view and process payments from this queue
- Each entry: patient, department, itemized charges, status, linked consultation
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from decimal import Decimal, InvalidOperation

from apps.visits.models import Visit
from apps.consultations.models import Consultation
from .billing_line_item_models import BillingLineItem
from .billing_service import BillingService
from .models import Payment, VisitCharge
from .permissions import CanProcessPayment
from core.audit import AuditLog
from .legacy_deferred_service import list_and_serialize_unsettled_deferred_charges, settle_deferred_charge


class BillingPendingQueueView(APIView):
    """
    GET /api/v1/billing/pending-queue/
    
    Unified billing queue for Receptionist: all visits with pending (unpaid or partially paid)
    BillingLineItems, plus legacy VisitCharges from migrated visits. Receptionist-only.
    
    Returns:
    - visits: list of { visit_id, patient, items[], total_pending, status, consultation_ref }
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def get(self, request):
        # Only Receptionist can access (CanProcessPayment)
        visit_ids_with_pending_line_items = (
            BillingLineItem.objects.filter(
                bill_status__in=['PENDING', 'PARTIALLY_PAID']
            )
            .values_list('visit_id', flat=True)
            .distinct()
        )
        visit_ids_with_legacy_charges = (
            VisitCharge.objects.values_list('visit_id', flat=True).distinct()
        )
        visits = (
            Visit.objects.filter(
                Q(id__in=visit_ids_with_pending_line_items) |
                Q(id__in=visit_ids_with_legacy_charges)
            )
            .select_related('patient')
            .prefetch_related(
                Prefetch(
                    'billing_line_items',
                    queryset=BillingLineItem.objects.filter(
                        bill_status__in=['PENDING', 'PARTIALLY_PAID']
                    ).select_related('service_catalog').order_by('service_catalog__department', 'created_at')
                ),
                Prefetch(
                    'charges',
                    queryset=VisitCharge.objects.order_by('category', 'created_at'),
                ),
            )
            .distinct()
            .order_by('-updated_at')
        )
        department_to_category = {
            'LAB': 'LAB',
            'PHARMACY': 'DRUG',
            'RADIOLOGY': 'RADIOLOGY',
            'PROCEDURE': 'PROCEDURE',
            'CONSULTATION': 'CONSULTATION',
        }
        result = []
        for visit in visits:
            items = []
            total_pending = Decimal('0.00')
            line_items = list(visit.billing_line_items.all())
            for li in line_items:
                dept = li.service_catalog.department if li.service_catalog else 'MISC'
                category = department_to_category.get(dept, 'MISC')
                items.append({
                    'id': li.id,
                    'department': category,
                    'description': li.source_service_name,
                    'amount': str(li.amount),
                    'amount_paid': str(li.amount_paid),
                    'outstanding': str(li.outstanding_amount),
                    'status': li.bill_status,
                })
                total_pending += li.outstanding_amount
            if not line_items:
                summary = BillingService.compute_billing_summary(visit)
                if summary.outstanding_balance <= 0:
                    continue
                legacy_charges = list(visit.charges.all())
                if not legacy_charges:
                    continue
                total_pending = summary.outstanding_balance
                for charge in legacy_charges:
                    items.append({
                        'id': -charge.id,
                        'department': charge.category,
                        'description': charge.description,
                        'amount': str(charge.amount),
                        'amount_paid': '0.00',
                        'outstanding': str(charge.amount),
                        'status': 'PENDING',
                    })
            consultation = Consultation.objects.filter(visit=visit).first()
            result.append({
                'visit_id': visit.id,
                'patient': {
                    'id': visit.patient.id,
                    'name': f"{visit.patient.first_name} {visit.patient.last_name}".strip() or f"Patient #{visit.patient.id}",
                },
                'items': items,
                'total_pending': str(total_pending),
                'consultation_id': consultation.id if consultation else None,
                'visit_status': visit.status,
            })
        AuditLog.log(
            user=request.user,
            role=getattr(request.user, 'role', None),
            action='BILLING_PENDING_QUEUE_VIEWED',
            visit_id=None,
            resource_type='billing_queue',
            resource_id=None,
            request=request,
        )
        return Response({'visits': result}, status=status.HTTP_200_OK)


class BillingPaymentHistoryView(APIView):
    """
    GET /api/v1/billing/payments/

    Receptionist-facing payment history across all visits. This is intentionally
    read-only and includes migrated legacy payments that were attached to visits.
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]

    def get(self, request):
        page = max(int(request.query_params.get('page', 1)), 1)
        page_size = min(max(int(request.query_params.get('page_size', 50)), 1), 200)
        status_filter = (request.query_params.get('status') or '').strip().upper()
        legacy_only = (request.query_params.get('legacy_only') or '').strip().lower() in {'1', 'true', 'yes'}
        search = (request.query_params.get('search') or '').strip()

        queryset = Payment.objects.select_related('visit__patient', 'processed_by').order_by('-created_at', '-id')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if legacy_only:
            queryset = queryset.filter(notes__startswith='[Legacy PatientPayID:')
        if search:
            search_q = (
                Q(transaction_reference__icontains=search)
                | Q(notes__icontains=search)
                | Q(visit__patient__first_name__icontains=search)
                | Q(visit__patient__last_name__icontains=search)
                | Q(visit__patient__patient_id__icontains=search)
            )
            if search.isdigit():
                search_q = search_q | Q(id=int(search)) | Q(visit_id=int(search))
            queryset = queryset.filter(search_q)

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        results = []
        for payment in queryset[start:end]:
            patient = payment.visit.patient
            processor = payment.processed_by
            results.append({
                'id': payment.id,
                'visit': payment.visit_id,
                'visit_id': payment.visit_id,
                'amount': str(payment.amount),
                'payment_method': payment.payment_method,
                'status': payment.status,
                'transaction_reference': payment.transaction_reference,
                'notes': payment.notes,
                'processed_by': payment.processed_by_id,
                'processed_by_name': (
                    f"{processor.first_name} {processor.last_name}".strip()
                    if processor else None
                ),
                'created_at': payment.created_at,
                'updated_at': payment.updated_at,
                'is_legacy': payment.notes.startswith('[Legacy PatientPayID:'),
                'patient': {
                    'id': patient.id,
                    'patient_id': patient.patient_id,
                    'name': patient.get_full_name() if hasattr(patient, 'get_full_name') else (
                        f"{patient.first_name} {patient.last_name}".strip()
                    ),
                },
                'visit_status': payment.visit.status,
            })

        AuditLog.log(
            user=request.user,
            role=getattr(request.user, 'role', None),
            action='BILLING_PAYMENT_HISTORY_VIEWED',
            visit_id=None,
            resource_type='payment_history',
            resource_id=None,
            request=request,
        )
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': results,
        }, status=status.HTTP_200_OK)


class DeferredLegacyPaymentsView(APIView):
    """
    GET /api/v1/billing/deferred-payments/

    Lists unsettled LIFEWAY flexible-payment services (legacy deferred VisitCharges).
    """

    permission_classes = [IsAuthenticated, CanProcessPayment]

    def get(self, request):
        search = (request.query_params.get("search") or "").strip()
        try:
            page = max(1, int(request.query_params.get("page") or 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(200, max(1, int(request.query_params.get("page_size") or 48)))
        except (TypeError, ValueError):
            page_size = 48

        total, results = list_and_serialize_unsettled_deferred_charges(
            search=search,
            page=page,
            page_size=page_size,
        )
        AuditLog.log(
            user=request.user,
            role=getattr(request.user, "role", None),
            action="DEFERRED_LEGACY_PAYMENTS_VIEWED",
            visit_id=None,
            resource_type="deferred_legacy_payments",
            resource_id=None,
            request=request,
        )
        return Response(
            {"count": total, "page": page, "page_size": page_size, "results": results},
            status=status.HTTP_200_OK,
        )


class DeferredLegacyPaymentSettleView(APIView):
    """
    POST /api/v1/billing/deferred-payments/{charge_id}/settle/

    Settles a deferred legacy service using the standard Payment flow.
  Body: { amount, payment_method, transaction_reference?, notes? }
    """

    permission_classes = [IsAuthenticated, CanProcessPayment]

    def post(self, request, charge_id: int):
        from django.core.exceptions import ValidationError as DjangoValidationError

        amount_raw = request.data.get("amount")
        payment_method = (request.data.get("payment_method") or "CASH").strip().upper()
        transaction_reference = (request.data.get("transaction_reference") or "").strip()
        notes = (request.data.get("notes") or "").strip()

        if payment_method not in {"CASH", "POS", "TRANSFER", "WALLET", "PAYSTACK", "INSURANCE"}:
            return Response(
                {"detail": "Invalid payment_method."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            amount = Decimal(str(amount_raw))
        except (InvalidOperation, TypeError, ValueError):
            return Response(
                {"detail": "A valid settlement amount is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = settle_deferred_charge(
                charge_id,
                amount=amount,
                payment_method=payment_method,
                processed_by=request.user,
                transaction_reference=transaction_reference,
                notes=notes,
            )
        except DjangoValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        AuditLog.log(
            user=request.user,
            role=getattr(request.user, "role", None),
            action="DEFERRED_LEGACY_PAYMENT_SETTLED",
            visit_id=result.get("visit_id"),
            resource_type="visit_charge",
            resource_id=charge_id,
            request=request,
        )
        return Response(result, status=status.HTTP_201_CREATED)
