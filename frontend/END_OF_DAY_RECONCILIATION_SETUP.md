# End-of-Day Reconciliation Screen Setup

## Overview

The End-of-Day Reconciliation screen provides a comprehensive interface for daily clinic operations closure. It allows Admin and Receptionist staff to review revenue, identify outstanding items, and finalize the day's operations.

## Features

### 1. Summary Cards
- **Total Revenue**: Overall revenue for the day
- **Cash**: Cash payments received
- **Paystack**: Online payments via Paystack
- **Wallet**: Wallet payments
- **HMO**: HMO/Insurance payments

### 2. Outstanding Items
- **Unpaid Services**: Visits with outstanding balances
- **Revenue Leaks**: Detected revenue leaks with amounts

### 3. Visit Statistics
- Total visits processed
- Active visits closed during reconciliation

### 4. Staff Sign-off
- Prepared by (auto-filled)
- Reviewed by (optional)
- Finalized by (after finalization)
- Notes field for additional information
- Confirmation checkbox

### 5. Finalization
- "Finalize Day" button with confirmation dialog
- Warning message before finalization
- Read-only mode after finalization
- Printable summary view

## Access Control

- **Admin**: Full access
- **Receptionist**: Full access (with permission)
- **Other roles**: Access denied

## Route

The page is accessible at `/reconciliation`.

## Usage Flow

1. **Access Page**: Navigate to `/reconciliation`
2. **Review Summary**: Check revenue summary cards
3. **Check Outstanding**: Review unpaid services and revenue leaks
4. **Sign-off**: Enter name and notes (optional)
5. **Confirm**: Check confirmation checkbox
6. **Finalize**: Click "Finalize Day" button
7. **Confirm Finalization**: Confirm in dialog
8. **View Finalized**: Page becomes read-only after finalization

## API Endpoints Used

- `POST /api/v1/billing/reconciliation/` - Create reconciliation
- `GET /api/v1/billing/reconciliation/today/` - Get today's reconciliation
- `GET /api/v1/billing/reconciliation/{id}/` - Get reconciliation by ID
- `POST /api/v1/billing/reconciliation/{id}/finalize/` - Finalize reconciliation
- `POST /api/v1/billing/reconciliation/{id}/refresh/` - Refresh calculations

## Components

### Main Page
- `EndOfDayReconciliationPage.tsx` - Main reconciliation page component

### API Client
- `reconciliation.ts` - API client functions

### Styling
- `EndOfDayReconciliation.module.css` - Component styles

## Integration

The page is already integrated into `App.tsx`:

```typescript
<Route
  path="/reconciliation"
  element={
    <ProtectedRoute>
      <EndOfDayReconciliationPage />
    </ProtectedRoute>
  }
/>
```

## Adding to Dashboard

To add a quick action card to the dashboard:

```typescript
// In DashboardPage.tsx
{
  (user?.role === 'ADMIN' || user?.role === 'RECEPTIONIST') && (
    <ActionCard
      title="End-of-Day Reconciliation"
      description="Daily revenue reconciliation and closure"
      icon={<FaCalendarCheck />}
      onClick={() => navigate('/reconciliation')}
      color="#4caf50"
    />
  )
}
```

## Print Support

The page includes print styles that hide action buttons and modals when printing, showing only the reconciliation summary.

## Constraints

- Once finalized, reconciliation cannot be edited
- One reconciliation per day
- Confirmation required before finalization
- Read-only mode after finalization

## UX Goals

- **Fast**: Quick access to all reconciliation data
- **Confident**: Clear warnings and confirmations
- **Audit-safe**: Full audit trail with staff sign-off

