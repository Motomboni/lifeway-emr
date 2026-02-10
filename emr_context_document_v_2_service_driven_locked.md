# EMR CONTEXT DOCUMENT v2 (LOCKED)

## 1. CORE PHILOSOPHY
This EMR is **Service-Driven, Visit-Scoped, and Consultation-Dependent**.

> Services are workflow triggers, permission gates, and billing anchors — not just prices.

All clinical and operational actions MUST originate from a **ServiceCatalog** entry.

---

## 2. NON-NEGOTIABLE GLOBAL RULES

1. **No Visit → No Consultation**
2. **No Consultation → No Lab / Radiology / Drug / Procedure Orders**
3. **No Order → No Result / Report**
4. **Billing is immutable once paid**
5. **Role-based access is strictly enforced**
6. **Every action must be auditable**

---

## 3. CORE DOMAIN ENTITIES

### 3.1 ServiceCatalog (Workflow Driver)
Defines *what happens* in the system.

Key fields:
- department
- service_code
- category
- workflow_type
- requires_visit
- requires_consultation
- auto_bill
- bill_timing
- allowed_roles

---

### 3.2 Visit
Represents a patient encounter.

Rules:
- One active Visit per patient at a time
- Created automatically by service selection when required

States:
- AWAITING_PAYMENT
- ACTIVE
- COMPLETED

---

### 3.3 Consultation
Represents doctor–patient clinical interaction.

Rules:
- MUST belong to a Visit
- Created only via CONSULTATION services

States:
- PENDING
- ACTIVE
- CLOSED

---

## 4. ORDER-BASED WORKFLOWS (STRICT)

### 4.1 Laboratory

**Trigger:** LAB service

Entities:
- LabOrder
- LabResult

Rules:
- Requires Visit + Consultation
- Ordered only by Doctor
- Results posted only by Lab Tech
- Doctor reviews results

---

### 4.2 Radiology (LOCKED)

**Trigger:** RADIOLOGY service

Entities:
- RadiologyOrder
- RadiologyReport
- RadiologyImage (file reference only)

Rules:
- Requires Visit + Consultation
- Ordered only by Doctor
- Performed by Radiographer
- Reported by Radiologist / Radiographer
- Doctor views report + images

States:
- ORDERED
- IN_PROGRESS
- COMPLETED
- REPORTED

---

### 4.3 Pharmacy

**Trigger:** DRUG_DISPENSE service

Rules:
- Requires Consultation
- Dispense only after payment (unless emergency flag)
- Stock deduction is atomic

---

### 4.4 Procedures / Nursing Tasks

**Trigger:** PROCEDURE service

Rules:
- Consultation-dependent
- Executed by Nurse
- Completion logged

---

## 5. BILLING & PAYMENTS

Billing is **service-originated**.

### BillingLineItem
- Linked to ServiceCatalog
- Snapshotted amount
- Linked to Visit (and Consultation if applicable)

States:
- PENDING
- PAID
- PARTIALLY_PAID

Payment Sources:
- Cash
- Wallet
- HMO
- Paystack

---

## 6. EVENT-DRIVEN ORCHESTRATION

Key events:
- SERVICE_SELECTED
- BILL_GENERATED
- PAYMENT_CONFIRMED
- CONSULTATION_UNLOCKED
- ORDER_CREATED
- RESULT_POSTED

Events MUST be idempotent.

---

## 7. OFFLINE-FIRST STRATEGY (IMAGING FOCUSED)

### Radiology Offline Upload

Principles:
- Images are stored locally first
- Metadata syncs before binaries

Flow:
1. RadiologyOrder created online
2. Imaging performed offline
3. Images stored locally (UUID-based)
4. Metadata queued
5. Background sync uploads when online
6. Server validates + attaches images

No image is deleted locally until server ACK.

---

## 8. PACS-LITE INTEGRATION

This EMR uses **PACS-lite**, not full PACS.

### PACS-lite Capabilities
- DICOM or JPEG storage
- Series grouping
- Viewer integration (read-only)

### What PACS-lite does NOT do
- No modality worklist
- No HL7 routing

### Storage Model
- Images stored outside DB
- DB stores references only

---

## 9. ROLE MATRIX (ENFORCED)

| Role | Capabilities |
|----|-------------|
| Receptionist | Register, select services, collect payment |
| Doctor | Consult, order services, view results |
| Lab Tech | Perform tests, post results |
| Radiographer | Perform imaging, upload images |
| Nurse | Execute procedures |
| Admin | Configure system |

---

## 10. AUDIT & MEDICO-LEGAL COMPLIANCE

Every entity must track:
- created_by
- created_at
- modified_by
- modified_at

No deletes — soft delete only.

---

## 11. FINAL STATEMENT (LOCKED)

> Any feature that violates this document is **non-compliant** and must not be merged.

This document supersedes all prior context versions.

