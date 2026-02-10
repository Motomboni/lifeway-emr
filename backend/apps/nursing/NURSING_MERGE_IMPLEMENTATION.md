# Nursing Care Records - Update and Merge Implementation

## ✅ Implementation Status

Nursing care records can now be:
1. **Added** ✅ - Create new records (already working)
2. **Updated** ✅ - Edit existing records (newly implemented)
3. **Merged with Patient Medical Record** ✅ - Merge into patient's cumulative medical history (newly implemented)

## Overview

Similar to consultations, nursing care records (Nursing Notes, Medication Administration, Lab Sample Collection) can now be:
- **Updated** while the visit is OPEN and payment is CLEARED
- **Merged** with the patient's medical history when the `merge_with_patient_record` flag is set

## Changes Made

### Backend Changes

#### 1. Models (`apps/nursing/models.py`)
- **Removed immutability restrictions** from `save()` methods
- **Updated `clean()` methods** to allow updates (check visit status on both create and update)
- **Nurse role validation** only on creation (not on updates)

#### 2. Serializers (`apps/nursing/serializers.py`)
- Added `merge_with_patient_record` boolean field to:
  - `NursingNoteCreateSerializer`
  - `MedicationAdministrationCreateSerializer`
  - `LabSampleCollectionCreateSerializer`
- Field is `write_only=True` (not saved to model, used for merge logic)

#### 3. Views (`apps/nursing/views.py`)
- **Updated permissions** to allow updates:
  - `create`, `update`, `partial_update`: `IsNurse()`, `IsVisitActiveAndPaid()`
  - `destroy`: Prevented (maintain audit trail)
- **Added `merge_with_patient_history()` methods** for each ViewSet:
  - Formats nursing record data
  - Appends to `patient.medical_history` field
  - Includes visit context and timestamps
- **Updated `perform_create()` and `perform_update()`**:
  - Extract `merge_with_patient_record` flag
  - Call merge method if flag is True
  - Log merge status in audit trail

### Frontend Changes

#### 1. Types (`frontend/src/types/nursing.ts`)
- Added `merge_with_patient_record?: boolean` to:
  - `NursingNoteCreate`
  - `MedicationAdministrationCreate`
  - `LabSampleCollectionCreate`
- Fixed `note_type` values to match backend (uppercase: `GENERAL`, `ADMISSION`, etc.)

#### 2. API Client (`frontend/src/api/nursing.ts`)
- Added `updateNursingNote()` function
- Added `updateMedicationAdministration()` function
- Added `updateLabSampleCollection()` function

#### 3. Components
- **NursingNotesSection.tsx**:
  - Added edit functionality (edit button on each note)
  - Added merge checkbox to form
  - Added `handleEdit()` and `handleCancel()` functions
  - Updated `handleSubmit()` to support both create and update
  - Display note type with proper formatting

## How It Works

### 1. Creating Records

```typescript
// Frontend
const formData = {
  note_type: 'GENERAL',
  note_content: 'Patient alert and oriented',
  merge_with_patient_record: true  // ← Merge flag
};

await createNursingNote(visitId, formData);
```

**Backend Flow:**
1. Validate Nurse role and visit status
2. Create nursing note
3. If `merge_with_patient_record === true`:
   - Format note data with visit context
   - Append to `patient.medical_history`
   - Save patient record
4. Log audit entry (includes merge status)

### 2. Updating Records

```typescript
// Frontend
const formData = {
  note_content: 'Updated note content',
  merge_with_patient_record: true  // ← Merge flag
};

await updateNursingNote(visitId, noteId, formData);
```

**Backend Flow:**
1. Validate Nurse role and visit status (OPEN + CLEARED)
2. Update nursing note
3. If `merge_with_patient_record === true`:
   - Format updated note data
   - Append to `patient.medical_history`
   - Save patient record
4. Log audit entry (includes merge status)

### 3. Merging with Patient Medical History

When `merge_with_patient_record` is `true`, the record is formatted and appended to `patient.medical_history`:

