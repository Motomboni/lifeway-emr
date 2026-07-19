# Billing Charges - Radiology Services Not Appearing Fix

## Problem
Radiology services ordered through Service Catalog were not appearing in the Billing & Payments charges breakdown, even though they were successfully creating billing line items.

## Root Cause
The billing charges API endpoint (`GET /api/v1/visits/{visit_id}/billing/charges/`) was only including:
1. **VisitCharge** objects (legacy system)
2. **BillItem** objects from the old Bill system

It was NOT including **BillingLineItem** objects, which are created by the new ServiceCatalog system when services are ordered.

## Solution
Updated the `BillingChargesView.get()` method in `backend/apps/billing/billing_endpoints.py` to also fetch and include **BillingLineItem** objects in the charges list.

### Code Changes

**File**: `backend/apps/billing/billing_endpoints.py`

Added a new section after the BillItem handling (around line 208):

```python
# Add BillingLineItems (ServiceCatalog system) that don't have corresponding VisitCharges
try:
    from .billing_line_item_models import BillingLineItem
    
    billing_line_items = BillingLineItem.objects.filter(visit=visit).select_related('service_catalog').order_by('-created_at')
    
    # Map ServiceCatalog department to charge category
    department_to_category = {
        'LAB': 'LAB',
        'PHARMACY': 'DRUG',
        'RADIOLOGY': 'RADIOLOGY',
        'PROCEDURE': 'PROCEDURE',
        'CONSULTATION': 'CONSULTATION',
    }
    
    for line_item in billing_line_items:
        # Get category from service catalog department
        department = line_item.service_catalog.department if line_item.service_catalog else 'MISC'
        category = department_to_category.get(department, 'MISC')
        
        # Check if a VisitCharge already exists for this line item
        existing_charge = VisitCharge.objects.filter(
            visit=visit,
            category=category,
            description=line_item.source_service_name,
            amount=line_item.amount
        ).first()
        
        # Only add if no corresponding VisitCharge exists
        if not existing_charge:
            charges_data.append({
                'id': f'billing_line_item_{line_item.id}',  # Use prefixed ID to avoid conflicts
                'visit_id': visit.id,
                'category': category,
                'description': line_item.source_service_name,
                'amount': str(line_item.amount),
                'created_by_system': True,
                'created_at': line_item.created_at.isoformat(),
                'updated_at': line_item.updated_at.isoformat()
            })
except Exception as e:
    # Log error but don't fail the request
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"Error including BillingLineItems in charges list: {str(e)}")
```

## How It Works

### Three Billing Systems
The EMR has THREE billing systems that coexist:

1. **VisitCharge** (Legacy)
   - Direct charge objects attached to visit
   - Still used for some manual charges

2. **Bill + BillItem** (Old System)
   - Visit has a Bill, Bill has BillItems
   - Used by older workflows

3. **BillingLineItem** (New ServiceCatalog System) ✨
   - Created automatically when services are ordered via ServiceCatalog
   - Links to ServiceCatalog for service definition
   - Links to Visit for visit-scoped billing
   - Snapshots service details (code, name, amount) at time of billing

### API Response Structure
The charges endpoint now returns a unified list containing all three types, converted to a common format:

```json
[
  {
    "id": "billing_line_item_15",
    "visit_id": 235,
    "category": "RADIOLOGY",
    "description": "Chest X-Ray PA",
    "amount": "5000.00",
    "created_by_system": true,
    "created_at": "2026-01-15T10:30:00",
    "updated_at": "2026-01-15T10:30:00"
  }
]
```

### Frontend Display
The frontend `ChargesBreakdown` component (`frontend/src/components/billing/ChargesBreakdown.tsx`) groups charges by category and displays them under the appropriate department:

- **LAB** → 🧪 Laboratory
- **RADIOLOGY** → 📷 Radiology
- **DRUG** (PHARMACY) → 💊 Pharmacy
- **PROCEDURE** → ⚕️ Procedures
- **CONSULTATION** → 🩺 Consultation
- **MISC** → 📋 Miscellaneous

## Testing

### Test Steps
1. **Order a radiology service** via Service Catalog in consultation
2. **Navigate to Billing & Payments** for that visit
3. **Click on "Charges" tab**
4. **Verify** radiology service appears under "📷 Radiology" section with correct amount

### Expected Result
- Radiology service appears in charges breakdown
- Grouped under "Radiology" category
- Shows service name and amount
- Marked as "System Generated"

## Impact
This fix ensures that ALL services ordered through the ServiceCatalog workflow (LAB, RADIOLOGY, PHARMACY, PROCEDURE, CONSULTATION) now correctly appear in the Billing & Payments charges breakdown.

## Files Modified
1. `backend/apps/billing/billing_endpoints.py` - Added BillingLineItem handling to charges endpoint

## Related Issues
- Previously, only LAB services were affected by this issue (if they were using BillingLineItem)
- Now fixed for ALL ServiceCatalog services including RADIOLOGY

## Note
No frontend changes were required. The frontend was already correctly handling the charges data format - it just wasn't receiving radiology charges because the backend wasn't including BillingLineItem objects.

