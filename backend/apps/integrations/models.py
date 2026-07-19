"""External national health hub integration configuration (stubs)."""

from django.db import models


class ExternalHealthHub(models.Model):
    HUB_CHOICES = [
        ("NHIA_PORTAL", "NHIA Claims Portal"),
        ("NATIONAL_EPRESCRIPTION", "National E-Prescription Hub"),
        ("LAB_EXCHANGE", "National Lab Exchange"),
    ]

    hub_type = models.CharField(max_length=32, choices=HUB_CHOICES, unique=True)
    base_url = models.URLField(blank=True)
    api_key_env = models.CharField(
        max_length=64,
        blank=True,
        help_text="Name of environment variable holding API key",
    )
    is_enabled = models.BooleanField(default=False)
    config = models.JSONField(default=dict, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integrations_external_health_hub"

    def __str__(self):
        return f"{self.hub_type} ({'enabled' if self.is_enabled else 'disabled'})"
