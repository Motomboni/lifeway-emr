"""NAFDAC-oriented drug formulary reference linked to NHIA drug tariffs."""

from django.db import models


class NAFDACFormularyEntry(models.Model):
    nafdac_reg_no = models.CharField(max_length=64, unique=True, db_index=True)
    product_name = models.CharField(max_length=255)
    active_ingredient = models.CharField(max_length=255, blank=True)
    dosage_form = models.CharField(max_length=128, blank=True)
    strength = models.CharField(max_length=128, blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    nhia_tariff_code = models.CharField(
        max_length=32,
        blank=True,
        help_text="Linked NHIA drug tariff code when applicable",
    )
    is_essential_medicine = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pharmacy_nafdac_formulary"
        ordering = ["product_name"]
        indexes = [
            models.Index(fields=["product_name"]),
            models.Index(fields=["nhia_tariff_code"]),
        ]

    def __str__(self):
        return f"{self.product_name} ({self.nafdac_reg_no})"
