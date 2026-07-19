"""
Parse and validate ICD-11 / NHIA codes from Clinical AI Scribe output.

Matches extracted codes against the NHIA tariff reference database.
"""

from __future__ import annotations

import re
from typing import Any

from apps.billing.nhia_tariff_models import NHIATariff

# e.g. Acute malaria [ICD-11: 1F44 / NHIA: 3-01-01]
BRACKETED_CODE_PATTERN = re.compile(
    r"(?P<label>[^\[\n]{0,120}?)"
    r"\[\s*ICD-11:\s*(?P<icd11>[^\]/\]]+)\s*/\s*NHIA:\s*(?P<nhia>[^\]]+)\s*\]",
    re.IGNORECASE,
)

# Fallback: ICD-11: 1F44 / NHIA: 3-01-01 (no brackets)
INLINE_CODE_PATTERN = re.compile(
    r"ICD-11:\s*(?P<icd11>[^\s/,]+)\s*/\s*NHIA:\s*(?P<nhia>[^\s,\]\)]+)",
    re.IGNORECASE,
)


def _normalize_icd11(code: str) -> str:
    return (code or "").strip().upper()


def _normalize_nhia(code: str) -> str:
    return (code or "").strip()


def extract_codes_from_note(text: str) -> list[dict[str, str]]:
    """Extract ICD-11 / NHIA pairs from structured scribe output."""
    if not text:
        return []

    seen: set[tuple[str, str]] = set()
    extracted: list[dict[str, str]] = []

    for match in BRACKETED_CODE_PATTERN.finditer(text):
        icd11 = _normalize_icd11(match.group("icd11"))
        nhia = _normalize_nhia(match.group("nhia"))
        key = (icd11, nhia)
        if key in seen:
            continue
        seen.add(key)
        label = (match.group("label") or "").strip(" *:-\t")
        extracted.append(
            {
                "diagnosis": label,
                "icd11": icd11,
                "nhia": nhia,
            }
        )

    for match in INLINE_CODE_PATTERN.finditer(text):
        icd11 = _normalize_icd11(match.group("icd11"))
        nhia = _normalize_nhia(match.group("nhia"))
        key = (icd11, nhia)
        if key in seen:
            continue
        seen.add(key)
        extracted.append(
            {
                "diagnosis": "",
                "icd11": icd11,
                "nhia": nhia,
            }
        )

    return extracted


def _tariff_by_nhia() -> dict[str, NHIATariff]:
    return {
        t.nhia_code: t
        for t in NHIATariff.objects.filter(is_active=True).only(
            "nhia_code",
            "name",
            "description",
            "amount_ngn",
            "icd11_codes",
            "category",
        )
    }


def _tariffs_by_icd11(tariffs: list[NHIATariff]) -> dict[str, list[NHIATariff]]:
    mapping: dict[str, list[NHIATariff]] = {}
    for tariff in tariffs:
        for code in tariff.icd11_code_set():
            mapping.setdefault(code, []).append(tariff)
    return mapping


def validate_scribe_codes(structured_note: str) -> dict[str, Any]:
    """
    Validate scribe-extracted codes against NHIA tariff DB.

    Returns extracted pairs, per-code validation, and suggested tariffs for
    unmatched ICD-11 codes.
    """
    extracted = extract_codes_from_note(structured_note)
    active_tariffs = list(
        NHIATariff.objects.filter(is_active=True).only(
            "nhia_code",
            "name",
            "description",
            "amount_ngn",
            "icd11_codes",
            "category",
        )
    )
    by_nhia = _tariff_by_nhia()
    by_icd11 = _tariffs_by_icd11(active_tariffs)

    validated: list[dict[str, Any]] = []
    unmatched_icd11: list[str] = []
    unmatched_nhia: list[str] = []
    suggested_tariffs: list[dict[str, Any]] = []
    seen_suggestions: set[str] = set()

    for item in extracted:
        icd11 = item["icd11"]
        nhia = item["nhia"]
        tariff = by_nhia.get(nhia)
        nhia_valid = tariff is not None
        icd11_valid = False
        match_status = "unmatched"

        if tariff:
            icd11_valid = icd11 in tariff.icd11_code_set()
            if icd11_valid:
                match_status = "matched"
            elif icd11 in by_icd11:
                match_status = "nhia_ok_icd11_mismatch"
                unmatched_icd11.append(icd11)
            else:
                match_status = "nhia_ok_icd11_unknown"
                unmatched_icd11.append(icd11)
        else:
            unmatched_nhia.append(nhia)
            if icd11 in by_icd11:
                match_status = "icd11_ok_nhia_unknown"
            else:
                unmatched_icd11.append(icd11)

        validated.append(
            {
                "diagnosis": item["diagnosis"],
                "icd11": icd11,
                "nhia": nhia,
                "icd11_valid": icd11_valid or icd11 in by_icd11,
                "nhia_valid": nhia_valid,
                "match_status": match_status,
                "tariff_name": tariff.name if tariff else None,
                "amount_ngn": str(tariff.amount_ngn) if tariff else None,
                "category": tariff.category if tariff else None,
            }
        )

        if icd11 in by_icd11 and nhia not in by_nhia:
            for alt in by_icd11[icd11]:
                if alt.nhia_code in seen_suggestions:
                    continue
                seen_suggestions.add(alt.nhia_code)
                suggested_tariffs.append(
                    {
                        "icd11": icd11,
                        "nhia_code": alt.nhia_code,
                        "name": alt.name,
                        "amount_ngn": str(alt.amount_ngn),
                        "category": alt.category,
                    }
                )

    return {
        "extracted_codes": extracted,
        "validated_codes": validated,
        "unmatched_icd11": sorted(set(unmatched_icd11)),
        "unmatched_nhia": sorted(set(unmatched_nhia)),
        "suggested_tariffs": suggested_tariffs,
        "all_matched": bool(validated)
        and all(v["match_status"] == "matched" for v in validated),
    }
