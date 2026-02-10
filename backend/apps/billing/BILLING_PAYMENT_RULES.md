# Billing Payment Rules (Strict)

## 1. Pre-Service Payments (Restricted)

Only these services **require payment before access**:
- **Patient Registration**
- **Doctor Consultation**

### System behavior
- **Registration unpaid** → Block access to consultation (API 403, UI gate).
- **Consultation unpaid** → Block doctor from starting encounter (API 403, UI gate).
- Payments can be collected by: **Receptionist**, or **Self-payment** (if enabled).
- Once paid, the next stage is unlocked automatically (gates use `BillingLineItem.bill_status = PAID`).

### Data model
- `ServiceCatalog.restricted_service_flag = True` for Registration and Consultation services only.
- Registration: `service_code` REG-* or name contains REGISTRATION.
- Consultation: `department = CONSULTATION`, `workflow_type = GOPD_CONSULT` (excluding registration).

## 2. Post-Consultation Payments (Reception Only)

All other services are **billed after consultation** and **must not require upfront payment**:
- Laboratory, Pharmacy, Radiology, Procedures, Consumables, etc.

### System behavior
- Doctors, nurses, lab staff can: **select services**, **add billable items**, **submit charges**.
- They **cannot**: collect payment, mark bills as paid.
- Bills enter the **Central Billing Queue** (pending queue) visible only to Reception.
- Receptionist can: view pending queue, combine/view by visit, accept Cash/POS/Transfer/Wallet/Paystack, mark paid, print/send receipt.

## 3. Central Billing Queue

- **Endpoint**: `GET /api/v1/billing/pending-queue/` (Receptionist only).
- Returns visits with at least one `BillingLineItem` in PENDING or PARTIALLY_PAID.
- Each entry: patient, department, itemized charges, status, linked consultation ref.

## 4. Departmental UI / Permissions

- **Doctors**: Can request consultation charges and add post-consultation services; **cannot** see payment buttons or process payment.
- **Lab / Radiology / Pharmacy**: Can add billable services; can see payment status (read-only); **cannot** process payments.
- **Receptionist**: Full billing access; can process payments, override, merge, split, or cancel bills (per policy).

## 5. Enforcement

- **Backend**: `IsRegistrationPaymentCleared` and `IsConsultationPaymentCleared` permission classes.
- Consultation API: read (retrieve/list) requires registration paid; write (create/update) requires consultation paid.
- **Frontend**: Payment gates in billing summary; consultation buttons and section gated by `payment_gates.registration_paid` and `payment_gates.consultation_paid`.

## 6. Audit & Traceability

- `BillingLineItem`: `created_by`, `created_at`, `paid_at`, `modified_by`, `updated_at`.
- `Payment`: `processed_by`, `created_at`, `updated_at`.
- Payment records are immutable once paid (`BillingLineItem` cannot be modified when `bill_status = PAID`).
- `AuditLog` used for billing actions (e.g. BILLING_PENDING_QUEUE_VIEWED, BILLING_CHARGE_CREATED, BILLING_PAYMENT_CREATED).
