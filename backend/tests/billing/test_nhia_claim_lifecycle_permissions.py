"""Tests for NHIA claim lifecycle API permissions."""

import pytest
from rest_framework import status

from apps.billing.nhia_charge_service import add_nhia_charges_from_scribe
from apps.billing.nhia_tariff_models import NHIATariff


@pytest.fixture
def malaria_tariff(db):
    return NHIATariff.objects.create(
        nhia_code="3-01-01",
        name="Treatment of Uncomplicated Malaria (Adult)",
        category="DRUG",
        amount_ngn="1200.00",
        icd11_codes=["1F44"],
        is_active=True,
    )


@pytest.mark.django_db
class TestNHIAClaimLifecyclePermissions:
    def test_receptionist_can_get_visit_claim(
        self, api_client, receptionist_user, open_visit_without_payment, malaria_tariff
    ):
        visit = open_visit_without_payment
        add_nhia_charges_from_scribe(
            visit,
            [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}],
        )
        client = api_client(user=receptionist_user)
        response = client.get(f"/api/v1/billing/visits/{visit.id}/nhia-claim/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["visit_id"] == visit.id

    def test_receptionist_can_validate_claim(
        self, api_client, receptionist_user, open_visit_without_payment, malaria_tariff
    ):
        visit = open_visit_without_payment
        add_nhia_charges_from_scribe(
            visit,
            [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}],
        )
        client = api_client(user=receptionist_user)
        response = client.post(
            f"/api/v1/billing/visits/{visit.id}/nhia-claim/",
            {"action": "validate"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] in ("DRAFT", "VALIDATED")

    def test_receptionist_can_list_claims(
        self, api_client, receptionist_user, open_visit_without_payment, malaria_tariff
    ):
        visit = open_visit_without_payment
        add_nhia_charges_from_scribe(
            visit,
            [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}],
        )
        client = api_client(user=receptionist_user)
        response = client.get("/api/v1/billing/nhia-claims/")
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)

    def test_receptionist_can_export_visit_claim_pack(
        self, api_client, receptionist_user, open_visit_without_payment, malaria_tariff
    ):
        visit = open_visit_without_payment
        add_nhia_charges_from_scribe(
            visit,
            [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}],
        )
        client = api_client(user=receptionist_user)
        response = client.get(f"/api/v1/visits/{visit.id}/billing/claim-pack/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get("line_count", 0) >= 1
