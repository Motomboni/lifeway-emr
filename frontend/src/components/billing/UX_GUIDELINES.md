# Billing UI UX Guidelines - Nigerian Clinics

## Design Principles

### 1. Clarity First
- Clear labels and instructions
- Obvious action buttons
- Minimal cognitive load
- Straightforward workflows

### 2. Speed Matters
- Fast loading (optimize for slow internet)
- Quick actions (one-click where possible)
- Minimal steps to complete payment
- Instant feedback

### 3. Trust Building
- Clear payment confirmations
- Receipt generation
- Transaction references
- Audit trail visibility

### 4. Error Prevention
- Input validation
- Confirmation dialogs
- Clear error messages
- Recovery paths

## Nigerian-Specific Considerations

### Currency Display
- Always show ₦ (Naira symbol)
- Use comma separators: ₦10,000.00
- Show kobo (2 decimal places)
- Large, readable numbers

**Example**:
```
Outstanding Balance
₦15,500.00
```

### Payment Method Priority
1. **Cash** (Most common) - Default option
2. **POS** (Common) - Card payments
3. **Transfer** (Common) - Bank transfers
4. **Paystack** (Growing) - Online payments

### Receipt Requirements
Nigerian clinics need detailed receipts:
- Clinic name and address
- Patient name and ID
- Visit ID
- Itemized charges
- Payment method
- Transaction reference
- Date and time
- Receipt number
- Staff name (Receptionist)

### Language
- English (primary)
- Clear, simple language
- Medical terms where needed
- Avoid jargon

### Mobile Considerations
- Many clinics use tablets
- Touch-friendly buttons (min 44px)
- Large input fields
- Easy navigation
- Swipe gestures where appropriate

## Component-Specific UX

### BillingDashboard
- **Header**: Patient name, Visit ID, Date (always visible)
- **Tabs**: Clear labels, active state obvious
- **Summary Card**: Prominent at top
- **Loading**: Skeleton screens, not spinners
- **Errors**: Inline, not modals

### ChargesBreakdown
- **Grouping**: Collapsible categories
- **Totals**: Always visible
- **Add Button**: Prominent, clear label
- **Empty State**: Helpful message
- **Icons**: Category icons for quick recognition

### PaymentOptions
- **Method Selection**: Large, clear buttons
- **Forms**: Single column, clear labels
- **Validation**: Real-time, inline
- **Confirmation**: Clear summary before submit
- **Success**: Clear success message with receipt option

### OutstandingBalance
- **Visual Hierarchy**: Balance is largest element
- **Status Badge**: Color-coded, clear
- **Progress Bar**: Visual payment progress
- **Breakdown**: Expandable details

### ClearanceConfirmation
- **Summary**: Complete payment summary
- **Confirmation**: Checkbox required
- **Actions**: Clear "Confirm" and "Cancel" buttons
- **Receipt**: Prominent "Print Receipt" button

## Color Scheme

### Status Colors
- **Pending**: Red (#DC2626)
- **Partial**: Yellow/Orange (#F59E0B)
- **Cleared**: Green (#10B981)

### Payment Method Colors
- **Cash**: Green (#10B981)
- **POS**: Blue (#3B82F6)
- **Transfer**: Purple (#8B5CF6)
- **Paystack**: Orange (#F97316)

### Balance Colors
- **Outstanding**: Red (#DC2626)
- **Zero/Paid**: Green (#10B981)
- **Credit**: Blue (#3B82F6)

## Typography

### Headings
- **H1**: 24px, Bold (Main titles)
- **H2**: 20px, Semi-bold (Section titles)
- **H3**: 18px, Medium (Subsection titles)

### Body Text
- **Regular**: 16px (Default)
- **Small**: 14px (Helper text)
- **Large**: 18px (Important numbers)

### Numbers
- **Balance**: 32px, Bold
- **Amounts**: 20px, Semi-bold
- **Totals**: 18px, Medium

## Spacing

### Component Spacing
- **Section Gap**: 24px
- **Card Padding**: 16px
- **Element Gap**: 12px
- **Input Gap**: 8px

### Button Spacing
- **Primary Actions**: 16px padding
- **Secondary Actions**: 12px padding
- **Icon Buttons**: 12px padding

## Interaction Patterns

### Loading States
- Use skeleton screens, not spinners
- Show partial content while loading
- Optimistic updates where possible

### Error States
- Inline error messages
- Clear error descriptions
- Recovery actions visible
- No error modals (unless critical)

### Success States
- Clear success messages
- Receipt option immediately visible
- Next action suggested
- Auto-refresh data

### Empty States
- Helpful messages
- Action suggestions
- No dead ends

## Accessibility

### Keyboard Navigation
- All actions keyboard accessible
- Tab order logical
- Focus indicators visible
- Escape closes modals

### Screen Readers
- Proper ARIA labels
- Form labels associated
- Status announcements
- Error announcements

### Visual
- High contrast (WCAG AA)
- Color not sole indicator
- Text alternatives for icons
- Resizable text

## Performance

### Loading
- Lazy load components
- Code splitting
- Image optimization
- API request batching

### Caching
- Cache billing summary
- Cache charges/payments
- Invalidate on updates
- Offline support

### Network
- Retry failed requests
- Queue offline actions
- Show connection status
- Graceful degradation

## Testing Scenarios

### Happy Path
1. View billing summary
2. Add MISC charge
3. Process cash payment
4. View updated summary
5. Generate receipt

### Error Scenarios
1. Network error
2. Invalid amount
3. Insufficient wallet balance
4. Payment failure
5. Validation errors

### Edge Cases
1. Zero charges
2. Full insurance coverage
3. Overpayment
4. Multiple payment methods
5. Closed visit

## User Flows

### Payment Flow (Cash)
```
1. View Outstanding Balance
2. Click "Pay Now"
3. Select "Cash"
4. Enter Amount
5. Add Notes (optional)
6. Click "Process Payment"
7. View Confirmation
8. Print Receipt
```

### Payment Flow (Paystack)
```
1. View Outstanding Balance
2. Click "Pay Now"
3. Select "Paystack"
4. Enter Amount
5. Enter Email (optional)
6. Click "Pay with Paystack"
7. Redirect to Paystack
8. Complete Payment
9. Return to Visit
10. View Updated Summary
11. Print Receipt
```

### Insurance Flow
```
1. View Insurance Section
2. Click "Add Insurance"
3. Select HMO Provider
4. Enter Policy Number
5. Select Coverage Type
6. Enter Coverage Percentage
7. Save Insurance
8. View Updated Summary
```

## Common Patterns

### Confirmation Dialogs
- Always show what will happen
- Clear action buttons
- Cancel option always available
- No destructive actions without confirmation

### Form Validation
- Real-time validation
- Clear error messages
- Inline errors
- Prevent invalid submission

### Data Refresh
- Auto-refresh after actions
- Manual refresh option
- Loading indicators
- Optimistic updates

### Receipt Generation
- Always available after payment
- Print-friendly format
- Download option
- Email option (future)

## Rejected Patterns

❌ **Modal Overload**: Don't use modals for everything  
❌ **Hidden Actions**: All actions should be visible  
❌ **Complex Workflows**: Keep it simple  
❌ **Technical Jargon**: Use plain language  
❌ **Slow Loading**: Optimize for performance  
❌ **Poor Mobile UX**: Mobile-first design  

