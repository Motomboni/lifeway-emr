"""Tests for NHIA tariff validation and scribe note parsing."""

import pytest

from apps.ai_integration.nhia_validation import extract_codes_from_note, validate_scribe_codes
from apps.ai_integration.note_parser import build_icd11_apply_payload, parse_scribe_sections
from apps.billing.nhia_tariff_models import NHIATariff


@pytest.fixture
def nhia_malaria_tariff(db):
    return NHIATariff.objects.create(
        nhia_code="3-01-01",
        name="Treatment of Uncomplicated Malaria (Adult)",
        category="DRUG",
        amount_ngn="1200.00",
        icd11_codes=["1F44", "1F45"],
        keywords="malaria",
        is_active=True,
    )


@pytest.fixture
def nhia_anc_tariff(db):
    return NHIATariff.objects.create(
        nhia_code="4-02-01",
        name="Antenatal Booking",
        category="ANC",
        amount_ngn="4500.00",
        icd11_codes=["QA00.Z"],
        is_active=True,
    )


class TestExtractCodesFromNote:
    def test_bracketed_format(self):
        text = (
            "Assessment: *Acute plasmodium falciparum malaria "
            "[ICD-11: 1F44 / NHIA: 3-01-01]*"
        )
        codes = extract_codes_from_note(text)
        assert len(codes) == 1
        assert codes[0]["icd11"] == "1F44"
        assert codes[0]["nhia"] == "3-01-01"

    def test_deduplicates_pairs(self):
        text = (
            "[ICD-11: 1F44 / NHIA: 3-01-01] and again [ICD-11: 1F44 / NHIA: 3-01-01]"
        )
        assert len(extract_codes_from_note(text)) == 1


class TestValidateScribeCodes:
    def test_matched_malaria(self, nhia_malaria_tariff):
        note = "*Malaria* [ICD-11: 1F44 / NHIA: 3-01-01]"
        result = validate_scribe_codes(note)
        assert result["all_matched"] is True
        assert result["validated_codes"][0]["match_status"] == "matched"
        assert result["validated_codes"][0]["amount_ngn"] == "1200.00"

    def test_unknown_nhia(self, nhia_malaria_tariff):
        note = "[ICD-11: 1F44 / NHIA: 9-99-99]"
        result = validate_scribe_codes(note)
        assert result["all_matched"] is False
        assert "9-99-99" in result["unmatched_nhia"]
        assert result["suggested_tariffs"]

    def test_icd11_mismatch_on_known_nhia(self, nhia_malaria_tariff, nhia_anc_tariff):
        # Malaria ICD-11 on an ANC NHIA code — NHIA valid, ICD-11 belongs to another tariff.
        note = "[ICD-11: 1F44 / NHIA: 4-02-01]"
        result = validate_scribe_codes(note)
        assert result["validated_codes"][0]["match_status"] == "nhia_ok_icd11_mismatch"


class TestNoteParser:
    def test_parse_soap_sections(self):
        note = """## Subjective
Fever for 2 days.

## Objective
Temp 38.5C.

## Assessment
Malaria suspected.

## Plan
Start ACT."""
        sections = parse_scribe_sections(note, template="soap")
        assert "Fever" in sections["history"]
        assert "38.5" in sections["examination"]
        assert "Malaria" in sections["diagnosis"]
        assert "ACT" in sections["clinical_notes"]

    def test_build_icd11_apply_payload(self):
        validated = [
            {
                "icd11": "1F44",
                "diagnosis": "Malaria",
                "match_status": "matched",
            }
        ]
        payload = build_icd11_apply_payload(validated)
        assert payload[0]["code"] == "1F44"
        assert payload[0]["confidence"] == 0.95
