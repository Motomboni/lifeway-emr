"""
Management command to seed common lab test templates.

Usage:
    python manage.py seed_lab_templates
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.laboratory.template_models import LabTestTemplate

User = get_user_model()


class Command(BaseCommand):
    help = "Seed common lab test templates"

    def handle(self, *args, **options):
        # Get or create a system user for templates (use first superuser or first doctor)
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            system_user = User.objects.filter(role="DOCTOR").first()
        if not system_user:
            self.stdout.write(
                self.style.WARNING(
                    "No user found to assign templates to. Please create a doctor user first."
                )
            )
            return

        templates_data = [
            {
                "name": "Complete Blood Count (CBC)",
                "category": "Hematology",
                "description": "Basic blood panel including RBC, WBC, Hemoglobin, Hematocrit, Platelets",
                "tests": [
                    "CBC",
                    "Hemoglobin",
                    "Hematocrit",
                    "WBC Count",
                    "Platelet Count",
                    "MCV",
                    "MCH",
                    "MCHC",
                ],
                "default_clinical_indication": "Routine checkup / Anemia screening",
            },
            {
                "name": "Liver Function Tests (LFT)",
                "category": "Chemistry",
                "description": "Comprehensive liver function panel",
                "tests": [
                    "ALT",
                    "AST",
                    "ALP",
                    "Total Bilirubin",
                    "Direct Bilirubin",
                    "Albumin",
                    "Total Protein",
                ],
                "default_clinical_indication": "Liver function assessment",
            },
            {
                "name": "Basic Metabolic Panel (BMP)",
                "category": "Chemistry",
                "description": "Basic metabolic panel for kidney and electrolyte function",
                "tests": [
                    "Glucose",
                    "Creatinine",
                    "BUN",
                    "Sodium",
                    "Potassium",
                    "Chloride",
                    "CO2",
                ],
                "default_clinical_indication": "Metabolic function assessment",
            },
            {
                "name": "Comprehensive Metabolic Panel (CMP)",
                "category": "Chemistry",
                "description": "Complete metabolic panel including liver and kidney function",
                "tests": [
                    "Glucose",
                    "Creatinine",
                    "BUN",
                    "Sodium",
                    "Potassium",
                    "Chloride",
                    "CO2",
                    "ALT",
                    "AST",
                    "ALP",
                    "Total Bilirubin",
                    "Albumin",
                    "Total Protein",
                ],
                "default_clinical_indication": "Comprehensive metabolic assessment",
            },
            {
                "name": "Lipid Profile",
                "category": "Chemistry",
                "description": "Complete lipid panel for cardiovascular risk assessment",
                "tests": [
                    "Total Cholesterol",
                    "HDL Cholesterol",
                    "LDL Cholesterol",
                    "Triglycerides",
                ],
                "default_clinical_indication": "Cardiovascular risk assessment",
            },
            {
                "name": "Thyroid Function Tests",
                "category": "Endocrinology",
                "description": "Complete thyroid function panel",
                "tests": ["TSH", "Free T4", "Free T3", "Total T4", "Total T3"],
                "default_clinical_indication": "Thyroid function assessment",
            },
            {
                "name": "Renal Function Tests",
                "category": "Chemistry",
                "description": "Kidney function assessment",
                "tests": ["Creatinine", "BUN", "Uric Acid", "Electrolytes"],
                "default_clinical_indication": "Renal function assessment",
            },
            {
                "name": "Diabetes Panel",
                "category": "Endocrinology",
                "description": "Comprehensive diabetes screening and monitoring",
                "tests": [
                    "Fasting Blood Sugar",
                    "HbA1c",
                    "Random Blood Sugar",
                    "Glucose Tolerance Test",
                ],
                "default_clinical_indication": "Diabetes screening / monitoring",
            },
            {
                "name": "Urine Analysis (Urinalysis)",
                "category": "Urine",
                "description": "Complete urinalysis",
                "tests": [
                    "Urine pH",
                    "Urine Specific Gravity",
                    "Urine Protein",
                    "Urine Glucose",
                    "Urine Ketones",
                    "Urine Blood",
                    "Urine Microscopy",
                ],
                "default_clinical_indication": "Urinary tract assessment",
            },
            {
                "name": "Pregnancy Test",
                "category": "Hormones",
                "description": "Pregnancy screening",
                "tests": ["Beta HCG", "Quantitative HCG"],
                "default_clinical_indication": "Pregnancy screening",
            },
            {
                "name": "Malaria Test",
                "category": "Parasitology",
                "description": "Malaria screening",
                "tests": ["Malaria Parasite (MP)", "Rapid Diagnostic Test (RDT)"],
                "default_clinical_indication": "Malaria screening",
            },
            {
                "name": "HIV Screening",
                "category": "Serology",
                "description": "HIV screening panel",
                "tests": ["HIV Rapid Test", "HIV ELISA", "HIV Confirmatory Test"],
                "default_clinical_indication": "HIV screening",
            },
            {
                "name": "Hepatitis Panel",
                "category": "Serology",
                "description": "Hepatitis screening panel",
                "tests": ["HBsAg", "Anti-HCV", "Anti-HAV IgM", "Anti-HAV IgG"],
                "default_clinical_indication": "Hepatitis screening",
            },
            {
                "name": "Blood Group & Crossmatch",
                "category": "Blood Bank",
                "description": "Blood typing and compatibility testing",
                "tests": ["Blood Group", "Rh Factor", "Crossmatch"],
                "default_clinical_indication": "Blood typing / Transfusion preparation",
            },
            {
                "name": "Coagulation Profile",
                "category": "Hematology",
                "description": "Blood clotting assessment",
                "tests": ["PT", "PTT", "INR", "Fibrinogen"],
                "default_clinical_indication": "Coagulation assessment",
            },
            # --- Additional common panels (primary care / Nigeria clinic) ---
            {
                "name": "Full Blood Count (FBC)",
                "category": "Hematology",
                "description": "Full blood count — same core indices as CBC (RBC, WBC, Hb, platelets)",
                "tests": [
                    "FBC",
                    "WBC Count",
                    "RBC Count",
                    "Hemoglobin",
                    "Hematocrit",
                    "PCV",
                    "Platelet Count",
                    "Neutrophils",
                    "Lymphocytes",
                    "Monocytes",
                    "Eosinophils",
                    "Basophils",
                ],
                "default_clinical_indication": "General health screen / infection or anemia workup",
            },
            {
                "name": "PCV & ESR",
                "category": "Hematology",
                "description": "Packed cell volume and erythrocyte sedimentation rate",
                "tests": ["PCV", "ESR"],
                "default_clinical_indication": "Anemia screening / inflammatory marker",
            },
            {
                "name": "Anemia Workup",
                "category": "Hematology",
                "description": "Initial anemia investigation panel",
                "tests": [
                    "CBC",
                    "PCV",
                    "Reticulocyte Count",
                    "Serum Iron",
                    "TIBC",
                    "Ferritin",
                    "Vitamin B12",
                    "Folate",
                ],
                "default_clinical_indication": "Unexplained anemia / fatigue",
            },
            {
                "name": "Hb Genotype (Electrophoresis)",
                "category": "Hematology",
                "description": "Hemoglobin electrophoresis for sickle cell and thalassemia screening",
                "tests": ["Hb Electrophoresis", "Hb Genotype"],
                "default_clinical_indication": "Sickle cell screening / family history",
            },
            {
                "name": "Electrolytes Panel",
                "category": "Chemistry",
                "description": "Serum electrolytes",
                "tests": ["Sodium", "Potassium", "Chloride", "Bicarbonate", "CO2"],
                "default_clinical_indication": "Dehydration / electrolyte imbalance",
            },
            {
                "name": "Renal Profile (U&E + Creatinine)",
                "category": "Chemistry",
                "description": "Urea, electrolytes, and creatinine",
                "tests": ["Urea", "Creatinine", "Sodium", "Potassium", "Chloride", "Bicarbonate"],
                "default_clinical_indication": "Renal function / hypertension follow-up",
            },
            {
                "name": "Fasting Blood Sugar (FBS)",
                "category": "Endocrinology",
                "description": "Single fasting glucose",
                "tests": ["Fasting Blood Sugar"],
                "default_clinical_indication": "Diabetes screening / monitoring",
            },
            {
                "name": "Random Blood Sugar (RBS)",
                "category": "Endocrinology",
                "description": "Random capillary or venous glucose",
                "tests": ["Random Blood Sugar"],
                "default_clinical_indication": "Hyperglycemia symptoms / emergency check",
            },
            {
                "name": "Inflammatory Markers",
                "category": "Chemistry",
                "description": "Non-specific inflammation screen",
                "tests": ["CRP", "ESR", "Procalcitonin"],
                "default_clinical_indication": "Fever of unknown origin / suspected infection",
            },
            {
                "name": "Typhoid (Widal) Test",
                "category": "Serology",
                "description": "Salmonella typhi serology",
                "tests": ["Widal Test (O)", "Widal Test (H)"],
                "default_clinical_indication": "Prolonged fever / enteric fever suspicion",
            },
            {
                "name": "Stool Analysis",
                "category": "Microbiology",
                "description": "Stool microscopy and basic culture",
                "tests": [
                    "Stool Microscopy",
                    "Stool Ova & Parasites",
                    "Stool Culture",
                    "Occult Blood",
                ],
                "default_clinical_indication": "Diarrhoea / dysentery / GI infection",
            },
            {
                "name": "Blood Culture & Sensitivity",
                "category": "Microbiology",
                "description": "Aerobic blood culture with antibiotic sensitivity",
                "tests": ["Blood Culture", "Sensitivity Report"],
                "default_clinical_indication": "Sepsis / severe infection / persistent fever",
            },
            {
                "name": "Urinary Tract Infection (UTI) Panel",
                "category": "Urine",
                "description": "Urinalysis with culture if indicated",
                "tests": [
                    "Urinalysis",
                    "Urine Microscopy",
                    "Urine Culture",
                    "Sensitivity Report",
                ],
                "default_clinical_indication": "Dysuria / frequency / suspected UTI",
            },
            {
                "name": "Prostate Profile (PSA)",
                "category": "Oncology",
                "description": "Prostate-specific antigen",
                "tests": ["Total PSA", "Free PSA"],
                "default_clinical_indication": "Prostate symptoms / screening",
            },
            {
                "name": "Antenatal (ANC) Routine Labs",
                "category": "Obstetrics",
                "description": "First-visit antenatal laboratory panel",
                "tests": [
                    "CBC",
                    "Blood Group",
                    "Rh Factor",
                    "Hb Genotype",
                    "Urinalysis",
                    "HIV Rapid Test",
                    "HBsAg",
                    "Syphilis (VDRL/RPR)",
                    "Blood Sugar",
                ],
                "default_clinical_indication": "Antenatal booking visit",
            },
            {
                "name": "Pre-Operative Lab Panel",
                "category": "General",
                "description": "Standard pre-surgery labs",
                "tests": [
                    "CBC",
                    "PT/INR",
                    "APTT",
                    "Blood Group",
                    "Crossmatch",
                    "Urinalysis",
                    "Creatinine",
                    "Electrolytes",
                    "Random Blood Sugar",
                ],
                "default_clinical_indication": "Pre-operative assessment",
            },
            {
                "name": "Liver & Pancreas Panel",
                "category": "Chemistry",
                "description": "Extended hepatobiliary panel",
                "tests": [
                    "ALT",
                    "AST",
                    "ALP",
                    "GGT",
                    "Total Bilirubin",
                    "Direct Bilirubin",
                    "Albumin",
                    "Amylase",
                    "Lipase",
                ],
                "default_clinical_indication": "Abdominal pain / jaundice / pancreatitis suspicion",
            },
            {
                "name": "Vitamin D & Bone Profile",
                "category": "Chemistry",
                "description": "Bone metabolism and vitamin D",
                "tests": ["Vitamin D", "Calcium", "Phosphate", "ALP"],
                "default_clinical_indication": "Bone pain / osteoporosis risk",
            },
            {
                "name": "TORCH Screen (Antenatal)",
                "category": "Serology",
                "description": "Antenatal infection screen",
                "tests": ["Toxoplasma IgG/IgM", "Rubella IgG", "CMV IgG/IgM", "HSV IgG"],
                "default_clinical_indication": "Antenatal infection screening",
            },
            {
                "name": "Helicobacter pylori Test",
                "category": "Microbiology",
                "description": "H. pylori detection",
                "tests": ["H. pylori Stool Antigen", "H. pylori Breath Test"],
                "default_clinical_indication": "Dyspepsia / peptic ulcer disease",
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates_data:
            template, created = LabTestTemplate.objects.update_or_create(
                name=template_data["name"],
                defaults={
                    "category": template_data["category"],
                    "description": template_data["description"],
                    "tests": template_data["tests"],
                    "default_clinical_indication": template_data[
                        "default_clinical_indication"
                    ],
                    "created_by": system_user,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created template: {template.name}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"Updated template: {template.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully seeded {created_count} new templates and updated {updated_count} existing templates."
            )
        )
