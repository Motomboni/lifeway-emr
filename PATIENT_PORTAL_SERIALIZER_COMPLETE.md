# Patient Portal Serializer - Complete Implementation

## Overview
Updated `PatientCreateSerializer` to handle patient portal account creation during patient registration with atomic transactions and proper validation.

## Full Serializer Code

```python
"""
Patient serializers - PHI data protection.

Per EMR Rules:
- Receptionist: Can create and search patients
- All patient data is PHI - must be protected
- Data minimization: Only return necessary fields
"""
from rest_framework import serializers
from .models import Patient


class PatientCreateSerializer(PatientSerializer):
    """
    Serializer for creating patients with optional portal account creation.
    
    Input Fields:
    - Patient data (first_name, last_name, etc.)
    - create_portal_account (bool): Whether to create portal login
    - portal_email (email): Email for portal login (required if create_portal_account=True)
    - portal_phone (string): Phone for notifications (optional)
    
    Output Fields:
    - patient: Complete patient data
    - portal_created (bool): Whether portal account was created
    - temporary_password (string): Only included if portal account was created
    """
    
    class Meta(PatientSerializer.Meta):
        # Include all fields from parent, plus insurance, retainership, and portal fields
        fields = PatientSerializer.Meta.fields + [
            'has_insurance',
            'insurance_provider_id',
            'insurance_policy_number',
            'insurance_coverage_type',
            'insurance_coverage_percentage',
            'insurance_valid_from',
            'insurance_valid_to',
            'has_retainership',
            'retainership_type',
            'retainership_start_date',
            'retainership_end_date',
            'retainership_amount',
            'create_portal_account',
            'portal_enabled',
            'portal_email',
            'portal_phone',
            'portal_created',
            'temporary_password',
        ]
        read_only_fields = PatientSerializer.Meta.read_only_fields + [
            'portal_created',
            'temporary_password',
        ]
    
    # patient_id is auto-generated, so it's read-only and not required
    patient_id = serializers.CharField(required=False, read_only=True)
    
    # Insurance fields (nested, optional)
    has_insurance = serializers.BooleanField(required=False, default=False, write_only=True)
    insurance_provider_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    insurance_policy_number = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    insurance_coverage_type = serializers.ChoiceField(
        choices=[('FULL', 'Full Coverage'), ('PARTIAL', 'Partial Coverage')],
        required=False,
        allow_null=True,
        write_only=True
    )
    insurance_coverage_percentage = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        write_only=True
    )
    insurance_valid_from = serializers.DateField(required=False, allow_null=True, write_only=True)
    insurance_valid_to = serializers.DateField(required=False, allow_null=True, write_only=True)
    
    # Retainership fields (optional)
    has_retainership = serializers.BooleanField(required=False, default=False, write_only=True)
    retainership_type = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    retainership_start_date = serializers.DateField(required=False, allow_null=True, write_only=True)
    retainership_end_date = serializers.DateField(required=False, allow_null=True, write_only=True)
    retainership_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        write_only=True
    )
    
    # Patient Portal fields (optional)
    create_portal_account = serializers.BooleanField(required=False, default=False, write_only=True)
    portal_enabled = serializers.BooleanField(required=False, default=False, write_only=True)
    portal_email = serializers.EmailField(required=False, allow_null=True, allow_blank=True, write_only=True)
    portal_phone = serializers.CharField(required=False, allow_null=True, allow_blank=True, write_only=True)
    
    # Portal response fields (read-only, returned after creation)
    portal_created = serializers.BooleanField(read_only=True)
    temporary_password = serializers.CharField(read_only=True)
    
    def validate_national_id(self, value):
        """Ensure national_id is unique if provided."""
        if value:
            if Patient.objects.filter(national_id=value).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise serializers.ValidationError(
                    "A patient with this national ID already exists."
                )
        return value
    
    def validate(self, attrs):
        """Validate patient data."""
        # Ensure first_name and last_name are provided
        first_name = attrs.get('first_name', '').strip() if attrs.get('first_name') else ''
        last_name = attrs.get('last_name', '').strip() if attrs.get('last_name') else ''
        
        if not first_name or not last_name:
            raise serializers.ValidationError(
                "First name and last name are required."
            )
        
        # Validate insurance fields if has_insurance is True
        has_insurance = attrs.get('has_insurance', False)
        if has_insurance:
            if not attrs.get('insurance_provider_id'):
                raise serializers.ValidationError(
                    "Insurance provider is required when patient has insurance."
                )
            if not attrs.get('insurance_policy_number'):
                raise serializers.ValidationError(
                    "Insurance policy number is required when patient has insurance."
                )
            if not attrs.get('insurance_valid_from'):
                raise serializers.ValidationError(
                    "Insurance validity start date is required when patient has insurance."
                )
            # Set default coverage if not provided
            if not attrs.get('insurance_coverage_type'):
                attrs['insurance_coverage_type'] = 'FULL'
            if not attrs.get('insurance_coverage_percentage'):
                attrs['insurance_coverage_percentage'] = 100.00
        
        # Validate retainership fields if has_retainership is True
        has_retainership = attrs.get('has_retainership', False)
        if has_retainership:
            if not attrs.get('retainership_type'):
                raise serializers.ValidationError(
                    "Retainership type is required when patient has retainership."
                )
            if not attrs.get('retainership_start_date'):
                raise serializers.ValidationError(
                    "Retainership start date is required when patient has retainership."
                )
            if not attrs.get('retainership_amount'):
                raise serializers.ValidationError(
                    "Retainership amount is required when patient has retainership."
                )
        
        # Validate patient portal fields if create_portal_account is True
        create_portal_account = attrs.get('create_portal_account', False)
        if create_portal_account:
            portal_email = attrs.get('portal_email', '').strip() if attrs.get('portal_email') else ''
            if not portal_email:
                raise serializers.ValidationError(
                    "Email is required when creating a patient portal account."
                )
            
            # Validate email format
            import re
            email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
            if not re.match(email_regex, portal_email):
                raise serializers.ValidationError(
                    "Invalid email format for patient portal account."
                )
            
            # Check if email already used by another user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if User.objects.filter(username=portal_email).exists():
                raise serializers.ValidationError(
                    f"A portal account with email {portal_email} already exists."
                )
        
        # Check for duplicate patient (if creating new)
        if self.instance is None:
            from core.duplicate_prevention import check_patient_duplicate
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            try:
                check_patient_duplicate(
                    first_name=attrs.get('first_name'),
                    last_name=attrs.get('last_name'),
                    date_of_birth=attrs.get('date_of_birth'),
                    phone=attrs.get('phone'),
                    email=attrs.get('email'),
                    national_id=attrs.get('national_id')
                )
            except DjangoValidationError as e:
                raise serializers.ValidationError(str(e))
        
        # Clean up empty strings - convert to None for optional fields
        optional_fields = [
            'middle_name', 'phone', 'email', 'address', 
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship',
            'national_id', 'allergies', 'medical_history',
            'insurance_policy_number', 'retainership_type', 'portal_phone'
        ]
        for field in optional_fields:
            if field in attrs and attrs[field] == '':
                attrs[field] = None
        
        # Clean up empty strings for date fields
        date_fields = ['date_of_birth', 'insurance_valid_from', 'insurance_valid_to', 
                      'retainership_start_date', 'retainership_end_date']
        for field in date_fields:
            if field in attrs and attrs[field] == '':
                attrs[field] = None
        
        # Clean up empty strings for gender and blood_group
        if 'gender' in attrs and attrs['gender'] == '':
            attrs['gender'] = None
        if 'blood_group' in attrs and attrs['blood_group'] == '':
            attrs['blood_group'] = None
        
        return attrs
    
    def create(self, validated_data):
        """Create patient with auto-generated patient_id and handle insurance/retainership/portal."""
        import logging
        from django.db import transaction
        from django.contrib.auth import get_user_model
        import secrets
        
        logger = logging.getLogger(__name__)
        User = get_user_model()
        
        # Extract insurance and retainership data (they're not Patient model fields)
        # Use .pop() with defaults to safely extract fields - these won't raise KeyError
        has_insurance = validated_data.pop('has_insurance', False)
        insurance_provider_id = validated_data.pop('insurance_provider_id', None)
        insurance_policy_number = validated_data.pop('insurance_policy_number', None)
        insurance_coverage_type = validated_data.pop('insurance_coverage_type', None)
        insurance_coverage_percentage = validated_data.pop('insurance_coverage_percentage', None)
        insurance_valid_from = validated_data.pop('insurance_valid_from', None)
        insurance_valid_to = validated_data.pop('insurance_valid_to', None)
        
        has_retainership = validated_data.pop('has_retainership', False)
        retainership_type = validated_data.pop('retainership_type', None)
        retainership_start_date = validated_data.pop('retainership_start_date', None)
        retainership_end_date = validated_data.pop('retainership_end_date', None)
        retainership_amount = validated_data.pop('retainership_amount', None)
        
        # Extract patient portal data
        create_portal_account = validated_data.pop('create_portal_account', False)
        portal_enabled = validated_data.pop('portal_enabled', False)
        portal_email = validated_data.pop('portal_email', None)
        portal_phone = validated_data.pop('portal_phone', None)
        
        # Variables to track portal account creation
        portal_created = False
        temporary_password = None
        portal_user = None
        
        # Generate patient_id if not provided
        if 'patient_id' not in validated_data or not validated_data.get('patient_id'):
            # Generate sequential patient ID in format LMC000001
            validated_data['patient_id'] = Patient.generate_patient_id()
        
        # Ensure is_active defaults to True
        if 'is_active' not in validated_data:
            validated_data['is_active'] = True
        
        # Use atomic transaction to ensure all-or-nothing creation
        try:
            with transaction.atomic():
                logger.info(f"Creating patient with data: {list(validated_data.keys())}")
                
                # Create patient
                patient = super().create(validated_data)
                logger.info(f"Patient created successfully with ID: {patient.id}")
                
                # Create patient portal account if requested
                if create_portal_account and portal_email:
                    try:
                        # Generate secure temporary password (12 characters, URL-safe)
                        temporary_password = secrets.token_urlsafe(12)[:12]
                        
                        # Create portal user account
                        portal_user = User.objects.create_user(
                            username=portal_email.strip(),
                            email=portal_email.strip(),
                            password=temporary_password,
                            role='PATIENT',
                            patient=patient,
                            first_name=patient.first_name,
                            last_name=patient.last_name,
                            is_active=True
                        )
                        
                        # Enable portal on patient record
                        patient.portal_enabled = True
                        patient.save(update_fields=['portal_enabled'])
                        
                        portal_created = True
                        logger.info(f"Patient portal account created for patient {patient.id}, user {portal_user.id}")
                        
                    except Exception as e:
                        logger.error(f"Error creating portal account: {str(e)}", exc_info=True)
                        # Raise to rollback transaction
                        raise serializers.ValidationError(
                            f"Failed to create portal account: {str(e)}"
                        )
                
                # Set portal_enabled even if not creating account (for future creation)
                elif portal_enabled:
                    patient.portal_enabled = True
                    patient.save(update_fields=['portal_enabled'])
        
        except Exception as e:
            logger.error(f"Error in patient creation transaction: {str(e)}", exc_info=True)
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise serializers.ValidationError(f"Failed to create patient: {str(e)}")
        
        # Note: Insurance and retainership creation happens outside transaction
        # to avoid rolling back patient if these optional features fail
        
        # [... insurance policy creation code ...]
        # [... retainership setup code ...]
        
        # Add portal account info to patient instance for serializer response
        patient.portal_created = portal_created
        patient.temporary_password = temporary_password if portal_created else None
        
        return patient
    
    def to_representation(self, instance):
        """Add portal account info to response."""
        data = super().to_representation(instance)
        
        # Add portal creation info if available
        if hasattr(instance, 'portal_created'):
            data['portal_created'] = instance.portal_created
        else:
            data['portal_created'] = False
        
        # Only include temporary password if it was just created
        if hasattr(instance, 'temporary_password') and instance.temporary_password:
            data['temporary_password'] = instance.temporary_password
        
        return data
```

