# Billing UI Global Rules

## Overview

This document defines the global UI rules that MUST be applied to all billing components.

## Rules

### 1. React Query for Data Freshness

**MUST:**
- Use React Query (`@tanstack/react-query`) for all billing data fetching
- Set appropriate `staleTime` and `refetchInterval` for real-time updates
- Use `useQuery` for reads, `useMutation` for writes
- Invalidate queries after mutations to ensure data freshness

**Example:**
```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Query
const { data, isLoading, error } = useQuery({
  queryKey: ['billing', 'summary', visitId],
  queryFn: () => getBillingSummary(visitId),
  staleTime: 10000, // 10 seconds
  refetchInterval: 30000, // 30 seconds
});

// Mutation
const queryClient = useQueryClient();
const mutation = useMutation({
  mutationFn: (data) => createPayment(visitId, data),
  onSuccess: () => {
    queryClient.invalidateQueries(['billing', 'summary', visitId]);
    showSuccess('Payment processed successfully');
  },
});
```

**NEVER:**
- Use `useState` + `useEffect` for data fetching
- Manually manage loading/error states when React Query can handle it
- Cache data in component state

### 2. Toast Notifications for All Financial Actions

**MUST:**
- Show success toast for all successful financial actions
- Show error toast for all failed financial actions
- Include clear, actionable error messages
- Use consistent toast styling

**Actions that require toasts:**
- Payment creation (Cash, POS, Transfer, Paystack, Wallet)
- Charge creation
- Insurance claim submission/approval/rejection
- Wallet top-up/debit
- Receipt/invoice generation
- Any billing mutation

**Example:**
```tsx
import { useToast } from '../../hooks/useToast';

const { showSuccess, showError } = useToast();

// On success
showSuccess('Payment processed successfully');

// On error
showError(error.message || 'Failed to process payment');
```

### 3. Loading Skeletons for Billing Data

**MUST:**
- Show loading skeletons while data is being fetched
- Use consistent skeleton components from `BillingSkeleton.tsx`
- Never show blank screens during loading
- Match skeleton structure to actual content

**Components:**
- `BillingSummarySkeleton` - For billing summary cards
- `ChargesTableSkeleton` - For charges tables
- `PaymentHistorySkeleton` - For payment history lists
- `BillingDashboardSkeleton` - For full dashboard
- `PaymentFormSkeleton` - For payment forms

**Example:**
```tsx
import { BillingSummarySkeleton } from './BillingSkeleton';

if (isLoading) {
  return <BillingSummarySkeleton />;
}
```

### 4. Error Boundaries for Payment Failures

**MUST:**
- Wrap all billing components in `BillingErrorBoundary`
- Catch and handle payment-related errors gracefully
- Show user-friendly error messages
- Provide "Try Again" functionality

**Example:**
```tsx
import BillingErrorBoundary from './BillingErrorBoundary';

<BillingErrorBoundary>
  <BillingDashboard {...props} />
</BillingErrorBoundary>
```

### 5. Consistent Currency Formatting

**MUST:**
- Always use `formatCurrency()` utility for displaying amounts
- Never hardcode currency symbols
- Use consistent formatting across all components

**Utility:**
```tsx
import { formatCurrency } from '../../utils/currency';

// Usage
<span>{formatCurrency(amount)}</span>
// Output: ₦1,234.56
```

**NEVER:**
- Manually format currency strings
- Use different currency symbols
- Display raw numbers without formatting

### 6. Never Calculate Totals on Frontend

**MUST:**
- Always fetch totals from backend API
- Use `BillingSummary` from backend for all totals
- Trust backend calculations exclusively

**Backend provides:**
- `total_charges`
- `total_payments`
- `total_wallet_debits`
- `insurance_amount`
- `patient_payable`
- `outstanding_balance`

**NEVER:**
```tsx
// ❌ WRONG - Calculating on frontend
const total = charges.reduce((sum, c) => sum + parseFloat(c.amount), 0);

// ✅ CORRECT - Using backend total
const total = billingSummary.total_charges;
```

### 7. Never Allow Edit/Delete of Financial Records

**MUST:**
- Financial records are immutable (append-only)
- Never show edit/delete buttons for:
  - Payments
  - Charges
  - Bill Items
  - Wallet Transactions
  - Receipts/Invoices

**UI Rules:**
- All financial records are read-only
- Only allow creation of new records
- Show audit trail (created_by, created_at) for transparency
- Disable edit/delete actions in UI

**Example:**
```tsx
// ❌ WRONG - Edit/Delete buttons
<button onClick={handleEdit}>Edit</button>
<button onClick={handleDelete}>Delete</button>

// ✅ CORRECT - Read-only display
<div className="read-only">
  <p>Amount: {formatCurrency(payment.amount)}</p>
  <p>Created: {new Date(payment.created_at).toLocaleString()}</p>
</div>
```

## Implementation Checklist

- [ ] All billing components use React Query
- [ ] All financial actions show toast notifications
- [ ] All loading states use skeletons
- [ ] All billing components wrapped in error boundary
- [ ] All amounts use `formatCurrency()`
- [ ] No frontend calculations of totals
- [ ] No edit/delete buttons on financial records
- [ ] All mutations invalidate queries
- [ ] Error handling is consistent
- [ ] Loading states are consistent

## Component Updates Required

1. **BillingDashboard.tsx**
   - Convert to React Query
   - Add error boundary
   - Add loading skeletons

2. **BillingSummary.tsx**
   - Use backend totals only
   - Add loading skeleton

3. **ChargesBreakdown.tsx**
   - Use React Query for charges
   - Remove any edit/delete buttons
   - Add loading skeleton

4. **PaymentOptions.tsx**
   - Use React Query mutations
   - Add toast notifications
   - Add error boundary

5. **All other billing components**
   - Apply same rules consistently

