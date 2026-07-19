"""
NHIA claim submission lifecycle — visit-scoped claim tracking for Nigerian facilities.

Statuses: DRAFT → VALIDATED → EXPORTED → SUBMITTED → PAID | DENIED → (RESUBMITTED)
"""

from decimal import Decimal

from django.db import models


class NHIAClaimSubmission(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("VALIDATED", "Validated"),
        ("EXPORTED", "Exported"),
        ("SUBMITTED", "Submitted"),
        ("PAID", "Paid"),
        ("DENIED", "Denied"),
        ("RESUBMITTED", "Resubmitted"),
    ]

    visit = models.ForeignKey(
        "visits.Visit",
        on_delete=models.CASCADE,
        related_name="nhia_claim_submissions",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="nhia_claim_submissions",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    claim_reference = models.CharField(max_length=64, blank=True, db_index=True)
    total_amount_ngn = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    line_count = models.PositiveIntegerField(default=0)
    validation_errors = models.JSONField(default=list, blank=True)
    claim_pack_snapshot = models.JSONField(default=dict, blank=True)
    denial_reason = models.TextField(blank=True)
    nhia_portal_reference = models.CharField(max_length=128, blank=True)
    paid_amount_ngn = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    exported_at = models.DateTimeField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    resubmission_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resubmissions",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nhia_claims_created",
    )
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="nhia_claims_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "nhia_claim_submissions"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["-updated_at"]),
        ]

    def __str__(self):
        return f"NHIA claim visit={self.visit_id} ({self.status})"
