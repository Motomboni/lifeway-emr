# Billing Component Implementation Prompts

## Component 1: BillingDashboard

**Prompt**:
```
Create a BillingDashboard component for a Nigerian EMR system.

Requirements:
- Visit-scoped billing container
- Only visible to Receptionist and Admin roles
- Tabbed interface with sections: Summary, Charges, Insurance, Payments, Wallet
- Real-time billing summary at top
- Loading and error states
- Nigerian currency formatting (₦)
- Mobile-responsive design
- Visit context header (patient name, visit ID, date)

Props:
- visitId: string
- visit: Visit object
- onUpdate?: callback function

State:
- billingSummary: BillingSummary | null
- activeTab: 'summary' | 'charges' | 'insurance' | 'payments' | 'wallet'
- loading: boolean
- error: string | null

Use:
- useBillingPermissions hook for role checks
- useBillingState hook for data management
- BillingGuard for permission enforcement
- Nigerian currency formatter utility
```

## Component 2: ChargesBreakdown

**Prompt**:
```
Create a ChargesBreakdown component for displaying visit charges.

Requirements:
- List all charges grouped by category
- Categories: Consultation, Lab, Radiology, Drug, Procedure, MISC
- Show total charges at bottom
- Add MISC charge button (Receptionist only)
- Read-only for non-Receptionist
- Nigerian currency formatting
- Category icons/colors
- Expandable category sections

Props:
- visitId: string
- charges: VisitCharge[]
- canEdit: boolean

Features:
- Group charges by category
- Show category totals
- Show grand total
- Add charge modal (Receptionist only)
- Delete charge (if allowed)
- Edit charge description (if allowed)
```

## Component 3: InsuranceDetails

**Prompt**:
```
Create an InsuranceDetails component for managing visit insurance.

Requirements:
- Display insurance information if exists
- Show provider name, policy number, coverage type
- Display approval status with color badges
- Show insurance amount and patient payable
- Add/Edit insurance button (Receptionist only)
- HMO provider selection
- Coverage percentage display
- Approval workflow display

Props:
- visitId: string
- insurance: VisitInsurance | null
- canEdit: boolean

Features:
- Insurance card display
- Status badges (PENDING/APPROVED/REJECTED)
- Coverage calculation display
- Add insurance form
- Edit insurance form
- Provider search/selection
```

## Component 4: WalletBalanceCard

**Prompt**:
```
Create a WalletBalanceCard component for wallet payments.

Requirements:
- Display current wallet balance
- Show if balance is sufficient for payment
- Pay from wallet button
- Balance after payment preview
- Insufficient balance warning
- Wallet transaction history (visit-scoped)
- Top-up wallet link

Props:
- visitId: string
- patientId: number
- walletBalance: number
- canProcessPayments: boolean

Features:
- Balance display with color coding
- Pay from wallet form
- Transaction history list
- Balance indicator (sufficient/insufficient)
- Top-up integration
```

## Component 5: PaymentOptions

**Prompt**:
```
Create a PaymentOptions component for payment method selection.

Requirements:
- Payment method tabs: Cash, POS, Transfer, Paystack
- Method-specific forms
- Amount input with validation
- Transaction reference input (for POS/Transfer)
- Paystack integration (redirect)
- Payment confirmation
- Receipt generation option

Props:
- visitId: string
- outstandingBalance: number
- canProcessPayments: boolean
- onPaymentSuccess: callback

Payment Methods:
1. Cash: Amount, Notes
2. POS: Amount, Transaction Reference, Notes
3. Transfer: Amount, Transaction Reference, Bank Name, Notes
4. Paystack: Amount, Email (optional), Redirect to Paystack

Features:
- Method selection tabs
- Form validation
- Amount validation (cannot exceed outstanding balance)
- Transaction reference validation
- Paystack redirect handling
- Payment confirmation dialog
- Receipt generation
```

## Component 6: OutstandingBalance

**Prompt**:
```
Create an OutstandingBalance component for displaying balance status.

Requirements:
- Large balance display
- Status indicator (Pending/Partial/Cleared)
- Progress bar (paid vs payable)
- Color coding (Red/Yellow/Green)
- Payment breakdown
- Clearance status

Props:
- outstandingBalance: number
- patientPayable: number
- totalPaid: number
- paymentStatus: 'PENDING' | 'PARTIAL' | 'CLEARED'

Visual Design:
- Large number display (₦X,XXX.XX)
- Status badge with color
- Progress bar showing payment percentage
- Breakdown: Total Charges, Insurance, Payments, Outstanding
- Clearance indicator

Color Coding:
- Red: Outstanding > 0 (Pending/Partial)
- Yellow: Partial payment
- Green: Fully paid (Cleared)
```

