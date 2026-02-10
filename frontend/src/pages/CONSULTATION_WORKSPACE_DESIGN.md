# Consultation Workspace UI Design

## Overview

Single-screen consultation workspace that maintains visit context and follows EMR rules.

## Component Hierarchy

```
ConsultationPage (Container)
├── ConsultationHeader
│   ├── Visit Context (Visit ID, Status, Payment Status)
│   └── Patient Summary (Read-only: Name, Age, Gender, Phone)
├── ConsultationForm
│   ├── HistorySection
│   ├── ExaminationSection
│   ├── DiagnosisSection
│   └── ClinicalNotesSection
└── ConsultationActions
    ├── Cancel Button
    └── Save/Update Button
```

## State Management Approach

### 1. Local Form State (Optimistic Updates)
- **Location**: `ConsultationPage` component
- **Purpose**: Track user input in real-time
- **Structure**: `ConsultationData` object
- **Updates**: Immediate on field changes
- **Benefits**: Instant UI feedback, no lag

### 2. Server State (Source of Truth)
- **Location**: `useConsultation` hook
- **Purpose**: Fetch and cache consultation data from API
- **Structure**: `Consultation` object (includes metadata)
- **Updates**: On mount, after save/update operations
- **Benefits**: Single source of truth, prevents stale data

### 3. Derived State
- **isDirty**: Compares local form state vs server state
- **isSaving**: Tracks save operation in progress
- **loading**: Tracks initial data fetch
- **error**: Captures API errors

### 4. State Flow

```
User Input
  ↓
Local Form State Updated (isDirty = true)
  ↓
User Clicks Save
  ↓
isSaving = true
  ↓
API Call (POST/PATCH)
  ↓
Success: Update Server State, isDirty = false
Error: Show error, isSaving = false
```

## API Interaction Outline

### Endpoints (All Visit-Scoped)

1. **GET `/api/v1/visits/{visitId}/consultation/`**
   - **Purpose**: Fetch existing consultation
   - **Response**: `Consultation[]` (array with single item or empty)
   - **Error Handling**:
     - 404: Consultation doesn't exist (expected for new)
     - 401: Unauthorized → redirect to login
     - 403: Forbidden → show error

2. **POST `/api/v1/visits/{visitId}/consultation/`**
   - **Purpose**: Create new consultation
   - **Request Body**: `ConsultationData`
   - **Response**: `Consultation` (created object)
   - **Error Handling**:
     - 400: Validation error → show field errors
     - 403: Payment not cleared / Visit closed → show error
     - 409: Consultation already exists → switch to update mode

3. **PATCH `/api/v1/visits/{visitId}/consultation/`**
   - **Purpose**: Update existing consultation
   - **Request Body**: `Partial<ConsultationData>`
   - **Response**: `Consultation` (updated object)
   - **Error Handling**:
     - 400: Validation error → show field errors
     - 403: Payment not cleared / Visit closed → show error
     - 404: Consultation not found → switch to create mode

### Authentication

- **Method**: Token-based (JWT or DRF Token)
- **Header**: `Authorization: Token {token}` or `Authorization: Bearer {token}`
- **Storage**: localStorage or auth context
- **Refresh**: Handle token expiration (401 → redirect to login)

### Error Handling Strategy

1. **401 Unauthorized**
   - Clear auth token
   - Redirect to login page
   - Show message: "Session expired. Please log in again."

2. **403 Forbidden**
   - Show error message from API
   - Common messages:
     - "Payment must be cleared before consultation"
     - "Visit is closed and cannot be modified"
     - "Only doctors can create consultations"
   - Disable save button
   - Show retry option if applicable

3. **404 Not Found**
   - For GET: Expected for new consultations, show empty form
   - For PATCH: Switch to create mode (POST)

4. **409 Conflict**
   - Show error: "Visit is closed and cannot be modified"
   - Disable form fields
   - Show read-only mode

5. **500 Server Error**
   - Show generic error: "Server error. Please try again."
   - Log error for debugging
   - Allow retry

## UI/UX Considerations

### 1. Visit Context Preservation
- **Header always visible**: Visit ID and status at top
- **No navigation**: Single screen, no sidebar
- **URL structure**: `/consultation/{visitId}` (visitId in URL)
- **Breadcrumb**: Show "Visit #{visitId} > Consultation" if needed

### 2. Form Layout
- **Sections**: Vertical stack, full width
- **Labels**: Clear section titles with descriptions
- **Textareas**: Adequate height (6 rows minimum)
- **Spacing**: Comfortable padding between sections
- **Responsive**: Mobile-friendly layout

### 3. Save Behavior
- **Auto-save**: Not implemented (explicit save only)
- **Dirty tracking**: Disable save if no changes
- **Loading state**: Show "Saving..." during API call
- **Success feedback**: Brief toast/notification on save
- **Error feedback**: Inline error messages

### 4. Read-Only States
- **Patient Summary**: Always read-only
- **Visit Status**: Display only (no edit)
- **CLOSED Visit**: All fields read-only, save disabled

## Future Enhancements

### Inline Components (Per EMR Rules)
When implemented, these will be added as inline sections:

1. **LabInline** (`<LabInline visitId={visitId} />`)
   - Display lab orders
   - Create new lab orders
   - View lab results

2. **RadiologyInline** (`<RadiologyInline visitId={visitId} />`)
   - Display radiology requests
   - Create new radiology requests
   - View imaging reports

3. **PrescriptionInline** (`<PrescriptionInline visitId={visitId} />`)
   - Display prescriptions
   - Create new prescriptions
   - View dispensing status

**Note**: These components will be added AFTER consultation is saved, maintaining the flow:
`Visit → Consultation → (Lab | Radiology) → Prescription → Closure`

## EMR Rule Compliance Checklist

✅ **Visit-Scoped**: All API calls include `visitId`  
✅ **No Sidebar Navigation**: Single screen design  
✅ **Context Preservation**: Visit header always visible  
✅ **Inline Components**: Structure ready for Lab/Radiology/Prescription  
✅ **Payment Enforcement**: Handled by backend (403 if not cleared)  
✅ **Role Enforcement**: Handled by backend (403 if not doctor)  
✅ **CLOSED Visit Handling**: Read-only mode when visit is closed  

## File Structure

```
frontend/src/
├── pages/
│   ├── ConsultationPage.tsx (main container)
│   └── CONSULTATION_WORKSPACE_DESIGN.md (this file)
├── components/
│   └── consultation/
│       ├── ConsultationHeader.tsx
│       ├── ConsultationForm.tsx
│       ├── ConsultationActions.tsx
│       └── sections/
│           ├── HistorySection.tsx
│           ├── ExaminationSection.tsx
│           ├── DiagnosisSection.tsx
│           └── ClinicalNotesSection.tsx
├── hooks/
│   └── useConsultation.ts (state management)
├── api/
│   ├── consultation.ts (API client)
│   └── visits.ts (visit API client)
└── types/
    └── consultation.ts (TypeScript types)
```
