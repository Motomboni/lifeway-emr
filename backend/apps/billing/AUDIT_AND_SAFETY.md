# Audit and Safety Features

## Overview

This document describes the audit and safety features implemented in the billing system to ensure data integrity, immutability, and comprehensive audit logging.

## Payment Rules (Strict Pre-Service Gates)

- **Registration** and **Consultation** services have `restricted_service_flag = True`: payment must be collected before access.
- **Registration unpaid** → block access to consultation (API and UI).
- **Consultation unpaid** → block doctor from starting encounter (API and UI).
- All other services (Lab, Pharmacy, Radiology, etc.) are **post-consultation**: bills enter the central Pending Queue; only **Receptionist** can collect payment.
- **Audit**: Who created charges (`BillingLineItem.created_by`), who received payment (`Payment.processed_by`), timestamps (`created_at`, `paid_at`). Payment records are immutable once created.

## Immutability Rules

### Never Delete

The following models are **immutable** and cannot be deleted:

1. **BillPayment** - Payments are append-only
2. **BillItem** - Bill items are immutable
3. **WalletTransaction** - Wallet transactions are immutable

### Implementation

#### BillPayment
```python
def delete(self, *args, **kwargs):
    """Prevent deletion - payments are append-only."""
    raise ValidationError("Payments are append-only and cannot be deleted.")
```

#### BillItem
```python
def delete(self, *args, **kwargs):
    """Prevent deletion - bill items are immutable."""
    raise ValidationError("Bill items are immutable and cannot be deleted.")
```

#### WalletTransaction
```python
def delete(self, *args, **kwargs):
    """Prevent deletion - transactions are immutable."""
    raise ValueError("Wallet transactions cannot be deleted.")
```

### Signal-Based Prevention

Django signals also prevent deletion at the database level:

```python
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
```

## Audit Fields

### Created By and Timestamps

All financial models include audit fields:

#### Bill
- `created_by` (ForeignKey to User, nullable)
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)

#### BillItem
- `created_by` (ForeignKey to User, nullable)
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)

#### BillPayment
- `processed_by` (ForeignKey to User, PROTECT)
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)

#### WalletTransaction
- `created_by` (ForeignKey to User, nullable)
- `created_at` (DateTimeField, auto_now_add)

## Audit Logging

### Automatic Logging

Django signals automatically log all financial actions:

#### Bill Creation
```python
@receiver(post_save, sender=Bill)
def log_bill_created(sender, instance, created, **kwargs):
    """Log bill creation."""
    if created:
        AuditLog.log(
            user=instance.created_by,
            action="BILL_CREATED",
            visit_id=instance.visit_id,
            resource_type="bill",
            resource_id=instance.id,
            metadata={
                'bill_id': instance.id,
                'visit_id': instance.visit_id,
                'is_insurance_backed': instance.is_insurance_backed,
                'status': instance.status,
            }
        )
```

#### BillItem Creation
```python
@receiver(post_save, sender=BillItem)
def log_bill_item_created(sender, instance, created, **kwargs):
    """Log bill item creation."""
    if created:
        AuditLog.log(
            user=instance.created_by,
            action="BILL_ITEM_CREATED",
            visit_id=instance.bill.visit_id,
            resource_type="bill_item",
            resource_id=instance.id,
            metadata={
                'bill_item_id': instance.id,
                'bill_id': instance.bill_id,
                'department': instance.department,
                'service_name': instance.service_name,
                'amount': str(instance.amount),
            }
        )
```

#### BillPayment Creation
```python
@receiver(post_save, sender=BillPayment)
def log_bill_payment_created(sender, instance, created, **kwargs):
    """Log bill payment creation."""
    if created:
        AuditLog.log(
            user=instance.processed_by,
            action="BILL_PAYMENT_CREATED",
            visit_id=instance.bill.visit_id,
            resource_type="bill_payment",
            resource_id=instance.id,
            metadata={
                'bill_payment_id': instance.id,
                'amount': str(instance.amount),
                'payment_method': instance.payment_method,
                'transaction_reference': instance.transaction_reference,
            }
        )
```

#### WalletTransaction Creation
```python
@receiver(post_save, sender=WalletTransaction)
def log_wallet_transaction_created(sender, instance, created, **kwargs):
    """Log wallet transaction creation."""
    if created:
        AuditLog.log(
            user=instance.created_by,
            action="WALLET_TRANSACTION_CREATED",
            visit_id=instance.visit_id if instance.visit else None,
            resource_type="wallet_transaction",
            resource_id=instance.id,
            metadata={
                'transaction_type': instance.transaction_type,
                'amount': str(instance.amount),
                'status': instance.status,
            }
        )
```

#### Bill Updates
```python
@receiver(post_save, sender=Bill)
def log_bill_updated(sender, instance, created, **kwargs):
    """Log bill status/total updates."""
    if not created:
        # Log significant changes (status, totals)
        AuditLog.log(
            user=None,  # System update
            role='SYSTEM',
            action="BILL_UPDATED",
            visit_id=instance.visit_id,
            resource_type="bill",
            resource_id=instance.id,
            metadata={
                'status': instance.status,
                'total_amount': str(instance.total_amount),
                'amount_paid': str(instance.amount_paid),
                'outstanding_balance': str(instance.outstanding_balance),
            }
        )
```

### Manual Logging

Views also log financial actions explicitly:

- `BILL_ITEM_ADDED` - When bill item is added via API
- `BILL_PAYMENT_CREATED` - When payment is created via API
- `WALLET_TOPUP` - When wallet is topped up
- `WALLET_PAYMENT` - When wallet payment is made
- `PAYSTACK_PAYMENT_INITIATED` - When Paystack payment is initiated
- `PAYSTACK_WEBHOOK_PROCESSED` - When Paystack webhook is processed

## Database Constraints

### Integrity Constraints

#### No Bill without Visit
```python
# Bill model
visit = models.OneToOneField(
    'visits.Visit',
    on_delete=models.CASCADE,
    db_constraint=True  # Explicit database constraint
)

# Check constraint
constraints = [
    models.CheckConstraint(
        check=models.Q(visit__isnull=False),
        name='bill_requires_visit'
    ),
]
```

#### No Orphan BillItems
```python
# BillItem model
bill = models.ForeignKey(
    Bill,
    on_delete=models.CASCADE,
    db_constraint=True  # Explicit database constraint
)

# Check constraint
constraints = [
    models.CheckConstraint(
        check=models.Q(bill__isnull=False),
        name='bill_item_requires_bill'
    ),
]
```

#### No Payment without Bill
```python
# BillPayment model
bill = models.ForeignKey(
    Bill,
    on_delete=models.CASCADE,
    db_constraint=True  # Explicit database constraint
)

# Check constraint
constraints = [
    models.CheckConstraint(
        check=models.Q(bill__isnull=False),
        name='bill_payment_requires_bill'
    ),
    models.CheckConstraint(
        check=models.Q(processed_by__isnull=False),
        name='bill_payment_requires_processor'
    ),
]
```

### Foreign Key Constraints

All foreign keys use appropriate `on_delete` behaviors:

- **CASCADE**: When parent is deleted, child is deleted
  - `Bill.visit` → CASCADE (no Bill without Visit)
  - `BillItem.bill` → CASCADE (no orphan BillItems)
  - `BillPayment.bill` → CASCADE (no payment without Bill)

- **PROTECT**: Prevents deletion if child exists
  - `BillPayment.processed_by` → PROTECT (cannot delete user who processed payments)

- **SET_NULL**: Sets to NULL if parent is deleted
  - `Bill.created_by` → SET_NULL (preserve record if user deleted)
  - `BillItem.created_by` → SET_NULL (preserve record if user deleted)

## Audit Log Actions

### Financial Actions Logged

1. **BILL_CREATED** - Bill created
2. **BILL_UPDATED** - Bill totals/status updated
3. **BILL_ITEM_CREATED** - Bill item added
4. **BILL_PAYMENT_CREATED** - Payment recorded
5. **WALLET_TRANSACTION_CREATED** - Wallet transaction created
6. **WALLET_TOPUP** - Wallet topped up
7. **WALLET_PAYMENT** - Wallet payment made
8. **PAYSTACK_PAYMENT_INITIATED** - Paystack payment initiated
9. **PAYSTACK_WEBHOOK_PROCESSED** - Paystack webhook processed
10. **BILLING_WALLET_DEBIT_CREATED** - Wallet debit for billing
11. **RECEIPT_GENERATED** - Receipt generated
12. **INVOICE_GENERATED** - Invoice generated

## Safety Features Summary

### ✅ Immutability
- BillPayment cannot be deleted
- BillItem cannot be deleted
- WalletTransaction cannot be deleted
- Signal-based prevention at database level

### ✅ Audit Fields
- All models have `created_by` or `processed_by`
- All models have `created_at` and `updated_at`
- User tracking for all financial actions

### ✅ Audit Logging
- Automatic logging via Django signals
- Manual logging in views
- Comprehensive metadata in logs
- All actions are auditable

### ✅ Database Constraints
- No Bill without Visit (OneToOne + CheckConstraint)
- No orphan BillItems (ForeignKey CASCADE + CheckConstraint)
- No payment without Bill (ForeignKey CASCADE + CheckConstraint)
- No payment without processor (CheckConstraint)

## Testing

### Test Cases

1. **Deletion Prevention**
   - Attempt to delete BillPayment → ValidationError
   - Attempt to delete BillItem → ValidationError
   - Attempt to delete WalletTransaction → ValueError

2. **Audit Logging**
   - Create Bill → BILL_CREATED logged
   - Create BillItem → BILL_ITEM_CREATED logged
   - Create BillPayment → BILL_PAYMENT_CREATED logged
   - Create WalletTransaction → WALLET_TRANSACTION_CREATED logged

3. **Database Constraints**
   - Create Bill without Visit → DatabaseError
   - Create BillItem without Bill → DatabaseError
   - Create BillPayment without Bill → DatabaseError
   - Create BillPayment without processed_by → DatabaseError

## Best Practices

1. **Never Delete Financial Records**
   - Use soft deletes if needed
   - Mark as inactive instead of deleting
   - Preserve audit trail

2. **Always Log Financial Actions**
   - Use signals for automatic logging
   - Add manual logs in views for context
   - Include relevant metadata

3. **Enforce Constraints at Database Level**
   - Use ForeignKey with appropriate on_delete
   - Add CheckConstraints for explicit validation
   - Use PROTECT for critical relationships

4. **Track All Users**
   - Set `created_by` or `processed_by` for all records
   - Use PROTECT for user foreign keys
   - Preserve records even if user is deleted

## Related Documentation

- `BILL_MODELS_DOCUMENTATION.md` - Bill model documentation
- `BILLING_SERVICE.md` - Billing service documentation
- `AUDIT_LOG.md` - Audit log system documentation