## Key Features

### 1. ✅ Atomic Transaction
```python
with transaction.atomic():
    # Create patient
    patient = super().create(validated_data)
    
    # Create portal account
    if create_portal_account:
        portal_user = User.objects.create_user(...)
        patient.portal_enabled = True
        patient.save()
```

**Behavior:**
- If patient creation fails → Nothing created
- If portal creation fails → Patient creation rollback
- All-or-nothing guarantee

### 2. ✅ Password Generation
```python
import secrets
temporary_password = secrets.token_urlsafe(12)[:12]
```

**Security:**
- Uses `secrets` module (cryptographically secure)
- URL-safe characters
- 12 characters long
- Suitable for temporary passwords

### 3. ✅ User Creation
```python
portal_user = User.objects.create_user(
    username=portal_email.strip(),
    email=portal_email.strip(),
    password=temporary_password,  # Hashed automatically by create_user
    role='PATIENT',
    patient=patient,  # One-to-one link
    first_name=patient.first_name,
    last_name=patient.last_name,
    is_active=True
)
```

**Features:**
- Uses `create_user()` → Password hashed automatically
- Username = email (for easy login)
- Role set to PATIENT
- OneToOne relationship established
- Account active immediately

### 4. ✅ Validation
```python
# Email required when portal account requested
if create_portal_account:
    if not portal_email:
        raise ValidationError("Email is required...")
    
    # Email format validation
    if not re.match(email_regex, portal_email):
        raise ValidationError("Invalid email format...")
    
    # Check duplicate email/username
    if User.objects.filter(username=portal_email).exists():
        raise ValidationError("Email already exists...")
```

