"""Tests for admin telemedicine pricing endpoint."""

import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.billing.service_catalog_models import ServiceCatalog
from apps.telemedicine.pricing import get_telemedicine_service_code


@pytest.mark.django_db
def test_admin_can_get_and_set_telemedicine_pricing(doctor_user):
    User = get_user_model()
    admin = User(username="admin_pricing", email="admin_pricing@test.com", role="ADMIN")
    admin.set_password("testpass123")
    admin.save()
    # Attach same org helper used by role fixtures
    from tests.conftest import _ensure_user_org

    _ensure_user_org(admin)

    client = APIClient()
    client.force_authenticate(user=admin)

    get_resp = client.get("/api/v1/telemedicine/pricing/")
    assert get_resp.status_code == status.HTTP_200_OK
    body = get_resp.json()
    assert body["configured"] is True
    assert body["can_edit"] is True
    assert body["service_code"] == get_telemedicine_service_code()

    put_resp = client.put(
        "/api/v1/telemedicine/pricing/",
        {"amount": "7500.00", "name": "Virtual Clinic Fee", "is_active": True},
        format="json",
    )
    assert put_resp.status_code == status.HTTP_200_OK
    assert put_resp.json()["amount"] == "7500.00"
    assert put_resp.json()["name"] == "Virtual Clinic Fee"

    svc = ServiceCatalog.objects.get(service_code=get_telemedicine_service_code())
    assert svc.amount == Decimal("7500.00")
    assert svc.name == "Virtual Clinic Fee"

    client.force_authenticate(user=doctor_user)
    doc_get = client.get("/api/v1/telemedicine/pricing/")
    assert doc_get.status_code == status.HTTP_200_OK
    assert doc_get.json()["amount"] == "7500.00"
    assert doc_get.json().get("can_edit") is False

    doc_put = client.put(
        "/api/v1/telemedicine/pricing/",
        {"amount": "100.00"},
        format="json",
    )
    assert doc_put.status_code == status.HTTP_403_FORBIDDEN
