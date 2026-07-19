"""Tests for NHIA portal client and lifecycle submit."""

import pytest
from decimal import Decimal
from unittest.mock import patch

from apps.billing.claim_pack_service import build_visit_claim_pack
from apps.billing.nhia_claim_lifecycle_service import mark_submitted
from apps.billing.nhia_claim_submission_models import NHIAClaimSubmission
from apps.billing.nhia_portal_client import NHIAPortalSubmitError, submit_claim_to_portal
from apps.billing.nhia_charge_service import add_nhia_charges_from_scribe
from apps.billing.nhia_tariff_models import NHIATariff
from apps.integrations.models import ExternalHealthHub


@pytest.fixture
def nhia_submission(open_visit_without_payment, doctor_user, malaria_tariff):
    visit = open_visit_without_payment
    patient = visit.patient
    patient.national_health_id = "12345678901"
    patient.id_verified = True
    patient.save(update_fields=["national_health_id", "id_verified"])

    add_nhia_charges_from_scribe(
        visit,
        [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}],
    )
    pack = build_visit_claim_pack(visit)
    sub = NHIAClaimSubmission.objects.create(
        visit=visit,
        organization=visit.organization,
        status="EXPORTED",
        claim_reference="NHIA-TEST-001",
        claim_pack_snapshot=pack,
        line_count=len(pack.get("lines") or pack.get("line_items") or []),
        total_amount_ngn=pack.get("total_amount_ngn") or "1200.00",
        created_by=doctor_user,
    )
    return sub


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


@pytest.fixture
def patient_with_nhid(patient):
    patient.national_health_id = "12345678901"
    patient.id_verified = True
    patient.save(update_fields=["national_health_id", "id_verified"])
    return patient


@pytest.mark.django_db
class TestNHIAPortalClient:
    def test_local_mode_when_hub_disabled(self, nhia_submission):
        ExternalHealthHub.objects.filter(hub_type="NHIA_PORTAL").delete()
        result = submit_claim_to_portal(nhia_submission)
        assert result.success is True
        assert result.mode == "local"
        assert result.portal_reference.startswith("LOCAL-")

    def test_mark_submitted_sets_portal_reference(self, nhia_submission, doctor_user):
        from apps.billing.nhia_claim_lifecycle_service import mark_submitted

        ExternalHealthHub.objects.filter(hub_type="NHIA_PORTAL").delete()
        updated = mark_submitted(nhia_submission, user=doctor_user)
        assert updated.status == "SUBMITTED"
        assert updated.nhia_portal_reference.startswith("LOCAL-")

    def test_enabled_hub_without_http_flag_stays_local(self, nhia_submission):
        ExternalHealthHub.objects.update_or_create(
            hub_type="NHIA_PORTAL",
            defaults={
                "is_enabled": True,
                "base_url": "https://portal.nhia.example",
            },
        )
        result = submit_claim_to_portal(nhia_submission)
        assert result.mode == "local"
        assert result.portal_reference.startswith("LOCAL-")

    @patch("apps.billing.nhia_portal_client.requests.post")
    def test_http_mode_submits_to_portal(self, mock_post, nhia_submission):
        ExternalHealthHub.objects.update_or_create(
            hub_type="NHIA_PORTAL",
            defaults={
                "is_enabled": True,
                "base_url": "https://portal.nhia.example",
                "api_key_env": "NHIA_PORTAL_API_KEY",
                "config": {"allow_http_submission": True},
            },
        )
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "portal_reference": "NHIA-PORTAL-999",
            "message": "Accepted",
        }

        result = submit_claim_to_portal(nhia_submission)
        assert result.mode == "http"
        assert result.portal_reference == "NHIA-PORTAL-999"
        mock_post.assert_called_once()

    @patch("apps.billing.nhia_portal_client.requests.post")
    def test_http_failure_raises(self, mock_post, nhia_submission):
        ExternalHealthHub.objects.update_or_create(
            hub_type="NHIA_PORTAL",
            defaults={
                "is_enabled": True,
                "base_url": "https://portal.nhia.example",
                "config": {"allow_http_submission": True},
            },
        )
        mock_post.return_value.status_code = 503
        mock_post.return_value.text = "Unavailable"

        with pytest.raises(NHIAPortalSubmitError):
            submit_claim_to_portal(nhia_submission)
