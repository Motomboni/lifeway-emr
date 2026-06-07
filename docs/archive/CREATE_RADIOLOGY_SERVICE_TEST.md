# How to Test Radiology Orders & Results

## Prerequisites

You need at least one RADIOLOGY service in your ServiceCatalog.

### Option 1: Create Via Django Admin

1. Go to Django Admin: `http://localhost:8000/admin/`
2. Navigate to **Billing → Service Catalogs**
3. Click **Add Service Catalog**
4. Fill in:
   - **Department:** RADIOLOGY
   - **Service Code:** RAD-XRAY-CHEST
   - **Name:** Chest X-Ray PA
   - **Amount:** 7500.00
   - **Category:** RADIOLOGY
   - **Workflow Type:** RADIOLOGY_STUDY
   - **Requires Visit:** ✓ (checked)
   - **Requires Consultation:** ✓ (checked)
   - **Auto Bill:** ✓ (checked)
   - **Bill Timing:** BEFORE
   - **Allowed Roles:** DOCTOR
   - **Is Active:** ✓ (checked)
5. Save

### Option 2: Create Via Django Shell

```bash
cd backend
python manage.py shell
```

```python
from apps.billing.service_catalog_models import ServiceCatalog

# Create Chest X-Ray service
ServiceCatalog.objects.create(
    department='RADIOLOGY',
    service_code='RAD-XRAY-CHEST',
    name='Chest X-Ray PA',
    amount=7500.00,
    category='RADIOLOGY',
    workflow_type='RADIOLOGY_STUDY',
    requires_visit=True,
    requires_consultation=True,
    auto_bill=True,
    bill_timing='BEFORE',
    allowed_roles=['DOCTOR'],
    is_active=True,
    description='Chest X-Ray - Posteroanterior view'
)

# Create additional radiology services (optional)
ServiceCatalog.objects.create(
    department='RADIOLOGY',
    service_code='RAD-XRAY-ABDOMEN',
    name='Abdominal X-Ray',
    amount=8000.00,
    category='RADIOLOGY',
    workflow_type='RADIOLOGY_STUDY',
    requires_visit=True,
    requires_consultation=True,
    auto_bill=True,
    bill_timing='BEFORE',
    allowed_roles=['DOCTOR'],
    is_active=True,
    description='Abdominal X-Ray'
)

ServiceCatalog.objects.create(
    department='RADIOLOGY',
    service_code='RAD-US-ABDOMEN',
    name='Ultrasound Abdomen',
    amount=12000.00,
    category='RADIOLOGY',
    workflow_type='RADIOLOGY_STUDY',
    requires_visit=True,
    requires_consultation=True,
    auto_bill=True,
    bill_timing='BEFORE',
    allowed_roles=['DOCTOR'],
    is_active=True,
    description='Abdominal Ultrasound'
)

print("Radiology services created successfully!")
```

## Testing the Complete Workflow

### Step 1: Login as Doctor
1. Login with doctor credentials
2. Navigate to an open patient visit

### Step 2: Create/Save Consultation
1. Fill in consultation details (history, examination, diagnosis)
2. Click **Save Consultation**
3. ✅ Consultation must be saved first (required for ordering services)

### Step 3: Order Radiology Service via Service Catalog

1. Scroll down to **"Order Services from Catalog"** section
2. Click **🔍 Search & Order Service**
3. Type "X-Ray" or "Chest" in the search box
4. Select "Chest X-Ray PA" from results
5. **Radiology Order Details Form** should appear:
   - **Study Type:** Pre-filled with "Chest X-Ray PA" (can modify)
   - **Clinical Indication:** Enter reason (e.g., "Suspected pneumonia")
   - **Instructions:** Enter special instructions (e.g., "Focus on right lower lobe")
6. Click **✓ Order Imaging Study**
7. ✅ Should see success message: "Radiology order for Chest X-Ray PA created successfully"

### Step 4: Verify Order Appears

Scroll down to **"Radiology Orders & Results"** section. You should now see:

```
🔬 Radiology Orders
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order #123                      [PENDING]
Imaging: X-Ray
Body Part: Chest  
Clinical Indication: Suspected pneumonia
Priority: ROUTINE
Instructions: Focus on right lower lobe

(No report yet - awaiting radiographer)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 5: Post Radiology Report (As Radiographer)

#### Option A: Via Radiographer Dashboard
1. Logout from doctor account
2. Login as radiographer (RADIOLOGY_TECH role)
3. Navigate to Radiology Orders page
4. Find the pending order
5. Click "Add Report"
6. Fill in:
   - **Report:** Enter findings
   - **Finding Flag:** Select NORMAL, ABNORMAL, or CRITICAL
7. Submit report

#### Option B: Via Django Shell (for testing)
```python
from apps.radiology.models import RadiologyRequest
from apps.users.models import User

