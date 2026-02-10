# Duplicate Prevention System

## Overview
This document describes the duplicate prevention mechanisms implemented across the EMR system to prevent accidental duplicate entries.

## Implementation

### Core Module
The duplicate prevention logic is centralized in `backend/core/duplicate_prevention.py`, providing reusable functions for checking duplicates across different entities.

### Entities Protected

#### 1. Patient Registration
- **Check**: Name + Date of Birth, Phone, Email, National ID
- **Window**: N/A (exact match)
- **Location**: `PatientCreateSerializer.validate()`
- **Rules**:
  - National ID must be unique (database constraint)
  - Phone number must be unique (if provided)
  - Email must be unique (if provided)
  - Name + DOB combination must be unique (if DOB provided)

#### 2. Visit Creation
- **Check**: Same patient + Same visit type + Same date + OPEN status
- **Window**: Same day
- **Location**: `VisitCreateSerializer.validate()`
- **Rules**:
  - Prevents creating multiple OPEN visits of the same type for the same patient on the same day
  - Allows multiple visits if previous ones are CLOSED

#### 3. Lab Orders
- **Check**: Same visit + Same test code
- **Window**: 5 minutes
- **Location**: `LabOrderCreateSerializer.validate()`
- **Rules**:
  - Prevents creating duplicate lab orders for the same test within 5 minutes
  - Allows re-ordering after 5 minutes have passed

#### 4. Radiology Orders
- **Check**: Same visit + Same study code
- **Window**: 5 minutes
- **Location**: `RadiologyOrderCreateSerializer.validate()`
- **Rules**:
  - Prevents creating duplicate radiology orders for the same study within 5 minutes
  - Allows re-ordering after 5 minutes have passed

#### 5. Payments
- **Check**: Same visit + Same amount + Same payment method
- **Window**: 2 minutes
- **Location**: `PaymentCreateSerializer.validate()`
- **Rules**:
  - Prevents duplicate payments of the same amount via the same method within 2 minutes
  - Protects against accidental double-clicking or form resubmission

#### 6. Vital Signs
- **Check**: Same visit
- **Window**: 3 minutes
- **Location**: `VitalSignsCreateSerializer.validate()`
- **Rules**:
  - Prevents recording vital signs multiple times within 3 minutes
  - Allows recording new vital signs after 3 minutes

#### 7. Appointments
- **Check**: Same patient + Same datetime
- **Window**: 30 minutes
- **Location**: `AppointmentCreateSerializer.validate()`
- **Rules**:
  - Prevents scheduling appointments for the same patient within 30 minutes of each other
  - Allows scheduling appointments with at least 30 minutes gap

## Usage

### In Serializers
```python
def validate(self, attrs):
    """Validate data and check for duplicates."""
    if self.instance is None:  # Only on create, not update
        from core.duplicate_prevention import check_entity_duplicate
        from django.core.exceptions import ValidationError as DjangoValidationError
        
        try:
            check_entity_duplicate(
                # ... entity-specific parameters
            )
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
    
    return attrs
```

### Time Windows
Time windows are configurable per entity:
- **Patient Registration**: No window (exact match)
- **Visits**: Same day
- **Lab Orders**: 5 minutes
- **Radiology Orders**: 5 minutes
- **Payments**: 2 minutes
- **Vital Signs**: 3 minutes
- **Appointments**: 30 minutes

## Error Messages
All duplicate prevention functions return clear, user-friendly error messages that include:
- What duplicate was found
- When it was created
- The ID of the duplicate record
- Suggestions for resolution

## Database Constraints
In addition to application-level checks, database-level unique constraints exist for:
- Patient `national_id` (unique)
- Patient `patient_id` (unique)
- Payment `paystack_reference` (unique)
- Various catalog items (test codes, study codes, etc.)

## Future Enhancements
- Configurable time windows via settings
- Admin override for duplicate creation
- Duplicate detection reports
- Bulk duplicate checking utilities

