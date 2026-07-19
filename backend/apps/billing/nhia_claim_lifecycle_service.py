"""
NHIA claim lifecycle — create, validate, export, submit, reconcile.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import models, transaction
from django.utils import timezone

from apps.billing.claim_pack_service import build_visit_claim_pack
from apps.billing.nhia_claim_submission_models import NHIAClaimSubmission
from apps.billing.nhia_portal_client import NHIAPortalSubmitError, submit_claim_to_portal


def _generate_reference(visit_id: int) -> str:
    return f"NHIA-{visit_id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"


def get_or_create_draft(visit, *, user=None) -> NHIAClaimSubmission:
    org = getattr(visit, "organization", None)
    existing = (
        NHIAClaimSubmission.objects.filter(visit=visit)
        .exclude(status__in=["PAID", "DENIED"])
        .order_by("-updated_at")
        .first()
    )
    if existing:
        if user:
            existing.updated_by = user
            existing.save(update_fields=["updated_by", "updated_at"])
        return existing
    return NHIAClaimSubmission.objects.create(
        visit=visit,
        organization=org,
        status="DRAFT",
        claim_reference=_generate_reference(visit.id),
        created_by=user,
        updated_by=user,
    )


def validate_submission(submission: NHIAClaimSubmission, *, user=None) -> NHIAClaimSubmission:
    pack = build_visit_claim_pack(submission.visit)
    errors: list[str] = []
    patient = pack.get("patient") or {}
    if not patient.get("national_health_id"):
        errors.append("Patient National Health ID is missing.")
    if patient.get("id_verified") not in (True, "True"):
        errors.append("Patient NHID is not verified.")
    lines = pack.get("lines") or []
    if not lines:
        errors.append("No NHIA billable lines on this visit.")
    total = sum(Decimal(str(line.get("amount_ngn") or 0)) for line in lines)

    submission.claim_pack_snapshot = pack
    submission.line_count = len(lines)
    submission.total_amount_ngn = total
    submission.validation_errors = errors
    submission.validated_at = timezone.now()
    submission.status = "VALIDATED" if not errors else "DRAFT"
    if user:
        submission.updated_by = user
    submission.save()
    return submission


def mark_exported(submission: NHIAClaimSubmission, *, user=None) -> NHIAClaimSubmission:
    if submission.status not in ("VALIDATED", "EXPORTED", "DENIED", "RESUBMITTED"):
        raise ValueError("Claim must be validated before export.")
    submission.status = "EXPORTED"
    submission.exported_at = timezone.now()
    if user:
        submission.updated_by = user
    submission.save(
        update_fields=["status", "exported_at", "updated_by", "updated_at"]
    )
    return submission


def mark_submitted(
    submission: NHIAClaimSubmission,
    *,
    portal_reference: str = "",
    user=None,
    skip_portal: bool = False,
) -> NHIAClaimSubmission:
    if submission.status not in ("EXPORTED", "SUBMITTED", "RESUBMITTED"):
        raise ValueError("Claim must be exported before submission.")

    if not skip_portal:
        if not submission.claim_pack_snapshot:
            submission.claim_pack_snapshot = build_visit_claim_pack(submission.visit)
        result = submit_claim_to_portal(submission)
        if not result.success:
            raise NHIAPortalSubmitError(result.message)
        portal_reference = portal_reference or result.portal_reference

    submission.status = "SUBMITTED"
    submission.submitted_at = timezone.now()
    if portal_reference:
        submission.nhia_portal_reference = portal_reference
    if user:
        submission.updated_by = user
    submission.save()
    return submission


def mark_paid(
    submission: NHIAClaimSubmission,
    *,
    paid_amount: Decimal | None = None,
    user=None,
) -> NHIAClaimSubmission:
    submission.status = "PAID"
    submission.paid_at = timezone.now()
    submission.paid_amount_ngn = paid_amount or submission.total_amount_ngn
    submission.denial_reason = ""
    if user:
        submission.updated_by = user
    submission.save()
    return submission


def mark_denied(
    submission: NHIAClaimSubmission,
    *,
    reason: str,
    user=None,
) -> NHIAClaimSubmission:
    submission.status = "DENIED"
    submission.denial_reason = reason.strip()
    if user:
        submission.updated_by = user
    submission.save()
    return submission


def create_resubmission(
    submission: NHIAClaimSubmission,
    *,
    user=None,
) -> NHIAClaimSubmission:
    if submission.status != "DENIED":
        raise ValueError("Only denied claims can be resubmitted.")
    visit = submission.visit
    resub = NHIAClaimSubmission.objects.create(
        visit=visit,
        organization=submission.organization,
        status="RESUBMITTED",
        claim_reference=_generate_reference(visit.id),
        resubmission_of=submission,
        created_by=user,
        updated_by=user,
    )
    return validate_submission(resub, user=user)


def lifecycle_summary(*, organization=None, start_date=None, end_date=None) -> dict[str, Any]:
    qs = NHIAClaimSubmission.objects.all()
    if organization:
        qs = qs.filter(organization=organization)
    if start_date:
        qs = qs.filter(created_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__date__lte=end_date)

    by_status: dict[str, int] = {}
    for row in qs.values("status").annotate(count=models.Count("id")):
        by_status[row["status"]] = row["count"]

    return {
        "total": qs.count(),
        "by_status": by_status,
        "paid_total_ngn": str(
            qs.filter(status="PAID").aggregate(
                total=models.Sum("paid_amount_ngn")
            )["total"]
            or Decimal("0")
        ),
    }
