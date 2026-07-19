# Patient Portal Implementation Guide

## Overview
The EMR system now supports optional patient portal accounts, allowing patients to:
- View their medical records
- Check lab results
- View prescriptions
- Book appointments
- Access radiology reports

## Database Changes

### 1. User Model Updates (`apps/users/models.py`)

**Added Field:**
```python
patient = models.OneToOneField(
    'patients.Patient',
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name='portal_user',
    help_text="Linked patient record (only for PATIENT role users)"
)
```

**Validation Added:**
- PATIENT role users MUST be linked to a patient record
- Non-PATIENT users CANNOT be linked to a patient record
- Enforces one-to-one relationship integrity

### 2. Patient Model Updates (`apps/patients/models.py`)

**Added Field:**
```python
portal_enabled = models.BooleanField(
    default=False,
    help_text="Whether patient portal access is enabled for this patient"
)
```

**Existing Related Fields:**
- `is_verified`: Whether patient account is verified by receptionist
- `verified_by`: Receptionist who verified the account
- `verified_at`: Timestamp of verification
- `user`: OneToOneField to User (already exists, inverse of User.patient)

## Migration Commands

### Generate Migrations
```bash
cd backend

# Generate migration for users app
python manage.py makemigrations users

# Generate migration for patients app
python manage.py makemigrations patients

# Apply all migrations
python manage.py migrate
```

### Expected Migration Output

**For users app:**
```
Migrations for 'users':
  apps/users/migrations/000X_add_patient_portal_link.py
    - Add field patient to user
```

**For patients app:**
```
Migrations for 'patients':
  apps/patients/migrations/000X_add_portal_enabled.py
    - Add field portal_enabled to patient
```

## Database Schema

### User Table (Extended)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254),
    password VARCHAR(128) NOT NULL,
    first_name VARCHAR(150),
    last_name VARCHAR(150),
    role VARCHAR(50) NOT NULL,
    patient_id INTEGER UNIQUE NULL,  -- New field
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_staff BOOLEAN NOT NULL DEFAULT FALSE,
    is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
    date_joined TIMESTAMP NOT NULL,
    last_login TIMESTAMP NULL,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP NULL,
    last_login_attempt TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);
```

### Patient Table (Extended)
```sql
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    middle_name VARCHAR(255) NULL,
    date_of_birth DATE NULL,
    gender VARCHAR(20) NULL,
    phone VARCHAR(20) NULL,
    email VARCHAR(254) NULL,
    address TEXT NULL,
    national_id VARCHAR(50) UNIQUE NULL,
    patient_id VARCHAR(50) UNIQUE NOT NULL,
    portal_enabled BOOLEAN NOT NULL DEFAULT FALSE,  -- New field
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_by_id INTEGER NULL,
    verified_at TIMESTAMP NULL,
    user_id INTEGER UNIQUE NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (verified_by_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
```

## Relationships

### One-to-One Constraint Enforcement

**From User side:**
```python
user.patient  # Access linked patient (or None)
```

**From Patient side:**
```python
patient.portal_user  # Access linked user (or None)
patient.user  # Legacy field (kept for backward compatibility)
```

### Validation Rules

1. **Creating a PATIENT user:**
   ```python
   # Must provide patient link
   user = User.objects.create_user(
       username='patient123',
       password='securepass',
       role='PATIENT',
       patient=patient_instance
   )
   ```

2. **Enabling portal for existing patient:**
   ```python
   patient.portal_enabled = True
   patient.save()
   
   # Then create user account
   user = User.objects.create_user(
       username=patient.email,
       password='temporary_password',
       role='PATIENT',
       patient=patient
   )
   ```

3. **Validation will fail if:**
   - PATIENT role without patient link
   - Non-PATIENT role with patient link
   - Attempting to link patient to multiple users
   - Attempting to link user to multiple patients

## API Implementation

### Create Patient Portal Account

**Endpoint:** `POST /api/v1/patients/{id}/create-portal-account/`

**Request:**
```json
{
  "username": "john.doe@email.com",
  "password": "SecurePass123!",
  "send_email": true
}
```

**Response:**
```json
{
  "id": 123,
  "username": "john.doe@email.com",
  "patient": 456,
  "role": "PATIENT",
  "is_active": true,
  "date_joined": "2026-02-06T16:00:00Z"
}
```

### Enable/Disable Portal Access

**Endpoint:** `PATCH /api/v1/patients/{id}/`

**Request:**
```json
{
  "portal_enabled": true
}
```

## Security Considerations

### 1. Account Creation Flow
1. Receptionist verifies patient identity (`is_verified = True`)
2. Receptionist enables portal (`portal_enabled = True`)
3. System generates portal account with temporary password
4. Patient receives email/SMS with login credentials
5. Patient forced to change password on first login

### 2. Access Control
- PATIENT users can only access their own data
- Middleware enforces patient-scoped queries
- All API responses filtered by patient_id
- Audit logging for all patient portal access

### 3. Password Requirements
- Minimum 12 characters
- Must include uppercase, lowercase, number, special char
- Cannot be similar to username or patient name
- Expires every 90 days (configurable)

### 4. Session Management
- JWT tokens with 1-hour expiry
- Refresh tokens valid for 7 days
- IP address logging
- Device tracking
- Automatic logout after 15 minutes of inactivity

## Testing

### Unit Tests

```python
# tests/test_patient_portal.py

def test_create_patient_user():
    """Test creating a user with PATIENT role and patient link."""
    patient = Patient.objects.create(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        portal_enabled=True
    )
    
    user = User.objects.create_user(
        username="john.doe",
        password="SecurePass123!",
        role="PATIENT",
        patient=patient
    )
    
    assert user.role == "PATIENT"
    assert user.patient == patient
    assert patient.portal_user == user


def test_patient_role_requires_patient_link():
    """Test that PATIENT role requires patient link."""
    with pytest.raises(ValidationError):
        user = User.objects.create_user(
            username="test",
            password="pass",
            role="PATIENT",
            patient=None  # Should fail
        )


def test_non_patient_role_cannot_link_patient():
    """Test that non-PATIENT roles cannot link to patient."""
    patient = Patient.objects.create(first_name="John", last_name="Doe")
    
    with pytest.raises(ValidationError):
        user = User.objects.create_user(
            username="doctor",
            password="pass",
            role="DOCTOR",
            patient=patient  # Should fail
        )


def test_one_to_one_constraint():
    """Test that one patient can only have one portal user."""
    patient = Patient.objects.create(first_name="John", last_name="Doe")
    
    user1 = User.objects.create_user(
        username="user1",
        password="pass",
        role="PATIENT",
        patient=patient
    )
    
    # Attempting to create second user for same patient should fail
    with pytest.raises(Exception):
        user2 = User.objects.create_user(
            username="user2",
            password="pass",
            role="PATIENT",
            patient=patient
        )
```

### Integration Tests

```bash
# Run all patient portal tests
python manage.py test apps.patients.tests.test_portal

# Run specific test
python manage.py test apps.patients.tests.test_portal.PatientPortalTestCase.test_login_flow
```

## Admin Panel

### Patient Portal Management

**Django Admin Actions:**
1. Enable portal for selected patients
2. Disable portal for selected patients
3. Send password reset email
4. View portal activity logs

**Custom Admin Page:**
```python
# apps/patients/admin.py

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'full_name', 'portal_enabled', 'is_verified', 'has_portal_user']
    list_filter = ['portal_enabled', 'is_verified', 'is_active']
    search_fields = ['first_name', 'last_name', 'email', 'patient_id']
    
    actions = ['enable_portal', 'disable_portal', 'create_portal_accounts']
    
    def has_portal_user(self, obj):
        return hasattr(obj, 'portal_user') and obj.portal_user is not None
    has_portal_user.boolean = True
    has_portal_user.short_description = 'Portal Account'
