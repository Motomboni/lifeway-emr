# Insurance and Retainership Registration

## Overview
This document describes the implementation of insurance and retainership support during patient registration.

## Features Implemented

### 1. Insurance Registration
- Patients can provide insurance details during registration
- Insurance policy is automatically created when patient registers with insurance
- Insurance details include:
  - Insurance provider (selected from list)
  - Policy number
  - Coverage type (Full/Partial)
  - Coverage percentage (for partial coverage)
  - Validity dates (start and optional end date)

### 2. Retainership Support
- Patients can have retainership agreements
- Retainership details include:
  - Retainership type (e.g., Monthly, Quarterly, Annual, Corporate)
  - Start date
  - End date (optional)
  - Retainership amount

## Backend Changes

### Models
- **Patient Model** (`apps/patients/models.py`):
  - Added `has_retainership` (BooleanField)
  - Added `retainership_type` (CharField)
  - Added `retainership_start_date` (DateField)
  - Added `retainership_end_date` (DateField, optional)
  - Added `retainership_amount` (DecimalField)

### Serializers
- **PatientCreateSerializer** (`apps/patients/serializers.py`):
  - Added insurance fields (write-only):
    - `has_insurance` (BooleanField)
    - `insurance_provider_id` (IntegerField)
    - `insurance_policy_number` (CharField)
    - `insurance_coverage_type` (ChoiceField)
    - `insurance_coverage_percentage` (DecimalField)
    - `insurance_valid_from` (DateField)
    - `insurance_valid_to` (DateField, optional)
  - Added retainership fields (write-only):
    - `has_retainership` (BooleanField)
    - `retainership_type` (CharField)
    - `retainership_start_date` (DateField)
    - `retainership_end_date` (DateField, optional)
    - `retainership_amount` (DecimalField)
  - Updated `create()` method to:
    - Create `InsurancePolicy` when patient has insurance
    - Set retainership fields when patient has retainership

### API Endpoints
- **Insurance Providers** (`/api/v1/billing/insurance-providers/`):
  - GET: List all active insurance providers (authenticated users)
  - Used for patient registration form dropdown

### Migrations
- `0007_add_retainership_fields.py`: Adds retainership fields to Patient model

## Frontend Changes

### Types
- **PatientCreateData** (`frontend/src/types/patient.ts`):
  - Added insurance fields
  - Added retainership fields

### API Client
- **insurance.ts** (new file):
  - `fetchInsuranceProviders()`: Fetches list of insurance providers

### Registration Form
- **PatientRegistrationPage.tsx**:
  - Added "Insurance Information" section with:
    - Checkbox to enable insurance
    - Insurance provider dropdown (populated from API)
    - Policy number input
    - Coverage type and percentage inputs
    - Validity date inputs
  - Added "Retainership Information" section with:
    - Checkbox to enable retainership
    - Retainership type input
    - Start and end date inputs
    - Amount input

## Usage

### Registering Patient with Insurance
1. Fill in patient personal information
2. Check "Patient has insurance"
3. Select insurance provider from dropdown
4. Enter policy number
5. Select coverage type (Full/Partial)
6. If partial, enter coverage percentage
7. Enter validity dates
8. Submit form

### Registering Patient with Retainership
1. Fill in patient personal information
2. Check "Patient has retainership"
3. Enter retainership type (e.g., "Monthly", "Annual")
4. Enter start date
5. Optionally enter end date
6. Enter retainership amount
7. Submit form

## Integration with Billing System

### Insurance
- When a patient with insurance creates a visit with `payment_type='INSURANCE'`:
  - The system automatically links the insurance policy to the visit's bill
  - Bill status is set to `INSURANCE_PENDING`
  - Visit payment_status is set to `INSURANCE_PENDING`

### Retainership
- Retainership information is stored on the patient record
- Can be used for:
  - Discount calculations
  - Billing rules
  - Visit creation defaults
  - Reporting and analytics

## Future Enhancements
- Retainership-based billing rules
- Automatic discount application for retainership patients
- Retainership expiry notifications
- Insurance policy expiry tracking
- Bulk insurance provider import

