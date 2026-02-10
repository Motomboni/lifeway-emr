# Revenue Leak Dashboard Setup

## Route Addition Required

Add the following to `frontend/src/App.tsx`:

### Import Statement
Add to the imports section:
```typescript
import RevenueLeakDashboardPage from './pages/RevenueLeakDashboardPage';
```

### Route Definition
Add to the routes section (typically inside a protected route wrapper):
```typescript
<Route 
  path="/revenue-leaks" 
  element={<RevenueLeakDashboardPage />} 
/>
```

## Access Control

The page automatically checks for Admin or Management roles and redirects unauthorized users.

## Features Implemented

✅ Summary cards with total revenue and leak counts
✅ Filterable table with all required columns
✅ Department, status, and date range filters
✅ High-value leak highlighting (₦10,000+)
✅ Warning icons for unresolved leaks
✅ Clickable rows for detailed view
✅ Visit navigation from detail modal
✅ No deletion functionality (as required)
✅ Responsive design

## API Endpoints Used

- `GET /api/v1/billing/revenue-leak/` - List leaks with filters
- `GET /api/v1/billing/revenue-leak/summary/` - Get summary statistics

## Usage

1. Navigate to `/revenue-leaks`
2. Use filters to narrow down results
3. Click on any row to view detailed leak information
4. Click "View Visit" to navigate to the associated visit

