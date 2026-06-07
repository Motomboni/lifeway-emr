# Testing Service Ordering - Quick Guide

## Current Status

The Prescriptions page shows **"0 prescriptions"** because **no services have been ordered yet** after the fix.

The backend fix is in place and ready. Now you need to **test ordering a service** to verify it works.

---

## How to Test (Step-by-Step)

### 1. Create or Open a Visit

**Option A: Use Existing Visit**
- Visit #235 is already open
- Patient already registered

**Option B: Create New Visit**
- Go to Dashboard → Register New Patient
- Create a new visit

### 2. Start/Continue Consultation

1. Click on the visit (e.g., Visit #235)
2. If no consultation exists, click "Start Consultation"
3. If consultation exists, ensure it's ACTIVE

### 3. Order a Service (THIS IS THE KEY STEP!)

**There are two ways to order services:**

#### Method A: From "Add Services" Section

1. In the Visit Details page, find the **"Add Services"** or **"Charges & Billing"** section
2. Click **"Add Service"** or **"Search Service Catalog"**
3. **Type**: "Aspirin" or "Paracetamol"
4. **Select** the service from the dropdown
5. **Click** "Add to Visit" or similar button

#### Method B: From Service Catalog Inline (During Consultation)

1. In the Consultation view
2. Look for **"Order Services from Catalog"** section
3. **Type**: "Aspirin" or any pharmacy service
4. **Select** it
5. System should show success message

---

## Expected Results

### ✅ If Fix is Working:

**Frontend Success Message:**
```
✓ Service added successfully
✓ Service ordered, will reflect in patient account
```

**Console Log:**
```
Service ordered successfully: {service details}
```

**Backend Creates:**
- ✅ Prescription (for pharmacy services)
- ✅ BillingLineItem
- ✅ Links to Visit and Consultation

**Pharmacist Dashboard:**
- ✅ Visit #235 now shows in prescriptions list
- ✅ Shows: "Aspirin 300mg - Status: Awaiting Payment"

### ❌ If Fix is NOT Working:

**Error Message:**
```
✗ Service with code 'PHARM-XXXX' not found in PHARMACY price list
```

**Console Log:**
```
Error ordering service: Service not found...
```

---

## Verification Steps

### Step 1: Order the Service
- Follow steps above to order "Aspirin" or any pharmacy service
- Watch for success/error message

### Step 2: Check Frontend Console
- Open Browser DevTools (F12)
- Go to Console tab
- Look for messages like:
  - "Service ordered successfully" ✅
  - "Service with code... not found" ❌

### Step 3: Refresh Prescriptions Page
- Go to Pharmacist Dashboard
- Check Prescriptions page
- Should now show the visit with prescription

### Step 4: Verify Database (Optional)
In backend terminal:
```bash
cd backend
python manage.py shell
```

```python
from apps.pharmacy.models import Prescription
print(f"Total Prescriptions: {Prescription.objects.count()}")
if Prescription.objects.exists():
    for p in Prescription.objects.all()[:5]:
        print(f"Visit {p.visit_id}: {p.drug_name} - {p.status}")
```

---

## Troubleshooting

### If You Get "Consultation Required" Error

**Problem:** Service requires consultation but none exists

**Solution:**
1. Go to Visit Details page
2. Click "Start Consultation" 
3. Wait for consultation to be created
4. Try ordering service again

### If You Get "Payment Cleared" Error

**Problem:** Some services require payment before ordering

**Solution:**
1. For LAB/RADIOLOGY services, patient must pay first
2. For PHARMACY/PROCEDURE services, can order first then pay later
3. Try ordering a pharmacy service (like Aspirin) - no payment needed

### If Page Shows "0 prescriptions" After Ordering

**Possible Causes:**
1. Service wasn't actually saved (check console for errors)
2. Page needs refresh (try F5)
3. Prescription was created but page is filtering it out (check filters)

**Solution:**
- Refresh the Prescriptions page (F5)
- Check browser console for errors
- Verify service was added in Visit Details page billing section

---

## Quick Test Script

**1-Minute Test:**

```
1. Go to Visit #235 (or create new visit)
2. Start consultation (if not started)
3. Click "Add Service" or "Order from Catalog"
4. Type "Aspirin"
5. Select it
6. Click Add/Order
7. Watch for success message
8. Go to Pharmacist Dashboard → Prescriptions
9. Should now show Visit #235 with prescription
```

---

## What Each Service Creates

| Service Type | Creates | Where to Check |
|--------------|---------|----------------|
| **Aspirin** | Prescription | Pharmacist Dashboard |
| **Paracetamol** | Prescription | Pharmacist Dashboard |
| **Lab Test** | LabOrder | Laboratory Dashboard |
| **X-Ray** | RadiologyRequest | Radiology Dashboard |
| **Procedure** | ProcedureTask | Nurse Dashboard |

---

## Current State

- ✅ Backend fix applied
- ✅ ServiceCatalog populated (1,443 services)
- ✅ Workflow system active
- ⏳ **Waiting for first service to be ordered**

**The system is ready! Just need to test ordering a service.** 🎯

---

## After Testing

Once you successfully order a service and see it in the Pharmacist Dashboard, the system is **fully confirmed working**.

Then you can:
- Order multiple services
- Test different service types (lab, radiology, procedures)
- Verify department routing
- Test payment workflows
- Test dispensing

**Start with ordering one pharmacy service to confirm the fix!**

