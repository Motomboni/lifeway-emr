"""
Visit-nested billing endpoints - unified billing API.

Per EMR Rules:
- Only Receptionist can mutate billing
- All endpoints must enforce visit scope
- Closed visits are read-only
- All actions logged to AuditLog

Endpoints:
- POST /api/v1/visits/{visit_id}/billing/charges/
- POST /api/v1/visits/{visit_id}/billing/payments/
- POST /api/v1/visits/{visit_id}/billing/wallet-debit/
- POST /api/v1/visits/{visit_id}/billing/insurance/
- GET  /api/v1/visits/{visit_id}/billing/summary/
"""
from rest_framework import views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError as DRFValidationError,
)
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from decimal import Decimal
import logging

from .models import Payment, VisitCharge
from .serializers import PaymentCreateSerializer
from .billing_service import BillingService
from .billing_line_item_service import allocate_payment_to_line_items
from .permissions import CanProcessPayment
from apps.visits.models import Visit
from apps.wallet.models import Wallet, WalletTransaction
from apps.billing.insurance_models import VisitInsurance
from apps.billing.insurance_serializers import VisitInsuranceCreateSerializer
from .bill_models import Bill
from core.permissions import IsVisitOpen
from core.audit import AuditLog


class BillingEndpointView(views.APIView):
    """
    Base class for billing endpoints.
    
    Provides common functionality:
    - Visit validation
    - Role checking
    - Closed visit protection
    """
    
    def get_visit(self, visit_id):
        """Get and validate visit from URL parameter."""
        visit = get_object_or_404(Visit, pk=visit_id)
        
        # Check if visit is closed (read-only)
        if visit.status == 'CLOSED' and self.request.method != 'GET':
            raise PermissionDenied(
                detail="Cannot modify billing for a CLOSED visit. "
                       "Closed visits are billing read-only per EMR rules.",
                code='visit_closed_billing_readonly'
            )
        
        return visit
    
    def check_user_role(self, request):
        """Ensure user is a Receptionist for mutations."""
        if request.method == 'GET':
            return  # Read operations don't need role check
        
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        if user_role != 'RECEPTIONIST':
            raise PermissionDenied(
                detail="Only Receptionists can process billing operations.",
                code='role_forbidden'
            )


