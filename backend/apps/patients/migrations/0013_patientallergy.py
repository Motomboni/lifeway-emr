# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0012_remove_patient_patients_nationa_health_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PatientAllergy",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("allergen", models.CharField(max_length=255)),
                (
                    "allergen_type",
                    models.CharField(
                        choices=[
                            ("DRUG", "Drug"),
                            ("FOOD", "Food"),
                            ("ENVIRONMENT", "Environment"),
                            ("OTHER", "Other"),
                            ("UNKNOWN", "Unknown"),
                        ],
                        default="UNKNOWN",
                        max_length=20,
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("MILD", "Mild"),
                            ("MODERATE", "Moderate"),
                            ("SEVERE", "Severe"),
                            ("UNKNOWN", "Unknown"),
                        ],
                        default="UNKNOWN",
                        max_length=20,
                    ),
                ),
                ("reaction", models.TextField(blank=True)),
                ("onset_date", models.DateField(blank=True, null=True)),
                ("verified", models.BooleanField(default=False)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("PATIENT_REPORTED", "Patient reported"),
                            ("CLINICIAN", "Clinician documented"),
                            ("ADMISSION", "Admission note"),
                            ("LEGACY_TEXT", "Legacy free-text import"),
                        ],
                        default="CLINICIAN",
                        max_length=32,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="patient_allergies_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="structured_allergies",
                        to="patients.patient",
                    ),
                ),
            ],
            options={
                "verbose_name": "Patient Allergy",
                "verbose_name_plural": "Patient Allergies",
                "db_table": "patient_allergies",
                "ordering": ["-severity", "allergen"],
            },
        ),
        migrations.AddIndex(
            model_name="patientallergy",
            index=models.Index(
                fields=["patient", "is_active"], name="patient_all_patient_8a1f2d_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patientallergy",
            index=models.Index(fields=["allergen"], name="patient_all_allerge_91c4e2_idx"),
        ),
        migrations.AddConstraint(
            model_name="patientallergy",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("patient", "allergen"),
                name="uniq_active_patient_allergen",
            ),
        ),
    ]
