"""
NHIA compliance dashboard metrics — claim readiness, code validation, revenue at risk.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Q

from apps.billing.claim_pack_service import build_visit_claim_pack
from apps.billing.leak_detection_models import LeakRecord
from apps.billing.models import VisitCharge
from apps.billing.nhia_charge_service import NHIA_CHARGE_PREFIX
from apps.visits.models import Visit


def get_nhia_compliance_summary(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    organization=None,
) -> dict[str, Any]:
    """Aggregate NHIA compliance metrics for admin dashboard."""
    if not end_date:
        end_date = date.today()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    visits_qs = Visit.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    ).select_related("patient")
    if organization:
        visits_qs = visits_qs.filter(organization=organization)

    visits = list(visits_qs.order_by("-created_at")[:200])
    claim_ready = 0
    missing_nhid = 0
    no_nhia_lines = 0
    total_nhia_amount = Decimal("0.00")
    visit_rows: list[dict[str, Any]] = []

    for visit in visits:
        pack = build_visit_claim_pack(visit)
        patient = visit.patient
        has_nhid = bool(getattr(patient, "national_health_id", None))
        line_count = pack["line_count"]
        amount = Decimal(pack["total_amount_ngn"] or "0")

        if not has_nhid:
            missing_nhid += 1
        if line_count == 0:
            no_nhia_lines += 1
        if pack["claim_ready"]:
            claim_ready += 1
            total_nhia_amount += amount

        issues: list[str] = []
        if not has_nhid:
            issues.append("missing_nhid")
        if line_count == 0:
            issues.append("no_nhia_codes")
        if not pack["claim_ready"]:
            issues.append("not_claim_ready")

        visit_rows.append(
            {
                "visit_id": visit.id,
                "visit_date": pack["visit_date"],
                "patient_name": pack["patient_name"],
                "patient_mrn": pack["patient_mrn"],
                "national_health_id": pack["national_health_id"],
                "line_count": line_count,
                "total_amount_ngn": pack["total_amount_ngn"],
                "claim_ready": pack["claim_ready"],
                "payment_status": pack["payment_status"],
                "issues": issues,
            }
        )

    leak_qs = LeakRecord.objects.filter(
        detected_at__date__gte=start_date,
        detected_at__date__lte=end_date,
        resolved_at__isnull=True,
    )
    if organization:
        leak_qs = leak_qs.filter(visit__organization=organization)
    open_leaks = leak_qs.count()

    nhia_charges_qs = VisitCharge.objects.filter(
        description__contains=NHIA_CHARGE_PREFIX,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date,
    )
    if organization:
        nhia_charges_qs = nhia_charges_qs.filter(visit__organization=organization)
    scribe_billed_count = nhia_charges_qs.count()

    return {
        "period": {"start": str(start_date), "end": str(end_date)},
        "visit_count": len(visits),
        "claim_ready_count": claim_ready,
        "claim_ready_pct": round(100 * claim_ready / len(visits), 1) if visits else 0,
        "missing_nhid_count": missing_nhid,
        "no_nhia_codes_count": no_nhia_lines,
        "total_nhia_billable_ngn": str(total_nhia_amount),
        "scribe_billed_items": scribe_billed_count,
        "open_revenue_leaks": open_leaks,
        "visits": visit_rows,
    }