**Format for Nursing Notes:**
```
============================================================
NURSING NOTE - Visit #123 - 2025-12-31 14:30
============================================================
Note Type: General Nursing Note

NOTE CONTENT:
Patient alert and oriented, no complaints

PATIENT CONDITION:
Alert and oriented

CARE PROVIDED:
Vital signs checked, patient educated on medication

PATIENT RESPONSE:
Patient understood instructions

Recorded by: Nurse Jane Doe
============================================================
```

**Format for Medication Administration:**
```
============================================================
MEDICATION ADMINISTRATION - Visit #123 - 2025-12-31 14:30
============================================================
Medication: Paracetamol
Dose Administered: 500mg
Route: Oral
Status: Given
Site: N/A

NOTES:
Patient took medication without issues

Administered by: Nurse Jane Doe
============================================================
```

**Format for Lab Sample Collection:**
```
============================================================
LAB SAMPLE COLLECTION - Visit #123 - 2025-12-31 14:30
============================================================
Sample Type: Blood
Status: Collected
Collection Site: Left arm
Sample Volume: 5ml
Container Type: Vacutainer

Tests: Complete Blood Count, Blood Glucose

Collected by: Nurse Jane Doe
============================================================
```

## Permissions

### Who Can Update?
- **Nurse** only (enforced by `IsNurse()` permission)
- Visit must be **OPEN** (enforced by `IsVisitActiveAndPaid()`)
- Payment must be **CLEARED** (enforced by `IsVisitActiveAndPaid()`)

### Who Can View?
- **Doctor** and **Nurse** (enforced by `CanViewNursingRecords()`)

### Who Can Delete?
- **No one** - Records are permanent to maintain audit trail

## Audit Logging

All create and update actions are logged with:
- User ID and role
- Visit ID
- Action type (`nursing_note.create`, `nursing_note.update`, etc.)
- Resource type and ID
- Merge status (`merged_with_patient_record: true/false`)
- Timestamp, IP address, user agent

## Example Usage

### Create and Merge
```typescript
// Create nursing note and merge with patient record
await createNursingNote(visitId, {
  note_type: 'GENERAL',
  note_content: 'Patient condition stable',
  merge_with_patient_record: true  // ← Will merge
});
```

### Update and Merge
```typescript
// Update existing note and merge
await updateNursingNote(visitId, noteId, {
  note_content: 'Updated: Patient condition improved',
  merge_with_patient_record: true  // ← Will merge
});
```

### Create Without Merging
```typescript
// Create note without merging (default)
await createNursingNote(visitId, {
  note_type: 'GENERAL',
  note_content: 'Routine check',
  merge_with_patient_record: false  // ← Will not merge
});
```

## Benefits

1. **Flexibility**: Nurses can correct errors or update records
2. **Medical History**: Important nursing care can be merged into patient's cumulative record
3. **Audit Trail**: All changes are logged (including merge status)
4. **Data Integrity**: Updates only allowed on OPEN visits with CLEARED payment
5. **Compliance**: Records cannot be deleted (maintains audit trail)

## Files Modified

### Backend
- `apps/nursing/models.py` - Removed immutability, updated validation
- `apps/nursing/serializers.py` - Added merge flag
- `apps/nursing/views.py` - Added merge methods, updated permissions

### Frontend
- `types/nursing.ts` - Added merge flag, fixed note_type values
- `api/nursing.ts` - Added update functions
- `components/nursing/NursingNotesSection.tsx` - Added edit and merge UI

## Next Steps

1. Add edit functionality to MedicationAdministrationSection
2. Add edit functionality to LabSampleCollectionSection
3. Add merge checkboxes to those sections
4. Test merge functionality end-to-end

## Testing Checklist

- [x] Models allow updates (removed immutability)
- [x] Serializers include merge flag
- [x] Views support updates and merging
- [x] Frontend supports editing nursing notes
- [x] Frontend includes merge checkbox
- [ ] Frontend supports editing medication administration
- [ ] Frontend supports editing lab sample collection
- [ ] End-to-end testing of merge functionality