```

## Frontend Implementation

### Patient Portal Pages

1. **Login Page:** `/patient-portal/login`
2. **Dashboard:** `/patient-portal/dashboard`
3. **Medical Records:** `/patient-portal/records`
4. **Lab Results:** `/patient-portal/lab-results`
5. **Prescriptions:** `/patient-portal/prescriptions`
6. **Appointments:** `/patient-portal/appointments`
7. **Radiology Results:** `/patient-portal/radiology`

### Receptionist Portal Management

**Location:** `/patients/{id}/portal`

**Features:**
- Enable/disable portal access
- Create portal account
- Reset password
- View login history
- Revoke access

## Data Migration

### Migrating Existing Patients

If you have existing patients who need portal access:

```python
# scripts/enable_portal_for_existing_patients.py

from apps.patients.models import Patient
from apps.users.models import User
from django.db import transaction

def create_portal_accounts_bulk():
    """Create portal accounts for verified patients without accounts."""
    
    patients = Patient.objects.filter(
        is_verified=True,
        portal_enabled=False,
        portal_user__isnull=True
    )
    
    for patient in patients:
        with transaction.atomic():
            # Enable portal
            patient.portal_enabled = True
            patient.save()
            
            # Create user account
            username = patient.email or f"patient_{patient.patient_id}"
            
            user = User.objects.create_user(
                username=username,
                email=patient.email,
                password=User.objects.make_random_password(length=12),
                role='PATIENT',
                patient=patient,
                first_name=patient.first_name,
                last_name=patient.last_name
            )
            
            # Send welcome email
            send_portal_welcome_email(patient, user)
            
            print(f"Created portal account for {patient.get_full_name()}")
```

## Troubleshooting

### Common Issues

**Issue:** "PATIENT role users must be linked to a patient record"
```python
# Solution: Always provide patient link for PATIENT role
user.patient = patient_instance
user.save()
```

**Issue:** "Only PATIENT role users can be linked to a patient record"
```python
# Solution: Remove patient link for non-PATIENT users
user.patient = None
user.save()
```

**Issue:** Duplicate key error when creating portal account
```python
# Check if patient already has a portal user
if hasattr(patient, 'portal_user'):
    print(f"Patient already has portal user: {patient.portal_user}")
```

## Next Steps

1. **Run migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. **Create test patient portal account:**
   ```bash
   python manage.py shell
   ```
   ```python
   from apps.patients.models import Patient
   from apps.users.models import User
   
   # Get or create test patient
   patient = Patient.objects.first()
   patient.portal_enabled = True
   patient.save()
   
   # Create portal user
   user = User.objects.create_user(
       username='testpatient',
       password='TestPass123!',
       role='PATIENT',
       patient=patient
   )
   print(f"Created portal user: {user.username}")
   ```

3. **Test login:**
   - Frontend: http://localhost:3000/patient-portal/login
   - Credentials: testpatient / TestPass123!

4. **Implement API endpoints** (see API Implementation section)

5. **Add frontend components** for patient portal

6. **Configure email/SMS** for password delivery

7. **Set up monitoring** for portal access logs

## Support

For issues or questions:
- Check validation errors in Django admin
- Review audit logs for portal access
- Test with patient role user in API documentation
- Verify database constraints are applied correctly
