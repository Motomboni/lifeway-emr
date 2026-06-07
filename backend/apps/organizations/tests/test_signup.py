"""Tests for self-serve organization signup (ENABLE_ORG_SIGNUP)."""

import pytest
from django.test import override_settings
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
@override_settings(ENABLE_ORG_SIGNUP=True)
def test_signup_creates_org_owner_and_subscription(api_client):
    from apps.organizations.models import Plan

    Plan.objects.get_or_create(
        slug="starter",
        defaults={"name": "Starter", "price_monthly": 0, "max_users": 10, "max_patients": 500},
    )

    slug = "pytest-clinic-signup"
    payload = {
        "name": "Pytest Clinic",
        "slug": slug,
        "username": "pytest_owner_signup",
        "password": "securepass123",
        "first_name": "Py",
        "last_name": "Test",
    }
    response = api_client.post("/api/v1/organizations/signup/", payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["organization"]["slug"] == slug
    assert data["user"]["username"] == payload["username"]
    assert "message" in data

    from apps.organizations.models import Organization, OrganizationUser, Subscription

    org = Organization.objects.get(slug=slug)
    assert org.is_active
    membership = OrganizationUser.objects.get(organization=org, user__username=payload["username"])
    assert membership.role == "OWNER"
    assert membership.is_default
    assert Subscription.objects.filter(organization=org).exists()


@pytest.mark.django_db
@override_settings(ENABLE_ORG_SIGNUP=False)
def test_signup_disabled_returns_403(api_client):
    response = api_client.post(
        "/api/v1/organizations/signup/",
        {
            "name": "Blocked Clinic",
            "slug": "blocked-clinic-signup",
            "username": "blocked_owner",
            "password": "securepass123",
            "first_name": "No",
            "last_name": "Signup",
        },
        format="json",
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Organization signup is not enabled."
