"""
Pytest fixtures for EMR test suite.

Fixtures provide:
- User factories with different roles
- Visit factories with different states
- Authentication tokens
- Patient factories
"""

import pytest
from rest_framework.test import APIClient


def build_api_client(test_org, user=None, token=None, organization=None):
    """Authenticated APIClient with tenant header (SaaS)."""
    org = organization if organization is not None else test_org
    client = APIClient()
    creds = {}
    if token:
        creds["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    if org is not None:
        creds["HTTP_X_ORGANIZATION_ID"] = str(org.id)
    if user is not None:
        client.force_authenticate(user=user)
    if creds:
        client.credentials(**creds)
    return client


def _get_or_create_test_org():
    from apps.organizations.models import Organization, Plan, Subscription

    org, _ = Organization.objects.get_or_create(
        slug="test-clinic",
        defaults={"name": "Test Clinic"},
    )
    plan, _ = Plan.objects.get_or_create(
        slug="starter",
        defaults={"name": "Starter", "price_monthly": 0, "max_users": 100, "max_patients": 1000},
    )
    Subscription.objects.get_or_create(
        organization=org,
        defaults={"plan": plan, "status": "ACTIVE"},
    )
    return org


def _ensure_user_org(user):
    org = _get_or_create_test_org()
    from apps.organizations.models import OrganizationUser

    OrganizationUser.objects.get_or_create(
        organization=org,
        user=user,
        defaults={"role": user.role, "is_default": True},
    )
    return org


@pytest.fixture
def test_org(db):
    return _get_or_create_test_org()


@pytest.fixture
def api_client(test_org):
    """Factory fixture: api_client(user=...) or api_client(token=...)."""

    def _make(user=None, token=None, organization=None):
        return build_api_client(
            test_org, user=user, token=token, organization=organization
        )

    return _make


@pytest.fixture
def patient(db, test_org):
    """Create a patient for testing."""
    from apps.patients.models import Patient

    return Patient.objects.create(
        first_name="Test",
        last_name="Patient",
        patient_id="TEST001",
        is_active=True,
        organization=test_org,
    )


@pytest.fixture
def patient_with_user(patient):
    """Create a patient with linked user account (unverified)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User(
        username="patient_user",
        email="patient@test.com",
        first_name="Test",
        last_name="Patient",
        role="PATIENT",
    )
    user.set_password("testpass123")
    user.save()
    _ensure_user_org(user)

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
def doctor_user(db):
    """Create a doctor user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User(username="doctor", email="doctor@test.com", role="DOCTOR")
    user.set_password("testpass123")
    user.save()
    _ensure_user_org(user)
    return user


@pytest.fixture
def receptionist_user(db):
    """Create a receptionist user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User(
        username="receptionist", email="receptionist@test.com", role="RECEPTIONIST"
    )
    user.set_password("testpass123")
    user.save()
    _ensure_user_org(user)
    return user


@pytest.fixture
def lab_tech_user(db):
    """Create a lab tech user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User(username="labtech", email="labtech@test.com", role="LAB_TECH")
    user.set_password("testpass123")
    user.save()
    _ensure_user_org(user)
    return user


@pytest.fixture
def pharmacist_user(db):
    """Create a pharmacist user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User(username="pharmacist", email="pharmacist@test.com", role="PHARMACIST")
    user.set_password("testpass123")
    user.save()
    _ensure_user_org(user)
    return user


@pytest.fixture
def nurse_user(db):
    """Create a nurse user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User(username="nurse", email="nurse@test.com", role="NURSE")
    user.set_password("testpass123")
    user.save()
    _ensure_user_org(user)
    return user


def _visit_kwargs(patient, **extra):
    kwargs = {
        "patient": patient,
        "organization": getattr(patient, "organization", None),
        "status": "OPEN",
        **extra,
    }
    return kwargs


@pytest.fixture
def open_visit_with_payment(patient):
    """Create an OPEN visit with payment cleared (PAID)."""
    from apps.visits.models import Visit

    return Visit.objects.create(**_visit_kwargs(patient, payment_status="PAID"))


@pytest.fixture
def open_visit_without_payment(patient):
    """Create an OPEN visit with payment unpaid."""
    from apps.visits.models import Visit

    return Visit.objects.create(**_visit_kwargs(patient, payment_status="UNPAID"))


@pytest.fixture
def closed_visit_with_payment(patient, doctor_user):
    """Create a CLOSED visit with payment PAID and consultation."""
    from django.utils import timezone

    from apps.consultations.models import Consultation
    from apps.visits.models import Visit

    visit = Visit.objects.create(**_visit_kwargs(patient, payment_status="PAID"))

    Consultation.objects.create(
        visit=visit,
        created_by=doctor_user,
        history="Test history",
        examination="Test examination",
        diagnosis="Test diagnosis",
        clinical_notes="Test notes",
    )

    visit.status = "CLOSED"
    visit.closed_by = doctor_user
    visit.closed_at = timezone.now()
    visit.save()

    return visit


@pytest.fixture
def visit(open_visit_with_payment):
    """Default visit fixture - OPEN with payment PAID."""
    return open_visit_with_payment


@pytest.fixture
def open_visit(open_visit_with_payment):
    """Alias used by billing/security tests."""
    return open_visit_with_payment


@pytest.fixture
def unpaid_visit(open_visit_without_payment):
    """Unpaid visit fixture - OPEN with payment UNPAID."""
    return open_visit_without_payment


@pytest.fixture
def patient_token(patient_with_user):
    """Get JWT authentication token for patient portal user."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(patient_with_user.user)
    return str(refresh.access_token)


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
def expired_token(test_org):
    """Create an expired JWT token for testing."""
    from datetime import timedelta

    import jwt
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from rest_framework_simplejwt.tokens import RefreshToken

    User = get_user_model()
    user = User(username="expired_user", email="expired@test.com", role="DOCTOR")
    user.set_password("testpass123")
    user.save()
    _ensure_user_org(user)

    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token

    from rest_framework_simplejwt.settings import api_settings

    token = jwt.encode(
        {
            "token_type": "access",
            "exp": int((timezone.now() - timedelta(days=1)).timestamp()),
            "iat": int((timezone.now() - timedelta(days=2)).timestamp()),
            "jti": str(access_token.get("jti", "")),
            "user_id": user.id,
        },
        api_settings.SIGNING_KEY,
        algorithm=api_settings.ALGORITHM,
    )

    return token


@pytest.fixture
def consultation(open_visit_with_payment, doctor_user):
    """Create a consultation for testing."""
    from apps.consultations.models import Consultation

    return Consultation.objects.create(
        visit=open_visit_with_payment,
        created_by=doctor_user,
        history="Test history",
        examination="Test examination",
        diagnosis="Test diagnosis",
        clinical_notes="Test notes",
    )
