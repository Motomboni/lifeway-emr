"""
Django management command to delete all Visit records.

This command will:
1. Delete all Visit records from the database
2. Cascade delete all related records (Consultations, Lab Orders, Radiology Orders, Prescriptions, Payments, Bills, etc.)
3. Preserve Patients, Users, and other independent records

Usage:
    python manage.py delete_all_visits
    python manage.py delete_all_visits --confirm  # Skip confirmation prompt
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.visits.models import Visit


class Command(BaseCommand):
    help = 'Delete all Visit records from the database (cascade deletes related records)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt and delete immediately',
        )

    def handle(self, *args, **options):
        visit_count = Visit.objects.count()
        
        if visit_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No visits found in the database. Nothing to delete.')
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f'\nWARNING: This will delete {visit_count} visit(s) and ALL related records:\n'
                '  - Consultations\n'
                '  - Lab Orders and Results\n'
                '  - Radiology Orders and Results\n'
                '  - Prescriptions\n'
                '  - Payments and Payment Intents\n'
                '  - Bills, Bill Items, and Bill Payments\n'
                '  - Visit Charges\n'
                '  - Referrals\n'
                '  - Nursing Notes\n'
                '  - Clinical Alerts\n'
                '  - Vital Signs\n'
                '\n'
                'This action CANNOT be undone!\n'
            )
        )

        if not options['confirm']:
            confirm = input('\nType "DELETE ALL VISITS" to confirm: ')
            if confirm != 'DELETE ALL VISITS':
                self.stdout.write(
                    self.style.ERROR('Deletion cancelled. Confirmation text did not match.')
                )
                return

        try:
            with transaction.atomic():
                # Delete related records that have PROTECT foreign keys first
                # Order matters: delete child records before parent records
                self.stdout.write('Deleting related records with PROTECT foreign keys...')
                
                # Delete Lab Orders first (they reference Consultations)
                from apps.laboratory.models import LabOrder
                lab_order_count = LabOrder.objects.count()
                if lab_order_count > 0:
                    LabOrder.objects.all().delete()
                    self.stdout.write(f'  - Deleted {lab_order_count} lab order(s)')
                
                # Delete Radiology Orders (they might reference Consultations)
                try:
                    from apps.radiology.models import RadiologyOrder
                    radiology_order_count = RadiologyOrder.objects.count()
                    if radiology_order_count > 0:
                        RadiologyOrder.objects.all().delete()
                        self.stdout.write(f'  - Deleted {radiology_order_count} radiology order(s)')
                except ImportError:
                    pass
                
                # Delete MedicationAdministration first (Prescription is PROTECTed by it)
                try:
                    from apps.nursing.models import MedicationAdministration
                    ma_count = MedicationAdministration.objects.count()
                    if ma_count > 0:
                        MedicationAdministration.objects.all().delete()
                        self.stdout.write(f'  - Deleted {ma_count} medication administration(s)')
                except (ImportError, AttributeError):
                    pass
                
                # Delete Prescriptions (they might reference Consultations)
                try:
                    from apps.pharmacy.models import Prescription
                    prescription_count = Prescription.objects.count()
                    if prescription_count > 0:
                        Prescription.objects.all().delete()
                        self.stdout.write(f'  - Deleted {prescription_count} prescription(s)')
                except ImportError:
                    pass
                
                # Delete Referrals (they reference Consultations)
                try:
                    from apps.referrals.models import Referral
                    referral_count = Referral.objects.count()
                    if referral_count > 0:
                        Referral.objects.all().delete()
                        self.stdout.write(f'  - Deleted {referral_count} referral(s)')
                except ImportError:
                    pass
                
                # Delete ProcedureTasks (visit + consultation PROTECT)
                try:
                    from apps.clinical.procedure_models import ProcedureTask
                    pt_count = ProcedureTask.objects.count()
                    if pt_count > 0:
                        ProcedureTask.objects.all().delete()
                        self.stdout.write(f'  - Deleted {pt_count} procedure task(s)')
                except (ImportError, AttributeError):
                    pass
                
                # Delete OperationNotes (visit-scoped, may reference Consultation)
                try:
                    from apps.clinical.operation_models import OperationNote
                    on_count = OperationNote.objects.count()
                    if on_count > 0:
                        OperationNote.objects.all().delete()
                        self.stdout.write(f'  - Deleted {on_count} operation note(s)')
                except (ImportError, AttributeError):
                    pass
                
                # Now delete Consultations
                from apps.consultations.models import Consultation
                consultation_count = Consultation.objects.count()
                if consultation_count > 0:
                    Consultation.objects.all().delete()
                    self.stdout.write(f'  - Deleted {consultation_count} consultation(s)')
                
                # Delete Telemedicine Sessions
                try:
                    from apps.telemedicine.models import TelemedicineSession
                    telemedicine_count = TelemedicineSession.objects.count()
                    if telemedicine_count > 0:
                        TelemedicineSession.objects.all().delete()
                        self.stdout.write(f'  - Deleted {telemedicine_count} telemedicine session(s)')
                except ImportError:
                    pass  # Telemedicine app might not exist
                
                # Delete AI Requests
                try:
                    from apps.ai_integration.models import AIRequest
                    ai_request_count = AIRequest.objects.count()
                    if ai_request_count > 0:
                        AIRequest.objects.all().delete()
                        self.stdout.write(f'  - Deleted {ai_request_count} AI request(s)')
                except (ImportError, AttributeError):
                    pass  # AI integration app might not exist
                
                # Delete Invoice/Receipt documents (visit PROTECT)
                try:
                    from apps.billing.invoice_receipt_models import InvoiceReceipt
                    ir_count = InvoiceReceipt.objects.count()
                    if ir_count > 0:
                        InvoiceReceipt.objects.all().delete()
                        self.stdout.write(f'  - Deleted {ir_count} invoice/receipt document(s)')
                except (ImportError, AttributeError):
                    pass
                
                # Now delete all visits (CASCADE will handle other related records)
                self.stdout.write('\nDeleting visits...')
                deleted_count = Visit.objects.all().delete()[0]
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\nSuccessfully deleted {deleted_count} visit(s) and all related records.'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        'Database cleanup completed successfully.'
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'\nError deleting visits: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
            raise

