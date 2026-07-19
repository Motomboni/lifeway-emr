"""Nigeria immunization schedule records (EPI guideline pack)."""

from django.db import models


class ImmunizationRecord(models.Model):
    VACCINE_CHOICES = [
        ("BCG", "BCG"),
        ("HEP_B", "Hepatitis B birth dose"),
        ("OPV", "OPV"),
        ("IPV", "Inactivated Polio Vaccine"),
        ("PENTA", "Pentavalent"),
        ("PCV", "PCV"),
        ("ROTA", "Rotavirus"),
        ("MEASLES", "Measles"),
        ("YELLOW_FEVER", "Yellow Fever"),
        ("MEN_A", "Meningococcal A"),
        ("MALARIA", "Malaria vaccine"),
        ("HPV", "HPV"),
        ("TD", "Tetanus-Diphtheria"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="immunization_records",
    )
    vaccine = models.CharField(max_length=32, choices=VACCINE_CHOICES)
    dose_number = models.PositiveSmallIntegerField(default=1)
    scheduled_date = models.DateField(null=True, blank=True)
    administered_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=64, blank=True)
    administered_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="immunizations_administered",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clinical_immunization_records"
        ordering = ["scheduled_date", "vaccine"]
        indexes = [
            models.Index(fields=["patient", "vaccine"]),
            models.Index(fields=["scheduled_date"]),
        ]

    def __str__(self):
        return f"{self.patient_id} — {self.vaccine} dose {self.dose_number}"