## Component 7: ClearanceConfirmation

**Prompt**:
```
Create a ClearanceConfirmation component for final payment clearance.

Requirements:
- Payment summary review
- Outstanding balance confirmation
- Insurance coverage confirmation
- Final clearance button
- Confirmation dialog
- Receipt generation option
- Print receipt option

Props:
- visitId: string
- billingSummary: BillingSummary
- onConfirm: callback
- onCancel: callback

Features:
- Summary display (charges, payments, balance)
- Confirmation checkbox
- Clearance button
- Receipt generation
- Print receipt
- Receipt number display
- Transaction references display
```

## Component 8: BillingSummary

**Prompt**:
```
Create a BillingSummary component for complete billing overview.

Requirements:
- Display complete billing summary
- Sections: Charges, Insurance, Payments, Balance
- Real-time updates
- Expandable sections
- Print option
- Export option

Props:
- summary: BillingSummary
- visitId: string
- canEdit: boolean

Sections:
1. Charges Summary: Total charges, by category
2. Insurance Summary: Insurance amount, patient payable
3. Payments Summary: Total payments, by method, wallet debits
4. Balance Summary: Patient payable, outstanding, status

Features:
- Card-based layout
- Section expansion
- Print summary
- Export to PDF
- Real-time refresh
```

## Component 9: PaymentForm

**Prompt**:
```
Create a PaymentForm component for unified payment input.

Requirements:
- Support all payment methods
- Method-specific fields
- Amount validation
- Transaction reference validation
- Form submission
- Loading states
- Error handling

Props:
- visitId: string
- paymentMethod: 'CASH' | 'CARD' | 'BANK_TRANSFER' | 'PAYSTACK'
- defaultAmount?: number
- onSuccess: callback
- onCancel: callback

Form Fields:
- Cash: Amount (required), Notes (optional)
- POS: Amount (required), Transaction Reference (required), Notes (optional)
- Transfer: Amount (required), Transaction Reference (required), Bank Name (optional), Notes (optional)
- Paystack: Amount (required), Email (optional), Redirect to Paystack

Validation:
- Amount > 0
- Amount <= outstanding balance (unless overpayment allowed)
- Transaction reference required for POS/Transfer
- Email validation for Paystack
```

## Hooks

### useBillingPermissions

**Prompt**:
```
Create a useBillingPermissions hook for role-based access control.

Requirements:
- Check user role (Receptionist/Admin)
- Return permission flags
- Handle role changes

Returns:
- canViewBilling: boolean
- canEditBilling: boolean
- canProcessPayments: boolean

Implementation:
- Use useAuth hook
- Check user.role
- Return permission flags
```

### useBillingState

**Prompt**:
```
Create a useBillingState hook for billing data management.

Requirements:
- Fetch billing summary
- Fetch charges
- Fetch payments
- Fetch insurance
- Refresh function
- Loading states
- Error handling

Returns:
- summary: BillingSummary | null
- charges: VisitCharge[]
- payments: Payment[]
- insurance: VisitInsurance | null
- loading: boolean
- error: string | null
- refreshBilling: function

Implementation:
- Use useState for state
- Use useEffect for initial load
- Use API functions for data fetching
- Handle errors gracefully
```

## API Functions

**Prompt**:
```
Create billing API functions for all billing operations.

Required Functions:
1. getBillingSummary(visitId: string): Promise<BillingSummary>
2. getCharges(visitId: string): Promise<VisitCharge[]>
3. createCharge(visitId: string, data: ChargeCreateData): Promise<VisitCharge>
4. getPayments(visitId: string): Promise<Payment[]>
5. createPayment(visitId: string, data: PaymentCreateData): Promise<Payment>
6. createWalletDebit(visitId: string, data: WalletDebitData): Promise<WalletDebitResponse>
7. getInsurance(visitId: string): Promise<VisitInsurance | null>
8. createInsurance(visitId: string, data: InsuranceCreateData): Promise<VisitInsurance>

All functions:
- Use apiRequest utility
- Handle errors
- Return typed responses
- Visit-scoped endpoints
```

## Types

**Prompt**:
```
Create TypeScript types for billing module.

Required Types:
- BillingSummary
- VisitCharge
- ChargeCreateData
- PaymentCreateData
- WalletDebitData
- WalletDebitResponse
- VisitInsurance
- InsuranceCreateData

All types should:
- Match backend API responses
- Include all required fields
- Use proper TypeScript types
- Include optional fields where appropriate
```

