# Billing UI Component Design - Nigerian EMR

## Overview

Billing UI components for visit-scoped billing operations. All billing UI is locked to visit context and only visible to Receptionist and Admin roles.

## Core Principles

1. **Visit-Context Locked**: All billing UI must be within a visit context
2. **Role-Based Access**: Only Receptionist and Admin can see billing UI
3. **No Clinical Editing**: Clinical roles cannot edit billing data
4. **Nigerian Payment Methods**: Support Cash, POS, Transfer, Paystack
5. **Real-Time Updates**: Billing summary updates in real-time

## Component Structure

```
billing/
├── BillingDashboard.tsx          # Main billing container (visit-scoped)
├── ChargesBreakdown.tsx          # Charges list and breakdown
├── InsuranceDetails.tsx          # Insurance information and management
├── WalletBalanceCard.tsx        # Wallet balance and usage
├── PaymentOptions.tsx            # Payment method selection
├── PaymentForm.tsx               # Payment input form
├── OutstandingBalance.tsx        # Balance indicator and alerts
├── ClearanceConfirmation.tsx    # Final clearance confirmation
├── BillingSummary.tsx           # Complete billing summary card
└── types.ts                     # TypeScript types
```

## Permission-Aware Rendering

### Role Check Hook

```typescript
// hooks/useBillingPermissions.ts
export function useBillingPermissions() {
  const { user } = useAuth();
  
  const canViewBilling = user?.role === 'RECEPTIONIST' || user?.role === 'ADMIN';
  const canEditBilling = user?.role === 'RECEPTIONIST';
  const canProcessPayments = user?.role === 'RECEPTIONIST';
  
  return {
    canViewBilling,
    canEditBilling,
    canProcessPayments
  };
}
```

### Component Guard

```typescript
// components/billing/BillingGuard.tsx
export function BillingGuard({ children }: { children: React.ReactNode }) {
  const { canViewBilling } = useBillingPermissions();
  
  if (!canViewBilling) {
    return (
      <div className="billing-restricted">
        <p>Billing information is only available to Receptionist and Admin.</p>
      </div>
    );
  }
  
  return <>{children}</>;
}
```

## Component Specifications

### 1. BillingDashboard.tsx

**Purpose**: Main container for all billing components within visit context

**Props**:
```typescript
interface BillingDashboardProps {
  visitId: string;
  visit: Visit;
  onUpdate?: () => void;
}
```

**Features**:
- Visit context header (patient name, visit ID, date)
- Tabbed interface for different billing sections
- Real-time billing summary at top
- Permission checks
- Loading states
- Error handling

**State Flow**:
```
Initial Load → Fetch Billing Summary → Render Components
  ↓
User Action (Payment/Charge) → API Call → Update Summary → Re-render
```

### 2. ChargesBreakdown.tsx

**Purpose**: Display all charges for the visit

**Props**:
```typescript
interface ChargesBreakdownProps {
  visitId: string;
  charges: VisitCharge[];
  canEdit: boolean;
}
```

**Features**:
- List of all charges by category
- Category grouping (Consultation, Lab, Radiology, Drug, Procedure, MISC)
- Total charges calculation
- Add MISC charge button (Receptionist only)
- Read-only for non-Receptionist roles
- Nigerian currency formatting (₦)

**Display Format**:
```
Charges Breakdown
├── Consultation
│   └── Consultation Fee: ₦5,000.00
├── Lab Orders
│   ├── CBC Test: ₦3,000.00
│   └── Blood Sugar: ₦2,000.00
├── Radiology
│   └── X-Ray Chest: ₦4,000.00
├── Prescriptions
│   └── Medication: ₦2,500.00
└── Total Charges: ₦16,500.00
```

### 3. InsuranceDetails.tsx

**Purpose**: Display and manage insurance information

**Props**:
```typescript
interface InsuranceDetailsProps {
  visitId: string;
  insurance: VisitInsurance | null;
  canEdit: boolean;
}
```

**Features**:
- Insurance provider information
- Policy number display
- Coverage type (FULL/PARTIAL)
- Coverage percentage
- Approval status (PENDING/APPROVED/REJECTED)
- Insurance amount covered
- Patient payable after insurance
- Add/Edit insurance button (Receptionist only)
- Status badges with colors

**Nigerian Context**:
- HMO provider selection
- Policy number validation
- Coverage percentage display
- Approval workflow

### 4. WalletBalanceCard.tsx

**Purpose**: Display wallet balance and enable wallet payments

**Props**:
```typescript
interface WalletBalanceCardProps {
  visitId: string;
  patientId: number;
  walletBalance: number;
  canProcessPayments: boolean;
}
```

**Features**:
- Current wallet balance display
- Wallet balance indicator (sufficient/insufficient)
- Pay from wallet button
- Wallet transaction history (visit-scoped)
- Balance after payment preview
- Insufficient balance warning

**Nigerian Context**:
- Wallet top-up integration
- Balance display in ₦
- Transaction reference display

### 5. PaymentOptions.tsx

