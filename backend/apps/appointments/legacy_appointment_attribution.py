"""Resolve LIFEWAY legacy doctors for migrated appointments."""
from __future__ import annotations

import re

from django.contrib.auth.hashers import make_password
from django.utils.crypto import get_random_string

from apps.users.models import User

LEGACY_APP_ID_RE = re.compile(r"\[Legacy AppID:(\d+)\]")
LEGACY_DOCTOR_NAME_RE = re.compile(r"\[Legacy doctor:([^\]]+)\]", re.IGNORECASE)


def legacy_user_email(legacy_user_id: int) -> str:
    return f"lifeway_uid{legacy_user_id}@example.com"


def extract_legacy_app_id(notes: str | None) -> int | None:
    if not notes:
        return None
    match = LEGACY_APP_ID_RE.search(notes)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def extract_legacy_doctor_name(notes: str | None) -> str | None:
    if not notes:
        return None
    match = LEGACY_DOCTOR_NAME_RE.search(notes)
    if not match:
        return None
    return match.group(1).strip() or None


def format_legacy_doctor_tag(name: str) -> str:
    clean = (name or "").strip()
    return f"[Legacy doctor: {clean}]"


def promote_legacy_doctor_user(user: User) -> User:
    changed = False
    if user.role != "DOCTOR":
        user.role = "DOCTOR"
        changed = True
    if not (user.specialization or "").strip():
        user.specialization = "General Practice"
        changed = True
    if changed:
        user.save(update_fields=["role", "specialization"])
    return user


def resolve_legacy_doctor_user(
    legacy_doctor_id: int | None,
    *,
    cache: dict[int, User],
) -> User | None:
    if legacy_doctor_id is None:
        return None
    if legacy_doctor_id in cache:
        return cache[legacy_doctor_id]
    user = User.objects.filter(email=legacy_user_email(legacy_doctor_id)).first()
    if not user:
        return None
    user = promote_legacy_doctor_user(user)
    cache[legacy_doctor_id] = user
    return user


def ensure_doctor_from_display_name(name: str, *, cache: dict[str, User]) -> User | None:
    clean = (name or "").strip()
    if not clean:
        return None
    key = clean.upper()
    if key in cache:
        return cache[key]

    if "," in clean:
        last, first = [part.strip() for part in clean.split(",", 1)]
    else:
        parts = clean.split()
        first = parts[0] if parts else "Doctor"
        last = " ".join(parts[1:]) if len(parts) > 1 else parts[0]

    username_base = re.sub(r"[^a-zA-Z0-9._-]+", "_", f"legacy_dr_{first}_{last}").strip("_").lower()[:80]
    username = username_base or "legacy_doctor"
    step = 0
    while User.objects.filter(username=username).exclude(first_name=first, last_name=last).exists():
        step += 1
        username = f"{username_base}_{step}"[:150]

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": f"{username}@legacy.local",
            "first_name": first[:255],
            "last_name": last[:255],
            "password": make_password(get_random_string(24)),
            "role": "DOCTOR",
            "specialization": "General Practice",
            "is_active": True,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    promote_legacy_doctor_user(user)
    cache[key] = user
    return user


def load_appointment_csv_index(csv_dir) -> dict[int, dict]:
    from pathlib import Path
    import csv

    path = Path(csv_dir) / "tblOPDAppointment.csv"
    if not path.exists():
        return {}
    index: dict[int, dict] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                app_id = int(row["AppointmentID"])
            except (TypeError, ValueError, KeyError):
                continue
            doctor_raw = (row.get("DoctorID") or "").strip()
            doctor_id = None
            if doctor_raw and doctor_raw.upper() != "NULL":
                try:
                    doctor_id = int(doctor_raw)
                except ValueError:
                    doctor_id = None
            index[app_id] = {
                "doctor_id": doctor_id,
                "doctor_name": (row.get("DoctorName") or row.get("ToSee") or "").strip(),
            }
    return index
