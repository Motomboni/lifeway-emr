"""
Regulatory facility reporting exports (Nigeria MOH / DHIS2-style CSV).
"""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

from django.db.models import Count

from apps.antenatal.models import AntenatalRecord
from apps.patients.models import Patient
from apps.visits.models import Visit


def build_moh_monthly_summary(
    *,
    organization=None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    visits = Visit.objects.all()
    patients = Patient.objects.filter(is_active=True)
    if organization:
        visits = visits.filter(organization=organization)
        patients = patients.filter(organization=organization)
    if start_date:
        visits = visits.filter(created_at__date__gte=start_date)
        patients = patients.filter(created_at__date__gte=start_date)
    if end_date:
        visits = visits.filter(created_at__date__lte=end_date)

    return {
        "report_type": "moh_monthly_summary",
        "period": {"start": str(start_date or ""), "end": str(end_date or "")},
        "total_visits": visits.count(),
        "new_patients": patients.count(),
        "visits_by_status": {
            row["status"]: row["count"]
            for row in visits.values("status").annotate(count=Count("id"))
        },
        "antenatal_active": AntenatalRecord.objects.filter(status="ACTIVE").count(),
    }


def moh_summary_to_csv(summary: dict[str, Any]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Report", summary.get("report_type", "")])
    writer.writerow(["Period start", summary.get("period", {}).get("start", "")])
    writer.writerow(["Period end", summary.get("period", {}).get("end", "")])
    writer.writerow(["Total visits", summary.get("total_visits", 0)])
    writer.writerow(["New patients", summary.get("new_patients", 0)])
    writer.writerow(["Active ANC records", summary.get("antenatal_active", 0)])
    for status, count in (summary.get("visits_by_status") or {}).items():
        writer.writerow([f"Visits — {status}", count])
    return buf.getvalue()


def build_dhis2_style_export(
    *,
    organization=None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> str:
    """Simplified DHIS2-compatible CSV (facility aggregate indicators)."""
    summary = build_moh_monthly_summary(
        organization=organization,
        start_date=start_date,
        end_date=end_date,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["dataElement", "period", "orgUnit", "value"])
    period = summary["period"]["end"][:7].replace("-", "") if summary["period"]["end"] else ""
    org = getattr(organization, "slug", "facility") if organization else "facility"
    writer.writerow(["OPD_VISITS", period, org, summary["total_visits"]])
    writer.writerow(["NEW_PATIENTS", period, org, summary["new_patients"]])
    writer.writerow(["ANC_ACTIVE", period, org, summary["antenatal_active"]])
    return buf.getvalue()