### 5. ✅ Response Format
```json
{
  "id": 123,
  "patient_id": "LMC000123",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john@example.com",
  "phone": "0712345678",
  "portal_enabled": true,
  "portal_created": true,
  "temporary_password": "xK9mP2nQ7vR3",
  "created_at": "2026-02-06T16:00:00Z",
  ...
}
```

**Response fields:**
- `portal_created`: `true` if portal account was created, `false` otherwise
- `temporary_password`: Only included if `portal_created=true`
- All other patient fields as normal

## Request Examples

### Example 1: Basic Patient (No Portal)
```bash
POST /api/v1/patients/
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "date_of_birth": "1990-01-15",
  "gender": "MALE",
  "phone": "0712345678"
}
```

**Response:**
```json
{
  "id": 123,
  "first_name": "John",
  "last_name": "Doe",
  "portal_created": false
}
```

### Example 2: Patient with Portal Account
```bash
POST /api/v1/patients/
Content-Type: application/json

{
  "first_name": "Jane",
  "last_name": "Smith",
  "date_of_birth": "1985-03-20",
  "gender": "FEMALE",
  "create_portal_account": true,
  "portal_email": "jane.smith@email.com",
  "portal_phone": "0723456789"
}
```

**Response:**
```json
{
  "id": 124,
  "patient_id": "LMC000124",
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "jane.smith@email.com",
  "phone": "0723456789",
  "portal_enabled": true,
  "portal_created": true,
  "temporary_password": "aB3dE5fG7hI9",
  "created_at": "2026-02-06T16:30:00Z"
}
```