# Get the order
rad_order = RadiologyRequest.objects.latest('id')
print(f"Order ID: {rad_order.id}, Study: {rad_order.study_type}, Status: {rad_order.status}")

# Get a user to assign as reporter (use any user for testing)
reporter = User.objects.filter(role='RADIOLOGY_TECH').first() or User.objects.first()

# Post the report
rad_order.status = 'COMPLETED'
rad_order.report = """
Right lower lobe consolidation consistent with pneumonia.
No pleural effusion. Cardiac silhouette normal.
No pneumothorax. Bones intact.

IMPRESSION: Right lower lobe pneumonia.
"""
rad_order.reported_by = reporter
from django.utils import timezone
rad_order.report_date = timezone.now()
rad_order.save()

print("Report posted successfully!")
```

### Step 6: View Report (Back to Doctor)

1. Return to doctor's consultation workspace
2. Refresh the page (or re-open the visit)
3. Scroll to **"Radiology Orders & Results"** section
4. ✅ Should now see the posted report:

```
🔬 Radiology Orders
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order #123                      [COMPLETED]
Imaging: X-Ray
Body Part: Chest
Clinical Indication: Suspected pneumonia

✓ Report                        [ABNORMAL]
  Right lower lobe consolidation consistent
  with pneumonia. No pleural effusion.
  Cardiac silhouette normal.
  
  IMPRESSION: Right lower lobe pneumonia.
  
  Reported by: Dr. Smith
  Reported: Jan 15, 2026 3:15 PM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Troubleshooting

### "No pending radiology orders for this visit"
This means:
- ✅ RadiologyInline component is working
- ❌ No radiology orders have been created yet
- **Action:** Order a radiology service via Service Catalog (Step 3)

### "Radiology Order Details Form doesn't appear"
Check:
- Is there a RADIOLOGY service in ServiceCatalog?
- Is the service active (is_active=True)?
- Is workflow_type set to 'RADIOLOGY_STUDY'?
- Do you have a saved consultation?

### "Service ordered successfully but no order appears"
Check browser console for errors:
- Backend may have rejected the request
- RadiologyInline may not be refreshing
- Try refreshing the page manually

### "Cannot order service"
Check:
- Do you have an active consultation? (Save consultation first)
- Is visit still OPEN?
- Are you logged in as DOCTOR?

## Expected Data Flow

```
1. Doctor orders "Chest X-Ray" via Service Catalog
   ↓
2. RadiologyOrderDetailsForm collects:
   - study_type: "Chest X-Ray PA"
   - clinical_indication: "Suspected pneumonia"
   - instructions: "Focus on right lower lobe"
   ↓
3. Frontend sends to: POST /api/v1/billing/add-item/
   {
     visit_id: 235,
     department: "RADIOLOGY",
     service_code: "RAD-XRAY-CHEST",
     additional_data: {
       study_type: "Chest X-Ray PA",
       clinical_indication: "Suspected pneumonia",
       instructions: "Focus on right lower lobe"
     }
   }
   ↓
4. Backend calls: _order_radiology_service()
   ↓
5. Creates: RadiologyRequest object
   ↓
6. Creates: BillingLineItem
   ↓
7. Returns success
   ↓
8. Frontend refreshes
   ↓
9. RadiologyInline fetches orders
   ↓
10. Order appears in "Radiology Orders & Results"
```

## Verification Queries

### Check if radiology services exist:
```python
from apps.billing.service_catalog_models import ServiceCatalog
rad_services = ServiceCatalog.objects.filter(department='RADIOLOGY', is_active=True)
print(f"Found {rad_services.count()} active radiology services")
for service in rad_services:
    print(f"  - {service.service_code}: {service.name} (₦{service.amount})")
```

### Check if radiology orders exist for a visit:
```python
from apps.radiology.models import RadiologyRequest
visit_id = 235  # Replace with your visit ID
rad_orders = RadiologyRequest.objects.filter(visit_id=visit_id)
print(f"Found {rad_orders.count()} radiology orders for visit {visit_id}")
for order in rad_orders:
    print(f"  Order #{order.id}: {order.study_type} - Status: {order.status}")
```

## Summary

1. ✅ Create radiology service in ServiceCatalog
2. ✅ Save consultation first
3. ✅ Order service via Service Catalog → Radiology form appears
4. ✅ Fill form and submit
5. ✅ Order appears in RadiologyInline section
6. ✅ Radiographer posts report
7. ✅ Doctor sees report in consultation workspace

The "No pending radiology orders" message means the component is working - you just need to create an order first!

