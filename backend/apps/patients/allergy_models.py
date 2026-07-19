"""Structured patient allergy records for CDS and clinical safety."""

from django.db import models


class PatientAllergy(models.Model):
    ALLERGEN_TYPES = [
        ("DRUG", "Drug"),
        ("FOOD", "Food"),
        ("ENVIRONMENT", "Environment"),
        ("OTHER", "Other"),
        ("UNKNOWN", "Unknown"),
    ]

    SEVERITY_CHOICES = [
        ("MILD", "Mild"),
        ("MODERATE", "Moderate"),
        ("SEVERE", "Severe"),
        ("UNKNOWN", "Unknown"),
    ]

    SOURCE_CHOICES = [
        ("PATIENT_REPORTED", "Patient reported"),
        ("CLINICIAN", "Clinician documented"),
        ("ADMISSION", "Admission note"),
        ("LEGACY_TEXT", "Legacy free-text import"),
    ]

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="structured_allergies",
    )
    allergen = models.CharField(max_length=255, help_text="Allergen name (e.g. Penicillin)")
    allergen_type = models.CharField(
        max_length=20,
        choices=ALLERGEN_TYPES,
        default="UNKNOWN",
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default="UNKNOWN",
    )
    reaction = models.TextField(blank=True, help_text="Reaction description")
    onset_date = models.DateField(null=True, blank=True)
    verified = models.BooleanField(default=False)
    source = models.CharField(
        max_length=32,
        choices=SOURCE_CHOICES,
        default="CLINICIAN",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_allergies_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_allergies"
        ordering = ["-severity", "allergen"]
        indexes = [
            models.Index(fields=["patient", "is_active"]),
            models.Index(fields=["allergen"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "allergen"],
                condition=models.Q(is_active=True),
                name="uniq_active_patient_allergen",
            ),
        ]
        verbose_name = "Patient Allergy"
        verbose_name_plural = "Patient Allergies"

    def __str__(self):
        return f"{self.allergen} ({self.patient_id})"
