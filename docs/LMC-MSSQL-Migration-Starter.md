# LMC MSSQL -> Modern EMR Migration Starter

This is a practical starter map from legacy SQL Server objects in `LMC.sql` to current Django/PostgreSQL models in `backend/apps/*/models.py`.

> Scope note: this is a **starter** for implementation planning. Final mapping must be validated with sample rows and business owners.

## 1) Current target schema (confirmed)

Key target tables/models already in this repo:

- `patients` (`apps.patients.Patient`)
- `users` (`apps.users.User`)
- `visits` (`apps.visits.Visit`)
- `appointments` (`apps.appointments.Appointment`)
- `consultations` (`apps.consultations.Consultation`)
- `vital_signs` (`apps.clinical.VitalSigns`)
- `nursing_notes`, `medication_administrations`, `lab_sample_collections` (`apps.nursing.*`)
- `lab_orders`, `lab_results` (`apps.laboratory.*`)
- `radiology_requests`, `radiology_orders`, `radiology_results` (`apps.radiology.*`)
- `drugs`, `drug_inventory`, `stock_movements`, `prescriptions` (`apps.pharmacy.*`)
- `payments`, `visit_charges` (`apps.billing.*`)
- `referrals` (`apps.referrals.Referral`)
- `antenatal_*`, `ivf_*`, `discharge_summaries`, `telemedicine_*`

## 2) Legacy objects detected (sample/high-value)

From `LMC.sql`, legacy SQL Server tables include:

- `tblOutPatientRecord`, `tblPatientVisits`, `tblVitalSign`, `tblOPDAppointment`
- `tblLabRequest`, `tblLabRequestDetails`, `tblLabResult`, `tblLabResultDetails`, `tblLabTest`
- `tblRadRequest`, `tblRadRequestDetails`, `tblRadResult`
- `tblDrugPrescription`, `tblDrugPresItems`, `tblPhamDrugItem`, `tblPhamDrugGroup`, `tblPhamDrugLedger`
- `tblPatientPayment`, `tblReceipt`, `tblReceiptGrid`, `tblNewAccTrans`
- `tblAdmission`, `tblAdmissionRequest`, `tblWard`
- `tblReferal`, `tblMedicalReports`, `tblUsers`, `tblStaff`
- `tblANC`, `tblANCVisits`

Also present:

- many views (`CREATE VIEW ...`)
- many stored procedures (`CREATE PROCEDURE ...`, e.g. `in_*`, `delete_*`)

## 3) Starter table-to-table mapping matrix

## Core Patient & Visit
- `tblOutPatientRecord` -> `patients`  
  - **Strategy:** primary patient master migration. Preserve old IDs as `legacy_patient_id` in a staging mapping table.
- `tblPatientVisits` -> `visits`  
  - **Strategy:** map visit status/payment fields to current enums; link to migrated patient.
- `tblOPDAppointment` -> `appointments`  
  - **Strategy:** map appointment datetime/status and doctor/patient refs via ID map.
- `tblVitalSign` -> `vital_signs`  
  - **Strategy:** unit normalization (temp/bp/weight) and visit FK resolution.

## Users/Staff
- `tblUsers` + `tblStaff` -> `users`  
  - **Strategy:** deduplicate identities, map role strings to current `ROLE_CHOICES`, enforce unique username/email.

## Laboratory
- `tblLabTest` -> `lab catalog / order payload` (target: `lab_orders` + catalog source in app)  
  - **Strategy:** preserve test names/codes and use as reference for order/result migration.
- `tblLabRequest` -> `lab_orders`  
  - **Strategy:** map requester, patient, visit, timestamps, status.
- `tblLabRequestDetails` -> `lab_orders` detail semantics  
  - **Strategy:** flatten into order metadata or child rows depending on current service structure.
- `tblLabResult` + `tblLabResultDetails` -> `lab_results`  
  - **Strategy:** combine header/detail rows into single result records tied to orders.

## Radiology
- `tblRadRequest` + `tblRadRequestDetails` -> `radiology_requests` / `radiology_orders`  
  - **Strategy:** header->request, detail->orders.
- `tblRadResult` -> `radiology_results`  
  - **Strategy:** map report text, performer/reviewer and result timestamps.

## Pharmacy
- `tblPhamDrugGroup` -> `drugs` taxonomy fields  
  - **Strategy:** map categories/groups to drug classification fields.
- `tblPhamDrugItem` -> `drugs`  
  - **Strategy:** canonical drug master migration (name/strength/form/price if available).
- `tblPhamDrugLedger` -> `stock_movements`  
  - **Strategy:** ledger in/out -> movement type + quantity delta.
- `tblDrugPrescription` -> `prescriptions`  
  - **Strategy:** prescription header migration with patient/visit/provider.
- `tblDrugPresItems` -> `prescriptions` items / medication rows  
  - **Strategy:** migrate line items and dosage instructions.

