"""
Management command to seed common radiology study templates.

Usage:
    python manage.py seed_radiology_templates
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.radiology.template_models import RadiologyTestTemplate

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed common radiology study templates'

    def handle(self, *args, **options):
        # Get or create a system user for templates (use first superuser or first doctor)
        system_user = User.objects.filter(is_superuser=True).first()
        if not system_user:
            system_user = User.objects.filter(role='DOCTOR').first()
        if not system_user:
            self.stdout.write(self.style.WARNING('No user found to assign templates to. Please create a doctor user first.'))
            return

        templates_data = [
            # X-Ray Templates
            {
                'name': 'Chest X-Ray (PA)',
                'category': 'X-Ray',
                'description': 'Posteroanterior chest X-ray for lung and heart assessment',
                'imaging_type': 'XRAY',
                'body_part': 'Chest',
                'study_code': 'CXR-PA',
                'default_clinical_indication': 'Chest pain / Respiratory symptoms / Pre-operative assessment',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Chest X-Ray (AP)',
                'category': 'X-Ray',
                'description': 'Anteroposterior chest X-ray (portable)',
                'imaging_type': 'XRAY',
                'body_part': 'Chest',
                'study_code': 'CXR-AP',
                'default_clinical_indication': 'Chest assessment (portable)',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Abdominal X-Ray',
                'category': 'X-Ray',
                'description': 'Abdominal X-ray for bowel assessment',
                'imaging_type': 'XRAY',
                'body_part': 'Abdomen',
                'study_code': 'AXR',
                'default_clinical_indication': 'Abdominal pain / Bowel obstruction assessment',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Pelvis X-Ray',
                'category': 'X-Ray',
                'description': 'Pelvic X-ray for bone assessment',
                'imaging_type': 'XRAY',
                'body_part': 'Pelvis',
                'study_code': 'PEL-XR',
                'default_clinical_indication': 'Pelvic pain / Fracture assessment',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Lumbar Spine X-Ray',
                'category': 'X-Ray',
                'description': 'Lumbar spine X-ray for back pain assessment',
                'imaging_type': 'XRAY',
                'body_part': 'Lumbar Spine',
                'study_code': 'LS-XR',
                'default_clinical_indication': 'Lower back pain / Spinal assessment',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Cervical Spine X-Ray',
                'category': 'X-Ray',
                'description': 'Cervical spine X-ray for neck pain assessment',
                'imaging_type': 'XRAY',
                'body_part': 'Cervical Spine',
                'study_code': 'CS-XR',
                'default_clinical_indication': 'Neck pain / Cervical spine assessment',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Skull X-Ray',
                'category': 'X-Ray',
                'description': 'Skull X-ray for head trauma assessment',
                'imaging_type': 'XRAY',
                'body_part': 'Skull',
                'study_code': 'SK-XR',
                'default_clinical_indication': 'Head trauma / Skull fracture assessment',
                'default_priority': 'URGENT'
            },
            {
                'name': 'Extremity X-Ray',
                'category': 'X-Ray',
                'description': 'X-ray of upper or lower extremity',
                'imaging_type': 'XRAY',
                'body_part': 'Extremity',
                'study_code': 'EXT-XR',
                'default_clinical_indication': 'Fracture assessment / Trauma',
                'default_priority': 'ROUTINE'
            },
            # CT Scan Templates
            {
                'name': 'CT Head',
                'category': 'CT Scan',
                'description': 'CT scan of the head for brain assessment',
                'imaging_type': 'CT',
                'body_part': 'Head',
                'study_code': 'CT-HEAD',
                'default_clinical_indication': 'Head trauma / Headache / Neurological symptoms',
                'default_priority': 'URGENT'
            },
            {
                'name': 'CT Chest',
                'category': 'CT Scan',
                'description': 'CT scan of the chest for detailed lung assessment',
                'imaging_type': 'CT',
                'body_part': 'Chest',
                'study_code': 'CT-CHEST',
                'default_clinical_indication': 'Lung assessment / Pulmonary embolism / Mass evaluation',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'CT Abdomen',
                'category': 'CT Scan',
                'description': 'CT scan of the abdomen for abdominal assessment',
                'imaging_type': 'CT',
                'body_part': 'Abdomen',
                'study_code': 'CT-ABD',
                'default_clinical_indication': 'Abdominal pain / Mass evaluation / Trauma',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'CT Pelvis',
                'category': 'CT Scan',
                'description': 'CT scan of the pelvis',
                'imaging_type': 'CT',
                'body_part': 'Pelvis',
                'study_code': 'CT-PEL',
                'default_clinical_indication': 'Pelvic pain / Mass evaluation / Trauma',
                'default_priority': 'ROUTINE'
            },
            # Ultrasound Templates
            {
                'name': 'Abdominal Ultrasound',
                'category': 'Ultrasound',
                'description': 'Ultrasound of the abdomen for organ assessment',
                'imaging_type': 'US',
                'body_part': 'Abdomen',
                'study_code': 'US-ABD',
                'default_clinical_indication': 'Abdominal pain / Organ assessment / Mass evaluation',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Pelvic Ultrasound',
                'category': 'Ultrasound',
                'description': 'Pelvic ultrasound for gynecological assessment',
                'imaging_type': 'US',
                'body_part': 'Pelvis',
                'study_code': 'US-PEL',
                'default_clinical_indication': 'Pelvic pain / Gynecological assessment / Pregnancy',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Obstetric Ultrasound',
                'category': 'Ultrasound',
                'description': 'Pregnancy ultrasound for fetal assessment',
                'imaging_type': 'US',
                'body_part': 'Pelvis',
                'study_code': 'US-OBS',
                'default_clinical_indication': 'Pregnancy assessment / Fetal monitoring',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Transvaginal Ultrasound',
                'category': 'Ultrasound',
                'description': 'Transvaginal ultrasound for detailed pelvic assessment',
                'imaging_type': 'US',
                'body_part': 'Pelvis',
                'study_code': 'US-TVS',
                'default_clinical_indication': 'Gynecological assessment / Early pregnancy',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Renal Ultrasound',
                'category': 'Ultrasound',
                'description': 'Ultrasound of the kidneys',
                'imaging_type': 'US',
                'body_part': 'Kidneys',
                'study_code': 'US-RENAL',
                'default_clinical_indication': 'Renal assessment / Kidney stones / Mass evaluation',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'Prostate Ultrasound',
                'category': 'Ultrasound',
                'description': 'Prostate ultrasound for prostate assessment',
                'imaging_type': 'US',
                'body_part': 'Prostate',
                'study_code': 'US-PROSTATE',
                'default_clinical_indication': 'Prostate assessment / PSA elevation',
                'default_priority': 'ROUTINE'
            },
            # MRI Templates
            {
                'name': 'MRI Brain',
                'category': 'MRI',
                'description': 'MRI of the brain for detailed neurological assessment',
                'imaging_type': 'MRI',
                'body_part': 'Brain',
                'study_code': 'MRI-BRAIN',
                'default_clinical_indication': 'Neurological symptoms / Brain mass / Stroke assessment',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'MRI Spine',
                'category': 'MRI',
                'description': 'MRI of the spine for spinal assessment',
                'imaging_type': 'MRI',
                'body_part': 'Spine',
                'study_code': 'MRI-SPINE',
                'default_clinical_indication': 'Back pain / Spinal cord assessment / Disc herniation',
                'default_priority': 'ROUTINE'
            },
            {
                'name': 'MRI Joint',
                'category': 'MRI',
                'description': 'MRI of a joint for detailed assessment',
                'imaging_type': 'MRI',
                'body_part': 'Joint',
                'study_code': 'MRI-JOINT',
                'default_clinical_indication': 'Joint pain / Ligament injury / Cartilage assessment',
                'default_priority': 'ROUTINE'
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates_data:
            template, created = RadiologyTestTemplate.objects.update_or_create(
                name=template_data['name'],
                defaults={
                    'category': template_data['category'],
                    'description': template_data['description'],
                    'imaging_type': template_data['imaging_type'],
                    'body_part': template_data['body_part'],
                    'study_code': template_data['study_code'],
                    'default_clinical_indication': template_data['default_clinical_indication'],
                    'default_priority': template_data['default_priority'],
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

