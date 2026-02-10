# Patient Portal UI - Quick Reference

## What Was Added

✅ **New Section in Patient Registration Form**

Location: After Contact Information, before Emergency Contact

## Visual Preview

### Default State (Unchecked)
```
╔════════════════════════════════════════════════════════════╗
║  Patient Portal Account                                    ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │ □ Create Patient Portal Login                       │  ║
║  │   Allows patient to log in to view appointments,    │  ║
║  │   records and bills.                                 │  ║
║  └─────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════╝
```

### Expanded State (Checked)
```
╔════════════════════════════════════════════════════════════╗
║  Patient Portal Account                                    ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │ ☑ Create Patient Portal Login                       │  ║
║  │   Allows patient to log in to view appointments,    │  ║
║  │   records and bills.                                 │  ║
║  │                                                       │  ║
║  │ ┃ Email *                  Phone Number             │  ║
║  │ ┃ ┌─────────────────────┐  ┌─────────────────────┐ │  ║
║  │ ┃ │patient@example.com  │  │0712345678           │ │  ║
║  │ ┃ └─────────────────────┘  └─────────────────────┘ │  ║
║  │ ┃ Used for login            Optional: For SMS      │  ║
║  │ ┃                                                    │  ║
║  │ ┃ ┌────────────────────────────────────────────┐   │  ║
║  │ ┃ │ ℹ Portal Access Information                │   │  ║
║  │ ┃ │ A temporary password will be generated     │   │  ║
║  │ ┃ │ and sent to the patient's email.           │   │  ║
║  │ ┃ └────────────────────────────────────────────┘   │  ║
║  └─────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════╝
```

### Error State
```
╔════════════════════════════════════════════════════════════╗
║  Email *                                                   ║
║  ┌─────────────────────────────────────────────────────┐  ║
║  │ patient@example                                      │  ║ ← Red border
║  └─────────────────────────────────────────────────────┘  ║
║  ⚠ Invalid email format                                   ║ ← Red text
║  Used for login and notifications                         ║
╚════════════════════════════════════════════════════════════╝
```

## Key Features

### 1. Checkbox
- **Default:** Unchecked
- **Action:** Toggles portal fields visibility
- **Clears errors:** When unchecked, removes portal field errors

### 2. Email Field (Conditional)
- **Required:** Yes (when portal enabled)
- **Validation:** Email format (regex)
- **Placeholder:** "patient@example.com"
- **Helper:** "Used for login and notifications"

### 3. Phone Field (Conditional)
- **Required:** No
- **Validation:** None
- **Placeholder:** "0712345678"
- **Helper:** "Optional: For SMS notifications"

### 4. Info Box
- **Icon:** Information symbol
- **Title:** "Portal Access Information"
- **Message:** Password generation and first login info

## Color Scheme

```css
/* Container */
Background: #EFF6FF (blue-50)
Border: #BFDBFE (blue-200)

/* Checkbox */
Checked: #2563EB (blue-600)
Focus Ring: #3B82F6 (blue-500)

/* Input Normal */
Background: #FFFFFF (white)
Border: #D1D5DB (gray-300)
Focus Ring: #3B82F6 (blue-500)

/* Input Error */
Background: #FEF2F2 (red-50)
Border: #EF4444 (red-500)
Error Text: #DC2626 (red-600)

/* Info Box */
Background: #DBEAFE (blue-100)
Border: #93C5FD (blue-300)
Text: #1E3A8A (blue-800)

/* Accent Border */
Left Border: #93C5FD (blue-300)
Width: 4px
```

## Validation Rules

```typescript
// Email required when portal enabled
if (createPortalAccount && !portalData.email) {
  return "Email is required for portal access";
}

// Email format validation
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
if (createPortalAccount && !emailRegex.test(portalData.email)) {
  return "Invalid email format";
}

// Phone is optional (no validation)
```

## Data Structure

```typescript
// State
const [createPortalAccount, setCreatePortalAccount] = useState(false);
const [portalData, setPortalData] = useState({
  email: '',
  phone: '',
});

// Submitted to API
{
  // ... existing patient fields ...
  create_portal_account: true,
  portal_enabled: true,
  portal_email: "patient@example.com",
  portal_phone: "0712345678"  // optional
}
```

## Tailwind Classes Quick Reference

### Container
```jsx
className="bg-blue-50 border-2 border-blue-200 rounded-lg p-6 mb-6"
```

### Checkbox
```jsx
className="w-5 h-5 text-blue-600 bg-white border-gray-300 rounded 
           focus:ring-2 focus:ring-blue-500 cursor-pointer"
```

### Label
```jsx
className="text-base font-semibold text-gray-900 cursor-pointer"
```

### Helper Text
```jsx
className="text-sm text-gray-600 mt-1"
```

### Input Normal
```jsx
className="w-full px-4 py-2.5 border rounded-lg 
           focus:ring-2 focus:ring-blue-500 focus:border-blue-500 
           transition-colors border-gray-300 bg-white"
```

### Input Error
```jsx
className="w-full px-4 py-2.5 border rounded-lg 
           focus:ring-2 focus:ring-blue-500 focus:border-blue-500 
           transition-colors border-red-500 bg-red-50"
```

### Error Message
```jsx
className="mt-1.5 text-sm text-red-600 flex items-center"
```

### Grid Layout
```jsx
className="grid grid-cols-1 md:grid-cols-2 gap-4"
```

### Left Border Accent
```jsx
className="pl-8 border-l-4 border-blue-300"
```

### Info Box
```jsx
className="bg-blue-100 border border-blue-300 rounded-lg p-4"
```

## Testing Scenarios

### ✅ Pass Cases
1. Checkbox unchecked → Submit form (no portal)
2. Checkbox checked + valid email → Submit form (portal created)
3. Checkbox checked + email + phone → All data included
4. Type valid email → Error clears
5. Uncheck checkbox → Fields hide, errors clear

### ❌ Fail Cases
1. Checkbox checked + no email → Show error
2. Checkbox checked + invalid email → Show error
3. Submit while errors present → Block submission

## Browser Support

✅ Chrome 90+
✅ Firefox 88+
✅ Safari 14+
✅ Edge 90+
✅ Mobile browsers

## Accessibility

✅ Keyboard navigation (Tab, Enter, Space)
✅ Screen reader support (ARIA labels)
✅ Focus indicators visible
✅ Error announcements
✅ Color contrast meets WCAG AA

## File Location

**Modified:** `frontend/src/pages/PatientRegistrationPage.tsx`

**Documentation:**
- `PATIENT_PORTAL_UI_UPDATE.md` - Full documentation
- `PatientPortalSection_Standalone.tsx` - Standalone component
- `PORTAL_UI_QUICK_REFERENCE.md` - This file

## Quick Copy-Paste

Need the section? Copy from:
`PatientPortalSection_Standalone.tsx`

Need validation? Use:
```typescript
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
if (createPortalAccount && !emailRegex.test(portalData.email)) {
  // Show error
}
```

Need to send data? Include:
```typescript
if (createPortalAccount) {
  data.create_portal_account = true;
  data.portal_enabled = true;
  data.portal_email = portalData.email.trim();
  data.portal_phone = portalData.phone.trim();
}
```

---

**Status:** ✅ Complete  
**Version:** 1.0  
**Last Updated:** February 6, 2026
