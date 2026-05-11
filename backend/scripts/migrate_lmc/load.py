from __future__ import annotations

import importlib
import logging
import os
import re
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)

_OP_NOTE_KEYS = (
    "ChiefComplaint",
    "VisitNotes",
    "HPC",
    "PMH",
    "FHx",
    "IMH",
    "DH",
    "Exam",
    "Assessment",
    "TreatPlan",
    "ResultsText",
    "Treatment",
    "Summary",
    "FollowUp",
    "Weight",
    "Temperature",
)


def _legacy_plain_text(value: Any) -> str:
    return (str(value or "")).strip()


def _truncate_migration_text(text: str, max_chars: int = 120_000) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 30] + "\n…[truncated for migration]"


def _visit_row_has_op_narrative(source_row: dict[str, Any]) -> bool:
    return any(_legacy_plain_text(source_row.get(k)) for k in _OP_NOTE_KEYS)


def _consultation_fields_from_patient_visit(source_row: dict[str, Any], legacy_visit_id: int) -> tuple[str, str, str, str]:
    """Map LIFEWAY tblPatientVisits OP columns into Consultation text fields."""

    def sec(title: str, key: str) -> str:
        t = _legacy_plain_text(source_row.get(key))
        if not t:
            return ""
        return f"{title}\n{t}"

    h_parts = [
        sec("Presenting complaint", "ChiefComplaint"),
        sec("Visit notes", "VisitNotes"),
        sec("History of presenting complaint", "HPC"),
        sec("Past medical history", "PMH"),
        sec("Family history", "FHx"),
        sec("Immunization / maternal history", "IMH"),
        sec("Developmental history", "DH"),
    ]
    wt, tmp = _legacy_plain_text(source_row.get("Weight")), _legacy_plain_text(source_row.get("Temperature"))
    if wt or tmp:
        bits = []
        if wt:
            bits.append(f"Weight {wt}")
        if tmp:
            bits.append(f"Temperature {tmp}")
        h_parts.append("Visit measurements (legacy)\n" + "; ".join(bits))
    history = _truncate_migration_text("\n\n".join(x for x in h_parts if x))
    examination = _truncate_migration_text(_legacy_plain_text(source_row.get("Exam")))
    diagnosis = _truncate_migration_text(_legacy_plain_text(source_row.get("Assessment")))
    tag = f"[Legacy VisitID:{legacy_visit_id}]"
    n_parts = [
        sec("Treatment plan", "TreatPlan"),
        sec("Investigations / results", "ResultsText"),
        sec("Treatment given", "Treatment"),
        sec("Summary", "Summary"),
        sec("Follow-up", "FollowUp"),
    ]
    body = "\n\n".join(x for x in n_parts if x)
    clinical_notes = _truncate_migration_text(f"{tag}\n\n{body}" if body else tag)
    return history, examination, diagnosis, clinical_notes


def _charge_category_from_receipt_line(field_name: Any, service_line: Any) -> str:
    blob = f"{field_name or ''} {service_line or ''}".upper()
    if any(x in blob for x in ("LAB", "PATH", "URINE", "BLOOD", "MICRO", "HISTOL")):
        return "LAB"
    if any(x in blob for x in ("XRAY", "X-RAY", "RADIO", "SCAN", "SONO", "ULTRA", " CT", "MRI", "ECHO")):
        return "RADIOLOGY"
    if any(x in blob for x in ("PHARM", "DRUG", "TAB ", " TAB", "CAP ", "SYRUP", "SUSP", "INJ ", "INSULIN", "IVFL")):
        return "DRUG"
    if any(x in blob for x in ("CONSULT", "OPD", "CLINIC", "REVIEW")):
        return "CONSULTATION"
    if any(x in blob for x in ("INJECT", "DRESS", "SUTURE", "PROC", "IUCD", "IUD ", "DRESSING")):
        return "PROCEDURE"
    return "MISC"


def resolve_model_class(target_model: str):
    """
    Resolve 'apps.patients.Patient' -> model class.
    """
    module_path, class_name = target_model.rsplit(".", 1)
    module = importlib.import_module(f"{module_path}.models")
    return getattr(module, class_name)


