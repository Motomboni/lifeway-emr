"""Tests for Clinical AI Scribe obstetric calculations."""

from datetime import date

import pytest

from apps.ai_integration.obstetric_calculations import (
    build_obstetric_context_block,
    calculate_edd,
    calculate_ega,
    extract_lmp_from_text,
    is_obstetric_context,
    resolve_template,
)


class TestObstetricCalculations:
    def test_edd_naegele_equivalent(self):
        lmp = date(2025, 10, 1)
        assert calculate_edd(lmp) == date(2026, 7, 8)

    def test_ega_weeks_and_days(self):
        lmp = date(2025, 10, 1)
        ref = date(2026, 6, 28)
        weeks, days = calculate_ega(lmp, ref)
        assert weeks == 38
        assert days == 4

    def test_extract_lmp_slash_format(self):
        text = "Patient is pregnant. LMP was 01/10/2025. BP normal."
        assert extract_lmp_from_text(text) == date(2025, 10, 1)

    def test_obstetric_keyword_detection(self):
        assert is_obstetric_context("She came for ANC booking today")
        assert not is_obstetric_context("Male adult with cough and fever")

    def test_resolve_template_auto_antenatal(self):
        assert resolve_template("auto", "Gravida 2 para 1 antenatal visit") == "antenatal"

    def test_resolve_template_auto_soap(self):
        assert resolve_template("auto", "Patient complains of headache") == "soap"

    def test_obstetric_context_block(self):
        block = build_obstetric_context_block(
            "LMP 01/10/2025", reference=date(2026, 6, 28)
        )
        assert "EDD" in block
        assert "38 weeks 4 days" in block
