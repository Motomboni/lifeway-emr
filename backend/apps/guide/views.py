"""Guide API views — progress, workflows, Ask Guide, sandbox visits, analytics."""

from django.contrib.auth import get_user_model
from datetime import date
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.organizations.models import OrganizationUser
from apps.patients.models import Patient
from apps.visits.models import Visit
from core.tenant import get_request_organization

from .analytics import get_guide_analytics_summary, log_guide_event
from .guide_corpus import search_guide_articles
from .guide_modules import normalize_guide_modules
from .models import UserGuideProgress, VisitWorkflowProgress
from .serializers import (
    AskGuideSerializer,
    GuideEventSerializer,
    GuideProgressUpdateSerializer,
    UserGuideProgressSerializer,
    VisitWorkflowSyncSerializer,
)
from .workflow_definitions import build_workflow_response

User = get_user_model()


def _get_or_create_progress(user) -> UserGuideProgress:
    progress, _ = UserGuideProgress.objects.get_or_create(user=user)
    return progress


def _get_visit_for_user(request, visit_id: int) -> Visit | None:
    try:
        visit = Visit.objects.select_related("patient").get(pk=visit_id)
    except Visit.DoesNotExist:
        return None
    org = get_request_organization(request)
    if org and visit.organization_id and visit.organization_id != org.id:
        return None
    return visit


def _org_guide_modules(request) -> dict[str, bool]:
    org = get_request_organization(request)
    if not org:
        from .guide_modules import DEFAULT_GUIDE_MODULES

        return dict(DEFAULT_GUIDE_MODULES)
    return normalize_guide_modules(getattr(org, "guide_modules", None))


def _user_can_view_guide_analytics(user, org) -> bool:
    if getattr(user, "role", None) == "ADMIN" or user.is_superuser:
        return True
    if not org:
        return False
    membership = OrganizationUser.objects.filter(organization=org, user=user).first()
    return membership is not None and membership.role in ("OWNER", "ADMIN")


@extend_schema(tags=["Guide"])
@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me_guide_progress(request):
    """
    GET/PATCH /api/v1/guide/me/progress/

    User guide onboarding state and preferences.
    """
    progress = _get_or_create_progress(request.user)
    org = get_request_organization(request)

    if request.method == "GET":
        serializer = UserGuideProgressSerializer(
            progress, context={"organization": org}
        )
        return Response(serializer.data)

    serializer = GuideProgressUpdateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    if data.get("step_id"):
        step_id = data["step_id"]
        if step_id not in progress.completed_steps:
            progress.completed_steps = list(progress.completed_steps) + [step_id]
            log_guide_event(
                user=request.user,
                organization=org,
                event_type="role_launch_step",
                metadata={"step_id": step_id},
            )
    if data.get("hint_id"):
        hint_id = data["hint_id"]
        if hint_id not in progress.dismissed_hints:
            progress.dismissed_hints = list(progress.dismissed_hints) + [hint_id]
            log_guide_event(
                user=request.user,
                organization=org,
                event_type="hint_dismiss",
                hint_id=hint_id,
            )
    if data.get("role_launch_role"):
        role = data["role_launch_role"]
        completed = dict(progress.role_launch_completed)
        completed[role] = True
        progress.role_launch_completed = completed
        log_guide_event(
            user=request.user,
            organization=org,
            event_type="role_launch_complete",
            metadata={"role": role},
        )
    if data.get("preferences"):
        prefs = dict(progress.guide_preferences)
        prefs.update(data["preferences"])
        progress.guide_preferences = prefs

    progress.save()
    return Response(
        UserGuideProgressSerializer(progress, context={"organization": org}).data
    )