**Purpose**: Payment method selection and forms

**Props**:
```typescript
interface PaymentOptionsProps {
  visitId: string;
  outstandingBalance: number;
  canProcessPayments: boolean;
  onPaymentSuccess: () => void;
}
```

**Payment Methods**:
1. **Cash** - Direct cash payment
2. **POS** - Point of Sale card payment
3. **Transfer** - Bank transfer
4. **Paystack** - Online payment gateway

**Features**:
- Payment method selection tabs
- Method-specific forms
- Amount input with validation
- Transaction reference input (for Transfer/POS)
- Paystack integration (redirect to Paystack)
- Payment confirmation
- Receipt generation

**Nigerian Payment Flow**:
```
Select Method → Enter Amount → Enter Details → Confirm → Process → Receipt
```

### 6. PaymentForm.tsx

**Purpose**: Unified payment form component

**Props**:
```typescript
interface PaymentFormProps {
  visitId: string;
  paymentMethod: 'CASH' | 'CARD' | 'BANK_TRANSFER' | 'PAYSTACK';
  defaultAmount?: number;
  onSuccess: () => void;
  onCancel: () => void;
}
```

**Form Fields by Method**:
- **Cash**: Amount, Notes
- **POS**: Amount, Transaction Reference, Notes
- **Transfer**: Amount, Transaction Reference, Bank Name, Notes
- **Paystack**: Amount, Email (optional), Redirect to Paystack

**Validation**:
- Amount must be > 0
- Amount cannot exceed outstanding balance (unless overpayment allowed)
- Transaction reference required for POS/Transfer
- Email validation for Paystack

### 7. OutstandingBalance.tsx

**Purpose**: Display outstanding balance with visual indicators

**Props**:
```typescript
interface OutstandingBalanceProps {
  outstandingBalance: number;
  patientPayable: number;
  totalPaid: number;
  paymentStatus: 'PENDING' | 'PARTIAL' | 'CLEARED';
}
```

**Features**:
- Large balance display
- Status indicator (Pending/Partial/Cleared)
- Progress bar (paid vs payable)
- Color coding:
  - Red: Outstanding balance > 0
  - Yellow: Partial payment
  - Green: Fully paid
- Payment breakdown
- Clearance status

**Visual Design**:
```
Outstanding Balance: ₦5,000.00
[████████░░] 50% Paid
Status: PARTIAL
```

### 8. ClearanceConfirmation.tsx

**Purpose**: Final confirmation before marking payment as cleared

**Props**:
```typescript
interface ClearanceConfirmationProps {
  visitId: string;
  billingSummary: BillingSummary;
  onConfirm: () => void;
  onCancel: () => void;
}
```

**Features**:
- Payment summary review
- Outstanding balance confirmation
- Insurance coverage confirmation
- Final clearance button
- Confirmation dialog
- Receipt generation option

**Nigerian Context**:
- Print receipt option
- Receipt number generation
- Payment method display
- Transaction reference display

### 9. BillingSummary.tsx

**Purpose**: Complete billing summary card

**Props**:
```typescript
interface BillingSummaryProps {
  summary: BillingSummary;
  visitId: string;
  canEdit: boolean;
}
```

**Display Sections**:
1. **Charges Summary**
   - Total charges
   - Charges by category
   
2. **Insurance Summary**
   - Insurance amount
   - Patient payable after insurance
   - Coverage status
   
3. **Payments Summary**
   - Total payments
   - Payment methods breakdown
   - Wallet debits
   
4. **Balance Summary**
   - Patient payable
   - Outstanding balance
   - Payment status

## State Management

### Billing State Hook

```typescript
// hooks/useBillingState.ts
export function useBillingState(visitId: string) {
  const [summary, setSummary] = useState<BillingSummary | null>(null);
  const [charges, setCharges] = useState<VisitCharge[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [insurance, setInsurance] = useState<VisitInsurance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const refreshBilling = async () => {
    // Fetch all billing data
  };
  
  return {
    summary,
    charges,
    payments,
    insurance,
    loading,
    error,
    refreshBilling
  };
}
```

## API Integration

### Billing API Functions

```typescript
// api/billing.ts

// Get billing summary
export async function getBillingSummary(visitId: string): Promise<BillingSummary>

// Get charges
export async function getCharges(visitId: string): Promise<VisitCharge[]>

// Create charge (MISC)
export async function createCharge(visitId: string, data: ChargeCreateData): Promise<VisitCharge>

// Get payments
export async function getPayments(visitId: string): Promise<Payment[]>

// Create payment
export async function createPayment(visitId: string, data: PaymentCreateData): Promise<Payment>

// Create wallet debit
export async function createWalletDebit(visitId: string, data: WalletDebitData): Promise<WalletDebitResponse>

// Get insurance
export async function getInsurance(visitId: string): Promise<VisitInsurance | null>

// Create insurance
export async function createInsurance(visitId: string, data: InsuranceCreateData): Promise<VisitInsurance>
```

## TypeScript Types

