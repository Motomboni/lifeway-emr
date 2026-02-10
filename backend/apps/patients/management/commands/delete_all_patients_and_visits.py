"""
Django management command to delete all Patient and Visit records.

This command will:
1. Delete all Patient records from the database
2. Cascade delete all related records:
   - Visits (CASCADE)
   - Consultations (CASCADE from Visit)
   - Lab Orders and Results (CASCADE from Visit)
   - Radiology Orders and Results (CASCADE from Visit)
   - Prescriptions (CASCADE from Visit)
   - Payments and Payment Intents (CASCADE from Visit)
   - Bills, Bill Items, and Bill Payments (CASCADE from Visit)
   - Visit Charges (CASCADE from Visit)
   - Referrals (CASCADE from Visit)
   - Nursing Notes (CASCADE from Visit)
   - Clinical Alerts (CASCADE from Visit)
   - Vital Signs (CASCADE from Visit)
   - Appointments (SET_NULL, but we'll clean them up)
3. Preserve Users, Services, Drugs, and other independent records

Usage:
    python manage.py delete_all_patients_and_visits
    python manage.py delete_all_patients_and_visits --confirm  # Skip confirmation prompt
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.patients.models import Patient
from apps.visits.models import Visit


class Command(BaseCommand):
    help = 'Delete all Patient and Visit records from the database (cascade deletes all related records)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt and delete immediately',
        )

    def handle(self, *args, **options):
        patient_count = Patient.objects.count()
        visit_count = Visit.objects.count()
        
        if patient_count == 0 and visit_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No patients or visits found in the database. Nothing to delete.')
            )
            return

        # Count related records
        related_counts = {}
        try:
            from apps.consultations.models import Consultation
            related_counts['consultations'] = Consultation.objects.count()
        except ImportError:
            related_counts['consultations'] = 0
        
        try:
            from apps.laboratory.models import LabOrder
            related_counts['lab_orders'] = LabOrder.objects.count()
        except ImportError:
            related_counts['lab_orders'] = 0
        
        try:
            from apps.radiology.models import RadiologyOrder
            related_counts['radiology_orders'] = RadiologyOrder.objects.count()
        except ImportError:
            related_counts['radiology_orders'] = 0
        
        try:
            from apps.pharmacy.models import Prescription
            related_counts['prescriptions'] = Prescription.objects.count()
        except ImportError:
            related_counts['prescriptions'] = 0
        
        try:
            from apps.billing.models import Bill, Payment
            related_counts['bills'] = Bill.objects.count()
            related_counts['payments'] = Payment.objects.count()
        except ImportError:
            related_counts['bills'] = 0
            related_counts['payments'] = 0
        
        try:
            from apps.clinical.models import VitalSigns, ClinicalAlert
            related_counts['vital_signs'] = VitalSigns.objects.count()
            related_counts['clinical_alerts'] = ClinicalAlert.objects.count()
        except ImportError:
            related_counts['vital_signs'] = 0
            related_counts['clinical_alerts'] = 0
        
        try:
            from apps.appointments.models import Appointment
            related_counts['appointments'] = Appointment.objects.count()
        except ImportError:
            related_counts['appointments'] = 0

        self.stdout.write(
            self.style.WARNING(
                f'\n⚠️  WARNING: This will delete:\n'
                f'  - {patient_count} patient(s)\n'
                f'  - {visit_count} visit(s)\n'
                f'  - {related_counts.get("consultations", 0)} consultation(s)\n'
                f'  - {related_counts.get("lab_orders", 0)} lab order(s)\n'
                f'  - {related_counts.get("radiology_orders", 0)} radiology order(s)\n'
                f'  - {related_counts.get("prescriptions", 0)} prescription(s)\n'
                f'  - {related_counts.get("bills", 0)} bill(s)\n'
                f'  - {related_counts.get("payments", 0)} payment(s)\n'
                f'  - {related_counts.get("vital_signs", 0)} vital signs record(s)\n'
                f'  - {related_counts.get("clinical_alerts", 0)} clinical alert(s)\n'
                f'  - {related_counts.get("appointments", 0)} appointment(s)\n'
                f'\n'
                f'And ALL other related records!\n'
                f'\n'
                f'This action CANNOT be undone!\n'
            )
        )

        if not options['confirm']:
            confirm = input('\nType "DELETE ALL PATIENTS AND VISITS" to confirm: ')
            if confirm != 'DELETE ALL PATIENTS AND VISITS':
                self.stdout.write(
                    self.style.ERROR('Deletion cancelled. Confirmation text did not match.')
                )
                return

        try:
            with transaction.atomic():
                self.stdout.write('\nStarting deletion process...')
                
                # First, delete appointments that reference patients (SET_NULL won't work for our cleanup)
                try:
                    from apps.appointments.models import Appointment
                    appointment_count = Appointment.objects.filter(patient__isnull=False).count()
                    if appointment_count > 0:
                        Appointment.objects.filter(patient__isnull=False).delete()
                        self.stdout.write(f'  ✓ Deleted {appointment_count} appointment(s)')
                except ImportError:
                    pass
                
                # Delete related records that have PROTECT foreign keys first
                # Order matters: delete child records before parent records
                self.stdout.write('\nDeleting related records with PROTECT foreign keys...')
                
                # Delete Lab Orders first (they reference Consultations)
                try:
                    from apps.laboratory.models import LabOrder
                    lab_order_count = LabOrder.objects.count()
                    if lab_order_count > 0:
                        LabOrder.objects.all().delete()
                        self.stdout.write(f'  ✓ Deleted {lab_order_count} lab order(s)')
                except ImportError:
                    pass
                
                # Delete Radiology Orders (they might reference Consultations)
                try:
                    from apps.radiology.models import RadiologyOrder
                    radiology_order_count = RadiologyOrder.objects.count()
                    if radiology_order_count > 0:
                        RadiologyOrder.objects.all().delete()
                        self.stdout.write(f'  ✓ Deleted {radiology_order_count} radiology order(s)')
                except ImportError:
                    pass
                
                # Delete Prescriptions (they might reference Consultations)
                try:
                    from apps.pharmacy.models import Prescription
                    prescription_count = Prescription.objects.count()
                    if prescription_count > 0:
                        Prescription.objects.all().delete()
                        self.stdout.write(f'  ✓ Deleted {prescription_count} prescription(s)')
                except ImportError:
                    pass
                
                # Delete Referrals (they reference Consultations)
                try:
                    from apps.referrals.models import Referral
                    referral_count = Referral.objects.count()
                    if referral_count > 0:
                        Referral.objects.all().delete()
                        self.stdout.write(f'  ✓ Deleted {referral_count} referral(s)')
                except ImportError:
                    pass
                
                # Now delete Consultations
                try:
                    from apps.consultations.models import Consultation
                    consultation_count = Consultation.objects.count()
                    if consultation_count > 0:
                        Consultation.objects.all().delete()
                        self.stdout.write(f'  ✓ Deleted {consultation_count} consultation(s)')
                except ImportError:
                    pass
                
                # Delete Telemedicine Sessions
                try:
                    from apps.telemedicine.models import TelemedicineSession
                    telemedicine_count = TelemedicineSession.objects.count()
                    if telemedicine_count > 0:
                        TelemedicineSession.objects.all().delete()
                        self.stdout.write(f'  ✓ Deleted {telemedicine_count} telemedicine session(s)')
                except ImportError:
                    pass
                
                # Delete AI Requests
                try:
                    from apps.ai_integration.models import AIRequest
                    ai_request_count = AIRequest.objects.count()
                    if ai_request_count > 0:
                        AIRequest.objects.all().delete()
                        self.stdout.write(f'  ✓ Deleted {ai_request_count} AI request(s)')
                except (ImportError, AttributeError):
                    pass
                
                # Delete all visits (CASCADE will handle other related records)
                self.stdout.write('\nDeleting visits (this will cascade delete many related records)...')
                visit_deleted_count = Visit.objects.all().delete()[0]
                self.stdout.write(f'  ✓ Deleted {visit_deleted_count} visit(s)')
                
                # Now delete all patients (this will also clean up any remaining patient-related data)
                self.stdout.write('\nDeleting patients...')
                patient_deleted_count = Patient.objects.all().delete()[0]
                self.stdout.write(f'  ✓ Deleted {patient_deleted_count} patient(s)')
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ Successfully deleted:\n'
                        f'  - {patient_deleted_count} patient(s)\n'
                        f'  - {visit_deleted_count} visit(s)\n'
                        f'  - And all related records\n'
                        f'\n'
                        f'Database cleanup completed successfully!'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\n❌ Error deleting patients and visits: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
            raise

