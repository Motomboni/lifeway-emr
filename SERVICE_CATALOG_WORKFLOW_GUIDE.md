# Service Catalog Workflow - Department Integration

## ✅ YES - Services Automatically Create Department Workflows!

When you select a service from the Service Catalog, the system **automatically**:
1. Creates the appropriate department workflow (Prescription, LabOrder, RadiologyRequest, etc.)
2. Generates billing
3. Makes it visible to the appropriate department staff

---

## How It Works

### Example 1: PHARMACY Services (Aspirin)

**When you select "Aspirin" from Service Catalog:**

1. ✅ System detects `workflow_type = 'DRUG_DISPENSE'`
2. ✅ Creates a **Prescription** (Drug Order)
3. ✅ Creates **BillingLineItem** for Aspirin
4. ✅ Prescription appears in **Pharmacist Dashboard**
5. ✅ Pharmacist can dispense after payment

**Workflow:**
```
Select Aspirin → Prescription Created → Bill Generated → 
Patient Pays → Pharmacist Sees Order → Pharmacist Dispenses
```

---

### Example 2: LABORATORY Services

**When you select a lab test (e.g., "Complete Blood Count"):**

1. ✅ System detects `workflow_type = 'LAB_ORDER'`
2. ✅ Creates a **LabOrder**
3. ✅ Creates **BillingLineItem** for the test
4. ✅ Lab order appears in **Laboratory Dashboard**
5. ✅ Lab technician can process after payment

**Workflow:**
```
Select Lab Test → LabOrder Created → Bill Generated → 
Patient Pays → Lab Tech Sees Order → Sample Collected → Results Posted
```

---

### Example 3: RADIOLOGY Services

**When you select a radiology study (e.g., "Chest X-Ray"):**

1. ✅ System detects `workflow_type = 'RADIOLOGY_STUDY'`
2. ✅ Creates a **RadiologyRequest**
3. ✅ Creates **BillingLineItem** for the study
4. ✅ Radiology order appears in **Radiographer Dashboard**
5. ✅ Radiographer can perform study after payment

**Workflow:**
```
Select Radiology Study → RadiologyRequest Created → Bill Generated → 
Patient Pays → Radiographer Sees Order → Study Performed → Report Posted
```

---

### Example 4: PROCEDURE Services

**When you select a procedure (e.g., "Wound Dressing"):**

1. ✅ System detects `workflow_type = 'PROCEDURE'`
2. ✅ Creates a **ProcedureTask**
3. ✅ Creates **BillingLineItem** for the procedure
4. ✅ Procedure appears in **Nurse Dashboard**
5. ✅ Nurse can perform procedure (usually after service)

**Workflow:**
```
Select Procedure → ProcedureTask Created → Bill Generated → 
Nurse Performs Procedure → Bill Finalized
```

---

## Service Catalog Configuration

Each service has a `workflow_type` that determines what gets created:

| Department | Workflow Type | Creates | Visible To |
|------------|---------------|---------|------------|
| **PHARMACY** | `DRUG_DISPENSE` | `Prescription` | Pharmacist |
| **LAB** | `LAB_ORDER` | `LabOrder` | Lab Technician |
| **RADIOLOGY** | `RADIOLOGY_STUDY` | `RadiologyRequest` | Radiographer |
| **PROCEDURE** | `PROCEDURE` | `ProcedureTask` | Nurse |
| **CONSULTATION** | `GOPD_CONSULT` | `Consultation` | Doctor |

---

## Current Service Configuration

### PHARMACY Services (1,051 services)
- **Workflow Type:** `DRUG_DISPENSE`
- **Creates:** `Prescription` object
- **Billing Timing:** `AFTER` (usually dispense then bill)
- **Allowed Roles:** `DOCTOR`, `PHARMACIST`
- **Dashboard:** Pharmacist can see all prescriptions

**Examples:**
- Aspirin → Creates Prescription
- Paracetamol → Creates Prescription
- 10ml Syringe → Creates Prescription
- IV Set → Creates Prescription

### LAB Services (1 service)
- **Workflow Type:** `LAB_ORDER`
- **Creates:** `LabOrder` object
- **Billing Timing:** `BEFORE` (pay first, then test)
- **Allowed Roles:** `DOCTOR`
- **Dashboard:** Lab technician can see all lab orders

### PROCEDURE Services (391 services)
- **Workflow Type:** `PROCEDURE`
- **Creates:** `ProcedureTask` object
- **Billing Timing:** `AFTER` (perform then bill)
- **Allowed Roles:** `DOCTOR`, `NURSE`
- **Dashboard:** Nurse can see all procedure tasks

**Examples:**
- ANC Registration → Creates ProcedureTask
- Normal Vaginal Delivery → Creates ProcedureTask
- Wound Dressing → Creates ProcedureTask

