"""
Nigerian ANC care schedule — IPTp, TT, routine visits, danger signs.

Based on WHO focused ANC and Nigeria MOH antenatal guidelines (simplified).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from apps.antenatal.models import AntenatalRecord, AntenatalVisit


def _add_weeks(base: date, weeks: int) -> date:
    return base + timedelta(days=weeks * 7)


def build_anc_schedule(record: AntenatalRecord) -> dict[str, Any]:
    """
    Build ANC schedule from LMP/booking for an ongoing pregnancy.

    Returns scheduled items with due dates, status (due/overdue/completed/upcoming),
    and danger-signs reminder text for WhatsApp.
    """
    if not record.lmp:
        return {"items": [], "danger_signs": _danger_signs_text()}

    today = date.today()
    lmp = record.lmp
    items: list[dict[str, Any]] = []

    routine_visits = [
        (0, "BOOKING", "Antenatal booking visit"),
        (12, "ROUTINE", "First trimester review"),
        (20, "ROUTINE", "Second trimester review (anomaly scan window)"),
        (28, "ROUTINE", "Third trimester review"),
        (32, "ROUTINE", "Third trimester review"),
        (36, "ROUTINE", "Pre-delivery review"),
        (38, "ROUTINE", "Late pregnancy review"),
        (40, "ROUTINE", "EDD week review"),
    ]

    completed_dates = set(
        AntenatalVisit.objects.filter(antenatal_record=record).values_list(
            "visit_date", flat=True
        )
    )

    for week, visit_type, label in routine_visits:
        due = _add_weeks(lmp, week)
        status = _schedule_status(due, today, completed_dates)
        items.append(
            {
                "kind": "ANC_VISIT",
                "week": week,
                "visit_type": visit_type,
                "label": label,
                "due_date": str(due),
                "status": status,
            }
        )

    for week, dose in [(12, 1), (20, 2), (28, 3)]:
        due = _add_weeks(lmp, week)
        items.append(
            {
                "kind": "TT_VACCINE",
                "week": week,
                "dose": dose,
                "label": f"Tetanus toxoid dose {dose}",
                "due_date": str(due),
                "status": _schedule_status(due, today, completed_dates),
            }
        )

    for week, dose in [(16, 1), (24, 2), (28, 3), (32, 4), (36, 5)]:
        due = _add_weeks(lmp, week)
        items.append(
            {
                "kind": "IPTp",
                "week": week,
                "dose": dose,
                "label": f"IPTp (Sulfadoxine-Pyrimethamine) dose {dose}",
                "due_date": str(due),
                "status": _schedule_status(due, today, completed_dates),
            }
        )

    items.sort(key=lambda x: x["due_date"])

    upcoming = [i for i in items if i["status"] in ("due", "upcoming")][:5]
    overdue = [i for i in items if i["status"] == "overdue"]

    return {
        "record_id": record.id,
        "lmp": str(record.lmp),
        "edd": str(record.edd),
        "current_gestational_age_weeks": record.current_gestational_age_weeks,
        "items": items,
        "upcoming": upcoming,
        "overdue": overdue,
        "danger_signs": _danger_signs_text(),
    }


def _schedule_status(due: date, today: date, completed_dates: set) -> str:
    window_start = due - timedelta(days=3)
    window_end = due + timedelta(days=7)
    if any(window_start <= d <= window_end for d in completed_dates):
        return "completed"
    if today > window_end:
        return "overdue"
    if window_start <= today <= window_end:
        return "due"
    return "upcoming"


def _danger_signs_text() -> str:
    return (
        "Seek care immediately if you have: severe headache, blurred vision, "
        "convulsions, severe abdominal pain, vaginal bleeding, reduced fetal movement, "
        "fever, or difficulty breathing."
    )


def format_anc_whatsapp_reminder(record: AntenatalRecord, item: dict[str, Any]) -> str:
    """Format ANC schedule item as WhatsApp reminder message."""
    patient = record.patient
    name = patient.first_name or "Mama"
    return (
        f"Hello {name}, Lifeway Medical Centre ANC reminder: "
        f"{item['label']} is scheduled around {item['due_date']}. "
        f"{_danger_signs_text()} Reply or call the clinic to book."
    )