def load_transformed_data(
    payloads: list[dict[str, Any]],
    dry_run: bool = True,
) -> dict[str, int]:
    """
    Load scaffold.
    Returns created counts keyed by target model.
    """
    created_counts: dict[str, int] = {}

    # In-run crosswalks for the first vertical slice.
    legacy_user_pk_by_id: dict[int, int] = {}
    patient_id_map: dict[int, int] = {}
    visit_id_map: dict[int, int] = {}
    lab_order_pk_by_request_id: dict[int, int] = {}

    from django.contrib.auth.hashers import make_password  # pylint: disable=import-outside-toplevel
    from django.utils import timezone  # pylint: disable=import-outside-toplevel
    from django.utils.crypto import get_random_string  # pylint: disable=import-outside-toplevel
    from apps.patients.models import Patient  # pylint: disable=import-outside-toplevel
    from apps.visits.models import Visit  # pylint: disable=import-outside-toplevel
    from apps.appointments.models import Appointment  # pylint: disable=import-outside-toplevel
    from apps.pharmacy.models import Drug, Prescription  # pylint: disable=import-outside-toplevel
    from apps.users.models import User  # pylint: disable=import-outside-toplevel
    from apps.clinical.models import VitalSigns  # pylint: disable=import-outside-toplevel
    from apps.consultations.models import Consultation  # pylint: disable=import-outside-toplevel
    from apps.laboratory.models import LabOrder, LabResult  # pylint: disable=import-outside-toplevel
    from apps.radiology.models import RadiologyRequest  # pylint: disable=import-outside-toplevel
    from apps.billing.models import Payment, VisitCharge  # pylint: disable=import-outside-toplevel
    from django.db import IntegrityError, OperationalError, connection  # pylint: disable=import-outside-toplevel

    patient_key_prefix = (os.environ.get("LEGACY_PATIENT_ID_PREFIX") or "LIFEWAYLEG").strip() or "LIFEWAYLEG"

    def _sqlite_lock_retry(label: str, op: Callable[[], T], *, attempts: int = 50, base: float = 0.05) -> T:
        """SQLite often returns 'database is locked' under concurrent writers; retry with backoff."""
        if connection.vendor != "sqlite":
            return op()
        last: OperationalError | None = None
        for i in range(attempts):
            try:
                return op()
            except OperationalError as e:
                last = e
                msg = str(e).lower()
                if "locked" not in msg and "busy" not in msg:
                    raise
                delay = min(2.0, base * (2 ** min(i, 8)))
                if i == 0 or (i + 1) % 10 == 0:
                    logger.warning("SQLite busy on %s (try %s/%s); sleeping %.2fs", label, i + 1, attempts, delay)
                time.sleep(delay)
        assert last is not None
        raise last

    def _patient_external_id(legacy_patient_id: int) -> str:
        return f"{patient_key_prefix}{legacy_patient_id:07d}"

    def _inc(model_name: str) -> None:
        created_counts[model_name] = created_counts.get(model_name, 0) + 1

    def _to_int(value: Any) -> int | None:
        try:
            if value is None or value == "":
                return None
            if isinstance(value, str) and value.strip().upper() in {"NULL", "N/A", "-"}:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _to_decimal(value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value).strip())
        except (InvalidOperation, ValueError):
            return None

    def _parse_bp_string(raw: Any) -> tuple[int | None, int | None]:
        s = (str(raw or "").strip().replace(" ", ""))
        if not s:
            return None, None
        m = re.match(r"^(\d{2,3})/(\d{1,3})$", s)
        if not m:
            return None, None
        try:
            sys_v = int(m.group(1))
            dia_v = int(m.group(2))
            if 50 <= sys_v <= 300 and 30 <= dia_v <= 200 and sys_v > dia_v:
                return sys_v, dia_v
        except ValueError:
            pass
        return None, None

    def _parse_temperature_celsius(raw: Any) -> Decimal | None:
        if raw is None or str(raw).strip() == "":
            return None
        try:
            t = float(str(raw).strip().replace(",", "."))
        except ValueError:
            return None
        if 90.0 <= t <= 110.0:
            t = (t - 32.0) * 5.0 / 9.0
        d = Decimal(str(round(t, 2)))
        if Decimal("30") <= d <= Decimal("45"):
            return d
        return None

    def _parse_vital_int(raw: Any, lo: int, hi: int) -> int | None:
        v = _to_int(raw)
        if v is None:
            return None
        if lo <= v <= hi:
            return v
        return None

    def _parse_vital_decimal(raw: Any, lo: Decimal, hi: Decimal) -> Decimal | None:
        d = _to_decimal(raw)
        if d is None:
            return None
        if lo <= d <= hi:
            return d
        return None

    def _parse_date_only(value: Any) -> date | None:
        """CSV / sqlcmd often sends 'YYYY-MM-DD HH:MM:SS.fff' for date columns."""
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        s = str(value).strip().strip("\ufeff")
        if len(s) >= 10 and s[4] == "-" and s[7] == "-":
            try:
                return datetime.strptime(s[:10], "%Y-%m-%d").date()
            except ValueError:
                return None
        return None

    def _to_datetime(value: Any) -> datetime | None:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            return value
        s = str(value).strip().strip("\ufeff")
        if not s:
            return None
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(s[:26], fmt)
            except ValueError:
                continue
        return None

    def _truthy_active(value: Any) -> bool:
        if value is None or value == "":
            return True
        s = str(value).strip().lower()
        return s not in ("0", "false", "no", "n")

    def _infer_staff_role(designation: str, staff_cat: str, description: str, can_consult: Any) -> str:
        blob = f"{designation} {staff_cat} {description}".upper()
        cc = False
        if isinstance(can_consult, bool):
            cc = can_consult
        else:
            cc = str(can_consult).strip() in ("1", "true", "yes", "y")
        if cc or "DOCTOR" in blob or "PHYSICIAN" in blob or "CONSULT" in blob:
            return "DOCTOR"
        if "NURSE" in blob:
            return "NURSE"
        if "LAB" in blob:
            return "LAB_TECH"
        if "RAD" in blob or "RADIO" in blob:
            return "RADIOLOGY_TECH"
        if "PHARM" in blob:
            return "PHARMACIST"
        if "IVF" in blob or "EMBRYO" in blob:
            return "IVF_SPECIALIST"
        if "ADMIN" in blob:
            return "ADMIN"
        return "RECEPTIONIST"

    def _split_staff_name(full: str) -> tuple[str, str]:
        s = (full or "").strip()
        if not s:
            return "Legacy", "User"
        parts = s.split()
        if len(parts) == 1:
            return parts[0], "Staff"
        return parts[0], " ".join(parts[1:])

    def _unique_staff_username(base: str, legacy_uid: int) -> str:
        reserved = {"admin", "migration_doctor", "migration_pharmacist", "migration_receptionist"}
        c = ((base or "").strip().lower() or f"user{legacy_uid}")[:120]
        if c in reserved:
            c = f"{c}_{legacy_uid}"
        candidate = c[:150]
        step = 0
        while User.objects.filter(username=candidate).exists():
            step += 1
            candidate = f"{c[:120]}_{legacy_uid}_{step}"[:150]
        return candidate

    def _clean_email(value: Any) -> str | None:
        from django.core.exceptions import ValidationError as DjangoValidationError  # pylint: disable=import-outside-toplevel
        from django.core.validators import validate_email  # pylint: disable=import-outside-toplevel

        if value is None or str(value).strip() == "":
            return None
        s = str(value).strip().lower()
        try:
            validate_email(s)
            return s
        except DjangoValidationError:
            return None

    def _ensure_aware(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    def _map_gender(value: Any) -> str | None:
        raw = (str(value).strip().upper() if value is not None else "")
        mapping = {
            "M": "MALE",
            "MALE": "MALE",
            "F": "FEMALE",
            "FEMALE": "FEMALE",
            "O": "OTHER",
            "OTHER": "OTHER",
        }
        return mapping.get(raw) or None

    def _map_visit_type(value: Any) -> str | None:
        raw = (str(value).strip().upper() if value is not None else "")
        mapping = {
            "CONSULTATION": "CONSULTATION",
            "FOLLOW_UP": "FOLLOW_UP",
            "FOLLOWUP": "FOLLOW_UP",
            "EMERGENCY": "EMERGENCY",
            "ROUTINE": "ROUTINE",
            "SPECIALIST": "SPECIALIST",
        }
        return mapping.get(raw) or "CONSULTATION"

    def _map_visit_status(value: Any) -> str:
        # Legacy CLOSED visits may fail current Visit.clean() on create (consultation-required closure),
        # so we keep migrated visits OPEN in this first-pass adapter.
        _ = value
        return "OPEN"

    def _map_payment_status(value: Any) -> str:
        raw = (str(value).strip().upper() if value is not None else "")
        allowed = {
            "UNPAID",
            "PARTIALLY_PAID",
            "PAID",
            "INSURANCE_PENDING",
            "INSURANCE_CLAIMED",
            "SETTLED",
        }
        return raw if raw in allowed else "UNPAID"

    def _map_appointment_status(value: Any) -> str:
        raw = (str(value).strip().upper() if value is not None else "")
        mapping = {
            "SCHEDULED": "SCHEDULED",
            "CONFIRMED": "CONFIRMED",
            "COMPLETED": "COMPLETED",
            "CANCELLED": "CANCELLED",
            "NO_SHOW": "NO_SHOW",
            "NOSHOW": "NO_SHOW",
        }
        return mapping.get(raw) or "SCHEDULED"

    def _get_default_creator() -> User:
        user = (
            User.objects.filter(is_superuser=True).order_by("id").first()
            or User.objects.filter(role__in=["ADMIN", "RECEPTIONIST"]).order_by("id").first()
            or User.objects.filter(role="DOCTOR").order_by("id").first()
            or User.objects.order_by("id").first()
        )
        if not user:
            raise RuntimeError("No users found. Create at least one user before loading appointments.")
        return user

    def _get_pharmacist_creator() -> User:
        user = User.objects.filter(username="migration_pharmacist").first()
        return user or _get_default_creator()

    for payload in payloads:
        target_model = payload["target_model"]
        field_values = payload["field_values"]
        source_table = payload.get("source_table", "")
        source_row = payload.get("source_row") or {}

        if dry_run:
            _inc(target_model)
            continue

        if source_table == "tblUsers" and target_model == "apps.users.User":
            legacy_uid = _to_int(source_row.get("UserID"))
            raw_username = (source_row.get("UserName") or "").strip()
            if legacy_uid is None or not raw_username:
                logger.warning("Skipping staff row without UserID/UserName: %s", source_row)
                continue
            base_slug = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in raw_username)[:80]
            username = _unique_staff_username(base_slug, legacy_uid)
            fn, ln = _split_staff_name(str(source_row.get("FullName") or ""))
            role = _infer_staff_role(
                str(source_row.get("Designation") or ""),
                str(source_row.get("StaffCategory") or ""),
                str(source_row.get("Description") or ""),
                source_row.get("CanConsult"),
            )
            spec = (str(source_row.get("Designation") or "").strip())[:120]
            email = f"lifeway_uid{legacy_uid}@example.com"
            def _staff_user_write() -> User:
                user_inner, created_inner = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "first_name": fn[:255],
                        "last_name": ln[:255],
                        "password": make_password(get_random_string(24)),
                        "role": role,
                        "specialization": spec if role == "DOCTOR" else "",
                        "is_active": _truthy_active(source_row.get("Active")),
                        "is_staff": role == "ADMIN",
                        "is_superuser": False,
                    },
                )
                if not created_inner:
                    user_inner.email = email
                    user_inner.first_name = fn[:255]
                    user_inner.last_name = ln[:255]
                    user_inner.role = role
                    user_inner.specialization = spec if role == "DOCTOR" else ""
                    user_inner.is_active = _truthy_active(source_row.get("Active"))
                    user_inner.is_staff = role == "ADMIN"
                user_inner.set_unusable_password()
                user_inner.save()
                return user_inner

            user = _sqlite_lock_retry("tblUsers", _staff_user_write)
            legacy_user_pk_by_id[legacy_uid] = user.id
            _inc(target_model)
            continue

        if source_table == "tblOutPatientRecord" and target_model == "apps.patients.Patient":
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if legacy_patient_id is None:
                logger.warning("Skipping patient row without PatientID: %s", source_row)
                continue

            patient_id = _patient_external_id(legacy_patient_id)
            first_name = (source_row.get("Othernames") or "").strip() or "Unknown"
            last_name = (source_row.get("Surname") or "").strip() or "Unknown"
            dob = _parse_date_only(source_row.get("DOB"))
            defaults = {
                "first_name": first_name,
                "last_name": last_name,
                "gender": _map_gender(source_row.get("Sex")),
                "date_of_birth": dob,
                "phone": (source_row.get("PhoneNo") or None),
                "email": _clean_email(source_row.get("Email")),
                "address": (source_row.get("Address") or None),
                "is_active": True,
            }
            patient, _ = _sqlite_lock_retry(
                "tblOutPatientRecord",
                lambda: Patient.objects.update_or_create(patient_id=patient_id, defaults=defaults),
            )
            patient_id_map[legacy_patient_id] = patient.id
            _inc(target_model)
            continue

        if source_table == "tblPatientVisits" and target_model == "apps.visits.Visit":
            legacy_visit_id = _to_int(source_row.get("VisitID"))
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if legacy_visit_id is None or legacy_patient_id is None:
                logger.warning("Skipping visit row missing VisitID/PatientID: %s", source_row)
                continue

            patient_pk = patient_id_map.get(legacy_patient_id)
            if not patient_pk:
                patient_id = _patient_external_id(legacy_patient_id)
                patient = Patient.objects.filter(patient_id=patient_id).first()
                if not patient:
                    logger.warning("Skipping visit %s; patient not found for legacy id %s", legacy_visit_id, legacy_patient_id)
                    continue
                patient_pk = patient.id
                patient_id_map[legacy_patient_id] = patient_pk

            created_dt = _ensure_aware(_to_datetime(source_row.get("Date"))) or timezone.now()
            chief_complaint = (source_row.get("ChiefComplaint") or source_row.get("Reason") or "").strip() or None
            clinic_name = (source_row.get("ClinicName") or "").strip()
            legacy_clinic_id = _to_int(source_row.get("ClinicID"))
            if clinic_name:
                visit_service_area = clinic_name[:200]
            elif legacy_clinic_id is not None:
                visit_service_area = f"ChargeItem {legacy_clinic_id}"[:200]
            else:
                visit_service_area = None

            # Avoid Visit.objects.update_or_create on SQLite: Django may use SELECT … FOR UPDATE and worsen locking.
            def _visit_write() -> Visit:
                existing = Visit.objects.filter(patient_id=patient_pk, created_at=created_dt).first()
                vt = _map_visit_type(source_row.get("VisitType"))
                st = _map_visit_status(source_row.get("Status"))
                ps = _map_payment_status(source_row.get("PaymentStatus"))
                if existing:
                    existing.visit_type = vt
                    existing.chief_complaint = chief_complaint
                    existing.status = st
                    existing.payment_status = ps
                    existing.service_area = visit_service_area
                    existing.save()
                    return existing
                return Visit.objects.create(
                    patient_id=patient_pk,
                    created_at=created_dt,
                    visit_type=vt,
                    chief_complaint=chief_complaint,
                    status=st,
                    payment_status=ps,
                    service_area=visit_service_area,
                )

            visit = _sqlite_lock_retry("tblPatientVisits", _visit_write)
            visit_id_map[legacy_visit_id] = visit.id

            if _visit_row_has_op_narrative(source_row):

                def _consultation_narrative_write() -> None:
                    hist, exam, diag, clin_notes = _consultation_fields_from_patient_visit(source_row, legacy_visit_id)
                    doctor = User.objects.filter(username="migration_doctor").first() or User.objects.filter(
                        role="DOCTOR"
                    ).order_by("id").first()
                    has_doc = bool(doctor and getattr(doctor, "role", None) == "DOCTOR")
                    payload: dict[str, Any] = {
                        "history": hist,
                        "examination": exam,
                        "diagnosis": diag,
                        "clinical_notes": clin_notes,
                    }
                    if has_doc:
                        payload["status"] = "ACTIVE"
                        payload["created_by_id"] = doctor.id
                    else:
                        payload["status"] = "PENDING"
                        payload["created_by_id"] = None
                    qs = Consultation.objects.filter(visit_id=visit.id)
                    if qs.exists():
                        qs.update(**payload)
                        return
                    Consultation.objects.bulk_create(
                        [
                            Consultation(
                                visit_id=visit.id,
                                history=hist,
                                examination=exam,
                                diagnosis=diag,
                                clinical_notes=clin_notes,
                                status=payload.get("status", "PENDING") or "PENDING",
                                created_by_id=payload.get("created_by_id"),
                            )
                        ]
                    )

                try:
                    _sqlite_lock_retry("tblPatientVisits_consultation", _consultation_narrative_write)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning("Consultation narrative for visit %s failed (visit saved): %s", legacy_visit_id, exc)

            _inc(target_model)
            continue

        if source_table == "tblPatientPayment" and target_model == "apps.billing.Payment":
            legacy_pay_id = _to_int(source_row.get("PatientPayID"))
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if legacy_pay_id is None or legacy_patient_id is None:
                logger.warning("Skipping patient payment row missing PatientPayID/PatientID: %s", source_row)
                continue

            amt = _to_decimal(source_row.get("PayAmount")) or Decimal("0")
            if amt is None or amt <= 0:
                logger.warning("Skipping patient payment %s; non-positive amount", legacy_pay_id)
                continue

            pay_dt = _ensure_aware(_to_datetime(source_row.get("PaymentDate"))) or timezone.now()
            patient_pk = patient_id_map.get(legacy_patient_id)
            if not patient_pk:
                patient = Patient.objects.filter(patient_id=_patient_external_id(legacy_patient_id)).only("id").first()
                if patient:
                    patient_pk = patient.id
                    patient_id_map[legacy_patient_id] = patient_pk
            if not patient_pk:
                logger.warning(
                    "Skipping patient payment %s; patient not found for legacy id %s",
                    legacy_pay_id,
                    legacy_patient_id,
                )
                continue

            same_day = list(Visit.objects.filter(patient_id=patient_pk, created_at__date=pay_dt.date()).only("id", "created_at"))
            cands = same_day or list(Visit.objects.filter(patient_id=patient_pk).only("id", "created_at").order_by("created_at")[:1000])
            if not cands:
                logger.warning(
                    "Skipping patient payment %s; no visit for patient %s to attach payment",
                    legacy_pay_id,
                    legacy_patient_id,
                )
                continue
            visit_pk = min(
                cands,
                key=lambda v: abs((v.created_at - pay_dt).total_seconds()) if v.created_at else float("inf"),
            ).id

            receptionist = User.objects.filter(username="migration_receptionist").first() or User.objects.filter(
                role="RECEPTIONIST"
            ).order_by("id").first()
            if not receptionist or getattr(receptionist, "role", None) != "RECEPTIONIST":
                logger.warning(
                    "Skipping patient payment %s; no RECEPTIONIST user (create migration_receptionist via ensure_migration_seed_users)",
                    legacy_pay_id,
                )
                continue

            def _map_legacy_payment_status(raw: Any) -> str:
                s = (str(raw or "").strip().upper())
                if any(x in s for x in ("REFUND", "REVERSE", "VOID")):
                    return "REFUNDED"
                if any(x in s for x in ("PAID", "CLEAR", "COMPLETE", "POST", "OK", "SUCCESS")):
                    return "CLEARED"
                if "PART" in s:
                    return "PARTIAL"
                if any(x in s for x in ("FAIL", "DECLIN", "REJECT", "BOUNCE")):
                    return "FAILED"
                return "PENDING"

            def _map_legacy_payment_method(raw_hmo: Any) -> str:
                if (str(raw_hmo or "").strip()):
                    return "INSURANCE"
                return "CASH"

            pay_status = _map_legacy_payment_status(source_row.get("LegacyStatus"))
            pay_method = _map_legacy_payment_method(source_row.get("HMOCode"))
            receipt_no = _to_int(source_row.get("ReceiptNo"))
            tx_ref = (str(receipt_no) if receipt_no is not None else "")[:255]

            tag = f"[Legacy PatientPayID:{legacy_pay_id}]"
            svc = (str(source_row.get("ServiceLine") or "")).strip()
            dx = (str(source_row.get("DiagnosisLine") or "")).strip()
            payer = (str(source_row.get("PayerName") or "")).strip()
            note_parts = [tag, ""]
            if payer:
                note_parts.append(f"Payer (legacy): {payer}")
            if svc:
                note_parts.append(f"Service (legacy): {svc[:4000]}")
            if dx:
                note_parts.append(f"Diagnosis (legacy): {dx[:1500]}")
            notes = _truncate_migration_text("\n".join(note_parts), max_chars=8000)

            def _payment_write() -> None:
                existing = Payment.objects.filter(notes__startswith=tag).first()
                if existing:
                    Payment.objects.filter(pk=existing.pk).update(
                        visit_id=visit_pk,
                        amount=amt,
                        payment_method=pay_method,
                        status=pay_status,
                        transaction_reference=tx_ref,
                        notes=notes,
                        processed_by_id=receptionist.id,
                        created_at=pay_dt,
                    )
                    return
                Payment.objects.bulk_create(
                    [
                        Payment(
                            visit_id=visit_pk,
                            amount=amt,
                            payment_method=pay_method,
                            status=pay_status,
                            transaction_reference=tx_ref,
                            notes=notes,
                            processed_by_id=receptionist.id,
                        )
                    ]
                )
                created = Payment.objects.filter(notes__startswith=tag).first()
                if created:
                    Payment.objects.filter(pk=created.pk).update(created_at=pay_dt)

            try:
                _sqlite_lock_retry("tblPatientPayment", _payment_write)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Skipping patient payment %s: %s", legacy_pay_id, exc)
                continue

            if pay_status == "CLEARED":
                try:
                    Visit.objects.filter(pk=visit_pk, payment_status="UNPAID").update(payment_status="PAID")
                except Exception:
                    pass

            _inc(target_model)
            continue

        if source_table == "tblTempReceipt" and target_model == "apps.billing.VisitCharge":
            line_id = _to_int(source_row.get("TempReceiptID"))
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if line_id is None or legacy_patient_id is None:
                logger.warning("Skipping receipt line missing TempReceiptID/PatientID: %s", source_row)
                continue

            amt = _to_decimal(source_row.get("LineAmount")) or Decimal("0")
            if amt is None or amt <= 0:
                continue

            line_dt = _ensure_aware(_to_datetime(source_row.get("LineDate"))) or timezone.now()
            patient_pk = patient_id_map.get(legacy_patient_id)
            if not patient_pk:
                patient = Patient.objects.filter(patient_id=_patient_external_id(legacy_patient_id)).only("id").first()
                if patient:
                    patient_pk = patient.id
                    patient_id_map[legacy_patient_id] = patient_pk
            if not patient_pk:
                logger.warning("Skipping receipt line %s; patient not found for legacy id %s", line_id, legacy_patient_id)
                continue

            same_day = list(Visit.objects.filter(patient_id=patient_pk, created_at__date=line_dt.date()).only("id", "created_at"))
            cands = same_day or list(Visit.objects.filter(patient_id=patient_pk).only("id", "created_at").order_by("created_at")[:1000])
            if not cands:
                logger.warning("Skipping receipt line %s; no visit for patient %s", line_id, legacy_patient_id)
                continue
            visit_pk = min(
                cands,
                key=lambda v: abs((v.created_at - line_dt).total_seconds()) if v.created_at else float("inf"),
            ).id

            svc = (str(source_row.get("ServiceLine") or "")).strip()
            field_nm = (str(source_row.get("FieldName") or "")).strip()
            cat = _charge_category_from_receipt_line(field_nm, svc)
            tag = f"[Legacy TempReceipt:{line_id}]"
            desc_body = (svc or field_nm or "Receipt line").strip() or "Receipt line"
            description = f"{tag} {desc_body}".strip()[:255]

            def _receipt_line_write() -> None:
                existing = VisitCharge.objects.filter(visit_id=visit_pk, description__startswith=tag).first()
                if existing:
                    VisitCharge.objects.filter(pk=existing.pk).update(
                        category=cat,
                        description=description,
                        amount=amt,
                        created_by_system=True,
                        created_at=line_dt,
                    )
                    return
                VisitCharge.objects.bulk_create(
                    [
                        VisitCharge(
                            visit_id=visit_pk,
                            category=cat,
                            description=description,
                            amount=amt,
                            created_by_system=True,
                        )
                    ]
                )
                created_vc = VisitCharge.objects.filter(visit_id=visit_pk, description__startswith=tag).first()
                if created_vc:
                    VisitCharge.objects.filter(pk=created_vc.pk).update(created_at=line_dt)

            try:
                _sqlite_lock_retry("tblTempReceipt", _receipt_line_write)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Skipping receipt line %s: %s", line_id, exc)
                continue

            _inc(target_model)
            continue

        if source_table == "tblLabRequest" and target_model == "apps.laboratory.LabOrder":
            legacy_req = _to_int(source_row.get("RequestID"))
            legacy_visit_id = _to_int(source_row.get("VisitID"))
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if legacy_req is None:
                logger.warning("Skipping lab request without RequestID: %s", source_row)
                continue
            request_dt = _ensure_aware(_to_datetime(source_row.get("DateRequested"))) or timezone.now()
            visit_pk = visit_id_map.get(legacy_visit_id) if legacy_visit_id else None
            if not visit_pk and legacy_patient_id is not None:
                patient_pk = patient_id_map.get(legacy_patient_id)
                if not patient_pk:
                    patient = Patient.objects.filter(patient_id=_patient_external_id(legacy_patient_id)).only("id").first()
                    if patient:
                        patient_pk = patient.id
                        patient_id_map[legacy_patient_id] = patient_pk
                if patient_pk:
                    same_day = list(Visit.objects.filter(patient_id=patient_pk, created_at__date=request_dt.date()).only("id", "created_at"))
                    cands = same_day or list(Visit.objects.filter(patient_id=patient_pk).only("id", "created_at").order_by("created_at")[:1000])
                    if cands:
                        visit_pk = min(
                            cands,
                            key=lambda v: abs((v.created_at - request_dt).total_seconds()) if v.created_at else float("inf"),
                        ).id
            if not visit_pk:
                logger.warning(
                    "Skipping lab request %s; could not resolve visit (legacy VisitID=%s, PatientID=%s)",
                    legacy_req,
                    legacy_visit_id,
                    legacy_patient_id,
                )
                continue

            doctor = User.objects.filter(username="migration_doctor").first() or User.objects.filter(
                role="DOCTOR"
            ).order_by("id").first()
            if not doctor or getattr(doctor, "role", None) != "DOCTOR":
                logger.warning("Skipping lab request %s; no DOCTOR user for ordered_by", legacy_req)
                continue

            def _map_lab_order_status(raw: Any) -> str:
                s = (str(raw or "").strip().upper())
                if any(x in s for x in ("RESULT", "READY", "COMPLETE", "DONE", "AUTHORIZED", "VALIDATED")):
                    return LabOrder.Status.RESULT_READY
                if any(x in s for x in ("SAMPLE", "COLLECT", "SPECIMEN")):
                    return LabOrder.Status.SAMPLE_COLLECTED
                return LabOrder.Status.ORDERED

            status_val = _map_lab_order_status(source_row.get("Status"))
            tests_raw = (str(source_row.get("TestsRequested") or "")).strip()
            tests_list = [t.strip() for t in tests_raw.split("|") if t.strip()] if tests_raw else []
            if not tests_list:
                tests_list = ["Legacy lab order"]

            diagnosis = (str(source_row.get("Diagnosis") or "")).strip()
            tag = f"[Legacy RequestID:{legacy_req}]"
            clinical = f"{tag}\n{diagnosis}".strip() if diagnosis else tag

            def _consultation_pk_for_visit(vpk: int) -> int:
                existing_id = Consultation.objects.filter(visit_id=vpk).values_list("id", flat=True).first()
                if existing_id is not None:
                    return int(existing_id)
                try:
                    Consultation.objects.bulk_create([Consultation(visit_id=vpk, status="PENDING")])
                except IntegrityError:
                    pass
                again = Consultation.objects.filter(visit_id=vpk).values_list("id", flat=True).first()
                if again is None:
                    raise RuntimeError(f"Could not ensure consultation for visit pk={vpk}")
                return int(again)

            def _lab_write() -> None:
                cons_pk = _consultation_pk_for_visit(visit_pk)
                existing = LabOrder.objects.filter(visit_id=visit_pk, clinical_indication__startswith=tag).first()
                if existing:
                    LabOrder.objects.filter(pk=existing.pk).update(
                        consultation_id=cons_pk,
                        ordered_by_id=doctor.id,
                        tests_requested=tests_list,
                        clinical_indication=clinical,
                        status=status_val,
                    )
                    lab_order_pk_by_request_id[legacy_req] = existing.pk
                    return
                LabOrder.objects.bulk_create(
                    [
                        LabOrder(
                            visit_id=visit_pk,
                            consultation_id=cons_pk,
                            ordered_by_id=doctor.id,
                            tests_requested=tests_list,
                            clinical_indication=clinical,
                            status=status_val,
                        )
                    ]
                )
                got = LabOrder.objects.filter(visit_id=visit_pk, clinical_indication__startswith=tag).first()
                if got:
                    lab_order_pk_by_request_id[legacy_req] = got.pk

            try:
                _sqlite_lock_retry("tblLabRequest", _lab_write)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Skipping lab request %s: %s", legacy_req, exc)
                continue
            _inc(target_model)
            continue

        if source_table == "tblLabResult" and target_model == "apps.laboratory.LabResult":
            legacy_req = _to_int(source_row.get("RequestID"))
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if legacy_req is None:
                logger.warning("Skipping lab result row without RequestID: %s", source_row)
                continue
            reported_dt = _ensure_aware(_to_datetime(source_row.get("Date")))
            tag_o = f"[Legacy RequestID:{legacy_req}]"
            order_pk = lab_order_pk_by_request_id.get(legacy_req)
            if not order_pk:
                found = LabOrder.objects.filter(clinical_indication__startswith=tag_o).values_list("id", flat=True).first()
                if found is not None:
                    order_pk = int(found)
            if not order_pk:
                visit_pk_fallback: int | None = None
                if legacy_patient_id is not None:
                    patient_pk = patient_id_map.get(legacy_patient_id)
                    if not patient_pk:
                        patient = Patient.objects.filter(patient_id=_patient_external_id(legacy_patient_id)).only("id").first()
                        if patient:
                            patient_pk = patient.id
                            patient_id_map[legacy_patient_id] = patient_pk
                    if patient_pk:
                        basis_dt = reported_dt or timezone.now()
                        same_day = list(
                            Visit.objects.filter(patient_id=patient_pk, created_at__date=basis_dt.date()).only("id", "created_at")
                        )
                        cands = same_day or list(
                            Visit.objects.filter(patient_id=patient_pk).only("id", "created_at").order_by("created_at")[:1000]
                        )
                        if cands:
                            visit_pk_fallback = min(
                                cands,
                                key=lambda v: abs((v.created_at - basis_dt).total_seconds()) if v.created_at else float("inf"),
                            ).id

                if visit_pk_fallback is not None:
                    existing_on_visit = LabOrder.objects.filter(visit_id=visit_pk_fallback).order_by("-id").first()
                    if existing_on_visit:
                        order_pk = existing_on_visit.id
                    else:
                        doctor = User.objects.filter(username="migration_doctor").first() or User.objects.filter(
                            role="DOCTOR"
                        ).order_by("id").first()
                        if doctor and getattr(doctor, "role", None) == "DOCTOR":
                            cons_id = Consultation.objects.filter(visit_id=visit_pk_fallback).values_list("id", flat=True).first()
                            if cons_id is None:
                                try:
                                    Consultation.objects.bulk_create([Consultation(visit_id=visit_pk_fallback, status="PENDING")])
                                except IntegrityError:
                                    pass
                                cons_id = Consultation.objects.filter(visit_id=visit_pk_fallback).values_list("id", flat=True).first()
                            if cons_id is not None:
                                LabOrder.objects.bulk_create(
                                    [
                                        LabOrder(
                                            visit_id=visit_pk_fallback,
                                            consultation_id=int(cons_id),
                                            ordered_by_id=doctor.id,
                                            tests_requested=["Legacy lab result fallback"],
                                            clinical_indication=f"{tag_o}\n[Auto-created from tblLabResult fallback]",
                                            status=LabOrder.Status.ORDERED,
                                        )
                                    ]
                                )
                                created_order = LabOrder.objects.filter(
                                    visit_id=visit_pk_fallback, clinical_indication__startswith=tag_o
                                ).first()
                                if created_order:
                                    order_pk = created_order.id

            if not order_pk:
                logger.warning("Skipping lab result; no resolvable LabOrder for legacy RequestID %s", legacy_req)
                continue

            body = (str(source_row.get("ResultData") or "")).strip()
            header_notes = (str(source_row.get("HeaderNotes") or "")).strip()
            auth_by = (str(source_row.get("AuthorizedBy") or "")).strip()
            tag = f"[Legacy RequestID:{legacy_req}]"
            chunks: list[str] = [tag]
            if header_notes:
                chunks.append(header_notes)
            if auth_by:
                chunks.append(f"Authorized: {auth_by}")
            if body:
                chunks.append(body)
            result_text = "\n".join(chunks).strip()
            if result_text == tag:
                logger.warning("Skipping lab result for RequestID %s; no result text or details", legacy_req)
                continue

            lab_tech = User.objects.filter(username="migration_lab_tech").first() or User.objects.filter(
                role="LAB_TECH"
            ).order_by("id").first()
            if not lab_tech:
                logger.warning(
                    "Skipping lab result for RequestID %s; no LAB_TECH user (e.g. username migration_lab_tech)",
                    legacy_req,
                )
                continue

            def _lab_result_write() -> None:
                existing_lr = LabResult.objects.filter(lab_order_id=order_pk).first()
                if existing_lr:
                    LabResult.objects.filter(pk=existing_lr.pk).update(
                        result_data=result_text,
                        recorded_by_id=lab_tech.id,
                        abnormal_flag="NORMAL",
                    )
                    if reported_dt:
                        LabResult.objects.filter(pk=existing_lr.pk).update(recorded_at=reported_dt)
                    return
                LabResult.objects.bulk_create(
                    [
                        LabResult(
                            lab_order_id=order_pk,
                            result_data=result_text,
                            abnormal_flag="NORMAL",
                            recorded_by_id=lab_tech.id,
                        )
                    ]
                )
                created_lr = LabResult.objects.filter(lab_order_id=order_pk).first()
                if created_lr and reported_dt:
                    LabResult.objects.filter(pk=created_lr.pk).update(recorded_at=reported_dt)

            try:
                _sqlite_lock_retry("tblLabResult", _lab_result_write)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Skipping lab result for RequestID %s: %s", legacy_req, exc)
                continue
            _inc(target_model)
            continue

        if source_table == "tblRadRequest" and target_model == "apps.radiology.RadiologyRequest":
            legacy_req = _to_int(source_row.get("RequestID"))
            legacy_visit_id = _to_int(source_row.get("VisitID"))
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if legacy_req is None:
                logger.warning("Skipping radiology request without RequestID: %s", source_row)
                continue
            request_dt = _ensure_aware(_to_datetime(source_row.get("Date"))) or timezone.now()
            visit_pk = visit_id_map.get(legacy_visit_id) if legacy_visit_id else None
            if not visit_pk and legacy_patient_id is not None:
                patient_pk = patient_id_map.get(legacy_patient_id)
                if not patient_pk:
                    patient = Patient.objects.filter(patient_id=_patient_external_id(legacy_patient_id)).only("id").first()
                    if patient:
                        patient_pk = patient.id
                        patient_id_map[legacy_patient_id] = patient_pk
                if patient_pk:
                    same_day = list(Visit.objects.filter(patient_id=patient_pk, created_at__date=request_dt.date()).only("id", "created_at"))
                    cands = same_day or list(Visit.objects.filter(patient_id=patient_pk).only("id", "created_at").order_by("created_at")[:1000])
                    if cands:
                        visit_pk = min(
                            cands,
                            key=lambda v: abs((v.created_at - request_dt).total_seconds()) if v.created_at else float("inf"),
                        ).id
            if not visit_pk:
                logger.warning(
                    "Skipping radiology request %s; could not resolve visit (legacy VisitID=%s, PatientID=%s)",
                    legacy_req,
                    legacy_visit_id,
                    legacy_patient_id,
                )
                continue

            doctor = User.objects.filter(username="migration_doctor").first() or User.objects.filter(
                role="DOCTOR"
            ).order_by("id").first()
            if not doctor or getattr(doctor, "role", None) != "DOCTOR":
                logger.warning("Skipping radiology request %s; no DOCTOR user for ordered_by", legacy_req)
                continue

            existing_cons = Consultation.objects.filter(visit_id=visit_pk).values_list("id", flat=True).first()
            if existing_cons is None:
                try:
                    Consultation.objects.bulk_create([Consultation(visit_id=visit_pk, status="PENDING")])
                except IntegrityError:
                    pass
                existing_cons = Consultation.objects.filter(visit_id=visit_pk).values_list("id", flat=True).first()
            if existing_cons is None:
                logger.warning("Skipping radiology request %s; could not ensure consultation for visit %s", legacy_req, visit_pk)
                continue

            def _map_radiology_status(raw: Any) -> str:
                s = (str(raw or "").strip().upper())
                if any(x in s for x in ("COMPLETE", "DONE", "RESULT", "REPORT", "CLOSED")):
                    return "COMPLETED"
                return "PENDING"

            investigations_raw = (str(source_row.get("Investigations") or "")).strip()
            studies = [x.strip() for x in investigations_raw.split("|") if x.strip()] if investigations_raw else []
            study_type = studies[0] if studies else "General Study"
            instructions = f"Investigations: {'; '.join(studies)}"[:2000] if studies else ""
            diagnosis = (str(source_row.get("Diagnosis") or "")).strip()
            status_val = _map_radiology_status(source_row.get("Status"))
            tag = f"[Legacy RadRequestID:{legacy_req}]"
            indication = f"{tag}\n{diagnosis}".strip() if diagnosis else tag

            def _rad_write() -> None:
                existing_rr = RadiologyRequest.objects.filter(visit_id=visit_pk, clinical_indication__startswith=tag).first()
                if existing_rr:
                    RadiologyRequest.objects.filter(pk=existing_rr.pk).update(
                        consultation_id=int(existing_cons),
                        ordered_by_id=doctor.id,
                        study_type=study_type[:255],
                        clinical_indication=indication,
                        instructions=instructions,
                        status=status_val,
                    )
                    return
                RadiologyRequest.objects.bulk_create(
                    [
                        RadiologyRequest(
                            visit_id=visit_pk,
                            consultation_id=int(existing_cons),
                            ordered_by_id=doctor.id,
                            study_type=study_type[:255],
                            clinical_indication=indication,
                            instructions=instructions,
                            status=status_val,
                        )
                    ]
                )

            try:
                _sqlite_lock_retry("tblRadRequest", _rad_write)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Skipping radiology request %s: %s", legacy_req, exc)
                continue
            _inc(target_model)
            continue

        if source_table == "tblRadResult" and target_model == "apps.radiology.RadiologyRequest":
            legacy_req = _to_int(source_row.get("RequestID"))
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if legacy_req is None:
                logger.warning("Skipping radiology result row without RequestID: %s", source_row)
                continue

            tag = f"[Legacy RadRequestID:{legacy_req}]"
            rr = RadiologyRequest.objects.filter(clinical_indication__startswith=tag).first()
            report_dt = _ensure_aware(_to_datetime(source_row.get("Date")))

            if not rr and legacy_patient_id is not None:
                patient_pk = patient_id_map.get(legacy_patient_id)
                if not patient_pk:
                    patient = Patient.objects.filter(patient_id=_patient_external_id(legacy_patient_id)).only("id").first()
                    if patient:
                        patient_pk = patient.id
                        patient_id_map[legacy_patient_id] = patient_pk
                if patient_pk:
                    basis_dt = report_dt or timezone.now()
                    cands = list(
                        RadiologyRequest.objects.filter(visit__patient_id=patient_pk)
                        .select_related("visit")
                        .order_by("-id")[:500]
                    )
                    if cands:
                        rr = min(
                            cands,
                            key=lambda x: abs((x.visit.created_at - basis_dt).total_seconds())
                            if x.visit and x.visit.created_at
                            else float("inf"),
                        )

            if not rr:
                logger.warning("Skipping radiology result %s; no RadiologyRequest match", legacy_req)
                continue

            report_text = (str(source_row.get("ReportText") or "")).strip()
            if not report_text:
                logger.warning("Skipping radiology result %s; empty report text", legacy_req)
                continue

            reporter = User.objects.filter(username="migration_radiology_tech").first() or User.objects.filter(
                role="RADIOLOGY_TECH"
            ).order_by("id").first()

            def _rad_result_write() -> None:
                update_payload: dict[str, Any] = {
                    "report": report_text,
                    "status": "COMPLETED",
                }
                if report_dt:
                    update_payload["report_date"] = report_dt
                if reporter:
                    update_payload["reported_by_id"] = reporter.id
                RadiologyRequest.objects.filter(pk=rr.pk).update(**update_payload)

            try:
                _sqlite_lock_retry("tblRadResult", _rad_result_write)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Skipping radiology result %s: %s", legacy_req, exc)
                continue
            _inc(target_model)
            continue

        if source_table == "tblVitalSign" and target_model == "apps.clinical.VitalSigns":
            legacy_vsid = _to_int(source_row.get("VSID"))
            legacy_visit_id = _to_int(source_row.get("VisitID"))
            if legacy_vsid is None or legacy_visit_id is None:
                logger.warning("Skipping vital without VSID or unresolved VisitID: %s", source_row)
                continue
            visit_pk = visit_id_map.get(legacy_visit_id)
            if not visit_pk:
                logger.warning(
                    "Skipping vital %s; visit not loaded for legacy visit id %s",
                    legacy_vsid,
                    legacy_visit_id,
                )
                continue

            recorded_dt = _ensure_aware(_to_datetime(source_row.get("RecordedAt"))) or timezone.now()
            tag = f"[Legacy VSID:{legacy_vsid}]"
            temp_c = _parse_temperature_celsius(source_row.get("Temperature"))
            sys_bp, dia_bp = _parse_bp_string(source_row.get("BloodPressure"))
            pulse = _parse_vital_int(source_row.get("Pulse"), 30, 250)
            resp = _parse_vital_int(source_row.get("Resp"), 8, 50)
            spo2 = _parse_vital_decimal(source_row.get("SPO2"), Decimal("0"), Decimal("100"))
            weight = _parse_vital_decimal(source_row.get("Wt"), Decimal("0.1"), Decimal("500"))
            height = _parse_vital_decimal(source_row.get("Ht"), Decimal("0.1"), Decimal("300"))

            if (
                temp_c is None
                and sys_bp is None
                and pulse is None
                and resp is None
                and spo2 is None
                and weight is None
                and height is None
            ):
                logger.warning("Skipping vital %s; no values within validation range", legacy_vsid)
                continue

            recorder = _get_default_creator()

            def _vital_write() -> None:
                existing = VitalSigns.objects.filter(visit_id=visit_pk, notes__startswith=tag).first()
                if existing:
                    existing.recorded_by = recorder
                    existing.temperature = temp_c
                    existing.systolic_bp = sys_bp
                    existing.diastolic_bp = dia_bp
                    existing.pulse = pulse
                    existing.respiratory_rate = resp
                    existing.oxygen_saturation = spo2
                    existing.weight = weight
                    existing.height = height
                    existing.recorded_at = recorded_dt
                    existing.notes = tag
                    existing.save()
                    return
                # auto_now_add on recorded_at overwrites any value passed to create(); set legacy time via update().
                created = VitalSigns.objects.create(
                    visit_id=visit_pk,
                    recorded_by=recorder,
                    temperature=temp_c,
                    systolic_bp=sys_bp,
                    diastolic_bp=dia_bp,
                    pulse=pulse,
                    respiratory_rate=resp,
                    oxygen_saturation=spo2,
                    weight=weight,
                    height=height,
                    notes=tag,
                )
                VitalSigns.objects.filter(pk=created.pk).update(recorded_at=recorded_dt)

            try:
                _sqlite_lock_retry("tblVitalSign", _vital_write)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Skipping vital %s after validation/DB error: %s", legacy_vsid, exc)
                continue
            _inc(target_model)
            continue

        if source_table == "tblOPDAppointment" and target_model == "apps.appointments.Appointment":
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if legacy_patient_id is None:
                logger.warning("Skipping appointment row without PatientID: %s", source_row)
                continue

            patient_pk = patient_id_map.get(legacy_patient_id)
            if not patient_pk:
                patient = Patient.objects.filter(patient_id=_patient_external_id(legacy_patient_id)).first()
                if not patient:
                    logger.warning("Skipping appointment; patient not found for legacy id %s", legacy_patient_id)
                    continue
                patient_pk = patient.id
                patient_id_map[legacy_patient_id] = patient_pk

            # DoctorID in LIFEWAY CSV is legacy tblUsers.UserID (from ToSee -> Staff -> User in export).
            legacy_doctor_id = _to_int(source_row.get("DoctorID"))
            doctor = None
            if legacy_doctor_id is not None:
                doc_pk = legacy_user_pk_by_id.get(legacy_doctor_id)
                if doc_pk:
                    cand = User.objects.filter(pk=doc_pk).first()
                    if cand and cand.role == "DOCTOR":
                        doctor = cand
            if not doctor:
                doctor = User.objects.filter(username="migration_doctor").first()
            if not doctor:
                doctor = User.objects.filter(role="DOCTOR").order_by("id").first()
            if not doctor:
                logger.warning("Skipping appointment; no doctor available.")
                continue

            creator = _get_default_creator()
            source_dt = _ensure_aware(_to_datetime(source_row.get("AppointmentDate"))) or timezone.now()
            if source_dt <= timezone.now():
                appointment_dt = timezone.now() + timedelta(minutes=1)
                reason_prefix = f"[Legacy datetime: {source_dt.isoformat()}] "
            else:
                appointment_dt = source_dt
                reason_prefix = ""

            reason = (source_row.get("Reason") or "").strip()
            notes = (source_row.get("Notes") or "").strip()
            if reason_prefix:
                notes = f"{reason_prefix}{notes}".strip()

            clinic_raw = (source_row.get("Clinic") or "").strip()
            appt_service_area = clinic_raw[:200] if clinic_raw else None

            legacy_appointment_id = _to_int(source_row.get("AppointmentID"))
            appt_tag = f"[Legacy AppID:{legacy_appointment_id}]" if legacy_appointment_id is not None else None
            if appt_tag:
                if notes.startswith(appt_tag):
                    pass
                elif notes:
                    notes = f"{appt_tag} {notes}".strip()
                else:
                    notes = appt_tag

            visit_fk = None
            legacy_visit_id = _to_int(source_row.get("VisitID"))
            if legacy_visit_id is not None:
                visit_fk = visit_id_map.get(legacy_visit_id)

            status_val = _map_appointment_status(source_row.get("Status"))
            duration_val = _to_int(source_row.get("Duration")) or 30

            if appt_tag:
                existing_appt = Appointment.objects.filter(patient_id=patient_pk, notes__startswith=appt_tag).first()
                if existing_appt:

                    def _appt_tag_save() -> None:
                        existing_appt.doctor = doctor
                        existing_appt.appointment_date = appointment_dt
                        existing_appt.visit_id = visit_fk
                        existing_appt.status = status_val
                        existing_appt.reason = reason
                        existing_appt.notes = notes
                        existing_appt.service_area = appt_service_area
                        existing_appt.duration_minutes = duration_val
                        existing_appt.created_by_id = creator.id
                        existing_appt.save()

                    _sqlite_lock_retry("tblOPDAppointment(tag)", _appt_tag_save)
                    _inc(target_model)
                    continue

            def _appt_triple_write() -> None:
                appt = Appointment.objects.filter(
                    patient_id=patient_pk,
                    doctor_id=doctor.id,
                    appointment_date=appointment_dt,
                ).first()
                if appt:
                    appt.created_by_id = creator.id
                    appt.visit_id = visit_fk
                    appt.status = status_val
                    appt.reason = reason
                    appt.notes = notes
                    appt.service_area = appt_service_area
                    appt.duration_minutes = duration_val
                    appt.save()
                    return
                Appointment.objects.create(
                    patient_id=patient_pk,
                    doctor_id=doctor.id,
                    appointment_date=appointment_dt,
                    created_by_id=creator.id,
                    visit_id=visit_fk,
                    status=status_val,
                    reason=reason,
                    notes=notes,
                    service_area=appt_service_area,
                    duration_minutes=duration_val,
                )

            _sqlite_lock_retry("tblOPDAppointment", _appt_triple_write)
            _inc(target_model)
            continue

        if source_table == "tblPhamDrugItem" and target_model == "apps.pharmacy.Drug":
            legacy_drug_id = _to_int(source_row.get("DrugItemID"))
            base_name = (source_row.get("DrugName") or "").strip()
            if legacy_drug_id is None or not base_name:
                logger.warning("Skipping drug row without DrugItemID/DrugName: %s", source_row)
                continue
            drug_code = f"LIFEWAY-{legacy_drug_id}"
            price = _to_decimal(source_row.get("UnitPrice"))
            cost = _to_decimal(source_row.get("Cost"))
            if price is not None and cost is not None and price < cost:
                cost = None
            creator = _get_pharmacist_creator()
            name = base_name[:255]
            if Drug.objects.filter(name=name).exclude(drug_code=drug_code).exists():
                suffix = f" ({drug_code})"
                name = (base_name[: max(0, 255 - len(suffix))] + suffix)[:255]
            def _drug_write() -> None:
                row = Drug.objects.filter(drug_code=drug_code).first()
                if row:
                    row.name = name
                    row.sales_price = price
                    row.cost_price = cost
                    row.is_active = True
                    row.created_by_id = creator.id
                    row.save()
                    return
                Drug.objects.create(
                    drug_code=drug_code,
                    name=name,
                    sales_price=price,
                    cost_price=cost,
                    is_active=True,
                    created_by_id=creator.id,
                )

            _sqlite_lock_retry("tblPhamDrugItem", _drug_write)
            _inc(target_model)
            continue

        if source_table == "tblDrugPresItems" and target_model == "apps.pharmacy.Prescription":
            pres_item_id = _to_int(source_row.get("PresItemID"))
            legacy_patient_id = _to_int(source_row.get("PatientID"))
            if pres_item_id is None or legacy_patient_id is None:
                logger.warning("Skipping prescription line missing PresItemID/PatientID: %s", source_row)
                continue

            pres_dt = _ensure_aware(_to_datetime(source_row.get("PrescriptionDate"))) or timezone.now()
            patient_pk = patient_id_map.get(legacy_patient_id)
            if not patient_pk:
                patient = Patient.objects.filter(patient_id=_patient_external_id(legacy_patient_id)).only("id").first()
                if patient:
                    patient_pk = patient.id
                    patient_id_map[legacy_patient_id] = patient_pk
            if not patient_pk:
                logger.warning("Skipping prescription line %s; patient not found for %s", pres_item_id, legacy_patient_id)
                continue

            same_day = list(Visit.objects.filter(patient_id=patient_pk, created_at__date=pres_dt.date()).only("id", "created_at"))
            cands = same_day or list(Visit.objects.filter(patient_id=patient_pk).only("id", "created_at").order_by("created_at")[:1000])
            if not cands:
                logger.warning("Skipping prescription line %s; no visit for patient %s", pres_item_id, legacy_patient_id)
                continue
            visit_pk = min(
                cands,
                key=lambda v: abs((v.created_at - pres_dt).total_seconds()) if v.created_at else float("inf"),
            ).id

            doctor = User.objects.filter(username="migration_doctor").first() or User.objects.filter(
                role="DOCTOR"
            ).order_by("id").first()
            pharmacist = User.objects.filter(username="migration_pharmacist").first() or User.objects.filter(
                role="PHARMACIST"
            ).order_by("id").first()
            if not doctor or getattr(doctor, "role", None) != "DOCTOR":
                logger.warning("Skipping prescription line %s; no DOCTOR user for prescribed_by", pres_item_id)
                continue

            legacy_drug_id = _to_int(source_row.get("DrugItemID"))
            drug_code = f"LIFEWAY-{legacy_drug_id}" if legacy_drug_id is not None else ""
            catalog_name = (
                Drug.objects.filter(drug_code=drug_code).values_list("name", flat=True).first()
                if drug_code
                else None
            )
            raw_name = (str(source_row.get("DrugName") or "")).strip()
            drug_name = (catalog_name or raw_name or "Unknown medication")[:255]

            qty = _to_int(source_row.get("QtyIssued"))
            qty_disp = qty if qty is not None and qty > 0 else 0
            status_val = "DISPENSED" if qty_disp > 0 else "PENDING"
            dispensed = qty_disp > 0

            item_notes = (str(source_row.get("ItemNotes") or "")).strip()
            tag = f"[Legacy PresItemID:{pres_item_id}]"
            instructions = _truncate_migration_text(
                f"{tag}\nLegacy PrescriptionID={_to_int(source_row.get('PrescriptionID'))}\n{item_notes}".strip(),
                max_chars=4000,
            )
            dosage = (f"Qty issued (legacy): {qty_disp}" if qty_disp else "As directed (legacy)")[:255]
            quantity_str = str(qty_disp) if qty_disp else ""

            cons_id = Consultation.objects.filter(visit_id=visit_pk).values_list("id", flat=True).first()
            if cons_id is None:
                try:
                    Consultation.objects.bulk_create([Consultation(visit_id=visit_pk, status="PENDING")])
                except IntegrityError:
                    pass
                cons_id = Consultation.objects.filter(visit_id=visit_pk).values_list("id", flat=True).first()
            if cons_id is None:
                logger.warning("Skipping prescription line %s; could not ensure consultation for visit %s", pres_item_id, visit_pk)
                continue

            def _pres_line_write() -> None:
                existing_rx = Prescription.objects.filter(instructions__startswith=tag).first()
                if existing_rx:
                    Prescription.objects.filter(pk=existing_rx.pk).update(
                        visit_id=visit_pk,
                        consultation_id=int(cons_id),
                        drug=drug_name,
                        drug_code=drug_code[:100] if drug_code else "",
                        dosage=dosage,
                        quantity=quantity_str[:100],
                        instructions=instructions,
                        status=status_val,
                        dispensed=dispensed,
                        dispensed_date=pres_dt if dispensed else None,
                        dispensed_by_id=(
                            pharmacist.id
                            if dispensed and pharmacist and getattr(pharmacist, "role", None) == "PHARMACIST"
                            else None
                        ),
                        dispensed_quantity=quantity_str[:100] if dispensed else "",
                        prescribed_by_id=doctor.id,
                        is_emergency=True,
                        created_at=pres_dt,
                    )
                    return
                Prescription.objects.bulk_create(
                    [
                        Prescription(
                            visit_id=visit_pk,
                            consultation_id=int(cons_id),
                            drug=drug_name,
                            drug_code=drug_code[:100] if drug_code else "",
                            dosage=dosage,
                            frequency="",
                            duration="",
                            quantity=quantity_str[:100],
                            instructions=instructions,
                            status=status_val,
                            dispensed=dispensed,
                            dispensed_date=pres_dt if dispensed else None,
                            dispensed_by_id=(
                                pharmacist.id
                                if dispensed and pharmacist and getattr(pharmacist, "role", None) == "PHARMACIST"
                                else None
                            ),
                            dispensing_notes="",
                            dispensed_quantity=quantity_str[:100] if dispensed else "",
                            prescribed_by_id=doctor.id,
                            is_emergency=True,
                        )
                    ]
                )
                row = Prescription.objects.filter(instructions__startswith=tag).first()
                if row:
                    Prescription.objects.filter(pk=row.pk).update(created_at=pres_dt)

            try:
                _sqlite_lock_retry("tblDrugPresItems", _pres_line_write)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Skipping prescription line %s: %s", pres_item_id, exc)
                continue

            _inc(target_model)
            continue

        # Fallback generic loader for non-adapted rows.
        model_cls = resolve_model_class(target_model)
        model_cls.objects.create(**field_values)
        _inc(target_model)

    logger.info("Load completed (dry_run=%s): %s", dry_run, created_counts)
    return created_counts

