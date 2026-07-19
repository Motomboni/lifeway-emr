# Modern EMR — One-Page Manual Test Checklist

**Print this page.** Date: __________  Tester: __________  Build/env: __________

**App:** http://localhost:3000 · **API health:** http://localhost:8000/api/v1/health/

---

## Logins (after `prepare-local.ps1`)

| Role | Email | Password |
|------|-------|----------|
| Receptionist | receptionist@clinic.com | Receptionist123! |
| Doctor | doctor@clinic.com | Doctor123! |
| Nurse | nurse@clinic.com | Nurse123! * |
| Lab tech | labtech@clinic.com | LabTech123! |
| Pharmacist | pharmacist@clinic.com | Pharmacist123! |
| Patient | patient@clinic.com | Patient123! |

\* Nurse/Radiology/Admin — create once (see full guide §1).

---

## Full clinic day (cross-role) — check when done

| # | Role | Action | Pass |
|---|------|--------|:----:|
| 1 | Receptionist | Register patient `/patients/register` | ☐ |
| 2 | Receptionist | Create visit `/visits/new` | ☐ |
| 3 | Receptionist | Pay **registration** on `/visits/{id}` → Billing | ☐ |
| 4 | Nurse | Vitals on `/visits/{id}/nursing` | ☐ |
| 5 | Doctor | Consultation saved `/visits/{id}/consultation` | ☐ |
| 6 | Doctor | Order lab + prescription (same visit) | ☐ |
| 7 | Lab tech | Post result `/lab-orders` | ☐ |
| 8 | Pharmacist | Dispense `/prescriptions` | ☐ |
| 9 | Receptionist | NHIA: validate → CSV → record submission | ☐ |
| 10 | Patient | See results on portal `/patient-portal/dashboard` | ☐ |

**Visit ID used for this run:** __________ **Patient name:** ____________________

---

## Quick smoke by role — check all that apply today

**Receptionist** ☐ Register ☐ Create visit ☐ Billing/Paystack ☐ Pending queue ☐ Offline sync

**Doctor** ☐ Consultation ☐ Service catalog ☐ Lab order ☐ Rx + CDS alert ☐ Close visit

**Nurse** ☐ Allergy banner ☐ Vitals ☐ Nursing notes ☐ Blocked when unpaid

**Lab tech** ☐ Worklist ☐ Critical result → alert ☐ Catalog view

**Radiology tech** ☐ Worklist ☐ Upload/report ☐ Upload status page

**Pharmacist** ☐ Worklist ☐ Dispense qty required ☐ CDS on dispense ☐ Drug catalog

**Admin** ☐ NHIA compliance ☐ Reports ☐ Audit log ☐ Integration hubs (manual NHIA note)

**Patient portal** ☐ Allergies ☐ Lab results ☐ Prescriptions ☐ Pay bill

---

## Blockers / notes

| Issue | Visit # | Notes |
|-------|---------|-------|
| | | |
| | | |

**Result:** ☐ PASS (all critical rows) ☐ FAIL — file bug: ____________________

*Detail scripts: `docs/MANUAL_TEST_ROLE_SCRIPTS.md` · Full guide: `docs/MANUAL_TESTING_GUIDE.md`*
