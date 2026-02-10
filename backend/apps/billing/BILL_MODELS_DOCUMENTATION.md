# Bill Models Documentation

## Overview

This document describes the Django models for the visit-scoped billing system with Bill, BillItem, and Payment models.

## Models

### 1. Bill Model

**OneToOne relationship with Visit**

```python
class Bill(models.Model):
    visit = OneToOneField('visits.Visit')
    is_insurance_backed = BooleanField(default=False)
    total_amount = DecimalField()  # Auto-calculated
    amount_paid = DecimalField()  # Auto-calculated
    outstanding_balance = DecimalField()  # Auto-calculated
    status = CharField()  # UNPAID, PARTIALLY_PAID, PAID, INSURANCE_PENDING, INSURANCE_CLAIMED, SETTLED
    insurance_policy = ForeignKey('InsurancePolicy', null=True)
```

**Key Features:**
- One bill per visit (OneToOne relationship)
- Auto-calculates `total_amount`, `amount_paid`, and `outstanding_balance`
- Supports insurance-backed bills
- Insurance bills cannot accept Paystack/Cash payments
- Insurance bills generate invoices, not receipts

**Methods:**
- `add_item(department, service_name, amount, created_by=None)` - Add a bill item
- `add_payment(amount, payment_method, transaction_reference='', notes='', processed_by=None)` - Add a payment
- `recalculate_totals()` - Recalculate all totals and status
- `can_generate_receipt()` - Check if bill can generate receipt (non-insurance)
- `can_generate_invoice()` - Check if bill can generate invoice (insurance)

### 2. BillItem Model

**Belongs to Bill**

```python
class BillItem(models.Model):
    bill = ForeignKey(Bill, related_name='items')
    department = CharField()  # CONSULTATION, LAB, RADIOLOGY, PHARMACY, PROCEDURE, MISC
    service_name = CharField()
    amount = DecimalField()
    status = CharField()  # UNPAID, PAID, INSURANCE
    created_by = ForeignKey('users.User', null=True)
```

**Key Features:**
- Each item belongs to a Bill
- Items have department, service name, and amount
- Status tracks payment status per item
- Auto-recalculates bill totals when saved

### 3. BillPayment Model

**Belongs to Bill (append-only)**

```python
class BillPayment(models.Model):
    bill = ForeignKey(Bill, related_name='payments')
    amount = DecimalField()
    payment_method = CharField()  # CASH, POS, TRANSFER, PAYSTACK, WALLET, INSURANCE
    transaction_reference = CharField(blank=True)
    notes = TextField(blank=True)
    processed_by = ForeignKey('users.User')
```

**Key Features:**
- Payments are append-only (cannot be deleted)
- Belongs to Bill (not directly to Visit)
- Auto-recalculates bill totals when saved
- Insurance bills reject Paystack/Cash payments

**Payment Methods:**
- CASH
- POS (Point of Sale)
- TRANSFER (Bank Transfer)
- PAYSTACK
- WALLET
- INSURANCE

### 4. InsuranceProvider Model

```python
class InsuranceProvider(models.Model):
    name = CharField(unique=True)
    code = CharField(unique=True, null=True)
    contact_person = CharField(blank=True)
    contact_phone = CharField(blank=True)
    contact_email = EmailField(blank=True)
    address = TextField(blank=True)
    is_active = BooleanField(default=True)
```

**Key Features:**
- Stores insurance provider information
- Unique name and code
- Contact information and address
- Active/inactive status

### 5. InsurancePolicy Model

```python
class InsurancePolicy(models.Model):
    patient = ForeignKey('patients.Patient')
    provider = ForeignKey(InsuranceProvider)
    policy_number = CharField()
    coverage_type = CharField()  # FULL, PARTIAL
    coverage_percentage = DecimalField()  # 0-100
    is_active = BooleanField(default=True)
    valid_from = DateField()
    valid_to = DateField(null=True)
```

