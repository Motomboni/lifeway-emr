"""Tests for NHIA scribe billing, claim pack, and compliance."""

import pytest
from decimal import Decimal

from apps.billing.claim_pack_service import build_visit_claim_pack, claim_pack_to_csv
from apps.billing.models import VisitCharge
from apps.billing.nhia_charge_service import add_nhia_charges_from_scribe
from apps.billing.nhia_compliance_service import get_nhia_compliance_summary
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


@pytest.fixture
def patient_with_nhid(patient):
    patient.national_health_id = "12345678901"
    patient.id_verified = True
    patient.save(update_fields=["national_health_id", "id_verified"])
    return patient


class TestNHIAScribeCharges:
    def test_add_matched_codes_creates_misc_charges(
        self, open_visit_without_payment, malaria_tariff
    ):
        visit = open_visit_without_payment
        result = add_nhia_charges_from_scribe(
            visit,
            [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}],
        )
        assert result["created_count"] == 1
        charge = VisitCharge.objects.get(visit=visit)
        assert "NHIA:3-01-01" in charge.description
        assert charge.amount == Decimal(str(malaria_tariff.amount_ngn))

    def test_skips_duplicate_nhia_code(self, open_visit_without_payment, malaria_tariff):
        visit = open_visit_without_payment
        codes = [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}]
        add_nhia_charges_from_scribe(visit, codes)
        result = add_nhia_charges_from_scribe(visit, codes)
        assert result["created_count"] == 0
        assert result["skipped_count"] == 1


class TestClaimPack:
    def test_build_visit_claim_pack_from_charges(
        self, open_visit_without_payment, patient_with_nhid, malaria_tariff
    ):
        visit = open_visit_without_payment
        add_nhia_charges_from_scribe(
            visit,
            [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}],
        )
        pack = build_visit_claim_pack(visit)
        assert pack["line_count"] == 1
        assert pack["claim_ready"] is True
        assert pack["line_items"][0]["nhia_code"] == "3-01-01"

    def test_claim_pack_csv_has_header(self, open_visit_without_payment, malaria_tariff):
        visit = open_visit_without_payment
        add_nhia_charges_from_scribe(
            visit,
            [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}],
        )
        pack = build_visit_claim_pack(visit)
        csv_text = claim_pack_to_csv([pack])
        assert "nhia_code" in csv_text.splitlines()[0]
        assert "3-01-01" in csv_text


class TestNHIACompliance:
    def test_compliance_summary_counts_claim_ready(
        self, open_visit_without_payment, patient_with_nhid, malaria_tariff
    ):
        visit = open_visit_without_payment
        add_nhia_charges_from_scribe(
            visit,
            [{"nhia": "3-01-01", "icd11": "1F44", "diagnosis": "Malaria"}],
        )
        summary = get_nhia_compliance_summary()
        assert summary["visit_count"] >= 1
        assert summary["claim_ready_count"] >= 1