class BillingSummaryView(BillingEndpointView):
    """
    GET /api/v1/visits/{visit_id}/billing/summary/
    
    Get complete billing summary for a Visit.
    Uses centralized BillingService for deterministic computation.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, visit_id):
        """Get billing summary for visit."""
        visit = self.get_visit(visit_id)
        
        # Compute billing summary using centralized service
        summary = BillingService.compute_billing_summary(visit)
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="BILLING_SUMMARY_VIEWED",
            visit_id=visit_id,
            resource_type="billing",
            resource_id=None,
            request=request
        )
        
        return Response(summary.to_dict(), status=status.HTTP_200_OK)


class BillingChargesView(BillingEndpointView):
    """
    GET/POST /api/v1/visits/{visit_id}/billing/charges/
    
    GET: List all charges for a Visit
    POST: Create a MISC charge for a Visit.
    
    Per EMR Rules:
    - Charges are system-generated, but Receptionist can create MISC charges
    - Only MISC category allowed for manual creation
    - Visit must be OPEN
    """
    
    def get_permissions(self):
        """GET: Authenticated users, POST: Receptionist only + Visit Open"""
        if self.request.method == 'GET':
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        else:
            return [CanProcessPayment(), IsVisitOpen()]
    
    def get(self, request, visit_id):
        """
        List all charges for visit with no duplication.

        Single source of truth:
        - Catalog items: from BillingLineItem only (one per service added from catalog).
        - Manual charges: from VisitCharge where category is MISC.
        - Legacy visits (no BillingLineItems): show all VisitCharges so old data still appears.
        """
        visit = self.get_visit(visit_id)
        from .billing_line_item_models import BillingLineItem

        charges_data = []
        department_to_category = {
            'LAB': 'LAB',
            'PHARMACY': 'DRUG',
            'RADIOLOGY': 'RADIOLOGY',
            'PROCEDURE': 'PROCEDURE',
            'CONSULTATION': 'CONSULTATION',
        }

        # 1. Primary source: BillingLineItems (one per catalog item, no duplicates)
        try:
            billing_line_items = list(
                BillingLineItem.objects.filter(visit=visit)
                .select_related('service_catalog')
                .order_by('-created_at')
            )
            has_billing_line_items = len(billing_line_items) > 0
            for line_item in billing_line_items:
                department = (
                    line_item.service_catalog.department
                    if line_item.service_catalog
                    else 'MISC'
                )
                category = department_to_category.get(department, 'MISC')
                charges_data.append({
                    'id': f'billing_line_item_{line_item.id}',
                    'visit_id': visit.id,
                    'category': category,
                    'description': line_item.source_service_name,
                    'amount': str(line_item.amount),
                    'created_by_system': True,
                    'created_at': line_item.created_at.isoformat(),
                    'updated_at': line_item.updated_at.isoformat()
                })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Error loading BillingLineItems: {str(e)}")
            has_billing_line_items = False

        # 2. Manual MISC charges (VisitCharge with category MISC)
        # 3. Legacy: if visit has no BillingLineItems, include all VisitCharges so old data shows
        visit_charges = VisitCharge.objects.filter(visit=visit).order_by('-created_at')
        for charge in visit_charges:
            if charge.category == 'MISC':
                charges_data.append({
                    'id': charge.id,
                    'visit_id': charge.visit_id,
                    'category': charge.category,
                    'description': charge.description,
                    'amount': str(charge.amount),
                    'created_by_system': charge.created_by_system,
                    'created_at': charge.created_at.isoformat(),
                    'updated_at': charge.updated_at.isoformat()
                })
            elif not has_billing_line_items:
                # Legacy visit: no catalog items, show legacy VisitCharges
                charges_data.append({
                    'id': charge.id,
                    'visit_id': charge.visit_id,
                    'category': charge.category,
                    'description': charge.description,
                    'amount': str(charge.amount),
                    'created_by_system': charge.created_by_system,
                    'created_at': charge.created_at.isoformat(),
                    'updated_at': charge.updated_at.isoformat()
                })

        # Sort by created_at descending
        charges_data.sort(key=lambda x: x['created_at'], reverse=True)
        return Response(charges_data, status=status.HTTP_200_OK)
    
    def post(self, request, visit_id):
        """Create a MISC charge for visit."""
        visit = self.get_visit(visit_id)
        self.check_user_role(request)
        
        # Validate request data
        amount = request.data.get('amount')
        description = request.data.get('description', '')
        
        if not amount:
            raise DRFValidationError("amount is required")
        
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            raise DRFValidationError("amount must be a valid decimal number")
        
        if amount <= 0:
            raise DRFValidationError("amount must be greater than zero")
        
        if not description:
            raise DRFValidationError("description is required")
        
        # Create MISC charge using system method
        try:
            charge = VisitCharge.create_misc_charge(
                visit=visit,
                amount=amount,
                description=description
            )
        except Exception as e:
            raise DRFValidationError(f"Failed to create charge: {str(e)}")
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="BILLING_CHARGE_CREATED",
            visit_id=visit_id,
            resource_type="visit_charge",
            resource_id=charge.id,
            request=request,
            metadata={
                'category': 'MISC',
                'amount': str(amount),
                'description': description
            }
        )
        
        return Response(
            {
                'id': charge.id,
                'visit_id': visit.id,
                'category': charge.category,
                'description': charge.description,
                'amount': str(charge.amount),
                'created_at': charge.created_at.isoformat()
            },
            status=status.HTTP_201_CREATED
        )


class BillingPaymentsView(BillingEndpointView):
    """
    GET  /api/v1/visits/{visit_id}/billing/payments/ - List payments for visit
    POST /api/v1/visits/{visit_id}/billing/payments/ - Create a payment for visit
    
    Per EMR Rules:
    - Receptionist-only for POST
    - Authenticated users can view payments (GET)
    - Visit must be OPEN for POST
    - Payment method required for POST
    """
    permission_classes = [CanProcessPayment, IsVisitOpen]
    
    def get(self, request, visit_id):
        """List payments for visit."""
        visit = self.get_visit(visit_id)
        
        # Get payments for this visit
        payments = Payment.objects.filter(visit=visit).select_related(
            'processed_by'
        ).order_by('-created_at')
        
        from .serializers import PaymentSerializer
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)
    
    def get_permissions(self):
        """Return appropriate permissions based on HTTP method."""
        if self.request.method == 'GET':
            # Allow authenticated users to view payments
            from rest_framework.permissions import IsAuthenticated
            from core.permissions import IsVisitAccessible
            return [IsAuthenticated(), IsVisitAccessible()]
        else:
            # POST requires CanProcessPayment and IsVisitOpen
            return [CanProcessPayment(), IsVisitOpen()]
    
    def post(self, request, visit_id):
        """Create a payment for visit."""
        visit = self.get_visit(visit_id)
        self.check_user_role(request)
        
        # Validate request data
        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ensure visit_id in URL matches request data if visit is provided
        if serializer.validated_data.get('visit'):
            if serializer.validated_data['visit'].id != visit.id:
                raise DRFValidationError(
                    "visit_id in URL must match visit in request data."
                )
        # If visit not in request data, it will be set from URL context
        
        # Create payment - visit comes from URL context
        # Determine initial status based on payment method
        initial_status = serializer.validated_data.get('status', 'PENDING')
        if serializer.validated_data.get('payment_method') in ['CASH', 'POS', 'TRANSFER', 'WALLET']:
            initial_status = 'CLEARED'
            
        payment = serializer.save(
            visit=visit,  # Always use visit from URL context
            processed_by=request.user,
            status=initial_status
        )
        
        # Allocate payment to BillingLineItems (Registration first, then Consultation, then others)
        # so payment_gates (registration_paid, consultation_paid) become true when paid
        try:
            allocate_payment_to_line_items(
                visit, Decimal(str(payment.amount)), payment.payment_method or 'CASH'
            )
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(
                "Payment created but allocation to line items failed for visit %s: %s",
                visit.id, e, exc_info=True
            )
        
        # Recalculate billing summary and update visit payment status
        try:
            summary = BillingService.compute_billing_summary(visit)
            visit.payment_status = summary.payment_status
            visit.save(update_fields=['payment_status'])
            
            # Also update bill status if bill exists
            try:
                bill = Bill.objects.get(visit=visit)
                bill.status = summary.payment_status
                # Recalculate bill amounts
                bill.total_amount = summary.total_charges
                bill.amount_paid = summary.total_payments + summary.total_wallet_debits
                bill.outstanding_balance = summary.outstanding_balance
                bill.save(update_fields=['status', 'total_amount', 'amount_paid', 'outstanding_balance', 'updated_at'])
                # Refresh visit from database to ensure is_payment_cleared() uses updated bill
                visit.refresh_from_db()
            except Bill.DoesNotExist:
                # No bill exists yet, create one
                try:
                    bill = Bill.objects.create(
                        visit=visit,
                        status=summary.payment_status,
                        total_amount=summary.total_charges,
                        amount_paid=summary.total_payments + summary.total_wallet_debits,
                        outstanding_balance=summary.outstanding_balance,
                        created_by=request.user
                    )
                    visit.refresh_from_db()
                except Exception as e:
                    # Log error but don't fail the payment creation
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create bill for visit {visit.id}: {str(e)}", exc_info=True)
            except Exception as e:
                # Log error but don't fail the payment creation
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to update bill for visit {visit.id}: {str(e)}", exc_info=True)
        except Exception as e:
            # Log error but don't fail the payment creation - billing summary calculation failed
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to compute billing summary for visit {visit.id}: {str(e)}", exc_info=True)
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="BILLING_PAYMENT_CREATED",
            visit_id=visit_id,
            resource_type="payment",
            resource_id=payment.id,
            request=request
        )
        
        from .serializers import PaymentSerializer
        return Response(
            PaymentSerializer(payment).data,
            status=status.HTTP_201_CREATED
        )


class BillingWalletDebitView(BillingEndpointView):
    """
    POST /api/v1/visits/{visit_id}/billing/wallet-debit/
    
    Create a wallet debit payment for a Visit.
    
    Per EMR Rules:
    - Receptionist-only
    - Visit must be OPEN
    - Wallet must have sufficient balance
    - Creates both WalletTransaction and Payment record
    """
    permission_classes = [CanProcessPayment, IsVisitOpen]
    
    def post(self, request, visit_id):
        """Create wallet debit payment for visit."""
        visit = self.get_visit(visit_id)
        self.check_user_role(request)
        
        # Validate request data
        wallet_id = request.data.get('wallet_id')
        amount = request.data.get('amount')
        description = request.data.get('description', f'Payment for visit {visit_id}')
        
        if not wallet_id:
            raise DRFValidationError("wallet_id is required")
        
        if not amount:
            raise DRFValidationError("amount is required")
        
        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            raise DRFValidationError("amount must be a valid decimal number")
        
        if amount <= 0:
            raise DRFValidationError("amount must be greater than zero")
        
        # Get wallet
        wallet = get_object_or_404(Wallet, pk=wallet_id)
        
        # Validate payment amount using BillingService
        is_valid, error_msg = BillingService.validate_payment_amount(visit, amount)
        if not is_valid:
            raise DRFValidationError(error_msg)
        
        # Check wallet balance
        if wallet.balance < amount:
            raise DRFValidationError(
                f"Insufficient wallet balance. Available: {wallet.balance}, Required: {amount}"
            )
        
        # Get billing summary for outstanding balance
        summary = BillingService.compute_billing_summary(visit)
        
        # Debit wallet
        try:
            transaction = wallet.debit(
                amount=amount,
                visit=visit,
                description=description,
                created_by=request.user
            )
        except Exception as e:
            raise DRFValidationError(f"Failed to debit wallet: {str(e)}")
        
        # Create Payment record
        payment = Payment.objects.create(
            visit=visit,
            amount=amount,
            payment_method='WALLET',
            status='CLEARED',
            transaction_reference=f'WALLET_{transaction.id}',
            notes=f'Paid from wallet. Transaction ID: {transaction.id}',
            processed_by=request.user
        )
        
        # Allocate payment to BillingLineItems so payment_gates (registration_paid, consultation_paid) update
        try:
            allocate_payment_to_line_items(visit, amount, 'WALLET')
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning(
                "Wallet debit recorded but allocation to line items failed for visit %s: %s",
                visit.id, e, exc_info=True
            )
        
        # Recalculate billing summary and update visit payment status
        updated_summary = BillingService.compute_billing_summary(visit)
        visit.payment_status = updated_summary.payment_status
        visit.save(update_fields=['payment_status'])
        
        # Also update bill status if bill exists
        try:
            bill = Bill.objects.get(visit=visit)
            bill.status = updated_summary.payment_status
            # Recalculate bill amounts
            bill.total_amount = updated_summary.total_charges
            bill.amount_paid = updated_summary.total_payments + updated_summary.total_wallet_debits
            bill.outstanding_balance = updated_summary.outstanding_balance
            bill.save(update_fields=['status', 'total_amount', 'amount_paid', 'outstanding_balance', 'updated_at'])
            # Refresh visit from database to ensure is_payment_cleared() uses updated bill
            visit.refresh_from_db()
        except Bill.DoesNotExist:
            # No bill exists yet, create one
            try:
                bill = Bill.objects.create(
                    visit=visit,
                    status=updated_summary.payment_status,
                    total_amount=updated_summary.total_charges,
                    amount_paid=updated_summary.total_payments + updated_summary.total_wallet_debits,
                    outstanding_balance=updated_summary.outstanding_balance,
                    created_by=request.user
                )
                visit.refresh_from_db()
            except Exception as e:
                # Log error but don't fail the payment creation
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create bill for visit {visit.id}: {str(e)}", exc_info=True)
        except Exception as e:
            # Log error but don't fail the payment creation
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update bill for visit {visit.id}: {str(e)}", exc_info=True)
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="BILLING_WALLET_DEBIT_CREATED",
            visit_id=visit_id,
            resource_type="wallet_transaction",
            resource_id=transaction.id,
            request=request,
            metadata={
                'amount': str(amount),
                'wallet_id': wallet_id,
                'transaction_id': transaction.id,
                'payment_id': payment.id,
                'outstanding_balance_before': str(summary.outstanding_balance),
                'outstanding_balance_after': str(updated_summary.outstanding_balance)
            }
        )
        
        return Response(
            {
                'wallet_transaction': {
                    'id': transaction.id,
                    'amount': str(transaction.amount),
                    'balance_after': str(transaction.balance_after),
                    'status': transaction.status
                },
                'payment': {
                    'id': payment.id,
                    'amount': str(payment.amount),
                    'status': payment.status
                },
                'outstanding_balance': str(updated_summary.outstanding_balance),
                'visit_payment_status': visit.payment_status
            },
            status=status.HTTP_201_CREATED
        )


class BillingInsuranceView(BillingEndpointView):
    """
    POST /api/v1/visits/{visit_id}/billing/insurance/
    
    Create insurance record for a Visit.
    
    Per EMR Rules:
    - Receptionist-only
    - Visit must be OPEN
    - Uses existing VisitInsurance model
    """
    permission_classes = [CanProcessPayment, IsVisitOpen]
    
    def post(self, request, visit_id):
        """Create insurance record for visit."""
        visit = self.get_visit(visit_id)
        self.check_user_role(request)
        
        # Validate request data
        serializer = VisitInsuranceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Ensure visit_id in URL matches request data
        if serializer.validated_data.get('visit') and serializer.validated_data['visit'].id != visit.id:
            raise DRFValidationError(
                "visit_id in URL must match visit in request data."
            )
        
        # Create insurance record
        insurance = serializer.save(
            visit=visit,
            created_by=request.user
        )
        
        # Audit log
        user_role = getattr(request.user, 'role', None) or \
                   getattr(request.user, 'get_role', lambda: None)()
        
        AuditLog.log(
            user=request.user,
            role=user_role,
            action="BILLING_INSURANCE_CREATED",
            visit_id=visit_id,
            resource_type="visit_insurance",
            resource_id=insurance.id,
            request=request
        )
        
        from apps.billing.insurance_serializers import VisitInsuranceSerializer
        return Response(
            VisitInsuranceSerializer(insurance).data,
            status=status.HTTP_201_CREATED
        )

