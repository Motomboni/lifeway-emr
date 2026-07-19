"""URL configuration for guide endpoints."""

from django.urls import path

from .views import (
    ask_guide,
    create_sandbox_visit,
    guide_analytics,
    log_guide_event_view,
    me_guide_progress,
    visit_workflow,
    visit_workflow_sync,
)

urlpatterns = [
    path("me/progress/", me_guide_progress, name="guide-me-progress"),
    path("me/ask/", ask_guide, name="guide-me-ask"),
    path("events/", log_guide_event_view, name="guide-events"),
    path("analytics/", guide_analytics, name="guide-analytics"),
    path("sandbox-visit/", create_sandbox_visit, name="guide-sandbox-visit"),
    path(
        "visits/<int:visit_id>/workflow/",
        visit_workflow,
        name="guide-visit-workflow",
    ),
    path(
        "visits/<int:visit_id>/workflow/sync/",
        visit_workflow_sync,
        name="guide-visit-workflow-sync",
    ),
]
