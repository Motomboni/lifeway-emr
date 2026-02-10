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
from rest_framework.exceptions import PermissionDenied
from django.db.models import Sum, Q, Prefetch
from decimal import Decimal

from apps.visits.models import Visit
from apps.consultations.models import Consultation
from .billing_line_item_models import BillingLineItem
from .permissions import CanProcessPayment
from core.audit import AuditLog


class BillingPendingQueueView(APIView):
    """
    GET /api/v1/billing/pending-queue/
    
    Unified billing queue for Receptionist: all visits with pending (unpaid or partially paid)
    BillingLineItems. Receptionist-only.
    
    Returns:
    - visits: list of { visit_id, patient, items[], total_pending, status, consultation_ref }
    """
    permission_classes = [IsAuthenticated, CanProcessPayment]
    
    def get(self, request):
        # Only Receptionist can access (CanProcessPayment)
        visit_ids_with_pending = (
            BillingLineItem.objects.filter(
                bill_status__in=['PENDING', 'PARTIALLY_PAID']
            )
            .values_list('visit_id', flat=True)
            .distinct()
        )
        visits = (
            Visit.objects.filter(id__in=visit_ids_with_pending)
            .select_related('patient')
            .prefetch_related(
                Prefetch(
                    'billing_line_items',
                    queryset=BillingLineItem.objects.filter(
                        bill_status__in=['PENDING', 'PARTIALLY_PAID']
                    ).select_related('service_catalog').order_by('department', 'created_at')
                )
            )
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
            for li in visit.billing_line_items.all():
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
