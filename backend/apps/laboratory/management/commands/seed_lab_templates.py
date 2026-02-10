"""
Management command to seed common lab test templates.

Usage:
    python manage.py seed_lab_templates
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.laboratory.template_models import LabTestTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed common lab test templates'

    def handle(self, *args, **options):
        # Get or create a system user for templates (use first superuser or first doctor)
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            system_user = User.objects.filter(role='DOCTOR').first()
        if not system_user:
            self.stdout.write(self.style.WARNING('No user found to assign templates to. Please create a doctor user first.'))
            return

        templates_data = [
            {
                'name': 'Complete Blood Count (CBC)',
                'category': 'Hematology',
                'description': 'Basic blood panel including RBC, WBC, Hemoglobin, Hematocrit, Platelets',
                'tests': ['CBC', 'Hemoglobin', 'Hematocrit', 'WBC Count', 'Platelet Count', 'MCV', 'MCH', 'MCHC'],
                'default_clinical_indication': 'Routine checkup / Anemia screening'
            },
            {
                'name': 'Liver Function Tests (LFT)',
                'category': 'Chemistry',
                'description': 'Comprehensive liver function panel',
                'tests': ['ALT', 'AST', 'ALP', 'Total Bilirubin', 'Direct Bilirubin', 'Albumin', 'Total Protein'],
                'default_clinical_indication': 'Liver function assessment'
            },
            {
                'name': 'Basic Metabolic Panel (BMP)',
                'category': 'Chemistry',
                'description': 'Basic metabolic panel for kidney and electrolyte function',
                'tests': ['Glucose', 'Creatinine', 'BUN', 'Sodium', 'Potassium', 'Chloride', 'CO2'],
                'default_clinical_indication': 'Metabolic function assessment'
            },
            {
                'name': 'Comprehensive Metabolic Panel (CMP)',
                'category': 'Chemistry',
                'description': 'Complete metabolic panel including liver and kidney function',
                'tests': ['Glucose', 'Creatinine', 'BUN', 'Sodium', 'Potassium', 'Chloride', 'CO2', 'ALT', 'AST', 'ALP', 'Total Bilirubin', 'Albumin', 'Total Protein'],
                'default_clinical_indication': 'Comprehensive metabolic assessment'
            },
            {
                'name': 'Lipid Profile',
                'category': 'Chemistry',
                'description': 'Complete lipid panel for cardiovascular risk assessment',
                'tests': ['Total Cholesterol', 'HDL Cholesterol', 'LDL Cholesterol', 'Triglycerides'],
                'default_clinical_indication': 'Cardiovascular risk assessment'
            },
            {
                'name': 'Thyroid Function Tests',
                'category': 'Endocrinology',
                'description': 'Complete thyroid function panel',
                'tests': ['TSH', 'Free T4', 'Free T3', 'Total T4', 'Total T3'],
                'default_clinical_indication': 'Thyroid function assessment'
            },
            {
                'name': 'Renal Function Tests',
                'category': 'Chemistry',
                'description': 'Kidney function assessment',
                'tests': ['Creatinine', 'BUN', 'Uric Acid', 'Electrolytes'],
                'default_clinical_indication': 'Renal function assessment'
            },
            {
                'name': 'Diabetes Panel',
                'category': 'Endocrinology',
                'description': 'Comprehensive diabetes screening and monitoring',
                'tests': ['Fasting Blood Sugar', 'HbA1c', 'Random Blood Sugar', 'Glucose Tolerance Test'],
                'default_clinical_indication': 'Diabetes screening / monitoring'
            },
            {
                'name': 'Urine Analysis (Urinalysis)',
                'category': 'Urine',
                'description': 'Complete urinalysis',
                'tests': ['Urine pH', 'Urine Specific Gravity', 'Urine Protein', 'Urine Glucose', 'Urine Ketones', 'Urine Blood', 'Urine Microscopy'],
                'default_clinical_indication': 'Urinary tract assessment'
            },
            {
                'name': 'Pregnancy Test',
                'category': 'Hormones',
                'description': 'Pregnancy screening',
                'tests': ['Beta HCG', 'Quantitative HCG'],
                'default_clinical_indication': 'Pregnancy screening'
            },
            {
                'name': 'Malaria Test',
                'category': 'Parasitology',
                'description': 'Malaria screening',
                'tests': ['Malaria Parasite (MP)', 'Rapid Diagnostic Test (RDT)'],
                'default_clinical_indication': 'Malaria screening'
            },
            {
                'name': 'HIV Screening',
                'category': 'Serology',
                'description': 'HIV screening panel',
                'tests': ['HIV Rapid Test', 'HIV ELISA', 'HIV Confirmatory Test'],
                'default_clinical_indication': 'HIV screening'
            },
            {
                'name': 'Hepatitis Panel',
                'category': 'Serology',
                'description': 'Hepatitis screening panel',
                'tests': ['HBsAg', 'Anti-HCV', 'Anti-HAV IgM', 'Anti-HAV IgG'],
                'default_clinical_indication': 'Hepatitis screening'
            },
            {
                'name': 'Blood Group & Crossmatch',
                'category': 'Blood Bank',
                'description': 'Blood typing and compatibility testing',
                'tests': ['Blood Group', 'Rh Factor', 'Crossmatch'],
                'default_clinical_indication': 'Blood typing / Transfusion preparation'
            },
            {
                'name': 'Coagulation Profile',
                'category': 'Hematology',
                'description': 'Blood clotting assessment',
                'tests': ['PT', 'PTT', 'INR', 'Fibrinogen'],
                'default_clinical_indication': 'Coagulation assessment'
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates_data:
            template, created = LabTestTemplate.objects.update_or_create(
                name=template_data['name'],
                defaults={
                    'category': template_data['category'],
                    'description': template_data['description'],
                    'tests': template_data['tests'],
                    'default_clinical_indication': template_data['default_clinical_indication'],
                    'created_by': system_user,
                    'is_active': True,
                }
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created template: {template.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'Updated template: {template.name}'))

        self.stdout.write(self.style.SUCCESS(
            f'\nSuccessfully seeded {created_count} new templates and updated {updated_count} existing templates.'
        ))