### RADIOLOGY Services (0 currently)
- **Workflow Type:** `RADIOLOGY_STUDY`
- **Creates:** `RadiologyRequest` object
- **Billing Timing:** `BEFORE` (pay first, then scan)
- **Allowed Roles:** `DOCTOR`
- **Dashboard:** Radiographer can see all radiology requests

---

## How to Use This Feature

### As a Doctor (During Consultation):

1. **Open patient visit**
2. **Start consultation**
3. **Search for services:**
   - Type "Aspirin" → Select it
   - Type "Complete Blood Count" → Select it
   - Type "Chest X-Ray" → Select it

4. **System automatically:**
   - Creates Prescription for Aspirin (Pharmacist will see it)
   - Creates LabOrder for CBC (Lab tech will see it)
   - Creates RadiologyRequest for X-Ray (Radiographer will see it)
   - Generates bills for all services

5. **Patient pays at reception**

6. **Department staff see their orders:**
   - Pharmacist sees "Aspirin" in their dashboard
   - Lab tech sees "CBC" in their dashboard
   - Radiographer sees "Chest X-Ray" in their dashboard

---

## Governance Rules

The system enforces strict rules:

### ✅ Service Requirements:
- **Visit Required:** Most services require an active visit
- **Consultation Required:** Clinical services require consultation
- **Payment Required:** Payment before service (for BEFORE services)
- **Role Required:** Only allowed roles can order

### ✅ Billing Rules:
- **Auto-Bill:** Services automatically create billing
- **Bill Timing:** 
  - `BEFORE` = Pay first (Lab, Radiology)
  - `AFTER` = Service first, pay later (Pharmacy, Procedures)

### ✅ Department Access:
- Pharmacist can only see/dispense Prescriptions
- Lab tech can only see/process LabOrders
- Radiographer can only see/perform RadiologyRequests
- Nurse can only see/perform ProcedureTasks

---

## Example Scenario

### Scenario: Patient with Malaria

**Doctor selects these services:**
1. **Malaria Test** (LAB_ORDER)
2. **IV Quinine** (DRUG_DISPENSE)
3. **IV Drip Setup** (PROCEDURE)

**System automatically creates:**
1. ✅ `LabOrder` for Malaria Test → Lab dashboard
2. ✅ `Prescription` for IV Quinine → Pharmacy dashboard
3. ✅ `ProcedureTask` for IV Setup → Nurse dashboard
4. ✅ `BillingLineItem` for each service → Bill

**Patient pays ₦15,000 at reception**

**Department staff can now:**
- **Lab Tech:** Sees "Malaria Test" order → Collects sample → Posts result
- **Pharmacist:** Sees "IV Quinine" prescription → Dispenses drug
- **Nurse:** Sees "IV Drip Setup" task → Sets up IV for patient

**All tracked in one visit, all billed correctly!**

---

## Verification

### Check Current Configuration:

```bash
cd backend
python manage.py shell
```

```python
from apps.billing.service_catalog_models import ServiceCatalog

# Check PHARMACY services
aspirin = ServiceCatalog.objects.filter(name__icontains='ASPIRIN').first()
if aspirin:
    print(f"Aspirin workflow: {aspirin.workflow_type}")  # Should be: DRUG_DISPENSE
    print(f"Creates: Prescription")

# Check LAB services
lab = ServiceCatalog.objects.filter(department='LAB').first()
if lab:
    print(f"Lab workflow: {lab.workflow_type}")  # Should be: LAB_ORDER
    print(f"Creates: LabOrder")

# Check PROCEDURE services
proc = ServiceCatalog.objects.filter(department='PROCEDURE').first()
if proc:
    print(f"Procedure workflow: {proc.workflow_type}")  # Should be: PROCEDURE
    print(f"Creates: ProcedureTask")
```

---

## Implementation File

The workflow orchestration is in:
`backend/apps/visits/downstream_service_workflow.py`

This file contains the `order_downstream_service()` function that:
1. Validates the service
2. Routes to the correct handler based on `workflow_type`
3. Creates the appropriate domain object (Prescription, LabOrder, etc.)
4. Generates billing
5. Returns both the domain object and billing line item

---

## Summary

### ✅ YES - It's Already Implemented!

- **Aspirin** → Creates `Prescription` → Pharmacist dispenses
- **Lab Tests** → Creates `LabOrder` → Lab tech processes
- **X-Rays** → Creates `RadiologyRequest` → Radiographer performs
- **Procedures** → Creates `ProcedureTask` → Nurse executes

**The system automatically routes services to the correct department based on the `workflow_type` field in the ServiceCatalog!**

### Benefits:

1. ✅ **Single entry point** - Doctor selects all services in one place
2. ✅ **Auto-routing** - Services automatically go to correct departments
3. ✅ **Auto-billing** - All services are billed automatically
4. ✅ **Role-based access** - Each department sees only their tasks
5. ✅ **Audit trail** - Every action is tracked and logged

**This is the core feature of the Service-Driven EMR architecture!** 🎉

