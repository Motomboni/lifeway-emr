"""
Management command to create IVF test data for development.

Usage:
    python manage.py create_ivf_test_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from apps.users.models import User
from apps.patients.models import Patient
from apps.ivf.models import (
    IVFCycle, OvarianStimulation, OocyteRetrieval, SpermAnalysis,
    Embryo, EmbryoTransfer, IVFMedication, IVFOutcome, IVFConsent
)


class Command(BaseCommand):
    help = 'Creates IVF test data for development and testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cycles',
            type=int,
            default=5,
            help='Number of IVF cycles to create (default: 5)'
        )

    def handle(self, *args, **options):
        num_cycles = options['cycles']
        
        self.stdout.write(self.style.NOTICE(f'Creating {num_cycles} IVF test cycles...'))
        
        # Clear existing IVF test data (delete related objects first due to FK constraints)
        self.stdout.write(self.style.NOTICE('Clearing existing IVF data...'))
        IVFOutcome.objects.all().delete()
        IVFConsent.objects.all().delete()
        IVFMedication.objects.all().delete()
        EmbryoTransfer.objects.all().delete()
        Embryo.objects.all().delete()
        OocyteRetrieval.objects.all().delete()
        OvarianStimulation.objects.all().delete()
        SpermAnalysis.objects.all().delete()
        IVFCycle.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Cleared existing IVF data.'))
        
        # Get or create IVF specialist user
        try:
            ivf_specialist = User.objects.get(username='ivf_specialist')
            self.stdout.write(f'Using existing IVF Specialist user: ivf_specialist')
        except User.DoesNotExist:
            ivf_specialist = User(
                username='ivf_specialist',
                email='ivf_specialist@emr.local',
                first_name='Dr. Sarah',
                last_name='Johnson',
                role='IVF_SPECIALIST',
                is_active=True,
            )
            ivf_specialist.set_password('ivfspecialist123')
            ivf_specialist.save()
            self.stdout.write(self.style.SUCCESS(f'Created IVF Specialist user: ivf_specialist'))
        
        # Get or create embryologist user
        try:
            embryologist = User.objects.get(username='embryologist')
            self.stdout.write(f'Using existing Embryologist user: embryologist')
        except User.DoesNotExist:
            embryologist = User(
                username='embryologist',
                email='embryologist@emr.local',
                first_name='Dr. Michael',
                last_name='Chen',
                role='EMBRYOLOGIST',
                is_active=True,
            )
            embryologist.set_password('embryologist123')
            embryologist.save()
            self.stdout.write(self.style.SUCCESS(f'Created Embryologist user: embryologist'))
        
        # Get existing patients or create test patients
        patients = list(Patient.objects.all()[:10])
        
        if len(patients) < 5:
            self.stdout.write(self.style.NOTICE('Creating test patients...'))
            for i in range(5 - len(patients)):
                patient = Patient.objects.create(
                    first_name=f'IVFPatient{i+1}',
                    last_name=f'Test{i+1}',
                    date_of_birth=timezone.now().date() - timedelta(days=random.randint(9000, 14000)),
                    gender='F',
                    phone=f'+234801234{i+1:04d}',
                    email=f'ivfpatient{i+1}@test.local',
                    address=f'{i+1} Test Street, Lagos',
                )
                patients.append(patient)
                self.stdout.write(f'  Created patient: {patient.first_name} {patient.last_name}')
        
        # Create IVF cycles with various statuses
        cycle_configs = [
            {'status': 'PLANNED', 'cycle_type': 'FRESH_IVF'},
            {'status': 'STIMULATION', 'cycle_type': 'FRESH_IVF'},
            {'status': 'RETRIEVAL', 'cycle_type': 'ICSI'},
            {'status': 'TRANSFER', 'cycle_type': 'ICSI'},
            {'status': 'LUTEAL', 'cycle_type': 'FET'},
            {'status': 'PREGNANCY_TEST', 'cycle_type': 'FRESH_IVF'},
            {'status': 'PREGNANT', 'cycle_type': 'ICSI', 'pregnancy_outcome': 'POSITIVE'},
            {'status': 'COMPLETED', 'cycle_type': 'FRESH_IVF', 'pregnancy_outcome': 'LIVE_BIRTH'},
            {'status': 'COMPLETED', 'cycle_type': 'ICSI', 'pregnancy_outcome': 'NEGATIVE'},
            {'status': 'CANCELLED', 'cycle_type': 'FRESH_IVF', 'cancellation_reason': 'POOR_RESPONSE'},
        ]
        
        created_cycles = []
        patient_cycle_counts = {}  # Track cycle numbers per patient
        
        for i in range(min(num_cycles, len(cycle_configs))):
            config = cycle_configs[i]
            patient = patients[i % len(patients)]
            
            # Track cycle number for this patient
            if patient.id not in patient_cycle_counts:
                patient_cycle_counts[patient.id] = 0
            patient_cycle_counts[patient.id] += 1
            cycle_number = patient_cycle_counts[patient.id]
            
            # Random start date within last 3 months
            start_date = timezone.now().date() - timedelta(days=random.randint(1, 90))
            
            cycle = IVFCycle.objects.create(
                patient=patient,
                cycle_number=cycle_number,  # Explicitly set cycle number
                cycle_type=config['cycle_type'],
                status=config['status'],
                planned_start_date=start_date,
                actual_start_date=start_date if config['status'] != 'PLANNED' else None,
                consent_signed=config['status'] not in ['PLANNED'],
                consent_date=start_date if config['status'] not in ['PLANNED'] else None,
                created_by=ivf_specialist,
                pregnancy_outcome=config.get('pregnancy_outcome', ''),
                cancellation_reason=config.get('cancellation_reason', ''),
                clinical_notes=f'Test IVF cycle {i+1} - {config["cycle_type"]}',
            )
            created_cycles.append(cycle)
            
            self.stdout.write(f'  Created cycle #{cycle.cycle_number}: {patient.first_name} {patient.last_name} - {config["status"]}')
            
            # Add stimulation records for cycles past PLANNED
            if config['status'] not in ['PLANNED']:
                for day in range(1, random.randint(3, 8)):
                    OvarianStimulation.objects.create(
                        cycle=cycle,
                        day=day,
                        date=start_date + timedelta(days=day),
                        estradiol=random.uniform(100, 3000),
                        lh=random.uniform(1, 20),
                        progesterone=random.uniform(0.1, 2.0),
                        endometrial_thickness=random.uniform(6, 14),
                        right_ovary_follicles=[random.randint(8, 22) for _ in range(random.randint(2, 6))],
                        left_ovary_follicles=[random.randint(8, 22) for _ in range(random.randint(2, 6))],
                        recorded_by=ivf_specialist,
                    )
            
            # Add retrieval for cycles past STIMULATION
            if config['status'] not in ['PLANNED', 'STIMULATION']:
                oocytes = random.randint(5, 20)
                mature = int(oocytes * random.uniform(0.6, 0.9))
                right_oocytes = oocytes // 2
                left_oocytes = oocytes - right_oocytes
                OocyteRetrieval.objects.create(
                    cycle=cycle,
                    procedure_date=start_date + timedelta(days=12),
                    total_oocytes_retrieved=oocytes,
                    right_ovary_oocytes=right_oocytes,
                    left_ovary_oocytes=left_oocytes,
                    mature_oocytes=mature,
                    immature_oocytes=oocytes - mature,
                    degenerated_oocytes=0,
                    anesthesia_type='GENERAL',
                    complications='None',
                    performed_by=ivf_specialist,
                )
                
                # Add embryos
                num_embryos = random.randint(3, min(mature, 8))
                for e in range(1, num_embryos + 1):
                    status = 'CLEAVING'
                    if config['status'] in ['COMPLETED', 'PREGNANT']:
                        status = random.choice(['TRANSFERRED', 'FROZEN', 'DISCARDED'])
                    
                    Embryo.objects.create(
                        cycle=cycle,
                        embryo_number=e,
                        fertilization_method='IVF' if 'IVF' in config['cycle_type'] else 'ICSI',
                        fertilization_date=start_date + timedelta(days=12),
                        day1_pn_status=random.choice(['2PN', '1PN', '3PN']),
                        day3_cell_count=random.randint(6, 10) if random.random() > 0.3 else None,
                        day3_grade=random.choice(['A', 'B', 'C']) if random.random() > 0.3 else '',
                        blastocyst_day=random.choice([5, 6]) if random.random() > 0.4 else None,
                        blastocyst_grade=random.choice(['4AA', '4AB', '3BA', '3BB', '3BC']) if random.random() > 0.4 else '',
                        status=status,
                        created_by=embryologist,
                    )
            
            # Add medications
            medication_names = [
                ('Gonal-F', 'GONADOTROPIN', 150, 'IU'),
                ('Cetrotide', 'GnRH_ANTAGONIST', 0.25, 'mg'),
                ('Ovidrel', 'TRIGGER', 250, 'mcg'),
                ('Progesterone', 'PROGESTERONE', 200, 'mg'),
            ]
            
            for med_name, category, dose, unit in random.sample(medication_names, random.randint(1, 3)):
                IVFMedication.objects.create(
                    cycle=cycle,
                    medication_name=med_name,
                    category=category,
                    dose=dose,
                    unit=unit,
                    frequency='Daily',
                    route='Subcutaneous' if category != 'PROGESTERONE' else 'Vaginal',
                    start_date=start_date,
                    end_date=start_date + timedelta(days=random.randint(7, 21)),
                    prescribed_by=ivf_specialist,
                )
            
            # Add consent records
            IVFConsent.objects.create(
                cycle=cycle,
                patient=patient,
                consent_type='TREATMENT',
                signed=config['status'] not in ['PLANNED'],
                signed_date=start_date if config['status'] not in ['PLANNED'] else None,
                recorded_by=ivf_specialist,
            )
            
            # Add outcome for completed cycles
            if config['status'] == 'COMPLETED' and config.get('pregnancy_outcome'):
                is_live_birth = config['pregnancy_outcome'] == 'LIVE_BIRTH'
                IVFOutcome.objects.create(
                    cycle=cycle,
                    clinical_pregnancy=is_live_birth,
                    clinical_pregnancy_date=start_date + timedelta(days=35) if is_live_birth else None,
                    fetal_heartbeat=is_live_birth,
                    fetal_heartbeat_date=start_date + timedelta(days=42) if is_live_birth else None,
                    gestational_sacs=1 if is_live_birth else 0,
                    fetal_poles=1 if is_live_birth else 0,
                    delivery_date=start_date + timedelta(days=280) if is_live_birth else None,
                    gestational_age_at_delivery=40 if is_live_birth else None,
                    delivery_type='VAGINAL' if is_live_birth else '',
                    live_births=1 if is_live_birth else 0,
                    recorded_by=ivf_specialist,
                )
        
        # Add some sperm analyses
        self.stdout.write(self.style.NOTICE('Creating sperm analysis records...'))
        for i, cycle in enumerate(created_cycles[:3]):
            SpermAnalysis.objects.create(
                patient=cycle.patient,
                cycle=cycle,
                collection_date=cycle.planned_start_date,
                sample_source='FRESH',
                abstinence_days=random.randint(2, 5),
                volume=random.uniform(1.5, 5.0),
                concentration=random.uniform(15, 100),
                total_sperm_count=random.uniform(39, 500),
                progressive_motility=random.uniform(30, 70),
                total_motility=random.uniform(40, 80),
                normal_forms=random.uniform(4, 15),
                assessment=random.choice(['NORMAL', 'OLIGOZOOSPERMIA', 'ASTHENOZOOSPERMIA']),
                analyzed_by=embryologist,
            )
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {len(created_cycles)} IVF cycles with related data!'))
        self.stdout.write(self.style.SUCCESS(f'\nTest credentials:'))
        self.stdout.write(f'  IVF Specialist: username=ivf_specialist, password=ivfspecialist123')
        self.stdout.write(f'  Embryologist: username=embryologist, password=embryologist123')