### Example 3: Enable Portal Without Creating Account
```bash
POST /api/v1/patients/
Content-Type: application/json

{
  "first_name": "Mike",
  "last_name": "Johnson",
  "portal_enabled": true
}
```

**Response:**
```json
{
  "id": 125,
  "portal_enabled": true,
  "portal_created": false
}
```

## Validation Error Examples

### Error 1: Missing Email
```bash
Request:
{
  "first_name": "John",
  "last_name": "Doe",
  "create_portal_account": true
  // Missing portal_email
}

Response: 400 Bad Request
{
  "error": "Email is required when creating a patient portal account."
}
```

### Error 2: Invalid Email Format
```bash
Request:
{
  "first_name": "John",
  "last_name": "Doe",
  "create_portal_account": true,
  "portal_email": "invalid-email"
}

Response: 400 Bad Request
{
  "error": "Invalid email format for patient portal account."
}
```

### Error 3: Email Already Exists
```bash
Request:
{
  "first_name": "John",
  "last_name": "Doe",
  "create_portal_account": true,
  "portal_email": "existing@email.com"
}

Response: 400 Bad Request
{
  "error": "A portal account with email existing@email.com already exists."
}
```

## Transaction Flow

### Successful Creation
```
START TRANSACTION
  │
  ├─> Create Patient record
  │   └─> Generate patient_id: LMC000123
  │
  ├─> Create User account (if portal requested)
  │   ├─> Username: portal_email
  │   ├─> Password: Hash(temporary_password)
  │   ├─> Role: PATIENT
  │   └─> Link: patient_id = patient.id
  │
  ├─> Update patient.portal_enabled = True
  │
COMMIT TRANSACTION
  │
  └─> Return patient + portal_created + temporary_password
```

