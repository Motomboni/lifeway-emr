"""
Seed common MedicationInteraction rules for clinical decision support.

Run: python manage.py seed_medication_interactions
"""

from django.core.management.base import BaseCommand

from apps.pharmacy.models import Medication, MedicationInteraction

# (drug_a, drug_b, severity, description)
STARTER_INTERACTIONS = [
    (
        "Warfarin",
        "Aspirin",
        "Severe",
        "Increased bleeding risk when warfarin is combined with aspirin.",
    ),
    (
        "Warfarin",
        "Ibuprofen",
        "Severe",
        "NSAIDs increase anticoagulant effect and GI bleeding risk with warfarin.",
    ),
    (
        "Metformin",
        "Contrast Media",
        "Moderate",
        "Hold metformin around iodinated contrast — risk of lactic acidosis.",
    ),
    (
        "ACE Inhibitor",
        "Potassium Supplement",
        "Moderate",
        "Combined use may cause hyperkalaemia.",
    ),
    (
        "Amoxicillin",
        "Methotrexate",
        "Moderate",
        "Penicillins may reduce methotrexate clearance.",
    ),
    (
        "Ciprofloxacin",
        "Theophylline",
        "Moderate",
        "Fluoroquinolones inhibit theophylline metabolism.",
    ),
    (
        "Simvastatin",
        "Clarithromycin",
        "Severe",
        "Macrolides increase statin levels — myopathy/rhabdomyolysis risk.",
    ),
    (
        "Paracetamol",
        "Alcohol",
        "Mild",
        "Chronic alcohol use increases hepatotoxicity risk at high paracetamol doses.",
    ),
]


class Command(BaseCommand):
    help = "Seed starter Medication + MedicationInteraction rows for CDS alerts"

    def handle(self, *args, **options):
        created_meds = 0
        created_interactions = 0

        med_cache: dict[str, Medication] = {}

        def get_or_create_med(name: str) -> Medication:
            nonlocal created_meds
            key = name.strip().lower()
            if key in med_cache:
                return med_cache[key]
            med, created = Medication.objects.get_or_create(
                name=name,
                defaults={"generic_name": name, "is_active": True},
            )
            if created:
                created_meds += 1
            med_cache[key] = med
            return med

        for drug_a, drug_b, severity, description in STARTER_INTERACTIONS:
            med_a = get_or_create_med(drug_a)
            med_b = get_or_create_med(drug_b)
            _, created = MedicationInteraction.objects.get_or_create(
                medication_a=med_a,
                medication_b=med_b,
                defaults={"severity": severity, "description": description},
            )
            if created:
                created_interactions += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_meds} medication(s) and {created_interactions} interaction(s)."
            )
        )
