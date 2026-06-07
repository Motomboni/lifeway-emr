"""
Multi-tenant isolation tests — Org A must not access Org B data.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.organizations.models import Organization, OrganizationUser, Plan, Subscription
from apps.patients.models import Patient
from apps.visits.models import Visit


@pytest.fixture
def starter_plan(db):
    plan, _ = Plan.objects.get_or_create(
        slug="starter",
        defaults={
            "name": "Starter",
            "price_monthly": 0,
            "max_users": 100,
            "max_patients": 1000,
        },
    )
    return plan


@pytest.fixture
def org_a(starter_plan):
    org = Organization.objects.create(name="Clinic A", slug="clinic-a")
    Subscription.objects.get_or_create(
        organization=org,
        defaults={"plan": starter_plan, "status": "ACTIVE"},
    )
    return org


@pytest.fixture
def org_b(starter_plan):
    org = Organization.objects.create(name="Clinic B", slug="clinic-b")
    Subscription.objects.get_or_create(
        organization=org,
        defaults={"plan": starter_plan, "status": "ACTIVE"},
    )
    return org


@pytest.fixture
def receptionist_a(receptionist_user, org_a):
    OrganizationUser.objects.filter(user=receptionist_user).delete()
    OrganizationUser.objects.create(
        organization=org_a, user=receptionist_user, role="RECEPTIONIST", is_default=True
    )
    return receptionist_user


@pytest.fixture
def receptionist_b(db, org_b, starter_plan):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User(username="receptionist_b", email="recb@test.com", role="RECEPTIONIST")
    user.set_password("testpass123")
    user.save()
    OrganizationUser.objects.create(
        organization=org_b, user=user, role="RECEPTIONIST", is_default=True
    )
    return user


@pytest.fixture
def patient_org_a(org_a):
    return Patient.objects.create(
        first_name="Alice",
        last_name="OrgA",
        patient_id="A-001",
        organization=org_a,
    )


@pytest.fixture
def patient_org_b(org_b):
    return Patient.objects.create(
        first_name="Bob",
        last_name="OrgB",
        patient_id="B-001",
        organization=org_b,
    )


@pytest.fixture
def visit_org_b(patient_org_b):
    return Visit.objects.create(
        patient=patient_org_b,
        organization=patient_org_b.organization,
        status="OPEN",
        payment_status="UNPAID",
    )


def _auth_client(user, org):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {token}",
        HTTP_X_ORGANIZATION_ID=str(org.id),
    )
    return client


@pytest.mark.django_db
class TestMultiTenantIsolation:
    def test_org_a_cannot_list_org_b_patients(
        self, receptionist_a, org_a, patient_org_a, patient_org_b
    ):
        client = _auth_client(receptionist_a, org_a)
        response = client.get("/api/v1/patients/")
        assert response.status_code == status.HTTP_200_OK
        ids = {p["id"] for p in response.data.get("results", response.data)}
        assert patient_org_a.id in ids
        assert patient_org_b.id not in ids

    def test_org_a_cannot_retrieve_org_b_patient(
        self, receptionist_a, org_a, patient_org_b
    ):
        client = _auth_client(receptionist_a, org_a)
        response = client.get(f"/api/v1/patients/{patient_org_b.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_org_a_cannot_retrieve_org_b_visit(
        self, receptionist_a, org_a, visit_org_b
    ):
        client = _auth_client(receptionist_a, org_a)
        response = client.get(f"/api/v1/visits/{visit_org_b.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_org_a_cannot_access_org_b_visit_consultation(
        self, receptionist_a, org_a, visit_org_b
    ):
        client = _auth_client(receptionist_a, org_a)
        response = client.get(f"/api/v1/visits/{visit_org_b.id}/consultation/")
        assert response.status_code in (
            status.HTTP_404_NOT_FOUND,
            status.HTTP_403_FORBIDDEN,
        )

    def test_org_a_wallets_exclude_org_b(
        self, receptionist_a, org_a, patient_org_a, patient_org_b
    ):
        from apps.wallet.models import Wallet

        Wallet.objects.get_or_create(patient=patient_org_a)
        Wallet.objects.get_or_create(patient=patient_org_b)

        client = _auth_client(receptionist_a, org_a)
        response = client.get("/api/v1/wallet/wallets/")
        assert response.status_code == status.HTTP_200_OK
        wallets = response.data if isinstance(response.data, list) else response.data.get("results", [])
        patient_ids = {w.get("patient") for w in wallets}
        assert patient_org_a.id in patient_ids
        assert patient_org_b.id not in patient_ids

    def test_api_requires_organization_header_when_no_default(
        self, receptionist_user, org_a, starter_plan
    ):
        """User with membership but no default org must send X-Organization-Id."""
        OrganizationUser.objects.filter(user=receptionist_user).delete()
        OrganizationUser.objects.create(
            organization=org_a, user=receptionist_user, role="RECEPTIONIST", is_default=False
        )

        from rest_framework_simplejwt.tokens import RefreshToken

        client = APIClient()
        token = str(RefreshToken.for_user(receptionist_user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = client.get("/api/v1/patients/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_ORGANIZATION_ID=str(org_a.id),
        )
        response = client.get("/api/v1/patients/")
        assert response.status_code == status.HTTP_200_OK

    def test_visits_require_organization_header_when_no_default(
        self, receptionist_user, org_a, starter_plan
    ):
        """Visit list also requires tenant context when user has no default org."""
        OrganizationUser.objects.filter(user=receptionist_user).delete()
        OrganizationUser.objects.create(
            organization=org_a, user=receptionist_user, role="RECEPTIONIST", is_default=False
        )

        from rest_framework_simplejwt.tokens import RefreshToken

        client = APIClient()
        token = str(RefreshToken.for_user(receptionist_user).access_token)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = client.get("/api/v1/visits/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_ORGANIZATION_ID=str(org_a.id),
        )
        response = client.get("/api/v1/visits/")
        assert response.status_code == status.HTTP_200_OK

    def test_org_a_admin_pending_staff_excludes_org_b(
        self, org_a, org_b, starter_plan
    ):
        """Org A admin must not see inactive staff awaiting approval in Org B."""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        admin_a = User(
            username="admin_a_iso",
            email="admina@iso.test",
            role="ADMIN",
            is_active=True,
        )
        admin_a.set_password("testpass123")
        admin_a.save()
        OrganizationUser.objects.create(
            organization=org_a, user=admin_a, role="ADMIN", is_default=True
        )

        pending_a = User(
            username="pending_a_iso",
            email="pendinga@iso.test",
            role="RECEPTIONIST",
            is_active=False,
        )
        pending_a.set_password("testpass123")
        pending_a.save()
        OrganizationUser.objects.create(
            organization=org_a, user=pending_a, role="RECEPTIONIST"
        )

        pending_b = User(
            username="pending_b_iso",
            email="pendingb@iso.test",
            role="RECEPTIONIST",
            is_active=False,
        )
        pending_b.set_password("testpass123")
        pending_b.save()
        OrganizationUser.objects.create(
            organization=org_b, user=pending_b, role="RECEPTIONIST"
        )

        client = _auth_client(admin_a, org_a)
        response = client.get("/api/v1/auth/pending-staff/")
        assert response.status_code == status.HTTP_200_OK
        usernames = {u["username"] for u in response.data}
        assert "pending_a_iso" in usernames
        assert "pending_b_iso" not in usernames