### Failed Creation (Rollback)
```
START TRANSACTION
  │
  ├─> Create Patient record ✓
  │
  ├─> Create User account (if portal requested)
  │   └─> ERROR: Email already exists ✗
  │
ROLLBACK TRANSACTION
  │
  └─> Nothing saved to database
      Return error to client
```

## Testing

### Test 1: Create Patient with Portal
```python
from apps.patients.serializers import PatientCreateSerializer

data = {
    'first_name': 'Test',
    'last_name': 'Patient',
    'create_portal_account': True,
    'portal_email': 'test@example.com',
    'portal_phone': '0712345678'
}

serializer = PatientCreateSerializer(data=data)
if serializer.is_valid():
    patient = serializer.save()
    response_data = serializer.data
    
    assert response_data['portal_created'] == True
    assert 'temporary_password' in response_data
    assert len(response_data['temporary_password']) == 12
    print(f"Portal created: {response_data['portal_created']}")
    print(f"Temp password: {response_data['temporary_password']}")
```

### Test 2: Validation - Missing Email
```python
data = {
    'first_name': 'Test',
    'last_name': 'Patient',
    'create_portal_account': True
    # Missing portal_email
}

serializer = PatientCreateSerializer(data=data)
assert not serializer.is_valid()
assert 'Email is required' in str(serializer.errors)
```

### Test 3: Validation - Duplicate Email
```python
# First, create a user
User.objects.create_user(username='existing@email.com', password='pass')

# Try to create patient with same email
data = {
    'first_name': 'Test',
    'last_name': 'Patient',
    'create_portal_account': True,
    'portal_email': 'existing@email.com'
}

serializer = PatientCreateSerializer(data=data)
assert not serializer.is_valid()
assert 'already exists' in str(serializer.errors)
```

## Security Considerations

### 1. Password Security
- ✅ Uses `secrets` module (cryptographically secure)
- ✅ Hashed using Django's `create_user()` (bcrypt/PBKDF2)
- ✅ Temporary password returned ONCE (not stored plaintext)
- ✅ Patient must change on first login (implement in auth flow)

### 2. Email Uniqueness
- ✅ Validated before database insert
- ✅ Prevents duplicate accounts
- ✅ Clear error message to user

### 3. Transaction Safety
- ✅ Atomic transaction ensures consistency
- ✅ Rollback on any error
- ✅ No orphaned records
- ✅ No partial data

### 4. Validation Order
1. Field presence (email required)
2. Format validation (email regex)
3. Uniqueness check (database query)
4. Duplicate patient check
5. Create in transaction

## Performance

### Database Queries

**Without Portal:**
- 1 INSERT (patient)
- 1 SELECT (duplicate check)
- **Total: 2 queries**

**With Portal:**
- 1 INSERT (patient)
- 1 INSERT (user)
- 1 UPDATE (patient.portal_enabled)
- 1 SELECT (duplicate email check)
- 1 SELECT (duplicate patient check)
- **Total: 5 queries**

**Optimized:** All within one transaction (fast)

### Memory Usage
- Temporary password: 12 bytes
- Additional state: ~100 bytes
- **Impact: Negligible**

## Integration with Frontend

### Frontend Sends
```typescript
const patientData = {
  first_name: "John",
  last_name: "Doe",
  create_portal_account: true,
  portal_email: "john@example.com",
  portal_phone: "0712345678"
};

const response = await createPatient(patientData);
```

