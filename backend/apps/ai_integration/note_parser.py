"""
Parse structured Clinical AI Scribe notes into consultation form sections.
"""

from __future__ import annotations

import re
from typing import Any


def _section_content(text: str, headers: list[str]) -> str:
    """Return text under the first matching markdown-style header."""
    for header in headers:
        pattern = re.compile(
            rf"^\s*#{{1,3}}\s*{re.escape(header)}\s*$",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        if not match:
            continue
        start = match.end()
        next_header = re.search(
            r"^\s*#{1,3}\s+.+$",
            text[start:],
            re.MULTILINE,
        )
        end = start + next_header.start() if next_header else len(text)
        return text[start:end].strip()
    return ""


def parse_scribe_sections(structured_note: str, template: str = "soap") -> dict[str, str]:
    """
    Map scribe markdown to consultation form fields.

    Returns keys: history, examination, diagnosis, clinical_notes
    """
    note = (structured_note or "").strip()
    if not note:
        return {
            "history": "",
            "examination": "",
            "diagnosis": "",
            "clinical_notes": "",
        }

    template_key = (template or "soap").lower()

    if template_key == "antenatal":
        history = _section_content(
            note,
            [
                "Maternal Complaints & History",
                "Maternal History",
                "History",
                "Subjective",
            ],
        )
        examination = _section_content(
            note,
            [
                "Vitals & Examination",
                "Examination",
                "Objective",
            ],
        )
        diagnosis = _section_content(
            note,
            [
                "Assessment",
                "Encounter Classification",
                "Diagnosis",
            ],
        )
        plan = _section_content(note, ["Plan", "Management Plan"])
        obstetric = _section_content(
            note,
            ["Obstetric Summary", "Antenatal Summary", "Booking Details"],
        )
        clinical_notes = "\n\n".join(p for p in [obstetric, plan] if p).strip()
        return {
            "history": history,
            "examination": examination,
            "diagnosis": diagnosis,
            "clinical_notes": clinical_notes,
        }

    subjective = _section_content(note, ["Subjective", "Chief Complaint", "History"])
    objective = _section_content(note, ["Objective", "Examination", "Physical Examination"])
    assessment = _section_content(
        note,
        ["Assessment", "Diagnosis", "Primary suspected condition"],
    )
    plan = _section_content(note, ["Plan", "Management", "Treatment Plan"])

    history_parts = []
    cc = _section_content(note, ["Chief Complaint"])
    hpi = _section_content(note, ["History of Present Illness", "HPI"])
    if cc:
        history_parts.append(f"Chief Complaint:\n{cc}")
    if hpi:
        history_parts.append(f"History of Present Illness:\n{hpi}")
    if subjective and not history_parts:
        history_parts.append(subjective)
    elif subjective and subjective not in "\n".join(history_parts):
        history_parts.append(subjective)

    clinical_notes = plan
    if not clinical_notes:
        clinical_notes = _section_content(note, ["Follow-up", "Patient Education"])

    return {
        "history": "\n\n".join(history_parts).strip(),
        "examination": objective,
        "diagnosis": assessment,
        "clinical_notes": clinical_notes,
    }


def build_icd11_apply_payload(
    validated_codes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build icd11_codes list for from-ai-suggestion endpoint."""
    payload: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in validated_codes:
        code = (item.get("icd11") or "").strip().upper()
        if not code or code in seen:
            continue
        seen.add(code)
        description = (item.get("diagnosis") or item.get("tariff_name") or code).strip()
        confidence = 0.95 if item.get("match_status") == "matched" else 0.75
        payload.append(
            {
                "code": code,
                "description": description or code,
                "confidence": confidence,
            }
        )
    return payload
