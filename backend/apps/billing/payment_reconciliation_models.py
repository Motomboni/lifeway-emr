"""Bank transfer / USSD payment reconciliation records."""

from decimal import Decimal

from django.db import models


class PaymentReconciliation(models.Model):
    METHOD_CHOICES = [
        ("BANK_TRANSFER", "Bank Transfer"),
        ("USSD", "USSD"),
        ("POS", "POS"),
        ("CASH", "Cash"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("MATCHED", "Matched"),
        ("DISPUTED", "Disputed"),
    ]

    visit = models.ForeignKey(
        "visits.Visit",
        on_delete=models.CASCADE,
        related_name="payment_reconciliations",
        null=True,
        blank=True,
    )
    payment = models.ForeignKey(
        "billing.Payment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reconciliations",
    )
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    reference = models.CharField(max_length=128, db_index=True)
    amount_ngn = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    payer_name = models.CharField(max_length=255, blank=True)
    bank_name = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_reconciliations_recorded",
    )
    matched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_payment_reconciliation"
        ordering = ["-created_at"]