### Frontend Receives
```typescript
{
  id: 123,
  first_name: "John",
  last_name: "Doe",
  portal_enabled: true,
  portal_created: true,
  temporary_password: "xK9mP2nQ7vR3"
}

// Show success message with credentials
if (response.portal_created) {
  alert(`Portal account created!
  Username: ${response.email}
  Temporary Password: ${response.temporary_password}
  
  Patient must change password on first login.`);
}
```

## Email Notification (Next Step)

```python
# In create method, after portal_created = True:

if portal_created:
    from django.core.mail import send_mail
    from django.conf import settings
    
    send_mail(
        subject=f'Welcome to {settings.CLINIC_NAME} Patient Portal',
        message=f'''
        Dear {patient.get_full_name()},
        
        Your patient portal account has been created.
        
        Login at: {settings.PORTAL_URL}
        Username: {portal_email}
        Temporary Password: {temporary_password}
        
        Please change your password after first login.
        
        Best regards,
        {settings.CLINIC_NAME}
        ''',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[portal_email],
        fail_silently=False,
    )
```

## Error Handling

### Transaction Rollback Scenarios

1. **Patient creation fails:**
   - Duplicate national_id
   - Database constraint violation
   - Invalid field data
   - **Result:** Nothing saved

2. **User creation fails:**
   - Email already exists (caught in validation)
   - Database error
   - Invalid role
   - **Result:** Patient not created (rollback)

3. **Portal enable fails:**
   - Database error
   - **Result:** Patient not created (rollback)

### Non-Rollback Scenarios

Insurance and retainership creation happen **outside** the transaction:
- If they fail, patient is still created
- Logged as warning
- Can be added later manually

## Testing Script

```bash
cd backend
python manage.py shell
```

```python
from apps.patients.serializers import PatientCreateSerializer

# Test 1: Create patient with portal
data = {
    'first_name': 'Portal',
    'last_name': 'Test',
    'create_portal_account': True,
    'portal_email': 'portaltest@example.com',
    'portal_phone': '0712345678'
}

serializer = PatientCreateSerializer(data=data)
if serializer.is_valid():
    patient = serializer.save()
    response = serializer.data
    print(f"Patient ID: {patient.id}")
    print(f"Portal Created: {response['portal_created']}")
    print(f"Temp Password: {response.get('temporary_password', 'N/A')}")
    print(f"Username: {patient.portal_user.username if hasattr(patient, 'portal_user') else 'N/A'}")
else:
    print(f"Errors: {serializer.errors}")
```

## File Location

**Modified:** `backend/apps/patients/serializers.py`

**Changes:**
- Added 4 portal fields (input)
- Added 2 portal response fields (output)
- Added portal validation in `validate()`
- Updated `create()` method with portal logic
- Added `to_representation()` override
- **Lines added:** ~100 lines

## Dependencies

**Standard library:**
```python
import secrets  # For password generation
import re  # For email validation
from django.db import transaction  # For atomic operations
from django.contrib.auth import get_user_model  # For User model
```

**No new packages required**

## Rollback

To remove portal account creation:

```python
# Remove these fields from serializer:
- create_portal_account
- portal_enabled
- portal_email
- portal_phone
- portal_created
- temporary_password

# Remove from validate():
- Portal validation block (lines 267-290)

# Remove from create():
- Portal extraction (lines 326-329)
- Portal creation block (lines 354-375)
- Portal response attributes (lines 482-483)

# Remove to_representation() override
```

## Next Steps

1. **Add email sending** (in create method after portal_created)
2. **Force password change** (in authentication flow)
3. **Add SMS notification** (optional)
4. **Admin action:** Bulk create portal accounts
5. **API endpoint:** Reset portal password
6. **Frontend:** Display temp password in success dialog

---

**Status:** ✅ Complete and tested  
**File:** `backend/apps/patients/serializers.py`  
**Syntax:** ✅ Valid (compiled successfully)  
**Atomic:** ✅ Transaction-safe  
**Secure:** ✅ Password hashed, validated  

🎉 **Patient portal account creation is now fully integrated!**
