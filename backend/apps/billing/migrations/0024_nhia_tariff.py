# Generated manually for phase 2.1 NHIA tariff reference

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0001_initial"),
        ("billing", "0023_rename_insurance_c_patient_6a8c0d_idx_insurance_c_patient_374c53_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="NHIATariff",
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
                (
                    "nhia_code",
                    models.CharField(
                        db_index=True,
                        help_text="NHIA tariff code (e.g. 3-01-01, 4-02-01).",
                        max_length=32,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("CONSULTATION", "Consultation"),
                            ("ANC", "Antenatal Care"),
                            ("LAB", "Laboratory"),
                            ("PROCEDURE", "Procedure"),
                            ("DRUG", "Drug"),
                            ("RADIOLOGY", "Radiology"),
                            ("OTHER", "Other"),
                        ],
                        db_index=True,
                        default="CONSULTATION",
                        max_length=32,
                    ),
                ),
                (
                    "amount_ngn",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Approved tariff amount in Nigerian Naira.",
                        max_digits=12,
                    ),
                ),
                (
                    "icd11_codes",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="ICD-11 MMS codes commonly billed under this tariff.",
                    ),
                ),
                (
                    "keywords",
                    models.TextField(
                        blank=True,
                        help_text="Search keywords (diagnosis names, synonyms).",
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("effective_from", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        help_text="Optional clinic override. Null = national reference row.",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nhia_tariffs",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={
                "db_table": "billing_nhia_tariff",
                "ordering": ["category", "nhia_code"],
                "indexes": [
                    models.Index(
                        fields=["category", "is_active"],
                        name="billing_nhi_categor_8f3a21_idx",
                    ),
                ],
            },
        ),
    ]
