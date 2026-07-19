"""Models for interactive guide progress and visit workflow checklists."""

from django.conf import settings
from django.db import models


class UserGuideProgress(models.Model):
    """Per-user guide onboarding and preference state."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guide_progress",
    )
    completed_steps = models.JSONField(
        default=list,
        blank=True,
        help_text="Guide step IDs completed by the user",
    )
    dismissed_hints = models.JSONField(
        default=list,
        blank=True,
        help_text="JIT hint IDs the user dismissed",
    )
    role_launch_completed = models.JSONField(
        default=dict,
        blank=True,
        help_text='Role launch completion, e.g. {"DOCTOR": true}',
    )
    guide_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Guide UI preferences (enabled, reduced motion, etc.)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "guide_user_progress"
        verbose_name = "User Guide Progress"
        verbose_name_plural = "User Guide Progress"

    def __str__(self):
        return f"Guide progress for {self.user.username}"


class VisitWorkflowProgress(models.Model):
    """Checklist progress for a visit workflow pack."""

    visit = models.ForeignKey(
        "visits.Visit",
        on_delete=models.CASCADE,
        related_name="workflow_progress",
    )
    pack_id = models.CharField(
        max_length=50,
        help_text="Workflow pack identifier (intake, charting, close_visit)",
    )
    completed_steps = models.JSONField(default=list, blank=True)
    skipped_steps = models.JSONField(default=list, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_updates",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "guide_visit_workflow_progress"
        unique_together = [["visit", "pack_id"]]
        indexes = [
            models.Index(fields=["visit", "pack_id"]),
        ]

    def __str__(self):
        return f"Visit {self.visit_id} — {self.pack_id}"


class GuideEvent(models.Model):
    """Guide interaction analytics — no PHI, no raw Ask Guide query text."""

    EVENT_TYPES = [
        ("ask", "Ask Guide query"),
        ("article_open", "Article opened"),
        ("spotlight", "Spotlight shown"),
        ("hint_dismiss", "Hint dismissed"),
        ("role_launch_step", "Role launch step"),
        ("role_launch_complete", "Role launch complete"),
        ("command_palette", "Command palette"),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="guide_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="guide_events",
    )
    user_role = models.CharField(max_length=50)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    article_id = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=100, blank=True)
    hint_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "guide_events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
            models.Index(fields=["article_id"]),
        ]
        verbose_name = "Guide Event"
        verbose_name_plural = "Guide Events"

    def __str__(self):
        return f"{self.event_type} by {self.user_id} @ {self.created_at}"
