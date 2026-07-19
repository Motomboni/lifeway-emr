"""
Add validated NHIA tariff items from Clinical AI Scribe to a visit bill.

Creates MISC VisitCharge rows tagged with NHIA codes for claim-pack export.
Skips duplicates already on the visit.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.billing.models import VisitCharge
from apps.billing.nhia_tariff_models import NHIATariff
from apps.visits.models import Visit

NHIA_CHARGE_PREFIX = "NHIA:"


def _charge_marker(nhia_code: str) -> str:
    return f"{NHIA_CHARGE_PREFIX}{nhia_code}"


def _existing_nhia_codes(visit: Visit) -> set[str]:
    codes: set[str] = set()
    for desc in VisitCharge.objects.filter(visit=visit).values_list(
        "description", flat=True
    ):
        if NHIA_CHARGE_PREFIX not in (desc or ""):
            continue
        start = desc.index(NHIA_CHARGE_PREFIX) + len(NHIA_CHARGE_PREFIX)
        code = desc[start:].split("|", 1)[0].strip()
        if code:
            codes.add(code)
    return codes


def add_nhia_charges_from_scribe(
    visit: Visit,
    codes: list[dict[str, str]],
    *,
    only_matched: bool = True,
) -> dict[str, Any]:
    """
    Add NHIA tariff charges for scribe-validated codes.

    Args:
        visit: Open visit.
        codes: List of {"nhia": "...", "icd11": "...", "diagnosis": "..."}.
        only_matched: If True, skip codes with no active tariff row.

    Returns:
        Summary with created/skipped items.
    """
    if visit.status == "CLOSED":
        raise ValidationError("Cannot add charges to a CLOSED visit.")

    if not codes:
        raise ValidationError("At least one NHIA code is required.")

    by_nhia = {
        t.nhia_code: t
        for t in NHIATariff.objects.filter(is_active=True).only(
            "nhia_code", "name", "amount_ngn", "category"
        )
    }
    already = _existing_nhia_codes(visit)
    created: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    with transaction.atomic():
        for item in codes:
            nhia = (item.get("nhia") or "").strip()
            icd11 = (item.get("icd11") or "").strip().upper()
            diagnosis = (item.get("diagnosis") or "").strip()
            if not nhia:
                skipped.append({"reason": "missing_nhia", **item})
                continue
            if nhia in already:
                skipped.append({"reason": "already_billed", "nhia": nhia, "icd11": icd11})
                continue

            tariff = by_nhia.get(nhia)
            if not tariff:
                if only_matched:
                    skipped.append({"reason": "no_tariff", "nhia": nhia, "icd11": icd11})
                    continue
                amount = Decimal("0.00")
                label = diagnosis or f"NHIA service {nhia}"
            else:
                amount = tariff.amount_ngn
                label = diagnosis or tariff.name

            description = (
                f"{_charge_marker(nhia)} | {label} [ICD-11: {icd11}]"
                if icd11
                else f"{_charge_marker(nhia)} | {label}"
            )
            charge = VisitCharge.create_misc_charge(
                visit=visit,
                amount=amount,
                description=description,
            )
            already.add(nhia)
            created.append(
                {
                    "id": charge.id,
                    "nhia": nhia,
                    "icd11": icd11,
                    "description": description,
                    "amount": str(charge.amount),
                    "tariff_name": tariff.name if tariff else None,
                }
            )

    return {
        "created": created,
        "skipped": skipped,
        "created_count": len(created),
        "skipped_count": len(skipped),
    }
