"""
Django signals for automatic audit logging of financial actions.

Per EMR Rules:
- Every financial action must be logged
- Logs are immutable
- All actions are auditable
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import logging

from .bill_models import Bill, BillItem, BillPayment
from apps.wallet.models import WalletTransaction
from core.audit import AuditLog

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Bill)
def log_bill_created(sender, instance, created, **kwargs):
    """Log bill creation."""
    if created:
        try:
            AuditLog.log(
                user=instance.created_by,
                role=getattr(instance.created_by, 'role', None) if instance.created_by else None,
                action="BILL_CREATED",
                visit_id=instance.visit_id,
                resource_type="bill",
                resource_id=instance.id,
                request=None,
                metadata={
                    'bill_id': instance.id,
                    'visit_id': instance.visit_id,
                    'is_insurance_backed': instance.is_insurance_backed,
                    'status': instance.status,
                }
            )
        except Exception as e:
            logger.error(f"Failed to log bill creation: {e}")


@receiver(post_save, sender=BillItem)
def log_bill_item_created(sender, instance, created, **kwargs):
    """Log bill item creation."""
    if created:
        try:
            AuditLog.log(
                user=instance.created_by,
                role=getattr(instance.created_by, 'role', None) if instance.created_by else None,
                action="BILL_ITEM_CREATED",
                visit_id=instance.bill.visit_id,
                resource_type="bill_item",
                resource_id=instance.id,
                request=None,
                metadata={
                    'bill_item_id': instance.id,
                    'bill_id': instance.bill_id,
                    'visit_id': instance.bill.visit_id,
                    'department': instance.department,
                    'service_name': instance.service_name,
                    'amount': str(instance.amount),
                    'status': instance.status,
                }
            )
        except Exception as e:
            logger.error(f"Failed to log bill item creation: {e}")


@receiver(post_save, sender=BillPayment)
def log_bill_payment_created(sender, instance, created, **kwargs):
    """Log bill payment creation."""
    if created:
        try:
            AuditLog.log(
                user=instance.processed_by,
                role=getattr(instance.processed_by, 'role', None) if instance.processed_by else None,
                action="BILL_PAYMENT_CREATED",
                visit_id=instance.bill.visit_id,
                resource_type="bill_payment",
                resource_id=instance.id,
                request=None,
                metadata={
                    'bill_payment_id': instance.id,
                    'bill_id': instance.bill_id,
                    'visit_id': instance.bill.visit_id,
                    'amount': str(instance.amount),
                    'payment_method': instance.payment_method,
                    'transaction_reference': instance.transaction_reference,
                    'bill_status_before': instance.bill.status,
                }
            )
        except Exception as e:
            logger.error(f"Failed to log bill payment creation: {e}")


@receiver(post_save, sender=Bill)
def log_bill_updated(sender, instance, created, **kwargs):
    """Log bill status/total updates."""
    if not created:
        try:
            # Only log significant changes
            if 'update_fields' in kwargs and kwargs['update_fields']:
                update_fields = kwargs['update_fields']
                if any(field in update_fields for field in ['status', 'total_amount', 'amount_paid', 'outstanding_balance']):
                    AuditLog.log(
                        user=None,  # System update
                        role='SYSTEM',
                        action="BILL_UPDATED",
                        visit_id=instance.visit_id,
                        resource_type="bill",
                        resource_id=instance.id,
                        request=None,
                        metadata={
                            'bill_id': instance.id,
                            'visit_id': instance.visit_id,
                            'status': instance.status,
                            'total_amount': str(instance.total_amount),
                            'amount_paid': str(instance.amount_paid),
                            'outstanding_balance': str(instance.outstanding_balance),
                            'updated_fields': list(update_fields),
                        }
                    )
        except Exception as e:
            logger.error(f"Failed to log bill update: {e}")


@receiver(pre_delete, sender=BillItem)
def prevent_bill_item_deletion(sender, instance, **kwargs):
    """Prevent deletion of bill items."""
    raise ValidationError("Bill items are immutable and cannot be deleted.")


@receiver(pre_delete, sender=BillPayment)
def prevent_bill_payment_deletion(sender, instance, **kwargs):
    """Prevent deletion of bill payments."""
    raise ValidationError("Bill payments are immutable and cannot be deleted.")


@receiver(pre_delete, sender=WalletTransaction)
def prevent_wallet_transaction_deletion(sender, instance, **kwargs):
    """Prevent deletion of wallet transactions."""
    raise ValidationError("Wallet transactions are immutable and cannot be deleted.")


@receiver(post_save, sender=WalletTransaction)
def log_wallet_transaction_created(sender, instance, created, **kwargs):
    """Log wallet transaction creation."""
    if created:
        try:
            AuditLog.log(
                user=instance.created_by,
                role=getattr(instance.created_by, 'role', None) if instance.created_by else None,
                action="WALLET_TRANSACTION_CREATED",
                visit_id=instance.visit_id if instance.visit else None,
                resource_type="wallet_transaction",
                resource_id=instance.id,
                request=None,
                metadata={
                    'wallet_transaction_id': instance.id,
                    'wallet_id': instance.wallet_id,
                    'visit_id': instance.visit_id if instance.visit else None,
                    'transaction_type': instance.transaction_type,
                    'amount': str(instance.amount),
                    'status': instance.status,
                    'balance_after': str(instance.balance_after),
                }
            )
        except Exception as e:
            logger.error(f"Failed to log wallet transaction creation: {e}")

