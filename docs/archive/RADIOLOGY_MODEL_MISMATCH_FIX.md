# Radiology Model Mismatch Fix

## Problem
Radiology orders created via Service Catalog were not appearing in the consultation workspace, even though the database showed they were created successfully.

### Error Symptoms:
- ✅ Service Catalog order succeeds
- ✅ Database has `RadiologyRequest` record
- ❌ UI shows "No pending radiology orders for this visit"
- ❌ Duplicate order error when trying again

## Root Cause

There are **TWO different radiology models** in the system:

### 1. RadiologyRequest (Newer, Consultation-Dependent)
- Created by: Service Catalog via `_order_radiology_service()`
- Fields: `study_type`, `study_code`, `clinical_indication`, `instructions`
- Requires: Visit + Consultation
- Table: `radiology_requests`
- Used for: Service Catalog integration

### 2. RadiologyOrder (Older, Visit-Scoped)
- Created by: Direct radiology order form
- Fields: `imaging_type`, `body_part`, `clinical_indication`
- Requires: Visit only
- Table: `radiology_orders`
- Used for: Legacy radiology workflow

### The Mismatch:
**Backend URL routing:**
```python
# backend/apps/radiology/urls.py
router.register(
    r'',
    RadiologyOrderViewSet,  # ❌ Returns RadiologyOrder objects
    basename='radiology-order'
)
```

**Service Catalog creates:**
```python
# backend/apps/visits/downstream_service_workflow.py
def _order_radiology_service(...):
    radiology_request = RadiologyRequest.objects.create(...)  # ✅ Creates RadiologyRequest
```

**Frontend fetches:**
```typescript
// frontend/src/api/radiology.ts
export const fetchRadiologyOrders = async (visitId: string) => {
  return apiRequest<any>(`/visits/${visitId}/radiology/`);  // ❌ Gets RadiologyOrder
};
```

**Result:** Orders created in `radiology_requests` table, but frontend queries `radiology_orders` table!

## Solution

### Changed Backend URL Routing

**File:** `backend/apps/radiology/urls.py`

**Before:**
```python
router.register(
    r'',
    RadiologyOrderViewSet,  # Returns RadiologyOrder
    basename='radiology-order'
)
```

**After:**
```python
router.register(
    r'',
    RadiologyRequestViewSet,  # Returns RadiologyRequest
    basename='radiology-request'
)
```

Now the `/visits/{visit_id}/radiology/` endpoint returns `RadiologyRequest` objects, which matches what the Service Catalog creates!

## API Endpoints After Fix

| Endpoint | ViewSet | Model | Purpose |
|----------|---------|-------|---------|
| `GET /visits/{visit_id}/radiology/` | `RadiologyRequestViewSet` | `RadiologyRequest` | List radiology requests (from Service Catalog) |
| `POST /visits/{visit_id}/radiology/` | `RadiologyRequestViewSet` | `RadiologyRequest` | Create radiology request |
| `GET /visits/{visit_id}/radiology/results/` | `RadiologyResultViewSet` | `RadiologyResult` | List radiology reports |

## Data Flow After Fix

```
1. Doctor orders "Chest X-Ray" via Service Catalog
   ↓
2. Backend creates RadiologyRequest object in radiology_requests table
   ↓
3. Frontend fetches from /visits/235/radiology/
   ↓
4. Backend returns RadiologyRequest objects (via RadiologyRequestViewSet)
   ↓
5. RadiologyInline displays the order ✅
```

## Model Comparison

### RadiologyRequest Fields:
```python
class RadiologyRequest(models.Model):
    visit = ForeignKey(Visit)
    consultation = ForeignKey(Consultation)  # Required
    study_type = CharField  # e.g., "Chest X-Ray PA"
    study_code = CharField  # e.g., "RAD-XRAY-CHEST"
    clinical_indication = TextField
    instructions = TextField
    status = CharField  # PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    report = TextField  # Posted by radiographer
    ordered_by = ForeignKey(User)
    reported_by = ForeignKey(User, null=True)
```

