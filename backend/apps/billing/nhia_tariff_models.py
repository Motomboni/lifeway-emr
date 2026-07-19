"""
NHIA tariff reference data for claim validation and Clinical AI Scribe.

Tariffs are national reference rows (not patient-specific). ICD-11 codes on each
row indicate diagnoses commonly billed under that NHIA service code.
"""

from django.db import models


class NHIATariff(models.Model):
    """National Health Insurance Authority service tariff."""

    CATEGORY_CHOICES = [
        ("CONSULTATION", "Consultation"),
        ("ANC", "Antenatal Care"),
        ("LAB", "Laboratory"),
        ("PROCEDURE", "Procedure"),
        ("DRUG", "Drug"),
        ("RADIOLOGY", "Radiology"),
        ("OTHER", "Other"),
    ]

    nhia_code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="NHIA tariff code (e.g. 3-01-01, 4-02-01).",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=32,
        choices=CATEGORY_CHOICES,
        default="CONSULTATION",
        db_index=True,
    )
    amount_ngn = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Approved tariff amount in Nigerian Naira.",
    )
    icd11_codes = models.JSONField(
        default=list,
        blank=True,
        help_text="ICD-11 MMS codes commonly billed under this tariff.",
    )
    keywords = models.TextField(
        blank=True,
        help_text="Search keywords (diagnosis names, synonyms).",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    effective_from = models.DateField(null=True, blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="nhia_tariffs",
        null=True,
        blank=True,
        help_text="Optional clinic override. Null = national reference row.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_nhia_tariff"
        ordering = ["category", "nhia_code"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self):
        return f"{self.nhia_code} — {self.name}"

    def icd11_code_set(self) -> set[str]:
        return {str(c).strip().upper() for c in (self.icd11_codes or []) if c}
