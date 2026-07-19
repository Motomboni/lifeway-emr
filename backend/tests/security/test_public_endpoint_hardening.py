"""
Security tests for public registration, API docs, and health endpoints.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def admin_token(db):
    from rest_framework_simplejwt.tokens import RefreshToken

    user = User.objects.create_user(
        username="adminuser",
        email="admin@test.com",
        password="testpass123!",
        role="ADMIN",
        is_staff=True,
    )
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


@pytest.mark.django_db
class TestPublicRegistrationHardening:
    @override_settings(
        DEBUG=False,
        PUBLIC_REGISTRATION_ENABLED=True,
        PUBLIC_REGISTRATION_ALLOWED_ROLES=["PATIENT"],
    )
    def test_patient_registration_allowed_in_production_mode(self):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/register/",
            {
                "username": "patient_prod",
                "email": "patient_prod@test.com",
                "password": "Testpass123!",
                "password_confirm": "Testpass123!",
                "first_name": "Pat",
                "last_name": "Prod",
                "role": "PATIENT",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    @override_settings(
        DEBUG=False,
        PUBLIC_REGISTRATION_ENABLED=True,
        PUBLIC_REGISTRATION_ALLOWED_ROLES=["PATIENT"],
    )
    def test_staff_registration_blocked_in_production_mode(self):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/register/",
            {
                "username": "doctor_prod",
                "email": "doctor_prod@test.com",
                "password": "Testpass123!",
                "password_confirm": "Testpass123!",
                "first_name": "Doc",
                "last_name": "Prod",
                "role": "DOCTOR",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "role" in response.data

    @override_settings(
        DEBUG=False,
        PUBLIC_REGISTRATION_ENABLED=True,
        PUBLIC_REGISTRATION_ALLOWED_ROLES=["PATIENT"],
    )
    def test_admin_registration_always_blocked(self):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/register/",
            {
                "username": "admin_prod",
                "email": "admin_prod@test.com",
                "password": "Testpass123!",
                "password_confirm": "Testpass123!",
                "first_name": "Admin",
                "last_name": "Prod",
                "role": "ADMIN",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "role" in response.data

    @override_settings(DEBUG=False, PUBLIC_REGISTRATION_ENABLED=False)
    def test_registration_disabled_returns_403(self):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/register/",
            {
                "username": "blocked_patient",
                "email": "blocked_patient@test.com",
                "password": "Testpass123!",
                "password_confirm": "Testpass123!",
                "first_name": "Blocked",
                "last_name": "Patient",
                "role": "PATIENT",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestApiDocsHardening:
    @override_settings(DEBUG=False, API_DOCS_ENABLED=False)
    def test_api_docs_disabled_setting(self):
        from django.conf import settings

        assert settings.API_DOCS_ENABLED is False

    @override_settings(DEBUG=False, API_DOCS_ENABLED=True)
    def test_api_docs_require_admin_when_enabled(self):
        client = APIClient()
        response = client.get("/api/docs/")
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @override_settings(DEBUG=False, API_DOCS_ENABLED=True)
    def test_api_docs_accessible_to_admin(self, admin_token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        response = client.get("/api/docs/")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestHealthEndpointHardening:
    @override_settings(DEBUG=False, HEALTH_DETAILED_PUBLIC=False)
    def test_basic_health_stays_public(self):
        client = APIClient()
        response = client.get("/api/v1/health/")
        assert response.status_code == status.HTTP_200_OK

    @override_settings(DEBUG=False, HEALTH_DETAILED_PUBLIC=False)
    def test_detailed_health_requires_auth_in_production(self):
        client = APIClient()
        response = client.get("/api/v1/health/detailed/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @override_settings(DEBUG=False, HEALTH_DETAILED_PUBLIC=False)
    def test_health_info_requires_auth_in_production(self):
        client = APIClient()
        response = client.get("/api/v1/health/info/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @override_settings(DEBUG=False, HEALTH_DETAILED_PUBLIC=False)
    def test_detailed_health_available_to_admin(self, admin_token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        response = client.get("/api/v1/health/detailed/")
        assert response.status_code == status.HTTP_200_OK

    @override_settings(DEBUG=False, HEALTH_DETAILED_PUBLIC=False)
    def test_health_info_hides_debug_fields_in_production(self, admin_token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        response = client.get("/api/v1/health/info/")
        assert response.status_code == status.HTTP_200_OK
        assert "debug" not in response.data
        assert "allowed_hosts" not in response.data
