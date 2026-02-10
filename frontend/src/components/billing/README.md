# Billing UI Module - Implementation Guide

## Overview

Complete UI component structure and implementation guide for the Billing module in the Nigerian EMR system. All billing UI is visit-context locked and permission-aware.

## Documentation Structure

1. **BILLING_UI_DESIGN.md** - Complete component structure, types, and architecture
2. **COMPONENT_PROMPTS.md** - Detailed prompts for each component implementation
3. **UX_GUIDELINES.md** - UX best practices for Nigerian clinics

## Quick Start

### 1. Create Types
```typescript
// types/billing.ts
// See BILLING_UI_DESIGN.md for complete type definitions
```

### 2. Create API Functions
```typescript
// api/billing.ts
// See COMPONENT_PROMPTS.md for API function specifications
```

### 3. Create Hooks
```typescript
// hooks/useBillingPermissions.ts
// hooks/useBillingState.ts
// See BILLING_UI_DESIGN.md for hook implementations
```

### 4. Create Components (in order)
1. BillingGuard.tsx
2. BillingSummary.tsx
3. OutstandingBalance.tsx
4. ChargesBreakdown.tsx
5. InsuranceDetails.tsx
6. WalletBalanceCard.tsx
7. PaymentOptions.tsx
8. PaymentForm.tsx
9. ClearanceConfirmation.tsx
10. BillingDashboard.tsx

### 5. Integration
```typescript
// In VisitDetailsPage.tsx
{user?.role === 'RECEPTIONIST' || user?.role === 'ADMIN' ? (
  <BillingDashboard visitId={visitId} visit={visit} />
) : null}
```

## Key Features

✅ **Visit-Context Locked**: All billing UI within visit context  
✅ **Permission-Aware**: Only Receptionist/Admin can view/edit  
✅ **Nigerian Payment Methods**: Cash, POS, Transfer, Paystack  
✅ **Real-Time Updates**: Billing summary updates automatically  
✅ **Receipt Generation**: Print receipts for all payments  
✅ **Mobile-First**: Optimized for tablets and phones  
✅ **Offline Support**: Queue payments when offline  

## Component Hierarchy

```
BillingDashboard (Main Container)
├── BillingGuard (Permission Check)
├── BillingSummary (Summary Card)
├── OutstandingBalance (Balance Indicator)
├── Tabs
│   ├── ChargesBreakdown
│   ├── InsuranceDetails
│   ├── PaymentOptions
│   │   └── PaymentForm
│   └── WalletBalanceCard
└── ClearanceConfirmation (Modal)
```

## Permission Rules

| Role | View Billing | Edit Billing | Process Payments |
|------|-------------|--------------|------------------|
| Receptionist | ✅ | ✅ | ✅ |
| Admin | ✅ | ✅ | ✅ |
| Doctor | ❌ | ❌ | ❌ |
| Nurse | ❌ | ❌ | ❌ |
| Other | ❌ | ❌ | ❌ |

## Payment Methods

1. **Cash** - Direct cash payment
2. **POS** - Point of Sale card payment
3. **Transfer** - Bank transfer with reference
4. **Paystack** - Online payment gateway

## State Flow

```
Initial Load
  ↓
Fetch Billing Summary
  ↓
Render Components
  ↓
User Action (Payment/Charge)
  ↓
API Call
  ↓
Update Summary
  ↓
Re-render Components
```

## API Endpoints

All endpoints are visit-scoped:
- `GET /api/v1/visits/{visit_id}/billing/summary/`
- `POST /api/v1/visits/{visit_id}/billing/charges/`
- `POST /api/v1/visits/{visit_id}/billing/payments/`
- `POST /api/v1/visits/{visit_id}/billing/wallet-debit/`
- `POST /api/v1/visits/{visit_id}/billing/insurance/`

## Testing Checklist

- [ ] Permission checks work
- [ ] Visit context maintained
- [ ] Payment methods functional
- [ ] Currency formatting correct
- [ ] Receipt generation works
- [ ] Offline mode handles gracefully
- [ ] Error states display
- [ ] Loading states show
- [ ] Real-time updates work
- [ ] Mobile responsive

## Rejected Patterns

❌ Billing UI in main navigation  
❌ Standalone billing page  
❌ Clinical role editing  
❌ Payment bypass  
❌ Non-visit billing  

## Next Steps

1. Review documentation
2. Create types and API functions
3. Implement components in order
4. Test with Nigerian clinic scenarios
5. Deploy and gather feedback

## Support

For questions or issues:
1. Check BILLING_UI_DESIGN.md for architecture
2. Check COMPONENT_PROMPTS.md for implementation details
3. Check UX_GUIDELINES.md for design patterns

