# Service Search Implementation

## Overview

Service search functionality has been implemented in the billing system, allowing Receptionists to quickly search and add services from the catalog (437 services) to patient bills.

## Components Created

### 1. ServiceSearchInput Component
**Location:** `frontend/src/components/billing/ServiceSearchInput.tsx`

**Features:**
- Real-time search with 300ms debounce
- Autocomplete dropdown with service suggestions
- Keyboard navigation (Arrow keys, Enter, Escape)
- Displays service name, code, department, and price
- Shows loading indicator during search
- Handles empty states and errors

**Props:**
```typescript
interface ServiceSearchInputProps {
  onServiceSelect: (service: Service) => void;
  department?: 'LAB' | 'PHARMACY' | 'RADIOLOGY' | 'PROCEDURE';
  placeholder?: string;
  disabled?: boolean;
}
```

**Usage:**
```tsx
<ServiceSearchInput
  onServiceSelect={handleServiceSelect}
  department="PROCEDURE" // Optional filter
  placeholder="Search services..."
/>
```

### 2. Updated ChargesBreakdown Component
**Location:** `frontend/src/components/billing/ChargesBreakdown.tsx`

**New Features:**
- "Add from Catalog" button - Opens service search
- "Add Manual Charge" button - Opens manual charge form
- Integrated ServiceSearchInput component
- Automatic bill item creation when service is selected
- Success/error notifications

## User Workflow

1. **Open Visit Details** → Navigate to Billing section → Charges tab
2. **Click "🔍 Add from Catalog"** button
3. **Type to search** (e.g., "consultation", "dental", "vaccine")
4. **See suggestions** with prices in real-time
5. **Select service** by clicking or pressing Enter
6. **Service added automatically** to bill with correct price
7. **Bill updates** immediately with new charge

## API Integration

### Search Services
```typescript
import { searchServices } from '../../api/billing';

const response = await searchServices({
  q: 'consultation',
  department: 'PROCEDURE', // Optional
  limit: 20
});
```

### Add Service to Bill
```typescript
import { addServiceToBill } from '../../api/billing';

await addServiceToBill({
  visit_id: 123,
  department: 'PROCEDURE',
  service_code: 'CONS-001-DENTALCONS'
});
```

## UI Features

### Service Search Input
- **Search box** with loading indicator
- **Dropdown suggestions** showing:
  - Department badge (Lab, Pharmacy, Radiology, Procedure)
  - Service name
  - Service code
  - Description (if available)
  - Price (formatted as currency)
- **Keyboard shortcuts:**
  - `Arrow Down/Up` - Navigate suggestions
  - `Enter` - Select service
  - `Escape` - Close dropdown
- **Empty state** - Shows "No services found" message

### Charges Breakdown
- **Two add options:**
  1. **Add from Catalog** (Green button) - Search and add from 437 services
  2. **Add Manual Charge** (Blue button) - Add custom charge
- **Visual distinction:**
  - Service search in green box
  - Manual charge in gray box
- **Real-time updates** after adding service

## Example Searches

Users can search by:
- **Service name:** "consultation", "dental", "vaccine"
- **Service code:** "CONS-001", "PROC-"
- **Department:** Filter by LAB, PHARMACY, RADIOLOGY, PROCEDURE
- **Partial matches:** "dent" finds "DENTAL CONSULTATION"

## Error Handling

- **Visit closed:** Shows error if trying to add to closed visit
- **Service not found:** Shows "No services found" message
- **API errors:** Displays error toast notification
- **Network issues:** Handles gracefully with loading states

## Accessibility

- Keyboard navigation support
- Focus management
- ARIA labels (can be enhanced)
- Screen reader friendly structure

## Performance

- **Debounced search:** 300ms delay to reduce API calls
- **Limited results:** Max 20 suggestions per search
- **Lazy loading:** Only searches when user types 2+ characters
- **Caching:** Can be enhanced with React Query in future

## Future Enhancements

1. **React Query integration** for better caching
2. **Recent services** - Show recently used services
3. **Favorites** - Allow users to favorite common services
4. **Bulk add** - Add multiple services at once
5. **Service categories** - Filter by category (Consultation, Procedure, etc.)
6. **Price history** - Show price changes over time
7. **Service descriptions** - More detailed descriptions
8. **Image support** - Add service images (if applicable)

## Testing

To test the implementation:

1. **Start the backend server:**
   ```bash
   cd backend
   python manage.py runserver
   ```

2. **Start the frontend:**
   ```bash
   cd frontend
   npm start
   ```

3. **Test flow:**
   - Login as Receptionist
   - Open a visit
   - Go to Billing → Charges tab
   - Click "🔍 Add from Catalog"
   - Type "consultation" and select a service
   - Verify service is added to bill
   - Check that price is correct

## Files Modified

1. `frontend/src/components/billing/ServiceSearchInput.tsx` - **NEW**
2. `frontend/src/components/billing/ChargesBreakdown.tsx` - **UPDATED**
3. `frontend/src/api/billing.ts` - **UPDATED** (Service API functions)

## Dependencies

- `formatCurrency` utility from `../../utils/currency`
- `searchServices`, `addServiceToBill` from `../../api/billing`
- `useToast` hook for notifications

## Notes

- Service search requires at least 2 characters
- Services are filtered by active status (is_active=true)
- Department filter is optional
- All prices are in Nigerian Naira (NGN)
- Services are added as BillItems, not VisitCharges

