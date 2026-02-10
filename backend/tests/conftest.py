"""
Pytest fixtures for EMR test suite.

Fixtures provide:
- User factories with different roles
- Visit factories with different states
- Authentication tokens
- Patient factories
"""
import pytest


@pytest.fixture
def patient():
    """Create a patient for testing."""
    from apps.patients.models import Patient
    return Patient.objects.create(
        first_name="Test",
        last_name="Patient",
        patient_id="TEST001",
        is_active=True
    )


@pytest.fixture
def patient_with_user(patient):
    """Create a patient with linked user account (unverified)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User(
        username='patient_user',
        email='patient@test.com',
        first_name='Test',
        last_name='Patient',
        role='PATIENT'
    )
    user.set_password('testpass123')
    user.save()
    
    patient.user = user
    patient.is_verified = False
    patient.save()
    return patient


@pytest.fixture
def verified_patient(patient_with_user, receptionist_user):
    """Create a verified patient."""
    from django.utils import timezone
    patient_with_user.is_verified = True
    patient_with_user.verified_by = receptionist_user
    patient_with_user.verified_at = timezone.now()
    patient_with_user.save()
    return patient_with_user


@pytest.fixture
def doctor_user():
    """Create a doctor user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User(
        username='doctor',
        email='doctor@test.com',
        role='DOCTOR'
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def receptionist_user():
    """Create a receptionist user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User(
        username='receptionist',
        email='receptionist@test.com',
        role='RECEPTIONIST'
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def lab_tech_user():
    """Create a lab tech user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User(
        username='labtech',
        email='labtech@test.com',
        role='LAB_TECH'
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def pharmacist_user():
    """Create a pharmacist user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User(
        username='pharmacist',
        email='pharmacist@test.com',
        role='PHARMACIST'
    )
    user.set_password('testpass123')
    user.save()
    return user


@pytest.fixture
def open_visit_with_payment(patient):
    """Create an OPEN visit with payment CLEARED."""
    from apps.visits.models import Visit
    return Visit.objects.create(
        patient=patient,
        status='OPEN',
        payment_status='CLEARED'
    )


@pytest.fixture
def open_visit_without_payment(patient):
    """Create an OPEN visit with payment PENDING."""
    from apps.visits.models import Visit
    return Visit.objects.create(
        patient=patient,
        status='OPEN',
        payment_status='PENDING'
    )


@pytest.fixture
def closed_visit_with_payment(patient, doctor_user):
    """Create a CLOSED visit with payment CLEARED and consultation."""
    from django.utils import timezone
    from apps.consultations.models import Consultation
    from apps.visits.models import Visit
    
    # Create open visit first
    visit = Visit.objects.create(
        patient=patient,
        status='OPEN',
        payment_status='CLEARED'
    )
    
    # Create consultation
    Consultation.objects.create(
        visit=visit,
        created_by=doctor_user,
        history='Test history',
        examination='Test examination',
        diagnosis='Test diagnosis',
        clinical_notes='Test notes'
    )
    
    # Close the visit
    visit.status = 'CLOSED'
    visit.closed_by = doctor_user
    visit.closed_at = timezone.now()
    visit.save()
    
    return visit


@pytest.fixture
def visit(open_visit_with_payment):
    """Default visit fixture - OPEN with payment CLEARED."""
    return open_visit_with_payment


@pytest.fixture
def unpaid_visit(open_visit_without_payment):
    """Unpaid visit fixture - OPEN with payment PENDING."""
    return open_visit_without_payment


@pytest.fixture
def doctor_token(doctor_user):
    """Get JWT authentication token for doctor user."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(doctor_user)
    return str(refresh.access_token)


@pytest.fixture
def receptionist_token(receptionist_user):
    """Get JWT authentication token for receptionist user."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(receptionist_user)
    return str(refresh.access_token)


@pytest.fixture
def lab_tech_token(lab_tech_user):
    """Get JWT authentication token for lab tech user."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(lab_tech_user)
    return str(refresh.access_token)


@pytest.fixture
def pharmacist_token(pharmacist_user):
    """Get JWT authentication token for pharmacist user."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(pharmacist_user)
    return str(refresh.access_token)


@pytest.fixture
def expired_token():
    """Create an expired JWT token for testing."""
    from rest_framework_simplejwt.tokens import RefreshToken
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from datetime import timedelta
    import jwt
    from django.conf import settings
    
    User = get_user_model()
    # Create a temporary user for the expired token
    user = User(
        username='expired_user',
        email='expired@test.com',
        role='DOCTOR'
    )
    user.set_password('testpass123')
    user.save()
    
    # Create a token and manually expire it
    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token
    
    # Manually set expiration to past
    from rest_framework_simplejwt.settings import api_settings
    token = jwt.encode(
        {
            'token_type': 'access',
            'exp': int((timezone.now() - timedelta(days=1)).timestamp()),
            'iat': int((timezone.now() - timedelta(days=2)).timestamp()),
            'jti': str(access_token.get('jti', '')),
            'user_id': user.id,
        },
        api_settings.SIGNING_KEY,
        algorithm=api_settings.ALGORITHM
    )
    
    return token


@pytest.fixture
def consultation(open_visit_with_payment, doctor_user):
    """Create a consultation for testing."""
    from apps.consultations.models import Consultation
    return Consultation.objects.create(
        visit=open_visit_with_payment,
        created_by=doctor_user,
        history='Test history',
        examination='Test examination',
        diagnosis='Test diagnosis',
        clinical_notes='Test notes'
    )
