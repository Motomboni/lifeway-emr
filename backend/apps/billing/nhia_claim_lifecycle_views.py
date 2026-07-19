"""
NHIA claim lifecycle API.
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.visits.models import Visit
from .nhia_claim_lifecycle_service import (
    create_resubmission,
    get_or_create_draft,
    lifecycle_summary,
    mark_denied,
    mark_exported,
    mark_paid,
    mark_submitted,
    validate_submission,
)
from .nhia_claim_submission_models import NHIAClaimSubmission
from .nhia_portal_client import NHIAPortalSubmitError
from .permissions import CanExportClaimPack


def _serialize(submission: NHIAClaimSubmission) -> dict:
    visit = submission.visit
    patient = visit.patient
    return {
        "id": submission.id,
        "visit_id": visit.id,
        "patient_id": patient.id,
        "patient_name": f"{patient.first_name} {patient.last_name}".strip(),
        "national_health_id": getattr(patient, "national_health_id", "") or "",
        "id_verified": getattr(patient, "id_verified", False),
        "status": submission.status,
        "claim_reference": submission.claim_reference,
        "total_amount_ngn": str(submission.total_amount_ngn),
        "line_count": submission.line_count,
        "validation_errors": submission.validation_errors,
        "denial_reason": submission.denial_reason,
        "nhia_portal_reference": submission.nhia_portal_reference,
        "paid_amount_ngn": str(submission.paid_amount_ngn or ""),
        "submitted_at": submission.submitted_at,
        "exported_at": submission.exported_at,
        "validated_at": submission.validated_at,
        "paid_at": submission.paid_at,
        "created_at": submission.created_at,
        "updated_at": submission.updated_at,
        "resubmission_of_id": submission.resubmission_of_id,
    }


def _org_filter(request):
    org = getattr(request, "organization", None)
    if org:
        return {"organization": org}
    return {}


@api_view(["GET"])
@permission_classes([IsAuthenticated, CanExportClaimPack])
def nhia_claim_lifecycle_list(request):
    qs = NHIAClaimSubmission.objects.select_related(
        "visit", "visit__patient"
    ).filter(**_org_filter(request))
    status_filter = request.query_params.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter.upper())
    start = request.query_params.get("start_date")
    end = request.query_params.get("end_date")
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)
    return Response([_serialize(s) for s in qs[:200]])


@api_view(["GET"])
@permission_classes([IsAuthenticated, CanExportClaimPack])
def nhia_claim_lifecycle_summary(request):
    org = getattr(request, "organization", None)
    return Response(
        lifecycle_summary(
            organization=org,
            start_date=request.query_params.get("start_date"),
            end_date=request.query_params.get("end_date"),
        )
    )


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, CanExportClaimPack])
def nhia_claim_lifecycle_action(request, visit_id: int):
    visit = get_object_or_404(Visit, id=visit_id, **_org_filter(request))
    if request.method == "GET":
        submission = get_or_create_draft(visit, user=request.user)
        return Response(_serialize(submission))

    action = (request.data.get("action") or "").strip().lower()
    submission = get_or_create_draft(visit, user=request.user)

    if action == "validate":
        submission = validate_submission(submission, user=request.user)
    elif action == "export":
        submission = validate_submission(submission, user=request.user)
        if submission.validation_errors:
            return Response(
                {"detail": "Validation failed.", "errors": submission.validation_errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        submission = mark_exported(submission, user=request.user)
    elif action == "submit":
        try:
            submission = mark_submitted(
                submission,
                portal_reference=request.data.get("portal_reference", ""),
                user=request.user,
            )
        except NHIAPortalSubmitError as exc:
            return Response(
                {"detail": exc.message, "portal_error": True},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    elif action == "paid":
        from decimal import Decimal

        amount = request.data.get("paid_amount")
        submission = mark_paid(
            submission,
            paid_amount=Decimal(str(amount)) if amount is not None else None,
            user=request.user,
        )
    elif action == "deny":
        reason = request.data.get("reason") or request.data.get("denial_reason") or ""
        if not reason.strip():
            return Response(
                {"detail": "Denial reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        submission = mark_denied(submission, reason=reason, user=request.user)
    elif action == "resubmit":
        denied = (
            NHIAClaimSubmission.objects.filter(visit=visit, status="DENIED")
            .order_by("-updated_at")
            .first()
        )
        if not denied:
            return Response(
                {"detail": "No denied claim to resubmit for this visit."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        submission = create_resubmission(denied, user=request.user)
    elif action == "draft":
        pass
    else:
        return Response(
            {"detail": "Unknown action. Use draft|validate|export|submit|paid|deny|resubmit."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(_serialize(submission))