**Key Features:**
- Links patient to insurance provider
- Tracks policy number and coverage details
- Coverage type (FULL or PARTIAL)
- Coverage percentage (0-100)
- Validity dates
- `is_valid()` method checks if policy is currently valid

## Usage Examples

### Creating a Bill

```python
from apps.visits.models import Visit
from apps.billing.bill_models import Bill, InsurancePolicy

# Create bill for a visit
visit = Visit.objects.get(id=1)
bill = Bill.objects.create(visit=visit)

# Or create insurance-backed bill
insurance_policy = InsurancePolicy.objects.get(id=1)
bill = Bill.objects.create(
    visit=visit,
    is_insurance_backed=True,
    insurance_policy=insurance_policy
)
```

### Adding Bill Items

```python
# Add items to bill
bill.add_item(
    department='LAB',
    service_name='Complete Blood Count (CBC)',
    amount=Decimal('5000.00'),
    created_by=request.user
)

bill.add_item(
    department='PHARMACY',
    service_name='Paracetamol 500mg x 20',
    amount=Decimal('1500.00'),
    created_by=request.user
)
```

### Adding Payments

```python
# Add payment (standard bill)
bill.add_payment(
    amount=Decimal('6500.00'),
    payment_method='POS',
    transaction_reference='POS-123456',
    notes='Payment via POS terminal',
    processed_by=request.user
)

# Insurance bills reject Paystack/Cash
try:
    bill.add_payment(
        amount=Decimal('5000.00'),
        payment_method='PAYSTACK',  # Will raise ValidationError
        processed_by=request.user
    )
except ValidationError as e:
    print(e)  # "Insurance-backed bills cannot accept PAYSTACK payments..."
```

### Recalculating Totals

```python
# Totals are auto-calculated, but you can manually recalculate
bill.recalculate_totals()
bill.save()

# After recalculation:
print(bill.total_amount)  # Sum of all bill items
print(bill.amount_paid)  # Sum of all payments
print(bill.outstanding_balance)  # total_amount - amount_paid
print(bill.status)  # UNPAID, PARTIALLY_PAID, PAID, etc.
```

### Checking Bill Status

```python
# Check if bill can generate receipt (non-insurance)
if bill.can_generate_receipt():
    # Generate receipt
    pass

# Check if bill can generate invoice (insurance)
if bill.can_generate_invoice():
    # Generate invoice
    pass
```

## Insurance Rules

1. **Insurance-backed bills:**
   - Must have an `insurance_policy`
   - Cannot accept Paystack or Cash payments
   - Generate invoices, not receipts
   - Status flow: INSURANCE_PENDING → INSURANCE_CLAIMED → SETTLED

2. **Non-insurance bills:**
   - Cannot have an `insurance_policy`
   - Accept all payment methods
   - Generate receipts, not invoices
   - Status flow: UNPAID → PARTIALLY_PAID → PAID

## Auto-Calculation

The Bill model automatically calculates:
- `total_amount`: Sum of all `BillItem.amount`
- `amount_paid`: Sum of all `BillPayment.amount`
- `outstanding_balance`: `total_amount - amount_paid`
- `status`: Based on `outstanding_balance` and `is_insurance_backed`

Calculations are triggered:
- When a `BillItem` is saved
- When a `BillPayment` is saved
- When `bill.recalculate_totals()` is called
- When `bill.save()` is called

## Append-Only Payments

Payments are append-only:
- Cannot be deleted (raises `ValidationError`)
- Cannot be modified after creation
- All payment history is preserved for audit

## Database Tables

- `bills` - Bill records
- `bill_items` - BillItem records
- `bill_payments` - BillPayment records
- `insurance_providers` - InsuranceProvider records
- `insurance_policies` - InsurancePolicy records

## Migration

To apply the models to the database:

```bash
python manage.py migrate billing
```

The migration file is: `0008_add_bill_models.py`

