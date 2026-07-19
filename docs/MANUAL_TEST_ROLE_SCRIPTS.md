# Modern EMR — Role-Specific Manual Test Scripts

Step-by-step scripts for manual QA. Run **Receptionist → Doctor → Nurse → Lab → Pharmacy** in order for a full visit, or run one script in isolation using an existing visit.

**Prerequisites:** Backend running (`.\scripts\start-local-backend.ps1 -UseSqlite`), frontend at http://localhost:3000, data seeded (`.\scripts\prepare-local.ps1 -UseSqlite`).

---

## Script A — Receptionist (≈15 min)

**Login:** receptionist@clinic.com / Receptionist123!

### A1. Register patient

1. Dashboard → **Patient Registration** (or `/patients/register`)
2. Fill: first name, last name, phone, gender, DOB
3. Optional: National Health ID, address, emergency contact
4. Submit → note **Patient ID** on confirmation

**Pass if:** Patient appears in search; no validation errors.

### A2. Create visit

1. `/visits/new` or Dashboard → **Create Visit**
2. Search and select patient from A1
3. Payment type: **CASH** (or INSURANCE)
4. Optional: chief complaint, visit type
5. Submit → note **Visit ID**

**Pass if:** Redirect to Visit Details or visits list; status **OPEN**, payment **UNPAID** (CASH).

### A3. Clear registration payment

1. Open `/visits/{Visit ID}`
2. Scroll to **Billing** section
3. Record payment (Cash / POS / Transfer) for **registration / intake** charge
4. Confirm visit payment status updates (PAID or PARTIALLY_PAID)

**Pass if:** Doctor can open consultation afterward (test in Script B).

### A4. Patient management (optional)

1. `/patients` → select patient → **Edit**
2. Add **structured allergy** (e.g. Penicillin, DRUG, SEVERE)
3. Save → confirm summary field updates

**Pass if:** Allergy appears in structured list and comma-separated summary.

### A5. Pending queue (optional)

1. `/billing/pending-queue`
2. Confirm visit from A2 appears if still unpaid items exist

### A6. NHIA claim prep (optional, needs NHID + charges)

1. On Visit Details → **NHIA Claim** panel
2. **Validate** → fix errors if any
3. **Download claim pack (for NHIA portal)**
4. **Mark pack exported** → **Record manual portal submission**

**Pass if:** Status progresses; CSV downloads; no API error (NHIA is manual/local only).

### A7. Offline check-in (optional)

1. DevTools → Network → Offline (or disconnect Wi‑Fi)
2. `/visits/new` → select patient → create visit
3. Confirm “queued” message
4. Go online → `/offline/queue` → sync entry

**Pass if:** Visit created after sync.

**Script A record:** Patient ID ______ Visit ID ______ Payment cleared ☐

---

## Script B — Doctor (≈20 min)

**Login:** doctor@clinic.com / Doctor123!  
**Requires:** Visit ID from Script A with **registration paid**.

### B1. Open consultation

1. `/visits` → open visit **OR** `/visits/{id}/consultation`
2. Confirm **allergy banner** (if patient has allergies)
3. If locked: stop — reception must clear registration payment

**Pass if:** Consultation form loads; sandbox banner only on SANDBOX visits.

### B2. Chart consultation

1. History, examination, diagnosis, clinical notes — enter sample text
2. **Save** (bottom actions)
3. Confirm save success toast

**Pass if:** Reload page — data persists.

### B3. Order services

1. **Service catalog** — add e.g. General Consultation or CBC
2. **Lab inline** — order Complete Blood Count (or seeded test)
3. **Prescription inline** — drug e.g. Paracetamol, dosage 500mg

**Pass if:** Orders appear in lists; Rx may trigger **clinical alerts** (check banner/panel).

### B4. Clinical AI Scribe (optional)

1. Open **Clinical AI Scribe** panel
2. Generate note → **Apply to consultation**
3. Confirm fields populate; save again

### B5. Diagnosis codes & close (optional)

1. Add ICD-11 / diagnosis codes if panel visible
2. When billing complete: **Close visit** from consultation actions

**Pass if:** Visit status CLOSED when intended; locks prevent illegal edits.

**Script B record:** Consultation saved ☐ Lab ordered ☐ Rx created ☐ Alerts seen ☐

---

## Script C — Nurse (≈10 min)

**Login:** nurse@clinic.com / Nurse123! (create user if missing — see main guide)  
**Requires:** Same Visit ID, **OPEN**, payment cleared.

### C1. Nursing visit page

1. Dashboard → search visit **OR** `/visits/{id}/nursing`
2. Confirm **allergy banner** and **clinical alerts** section

### C2. Vital signs

1. **Vital Signs** section → enter BP, pulse, temp, SpO2, weight
2. Save

**Pass if:** Vitals listed on reload; offline queue works if tested offline.

### C3. Nursing documentation

