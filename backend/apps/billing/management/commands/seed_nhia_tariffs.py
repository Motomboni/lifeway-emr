"""
Seed starter NHIA tariff reference rows for Clinical AI Scribe validation.

Run: python manage.py seed_nhia_tariffs
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.billing.nhia_tariff_models import NHIATariff

STARTER_TARIFFS = [
    {
        "nhia_code": "1-01-01",
        "name": "General Outpatient Consultation",
        "category": "CONSULTATION",
        "amount_ngn": Decimal("3500.00"),
        "icd11_codes": ["CA40.Z", "MD11", "1D01"],
        "keywords": "gopd outpatient consultation fever cough",
    },
    {
        "nhia_code": "1-02-01",
        "name": "Specialist Outpatient Consultation",
        "category": "CONSULTATION",
        "amount_ngn": Decimal("5000.00"),
        "icd11_codes": ["BA00", "8A80"],
        "keywords": "specialist consultation",
    },
    {
        "nhia_code": "3-01-01",
        "name": "Treatment of Uncomplicated Malaria (Adult)",
        "category": "DRUG",
        "amount_ngn": Decimal("1200.00"),
        "icd11_codes": ["1F44", "1F45"],
        "keywords": "malaria plasmodium falciparum ACT artemether",
    },
    {
        "nhia_code": "3-02-01",
        "name": "Treatment of Uncomplicated Malaria (Child)",
        "category": "DRUG",
        "amount_ngn": Decimal("900.00"),
        "icd11_codes": ["1F44", "1F45"],
        "keywords": "paediatric malaria child",
    },
    {
        "nhia_code": "4-02-01",
        "name": "Antenatal Booking / Supervision of Normal Pregnancy",
        "category": "ANC",
        "amount_ngn": Decimal("4500.00"),
        "icd11_codes": ["QA00.Z", "QA00.0"],
        "keywords": "anc antenatal booking pregnancy supervision",
    },
    {
        "nhia_code": "4-02-02",
        "name": "Routine Antenatal Visit",
        "category": "ANC",
        "amount_ngn": Decimal("2500.00"),
        "icd11_codes": ["QA00.Z", "QA00.0"],
        "keywords": "anc follow up antenatal visit",
    },
    {
        "nhia_code": "4-03-01",
        "name": "Obstetric Ultrasound Scan",
        "category": "RADIOLOGY",
        "amount_ngn": Decimal("6000.00"),
        "icd11_codes": ["QA00.Z"],
        "keywords": "obstetric ultrasound scan anc",
    },
    {
        "nhia_code": "2-01-01",
        "name": "Full Blood Count (FBC)",
        "category": "LAB",
        "amount_ngn": Decimal("1500.00"),
        "icd11_codes": ["3A00", "1A00.Z", "QA00.Z"],
        "keywords": "fbc full blood count haemoglobin anaemia",
    },
    {
        "nhia_code": "2-02-01",
        "name": "Malaria Rapid Diagnostic Test (mRDT)",
        "category": "LAB",
        "amount_ngn": Decimal("800.00"),
        "icd11_codes": ["1F44", "1F45"],
        "keywords": "mrdt malaria rapid test",
    },
    {
        "nhia_code": "2-03-01",
        "name": "Urinalysis",
        "category": "LAB",
        "amount_ngn": Decimal("600.00"),
        "icd11_codes": ["MF50", "QA00.Z", "GB90"],
        "keywords": "urinalysis urine UTI pregnancy",
    },
    {
        "nhia_code": "3-10-01",
        "name": "Treatment of Upper Respiratory Tract Infection",
        "category": "DRUG",
        "amount_ngn": Decimal("1800.00"),
        "icd11_codes": ["CA40.Z", "CA41"],
        "keywords": "urti upper respiratory infection cough cold",
    },
    {
        "nhia_code": "3-11-01",
        "name": "Treatment of Hypertension (Monthly)",
        "category": "DRUG",
        "amount_ngn": Decimal("2200.00"),
        "icd11_codes": ["BA00", "BA00.Z"],
        "keywords": "hypertension BP blood pressure",
    },
    {
        "nhia_code": "3-12-01",
        "name": "Treatment of Type 2 Diabetes Mellitus (Monthly)",
        "category": "DRUG",
        "amount_ngn": Decimal("2500.00"),
        "icd11_codes": ["5A11", "5A10"],
        "keywords": "diabetes dm type 2 sugar",
    },
    {
        "nhia_code": "5-01-01",
        "name": "Normal Vaginal Delivery",
        "category": "PROCEDURE",
        "amount_ngn": Decimal("25000.00"),
        "icd11_codes": ["JA00.Z"],
        "keywords": "delivery labour nvd childbirth",
    },
    {
        "nhia_code": "5-02-01",
        "name": "Caesarean Section",
        "category": "PROCEDURE",
        "amount_ngn": Decimal("45000.00"),
        "icd11_codes": ["JB00.Z", "JB0Z"],
        "keywords": "caesarean c-section cs",
    },
    {
        "nhia_code": "2-04-01",
        "name": "HIV Rapid Test",
        "category": "LAB",
        "amount_ngn": Decimal("1000.00"),
        "icd11_codes": ["1C62.Z", "QA00.Z"],
        "keywords": "hiv rapid test anc screening",
    },
    {
        "nhia_code": "2-05-01",
        "name": "Hepatitis B Surface Antigen (HBsAg)",
        "category": "LAB",
        "amount_ngn": Decimal("1200.00"),
        "icd11_codes": ["1E50.0", "QA00.Z"],
        "keywords": "hepatitis hbsag anc screening",
    },
    {
        "nhia_code": "3-20-01",
        "name": "Treatment of Uncomplicated UTI",
        "category": "DRUG",
        "amount_ngn": Decimal("1400.00"),
        "icd11_codes": ["GC00", "MF50"],
        "keywords": "uti urinary tract infection",
    },
]


class Command(BaseCommand):
    help = "Seed NHIA tariff reference rows for scribe validation and claims."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing national (organization=null) tariffs before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            deleted, _ = NHIATariff.objects.filter(organization__isnull=True).delete()
            self.stdout.write(self.style.WARNING(f"Removed {deleted} existing tariff rows."))

        created = 0
        updated = 0
        for row in STARTER_TARIFFS:
            obj, was_created = NHIATariff.objects.update_or_create(
                nhia_code=row["nhia_code"],
                defaults={
                    "organization": None,
                    "name": row["name"],
                    "category": row["category"],
                    "amount_ngn": row["amount_ngn"],
                    "icd11_codes": row["icd11_codes"],
                    "keywords": row.get("keywords", ""),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"NHIA tariffs seeded: {created} created, {updated} updated "
                f"({len(STARTER_TARIFFS)} reference rows)."
            )
        )
