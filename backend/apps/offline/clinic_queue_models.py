"""
Clinic offline queue — lightweight sync for registration/vitals when connectivity drops.
"""

from django.db import models


class ClinicOfflineQueueEntry(models.Model):
    ACTION_CHOICES = [
        ("REGISTER_PATIENT", "Register Patient"),
        ("CHECK_IN_VISIT", "Check In Visit"),
        ("RECORD_VITALS", "Record Vitals"),
        ("QUEUE_NOTE", "Queue Note"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("SYNCED", "Synced"),
        ("FAILED", "Failed"),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="offline_queue_entries",
        null=True,
        blank=True,
    )
    device_id = models.CharField(max_length=128, db_index=True)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offline_queue_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "offline_clinic_queue"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device_id", "status"]),
            models.Index(fields=["organization", "status"]),
        ]