1. **Nursing notes** — add short note
2. **Patient education** — add entry (optional)
3. **Lab sample collection** — mark sample collected if lab ordered

### C4. Payment gate

1. Open an **UNPAID** visit nursing page (separate test visit)
2. Confirm warning: cannot perform actions until payment cleared

**Script C record:** Vitals ☐ Notes ☐ Unpaid warning ☐

---

## Script D — Lab technician (≈10 min)

**Login:** labtech@clinic.com / LabTech123!  
**Requires:** Visit with **pending lab order** from Script B.

### D1. Worklist

1. `/lab-orders`
2. Select visit from left panel
3. Confirm allergy banner + clinical alerts

### D2. Post result

1. Open pending order → enter result text (e.g. `HGB 6.5 g/dL — critically low`)
2. Set abnormal flag: **CRITICAL**
3. Submit

**Pass if:** Order moves out of pending; doctor visit shows new **clinical alert** after refresh/event.

### D3. Catalog (optional)

1. `/lab-test-catalog` — browse seeded templates (CBC, LFT, etc.)

**Script D record:** Result posted ☐ Critical alert on doctor side ☐

---

## Script E — Radiology technician (≈10 min)

**Login:** radiology@clinic.com / RadTech123!  
**Requires:** Doctor ordered radiology on a visit (order in consultation if not done in B).

### E1. Worklist

1. `/radiology-orders`
2. Select visit with pending imaging order

### E2. Complete order

1. Post report or upload per UI (metadata / PACS if Orthanc running)
2. Flag abnormal/critical if applicable

### E3. Upload status (optional)

1. `/radiology/upload-status` — confirm session status visible

**Script E record:** Order completed ☐

---

## Script F — Pharmacist (≈10 min)

**Login:** pharmacist@clinic.com / Pharmacist123!  
**Requires:** Pending prescription from Script B; visit **OPEN**, payment cleared.

### F1. Prescription worklist

1. `/prescriptions`
2. Select visit → confirm **allergy banner** + **clinical alerts**

### F2. Dispense

1. Select pending Rx
2. Enter **exact dispensed quantity** (required)
3. Optional dispensing notes
4. Click **Dispense**

**Pass if:** Status **DISPENSED**; CDS warning if alerts generated; cannot dispense without quantity.

### F3. Drug catalog (optional)

1. `/drugs` — view catalog
2. `/pharmacy/nafdac-formulary` — browse formulary

**Script F record:** Dispensed ☐ Alert on dispense ☐

---

## Script G — Patient portal (≈10 min)

**Login:** patient@clinic.com / Patient123!  
**Requires:** Portal patient linked to visits with results/Rx from prior scripts (or use portal test patient from seed).

### G1. Dashboard

1. `/patient-portal/dashboard`
2. Confirm profile, **structured allergies**, outstanding bills

### G2. Clinical data

1. `/patient-portal/lab-results` — results visible after lab posts
2. `/patient-portal/prescriptions` — Rx after doctor orders
3. `/patient-portal/medical-history` — full summary

### G3. Pay bill (optional, Paystack test keys)

1. Dashboard → **Pay now** on outstanding visit
2. Complete Paystack test flow

**Script G record:** Allergies ☐ Labs ☐ Rx ☐

---

## Script H — Admin / billing oversight (≈15 min)

**Login:** admin@clinic.com / Admin123! (or Django superuser)

### H1. Compliance & billing

1. `/billing/nhia-compliance` — summary loads
2. `/billing/revenue-leaks` — page loads
3. `/billing/payment-reconciliation` — page loads

### H2. Operations

1. `/audit-logs` — recent actions from Scripts A–F appear
2. `/reports` — dashboard metrics
3. `/admin/integrations` — NHIA hub shows **manual workflow** note

### H3. Configuration (optional)

1. `/service-catalog` — REG-001, CONS-001, CBC-001 present after seed
2. `/organization/settings` — org loads

**Script H record:** NHIA dashboard ☐ Audit trail ☐

---

## Script I — Interactive Guide / Sandbox (≈5 min)

**Login:** any staff role (e.g. doctor)

1. Click **Guide orb** (bottom-right)
2. **Practice in sandbox** → new SANDBOX visit
3. Complete **Role Launch** tour steps
4. **Ctrl+K** → command palette → navigate to Visits

**Pass if:** Sandbox banner visible; no real PHI required.

---

## Regression matrix (pick one row per release)

| Release | A Rec | B Doc | C Nurse | D Lab | E Rad | F Pharm | G Portal | H Admin | Pass |
|---------|:-----:|:-----:|:-------:|:-----:|:-----:|:-------:|:--------:|:-------:|:----:|
| | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |
| | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | ☐ | |

---

*One-page checklist: `docs/MANUAL_TEST_ONE_PAGE.md` · Full guide: `docs/MANUAL_TESTING_GUIDE.md`*