@extend_schema(tags=["Guide"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def me_guide_progress_complete(request):
    """POST /api/v1/guide/me/progress/ — alias for step completion."""
    return me_guide_progress(request)


@extend_schema(tags=["Guide"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ask_guide(request):
    """
    POST /api/v1/guide/me/ask/

    Bounded keyword search over guide articles for the user's role.
    """
    serializer = AskGuideSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    query = serializer.validated_data["query"]
    role = getattr(request.user, "role", "DOCTOR")
    org = get_request_organization(request)
    modules = _org_guide_modules(request)
    articles = search_guide_articles(query, role, enabled_modules=modules)

    if articles:
        best = articles[0]
        log_guide_event(
            user=request.user,
            organization=org,
            event_type="ask",
            article_id=best["id"],
            target_id=best.get("guide_target") or "",
            metadata={"result_count": len(articles)},
        )

    if not articles:
        return Response(
            {
                "query": query,
                "answer": "I couldn't find a specific guide for that. Try searching for lab, billing, vitals, or appointments.",
                "articles": [],
                "guide_target": None,
            }
        )

    best = articles[0]
    steps_text = " ".join(f"{i + 1}. {s}" for i, s in enumerate(best.get("steps", [])))
    answer = f"{best['summary']} {steps_text}".strip()

    return Response(
        {
            "query": query,
            "answer": answer,
            "articles": [
                {
                    "id": a["id"],
                    "title": a["title"],
                    "summary": a["summary"],
                    "guide_target": a.get("guide_target"),
                }
                for a in articles
            ],
            "guide_target": best.get("guide_target"),
        }
    )


@extend_schema(tags=["Guide"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def log_guide_event_view(request):
    """
    POST /api/v1/guide/events/

    Record a guide UI event (spotlight, article open, command palette).
    Never accepts raw Ask Guide query text.
    """
    serializer = GuideEventSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    org = get_request_organization(request)

    event = log_guide_event(
        user=request.user,
        organization=org,
        event_type=data["event_type"],
        article_id=data.get("article_id") or "",
        target_id=data.get("target_id") or "",
        hint_id=data.get("hint_id") or "",
        metadata=data.get("metadata") or {},
    )
    return Response({"id": event.id, "event_type": event.event_type})


@extend_schema(tags=["Guide"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def guide_analytics(request):
    """
    GET /api/v1/guide/analytics/

    Admin summary of guide interactions (no PHI).
    """
    org = get_request_organization(request)
    if not _user_can_view_guide_analytics(request.user, org):
        return Response(
            {"detail": "Only clinic admins can view guide analytics."},
            status=status.HTTP_403_FORBIDDEN,
        )

    days = int(request.query_params.get("days", 30))
    summary = get_guide_analytics_summary(organization=org, days=days)
    return Response(summary)


@extend_schema(tags=["Guide"])
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def visit_workflow(request, visit_id: int):
    """
    GET /api/v1/guide/visits/{visit_id}/workflow/

    Role-filtered workflow checklists with auto-detected completion.
    """
    visit = _get_visit_for_user(request, visit_id)
    if not visit:
        return Response({"detail": "Visit not found."}, status=status.HTTP_404_NOT_FOUND)

    role = getattr(request.user, "role", "DOCTOR")
    stored_qs = VisitWorkflowProgress.objects.filter(visit=visit)
    stored = {p.pack_id: p for p in stored_qs}
    workflows = build_workflow_response(visit, role, stored)

    return Response({"visit_id": visit.id, "workflows": workflows})


@extend_schema(tags=["Guide"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def visit_workflow_sync(request, visit_id: int):
    """
    POST /api/v1/guide/visits/{visit_id}/workflow/sync/

    Sync auto-detected steps or manually complete/skip a step.
    """
    visit = _get_visit_for_user(request, visit_id)
    if not visit:
        return Response({"detail": "Visit not found."}, status=status.HTTP_404_NOT_FOUND)

    serializer = VisitWorkflowSyncSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    pack_id = serializer.validated_data["pack_id"]
    action = serializer.validated_data["action"]
    step_id = serializer.validated_data.get("step_id")

    progress, _ = VisitWorkflowProgress.objects.get_or_create(
        visit=visit,
        pack_id=pack_id,
        defaults={"updated_by": request.user},
    )
    progress.updated_by = request.user

    if action == "complete" and step_id:
        if step_id not in progress.completed_steps:
            progress.completed_steps = list(progress.completed_steps) + [step_id]
    elif action == "skip" and step_id:
        if step_id not in progress.skipped_steps:
            progress.skipped_steps = list(progress.skipped_steps) + [step_id]
    elif action == "sync":
        from .workflow_definitions import detect_completed_steps

        auto = detect_completed_steps(visit, pack_id)
        merged = list(dict.fromkeys(list(progress.completed_steps) + auto))
        progress.completed_steps = merged

    progress.save()

    role = getattr(request.user, "role", "DOCTOR")
    stored_qs = VisitWorkflowProgress.objects.filter(visit=visit)
    stored = {p.pack_id: p for p in stored_qs}
    workflows = build_workflow_response(visit, role, stored)

    return Response({"visit_id": visit.id, "workflows": workflows})


@extend_schema(tags=["Guide"])
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_sandbox_visit(request):
    """
    POST /api/v1/guide/sandbox-visit/

    Create or return an isolated sandbox visit for guided practice.
    """
    org = get_request_organization(request)
    user = request.user
    sandbox_patient_id = f"GUIDE-SB-{user.id}"

    patient_defaults = {
        "first_name": "Guide",
        "last_name": "Sandbox",
        "gender": "OTHER",
        "date_of_birth": date(1990, 1, 1),
        "phone": "0000000000",
        "allergies": "Penicillin (demo only)",
        "organization": org,
        "is_active": True,
    }
    patient, _ = Patient.objects.get_or_create(
        patient_id=sandbox_patient_id,
        organization=org,
        defaults=patient_defaults,
    )

    existing = (
        Visit.objects.filter(
            patient=patient,
            visit_type="SANDBOX",
            status="OPEN",
        )
        .order_by("-created_at")
        .first()
    )
    if existing:
        return Response(
            {
                "visit_id": existing.id,
                "patient_id": patient.id,
                "message": "Returning existing sandbox visit.",
            },
            status=status.HTTP_200_OK,
        )

    visit = Visit.objects.create(
        patient=patient,
        organization=org,
        visit_type="SANDBOX",
        chief_complaint="Guide practice visit — not real PHI",
        status="OPEN",
        payment_type="CASH",
        payment_status="PAID",
    )

    return Response(
        {
            "visit_id": visit.id,
            "patient_id": patient.id,
            "message": "Sandbox visit created.",
        },
        status=status.HTTP_201_CREATED,
    )