## Billing/Finance
- `tblPatientPayment` -> `payments`  
  - **Strategy:** map payment methods/statuses/receipts to current payment model.  
  - **Implemented (migrate_lmc):** CSV export + loader attaches `Payment` to nearest `Visit` by `PatientID` + `PaymentDate`; idempotency via `[Legacy PatientPayID:N]` in `notes`; `processed_by` uses `migration_receptionist`.
- `tblReceipt` + `tblReceiptGrid` -> `payments` + `visit_charges`  
  - **Strategy:** receipt header to payment; grid lines to charge line items.  
  - **Implemented (migrate_lmc):** `tblTempReceipt` joined to `tblReceiptGrid` → `VisitCharge` (POS-style lines; `tblReceipt`/`tblReceiptLog` often empty in OPD backups).
- `tblDrugPrescription` + `tblDrugPresItems` -> `prescriptions`  
  - **Implemented (migrate_lmc):** denormalized export `tblDrugPresItems.csv` (items + header + drug name) → `Prescription` per line after `tblPhamDrugItem` load.
- `tblNewAccTrans` -> `payments` / finance audit trail  
  - **Strategy:** classify by transaction type and map where clinically relevant.

## Admission/Inpatient
- `tblAdmissionRequest` -> admission workflow (current inpatient flow in app)  
  - **Strategy:** migrate active/pending requests first.
- `tblAdmission` -> inpatient admission records (mapped via existing admission/discharge modules)
  - **Strategy:** migrate with bed/ward relationships.
- `tblWard` -> ward/bed management tables in current system  
  - **Strategy:** create ward master first before admissions.

## Other clinical areas
- `tblReferal` -> `referrals`
- `tblMedicalReports` -> `medical_documents`
- `tblANC`, `tblANCVisits` -> `antenatal_records`, `antenatal_visits`

## 4) Data-type conversion rules (MSSQL -> Postgres)

- `IDENTITY(1,1)` -> `SERIAL/BIGSERIAL` equivalent (handled by Django PK)
- `nvarchar/varchar/text` -> `text/varchar`
- `datetime` -> `timestamp with time zone` (normalize timezone)
- `date` -> `date`
- `bit` -> `boolean`
- `money` -> `numeric(12,2)` (or project standard)
- SQL Server bracket names `[dbo].[X]` -> plain lowercase target table names

## 5) Stored procedure strategy

Do not port procedures 1:1. Re-implement behavior in:

- Django services (`apps/*/services.py`)
- serializers/viewsets validation
- domain services already present (billing, lab, radiology, pharmacy)

For each `in_*`, `delete_*`, `upd_*` proc:
1. identify affected legacy tables
2. map intended business rule
3. implement in Python with tests

## 6) Migration execution checklist (actionable)

## Phase A - Discovery
- [ ] Generate complete legacy table inventory (`CREATE TABLE` list).
- [ ] For each table, capture row counts in SQL Server staging.
- [ ] Identify PK/FK relationships from legacy schema.
- [ ] Freeze legacy extract date/time for reproducibility.

## Phase B - Mapping specification
- [ ] Approve column-by-column mapping sheet per domain.
- [ ] Define enum/status translation dictionaries.
- [ ] Define required defaults for missing values.
- [ ] Define identity crosswalk tables (`legacy_id` -> `new_id`) for patient, user, visit.

## Phase C - ETL build
- [ ] Build extract layer (SQL Server reader via `pyodbc`/`sqlalchemy`).
- [ ] Build transform layer (cleaning, typing, enum normalization, dedupe).
- [ ] Build load layer using Django ORM in dependency order:
  1) users/reference masters  
  2) patients  
  3) visits/appointments  
  4) lab/radiology/pharmacy  
  5) billing/payments  
  6) referrals/antenatal/admission extras
- [ ] Add idempotent upsert behavior for reruns.

## Phase D - Validation
- [ ] Row-count reconciliation per migrated table.
- [ ] 20-patient clinical spot-check (chart parity).
- [ ] Financial totals reconciliation (payments/charges/receipts).
- [ ] Sampling of date/time correctness and status accuracy.
- [ ] Validate orphan checks (no broken FKs).

## Phase E - Cutover
- [ ] Dry-run in staging with production-sized data.
- [ ] Define downtime/read-only window.
- [ ] Run final ETL.
- [ ] Post-cutover smoke tests by role (Receptionist/Doctor/Nurse/Lab/Pharmacy/Billing).
- [ ] Sign-off and archive migration logs.

## 7) Suggested implementation artifacts to create next

- `docs/migration/lmc-column-mapping.xlsx` (source->target columns, transforms)
- `backend/scripts/migrate_lmc/extract.py`
- `backend/scripts/migrate_lmc/transform.py`
- `backend/scripts/migrate_lmc/load.py`
- `backend/scripts/migrate_lmc/reconcile.py`