```typescript
// types/billing.ts

export interface BillingSummary {
  total_charges: string;
  total_payments: string;
  total_wallet_debits: string;
  has_insurance: boolean;
  insurance_status: 'PENDING' | 'APPROVED' | 'REJECTED' | null;
  insurance_amount: string;
  insurance_coverage_type: 'FULL' | 'PARTIAL' | null;
  patient_payable: string;
  outstanding_balance: string;
  payment_status: 'PENDING' | 'PARTIAL' | 'CLEARED';
  is_fully_covered_by_insurance: boolean;
  can_be_cleared: boolean;
  computation_timestamp: string;
  visit_id: number;
}

export interface VisitCharge {
  id: number;
  visit: number;
  category: 'CONSULTATION' | 'LAB' | 'RADIOLOGY' | 'DRUG' | 'PROCEDURE' | 'MISC';
  description: string;
  amount: string;
  created_at: string;
}

export interface ChargeCreateData {
  amount: string;
  description: string;
}

export interface PaymentCreateData {
  amount: string;
  payment_method: 'CASH' | 'CARD' | 'BANK_TRANSFER' | 'PAYSTACK';
  transaction_reference?: string;
  notes?: string;
  status?: 'PENDING' | 'CLEARED';
}

export interface WalletDebitData {
  wallet_id: number;
  amount: string;
  description?: string;
}

export interface WalletDebitResponse {
  wallet_transaction: WalletTransaction;
  payment: Payment;
  outstanding_balance: string;
  visit_payment_status: string;
}
```

## UX Notes for Nigerian Clinics

### 1. Currency Formatting
- Always display amounts in Nigerian Naira (₦)
- Use comma separators: ₦10,000.00
- Show kobo (decimal places) for precision

### 2. Payment Methods Priority
- **Cash**: Most common, should be default
- **POS**: Common for card payments
- **Transfer**: Bank transfer with reference
- **Paystack**: Online payments (growing in Nigeria)

### 3. Receipt Generation
- Always offer receipt printing
- Receipt should include:
  - Clinic name and address
  - Patient name and visit ID
  - Itemized charges
  - Payment method and reference
  - Date and time
  - Receipt number

### 4. Offline Considerations
- Show offline indicator if no internet
- Queue payments for sync when online
- Store payment data locally

### 5. Error Handling
- Clear error messages in English
- Network error handling
- Validation error display
- Retry mechanisms

### 6. Performance
- Fast loading (Nigerian internet can be slow)
- Optimistic UI updates
- Loading states
- Skeleton screens

### 7. Mobile-First
- Many clinics use tablets/phones
- Touch-friendly buttons
- Large input fields
- Easy navigation

### 8. Language
- English (primary language for medical records)
- Clear, simple language
- Medical terminology where appropriate

## Component Implementation Order

1. **Types and API** (`types.ts`, `api/billing.ts`)
2. **Permission Hook** (`hooks/useBillingPermissions.ts`)
3. **Billing State Hook** (`hooks/useBillingState.ts`)
4. **BillingGuard** (`BillingGuard.tsx`)
5. **BillingSummary** (`BillingSummary.tsx`)
6. **OutstandingBalance** (`OutstandingBalance.tsx`)
7. **ChargesBreakdown** (`ChargesBreakdown.tsx`)
8. **InsuranceDetails** (`InsuranceDetails.tsx`)
9. **WalletBalanceCard** (`WalletBalanceCard.tsx`)
10. **PaymentOptions** (`PaymentOptions.tsx`)
11. **PaymentForm** (`PaymentForm.tsx`)
12. **ClearanceConfirmation** (`ClearanceConfirmation.tsx`)
13. **BillingDashboard** (`BillingDashboard.tsx`)

## Integration Points

### Visit Details Page
```typescript
// In VisitDetailsPage.tsx
{user?.role === 'RECEPTIONIST' || user?.role === 'ADMIN' ? (
  <BillingDashboard visitId={visitId} visit={visit} />
) : null}
```

### Visit List Page
- Show payment status badge
- Filter by payment status
- Quick access to billing for Receptionist

## Security Considerations

1. **Role Checks**: Always check role before rendering
2. **API Calls**: Backend validates permissions
3. **Data Masking**: Non-Receptionist see read-only view
4. **Audit Trail**: All actions logged
5. **Input Validation**: Client and server validation

## Testing Checklist

- [ ] Permission checks work correctly
- [ ] Visit context is maintained
- [ ] Payment methods work
- [ ] Currency formatting correct
- [ ] Receipt generation works
- [ ] Offline mode handles gracefully
- [ ] Error states display properly
- [ ] Loading states show
- [ ] Real-time updates work
- [ ] Mobile responsive

## Rejected Patterns

❌ **Billing UI in Navigation**: No billing links in main navigation  
❌ **Global Billing Page**: No standalone billing page outside visit context  
❌ **Clinical Role Editing**: Doctors/Nurses cannot edit billing  
❌ **Payment Bypass**: No way to bypass payment enforcement  
❌ **Non-Visit Billing**: All billing must be visit-scoped  

