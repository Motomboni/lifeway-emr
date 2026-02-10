# Nursing App - Visit-Scoped Models

## Overview

The Nursing app provides Django models for Nurse role functionality in the EMR system.

## Models

### 1. NursingNote

**Purpose**: Non-diagnostic clinical observations and care documentation by nurses.

**Key Features**:
- Visit-scoped (ForeignKey to Visit)
- Nurse-only creation (validated in `clean()`)
- No diagnosis fields allowed
- Immutable after creation
- Multiple note types (General, Admission, Shift Handover, Procedure, Wound Care, Patient Education, Antenatal, Inpatient)

**Fields**:
- `visit` - ForeignKey to Visit (CASCADE)
- `recorded_by` - ForeignKey to User (PROTECT)
- `note_type` - Choice field for note category
- `note_content` - TextField for note content (NO DIAGNOSIS)
- `patient_condition` - General condition observation
- `care_provided` - Description of nursing care
- `patient_response` - Patient's response to care
- `recorded_at` - Auto timestamp

**Validation**:
- Visit must be OPEN when creating note
- Only Nurses can create notes
- Notes are immutable after creation

### 2. MedicationAdministration

**Purpose**: Tracks medication administration from existing prescriptions.

**Key Features**:
- Visit-scoped (ForeignKey to Visit)
- Requires existing Prescription (Nurse cannot create prescriptions)
- Nurse-only creation
- Immutable after creation
- Tracks actual administration vs. prescribed

**Fields**:
- `visit` - ForeignKey to Visit (CASCADE)
- `prescription` - ForeignKey to Prescription (PROTECT)
- `administered_by` - ForeignKey to User (PROTECT)
- `administration_time` - When medication was given
- `dose_administered` - Actual dose given
- `route` - Route of administration (Oral, IV, IM, etc.)
- `site` - Administration site
- `status` - Given, Refused, Held, Not Available, Error
- `administration_notes` - Notes about administration
- `reason_if_held` - Required if status is HELD
- `recorded_at` - Auto timestamp

**Validation**:
- Visit must be OPEN when creating administration
- Prescription must belong to same visit
- Only Nurses can record administration
- Reason required if medication was held
- Records are immutable after creation

### 3. LabSampleCollection

**Purpose**: Tracks lab sample collection from existing lab orders.

**Key Features**:
- Visit-scoped (ForeignKey to Visit)
- Requires existing LabOrder (Nurse cannot create lab orders)
- Nurse-only creation
- Immutable after creation
- Automatically updates LabOrder status to SAMPLE_COLLECTED on successful collection

**Fields**:
- `visit` - ForeignKey to Visit (CASCADE)
- `lab_order` - ForeignKey to LabOrder (PROTECT)
- `collected_by` - ForeignKey to User (PROTECT)
- `collection_time` - When sample was collected
- `sample_type` - Type of sample (Blood, Urine, etc.)
- `collection_site` - Collection site
- `status` - Collected, Partial, Failed, Refused
- `sample_volume` - Volume collected
- `container_type` - Type of container used
- `collection_notes` - Notes about collection
- `reason_if_failed` - Required if status is FAILED
- `recorded_at` - Auto timestamp

**Validation**:
- Visit must be OPEN when creating collection
- LabOrder must belong to same visit
- LabOrder must be in ORDERED or SAMPLE_COLLECTED status
- Only Nurses can record collection
- Reason required if collection failed
- Records are immutable after creation
- Updates LabOrder status to SAMPLE_COLLECTED on successful collection

## EMR Rule Compliance

✅ **Visit-Scoped**: All models have ForeignKey to Visit  
✅ **No Diagnosis Fields**: No diagnosis-related fields in any model  
✅ **Immutable Records**: All models prevent updates after creation  
✅ **Auditable**: All models track `created_by`/`recorded_by` and `created_at`/`recorded_at`  
✅ **Nurse-Only**: All models validate that only Nurses can create records  
✅ **Dependency Validation**: MedicationAdministration requires Prescription, LabSampleCollection requires LabOrder  

## Database Tables

- `nursing_notes` - NursingNote model
- `medication_administrations` - MedicationAdministration model
- `lab_sample_collections` - LabSampleCollection model

## Indexes

All models have indexes on:
- Visit and timestamp (for chronological queries)
- Foreign key relationships (for joins)
- Status fields (for filtering)

## Next Steps

1. **Run Migration**:
   ```bash
   python manage.py migrate nursing
   ```

2. **Create Serializers**: Add serializers for API access

3. **Create Views**: Add ViewSets with proper permissions

4. **Create URLs**: Register routes under visit-scoped endpoints

5. **Add Permissions**: Ensure Nurse-only access with proper validation