### RadiologyOrder Fields:
```python
class RadiologyOrder(models.Model):
    visit = ForeignKey(Visit)
    imaging_type = CharField  # XRAY, CT, MRI, US
    body_part = CharField
    clinical_indication = TextField
    priority = CharField  # ROUTINE, URGENT, EMERGENCY
    status = CharField
    ordered_by = ForeignKey(User)
```

**Key Difference:** `RadiologyRequest` requires consultation and uses `study_type`, while `RadiologyOrder` uses `imaging_type` and `body_part`.

## Testing

### 1. Restart Django Server
```bash
cd backend
python manage.py runserver
```

### 2. Order a Radiology Service
1. Go to consultation workspace
2. Search for "X-Ray" in Service Catalog
3. Fill in Radiology Order Details form
4. Submit

### 3. Verify Order Appears
Scroll to "Radiology Orders & Results" section - should now see:
```
🔬 Radiology Orders & Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Order #123                    [PENDING]
Study Type: Chest X-Ray PA
Study Code: RAD-XRAY-CHEST
Clinical Indication: Suspected pneumonia
Instructions: Focus on right lower lobe

(Awaiting radiographer report)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 4. Verify in Database
```python
from apps.radiology.models import RadiologyRequest

# Check radiology requests
requests = RadiologyRequest.objects.filter(visit_id=235)
print(f"Found {requests.count()} radiology requests")
for req in requests:
    print(f"  #{req.id}: {req.study_type} - {req.status}")
```

## Migration Path

### For Existing RadiologyOrder Records
If you have existing `RadiologyOrder` records that need to be visible, you have two options:

**Option 1:** Migrate data from `RadiologyOrder` to `RadiologyRequest`:
```python
from apps.radiology.models import RadiologyOrder, RadiologyRequest
from apps.consultations.models import Consultation

for order in RadiologyOrder.objects.all():
    # Find or create a consultation for this visit
    consultation = Consultation.objects.filter(visit=order.visit).first()
    if not consultation:
        continue  # Skip orders without consultation
    
    # Create corresponding RadiologyRequest
    RadiologyRequest.objects.create(
        visit=order.visit,
        consultation=consultation,
        study_type=f"{order.get_imaging_type_display()} - {order.body_part}",
        study_code=f"RAD-{order.imaging_type}-{order.id}",
        clinical_indication=order.clinical_indication or '',
        instructions='',
        status=order.status,
        ordered_by=order.ordered_by,
    )
    print(f"Migrated order #{order.id}")
```

**Option 2:** Keep both endpoints (not recommended, adds complexity):
- `/visits/{visit_id}/radiology/` → RadiologyRequest (from Service Catalog)
- `/visits/{visit_id}/radiology-orders/` → RadiologyOrder (legacy)

## Why This Happened

The system was in transition from the older `RadiologyOrder` model to the newer `RadiologyRequest` model (consultation-dependent, Service Catalog integrated). The URL routing wasn't updated to match the new model being created.

## Files Modified
1. ✅ `backend/apps/radiology/urls.py` - Changed router to use `RadiologyRequestViewSet`

## Related Files (No Changes Needed)
- `backend/apps/visits/downstream_service_workflow.py` - Already creates `RadiologyRequest` ✅
- `frontend/src/components/inline/RadiologyInline.tsx` - Already displays orders correctly ✅
- `frontend/src/api/radiology.ts` - Already fetches from correct endpoint ✅
- `frontend/src/hooks/useRadiologyOrders.ts` - Already handles data correctly ✅

## Summary

**Problem:** Service Catalog created `RadiologyRequest` objects, but URL routed to `RadiologyOrderViewSet` which returned `RadiologyOrder` objects.

**Solution:** Updated URL routing to use `RadiologyRequestViewSet` instead of `RadiologyOrderViewSet`.

**Result:** Orders created via Service Catalog now appear in consultation workspace! ✅

After restarting Django, your radiology orders will appear immediately! 🎉

