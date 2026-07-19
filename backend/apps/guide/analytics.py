"""Guide interaction analytics — no PHI, no raw Ask Guide query text."""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .models import GuideEvent


def log_guide_event(
    *,
    user,
    event_type: str,
    organization=None,
    article_id: str = "",
    target_id: str = "",
    hint_id: str = "",
    metadata: dict | None = None,
) -> GuideEvent:
    """Append a guide analytics event (article/target ids only — never query text)."""
    role = getattr(user, "role", None) or "UNKNOWN"
    return GuideEvent.objects.create(
        organization=organization,
        user=user,
        user_role=role,
        event_type=event_type,
        article_id=article_id or "",
        target_id=target_id or "",
        hint_id=hint_id or "",
        metadata=metadata or {},
    )


def get_guide_analytics_summary(*, organization, days: int = 30) -> dict:
    """Aggregate guide events for admin dashboards."""
    since = timezone.now() - timedelta(days=max(1, min(days, 365)))
    qs = GuideEvent.objects.filter(created_at__gte=since)
    if organization:
        qs = qs.filter(organization=organization)

    totals = {
        row["event_type"]: row["count"]
        for row in qs.values("event_type").annotate(count=Count("id"))
    }

    top_articles = list(
        qs.exclude(article_id="")
        .values("article_id")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    events_by_role = {
        row["user_role"]: row["count"]
        for row in qs.values("user_role").annotate(count=Count("id"))
    }

    return {
        "days": days,
        "totals": totals,
        "top_articles": top_articles,
        "events_by_role": events_by_role,
        "unique_users": qs.values("user_id").distinct().count(),
        "total_events": qs.count(),
    }
