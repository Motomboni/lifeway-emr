"""
Legacy LIFEWAY flexible-payment (deferred) charges.

Zero-amount tblPatientPayment rows were imported as VisitCharge records tagged
[Legacy Deferred PatientPayID:N]. Settlement uses the standard Payment model and
BillingService, with an idempotent settlement marker in payment notes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from apps.billing.billing_line_item_service import allocate_payment_to_line_items
from apps.billing.billing_service import BillingService
from apps.billing.models import Payment, VisitCharge
from apps.billing.service_catalog_models import ServiceCatalog

DEFERRED_TAG_PREFIX = "[Legacy Deferred PatientPayID:"
SETTLED_TAG_PREFIX = "[Legacy Settled PatientPayID:"
_DEFERRED_PAY_ID_RE = re.compile(r"\[Legacy Deferred PatientPayID:(\d+)\]")
_SETTLED_PAY_ID_RE = re.compile(r"\[Legacy Settled PatientPayID:(\d+)\]")

# Median paid amounts from LIFEWAY tblPatientPayment (positive PayAmount rows).
_LEGACY_DEFERRED_PRICE_HINTS: dict[str, Decimal] = {
    "REGISTRATION": Decimal("3000.00"),
    "FULL BLOOD COUNT": Decimal("3500.00"),
    "MANTOUX TEST": Decimal("7000.00"),
    "TUBERCULOSIS SCREENING": Decimal("2500.00"),
    "OBSTETRICS/GYNAECOLOGIST": Decimal("10000.00"),
    "OBSTETRICS AND GYNAECOLOGIST": Decimal("10000.00"),
    "DENTAL REGISTRATION": Decimal("5000.00"),
    "IVF REGISTRATION": Decimal("5000.00"),
}


@dataclass
class _DeferredListContext:
    """In-memory indexes for fast deferred-payment list serialization."""

    settled_pay_ids: set[int] = field(default_factory=set)
    catalog_exact: dict[str, tuple[Decimal, str]] = field(default_factory=dict)
    catalog_names: list[tuple[str, Decimal, str]] = field(default_factory=list)

    @classmethod
    def build(cls) -> _DeferredListContext:
        settled_pay_ids: set[int] = set()
        for notes in Payment.objects.filter(
            status="CLEARED",
            notes__contains=SETTLED_TAG_PREFIX,
        ).values_list("notes", flat=True):
            if not notes:
                continue
            for match in _SETTLED_PAY_ID_RE.finditer(notes):
                settled_pay_ids.add(int(match.group(1)))

        catalog_exact: dict[str, tuple[Decimal, str]] = {}
        catalog_names: list[tuple[str, Decimal, str]] = []
        for name, amount in ServiceCatalog.objects.filter(
            is_active=True,
            amount__gt=0,
        ).values_list("name", "amount"):
            key = str(name or "").strip().lower()
            if not key:
                continue
            prev = catalog_exact.get(key)
            if prev is None or amount > prev[0]:
                catalog_exact[key] = (amount, name)
            catalog_names.append((key, amount, name))

        return cls(
            settled_pay_ids=settled_pay_ids,
            catalog_exact=catalog_exact,
            catalog_names=catalog_names,
        )

    def is_settled(self, charge: VisitCharge) -> bool:
        legacy_pay_id = extract_deferred_pay_id(charge.description)
        return legacy_pay_id is not None and legacy_pay_id in self.settled_pay_ids

    def resolve_catalog_match(self, service_line: str) -> tuple[Decimal | None, str | None]:
        svc = normalize_service_line(service_line)
        if not svc:
            return None, None
        key = svc.lower()
        if key in self.catalog_exact:
            amount, name = self.catalog_exact[key]
            return amount, name
        snippet = svc[:120].lower()
        best_amount: Decimal | None = None
        best_name: str | None = None
        for name_lower, amount, name in self.catalog_names:
            if snippet in name_lower:
                if best_amount is None or amount > best_amount:
                    best_amount = amount
                    best_name = name
        if best_amount is not None:
            return best_amount, best_name
        return None, None

    def resolve_deferred_price(self, service_line: str) -> tuple[Decimal, str, str | None]:
        catalog_amount, catalog_name = self.resolve_catalog_match(service_line)
        if catalog_amount and catalog_amount > 0:
            return catalog_amount, "catalog", catalog_name
        hint = resolve_legacy_hint_amount(service_line)
        if hint and hint > 0:
            return hint, "legacy_median", None
        return Decimal("0.00"), "unknown", None

    def effective_charge_amount(self, charge: VisitCharge) -> tuple[Decimal, str, str | None]:
        if charge.amount and charge.amount > 0:
            return charge.amount, "recorded", None
        if not (charge.description or "").startswith(DEFERRED_TAG_PREFIX):
            return charge.amount or Decimal("0.00"), "unknown", None
        return self.resolve_deferred_price(extract_service_line(charge.description))


def normalize_service_line(service_line: str | None) -> str:
    """Clean legacy LIFEWAY service labels for display and catalog lookup."""
    text = str(service_line or "").strip()
    if not text:
        return ""
    text = text.replace("\ufffd", " ").replace("\u2014", " ").replace("\u2013", " ")
    text = re.sub(r"^[\s\-–—:|/\\.;]+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_deferred_pay_id(description: str | None) -> int | None:
    if not description:
        return None
    match = _DEFERRED_PAY_ID_RE.search(description)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def extract_service_line(description: str | None) -> str:
    if not description:
        return ""
    text = str(description).strip()
    if text.startswith(DEFERRED_TAG_PREFIX):
        remainder = text.split("]", 1)[-1].strip()
        if " — " in remainder:
            remainder = remainder.split(" — ", 1)[0].strip()
        elif " - " in remainder:
            remainder = remainder.split(" - ", 1)[0].strip()
        return normalize_service_line(remainder)
    return normalize_service_line(text)


def resolve_catalog_match(service_line: str) -> tuple[Decimal | None, str | None]:
    svc = normalize_service_line(service_line)
    if not svc:
        return None, None
    exact = (
        ServiceCatalog.objects.filter(is_active=True, name__iexact=svc)
        .order_by("-amount")
        .first()
    )
    if exact and exact.amount and exact.amount > 0:
        return exact.amount, exact.name
    fuzzy = (
        ServiceCatalog.objects.filter(is_active=True, name__icontains=svc[:120])
        .order_by("-amount")
        .first()
    )
    if fuzzy and fuzzy.amount and fuzzy.amount > 0:
        return fuzzy.amount, fuzzy.name
    return None, None


def resolve_legacy_hint_amount(service_line: str) -> Decimal | None:
    svc = normalize_service_line(service_line).upper()
    if not svc:
        return None
    if svc in _LEGACY_DEFERRED_PRICE_HINTS:
        return _LEGACY_DEFERRED_PRICE_HINTS[svc]
    for key, amount in _LEGACY_DEFERRED_PRICE_HINTS.items():
        if key in svc or svc in key:
            return amount
    return None


def resolve_deferred_price(service_line: str) -> tuple[Decimal, str, str | None]:
    """
    Returns (amount, price_source, catalog_match_name).
    price_source: catalog | legacy_median | unknown
    """
    catalog_amount, catalog_name = resolve_catalog_match(service_line)
    if catalog_amount and catalog_amount > 0:
        return catalog_amount, "catalog", catalog_name
    hint = resolve_legacy_hint_amount(service_line)
    if hint and hint > 0:
        return hint, "legacy_median", None
    return Decimal("0.00"), "unknown", None


def effective_charge_amount(charge: VisitCharge) -> tuple[Decimal, str, str | None]:
    if charge.amount and charge.amount > 0:
        return charge.amount, "recorded", None
    if not (charge.description or "").startswith(DEFERRED_TAG_PREFIX):
        return charge.amount or Decimal("0.00"), "unknown", None
    amount, source, catalog_name = resolve_deferred_price(extract_service_line(charge.description))
    return amount, source, catalog_name


def is_deferred_charge(charge: VisitCharge) -> bool:
    return (charge.description or "").startswith(DEFERRED_TAG_PREFIX)


def is_settled(charge: VisitCharge) -> bool:
    legacy_pay_id = extract_deferred_pay_id(charge.description)
    if legacy_pay_id is None:
        return False
    settled_tag = f"{SETTLED_TAG_PREFIX}{legacy_pay_id}]"
    return Payment.objects.filter(
        visit_id=charge.visit_id,
        status="CLEARED",
        notes__contains=settled_tag,
    ).exists()


def list_unsettled_deferred_charges(
    *,
    search: str = "",
    ctx: _DeferredListContext | None = None,
) -> list[VisitCharge]:
    context = ctx or _DeferredListContext.build()
    queryset = (
        VisitCharge.objects.filter(description__startswith=DEFERRED_TAG_PREFIX)
        .select_related("visit", "visit__patient")
        .order_by("-created_at", "-id")
    )
    if search:
        search_q = (
            Q(description__icontains=search)
            | Q(visit__patient__first_name__icontains=search)
            | Q(visit__patient__last_name__icontains=search)
            | Q(visit__patient__patient_id__icontains=search)
        )
        if search.isdigit():
            search_q = search_q | Q(visit_id=int(search)) | Q(id=int(search))
        queryset = queryset.filter(search_q)
    return [charge for charge in queryset if not context.is_settled(charge)]


def list_and_serialize_unsettled_deferred_charges(
    *,
    search: str = "",
    page: int = 1,
    page_size: int = 48,
) -> tuple[int, list[dict]]:
    context = _DeferredListContext.build()
    charges = list_unsettled_deferred_charges(search=search, ctx=context)
    total = len(charges)
    start = max(0, (page - 1) * page_size)
    page_charges = charges[start : start + page_size]
    results = [serialize_deferred_charge(charge, ctx=context) for charge in page_charges]
    return total, results


def serialize_deferred_charge(
    charge: VisitCharge,
    *,
    ctx: _DeferredListContext | None = None,
) -> dict:
    context = ctx or _DeferredListContext.build()
    patient = charge.visit.patient
    service_line = extract_service_line(charge.description)
    effective, price_source, catalog_name = context.effective_charge_amount(charge)
    catalog_amount, _ = context.resolve_catalog_match(service_line)
    legacy_pay_id = extract_deferred_pay_id(charge.description)
    return {
        "charge_id": charge.id,
        "legacy_pay_id": legacy_pay_id,
        "visit_id": charge.visit_id,
        "visit_status": charge.visit.status,
        "patient": {
            "id": patient.id,
            "patient_id": patient.patient_id,
            "name": (
                patient.get_full_name()
                if hasattr(patient, "get_full_name")
                else f"{patient.first_name} {patient.last_name}".strip()
            ),
        },
        "service_line": service_line,
        "category": charge.category,
        "recorded_amount": str(charge.amount or Decimal("0.00")),
        "catalog_amount": str(catalog_amount) if catalog_amount else None,
        "catalog_match_name": catalog_name,
        "amount_due": str(effective),
        "price_source": price_source,
        "needs_price": effective <= 0,
        "description": charge.description,
        "created_at": charge.created_at.isoformat() if charge.created_at else None,
    }


@transaction.atomic
def settle_deferred_charge(
    charge_id: int,
    *,
    amount: Decimal,
    payment_method: str,
    processed_by,
    transaction_reference: str = "",
    notes: str = "",
) -> dict:
    charge = (
        VisitCharge.objects.select_related("visit", "visit__patient")
        .filter(pk=charge_id, description__startswith=DEFERRED_TAG_PREFIX)
        .first()
    )
    if not charge:
        raise ValidationError("Deferred legacy charge not found.")

    if is_settled(charge):
        raise ValidationError("This deferred service has already been settled.")

    if amount <= 0:
        raise ValidationError("Settlement amount must be greater than zero.")

    legacy_pay_id = extract_deferred_pay_id(charge.description)
    if legacy_pay_id is None:
        raise ValidationError("Invalid deferred charge tag.")

    visit = charge.visit
    if charge.amount is None or charge.amount <= 0:
        VisitCharge.objects.filter(pk=charge.pk).update(amount=amount)

    settled_tag = f"{SETTLED_TAG_PREFIX}{legacy_pay_id}]"
    payment_notes_parts = [
        settled_tag,
        f"Settles deferred legacy service: {extract_service_line(charge.description)[:500]}",
    ]
    if notes:
        payment_notes_parts.append(notes.strip())
    payment_notes = "\n".join(payment_notes_parts)

    initial_status = "CLEARED" if payment_method in {"CASH", "POS", "TRANSFER", "WALLET"} else "PENDING"
    payment = Payment.objects.create(
        visit=visit,
        amount=amount,
        payment_method=payment_method,
        status=initial_status,
        transaction_reference=(transaction_reference or "")[:255],
        notes=payment_notes,
        processed_by=processed_by,
    )

    try:
        allocate_payment_to_line_items(visit, Decimal(str(payment.amount)), payment.payment_method or "CASH")
    except Exception:
        pass

    summary = BillingService.compute_billing_summary(visit)
    visit.payment_status = summary.payment_status
    visit.save(update_fields=["payment_status"])

    return {
        "payment_id": payment.id,
        "charge_id": charge.id,
        "visit_id": visit.id,
        "amount": str(payment.amount),
        "payment_status": payment.status,
        "outstanding_balance": str(summary.outstanding_balance),
    }
