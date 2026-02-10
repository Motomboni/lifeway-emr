"""
Management command to create wallets for existing patients that don't have one.
"""
from django.core.management.base import BaseCommand
from apps.patients.models import Patient
from apps.wallet.models import Wallet
from decimal import Decimal


class Command(BaseCommand):
    help = 'Create wallets for patients that don\'t have one'

    def handle(self, *args, **options):
        patients_without_wallets = Patient.objects.filter(wallet__isnull=True)
        count = patients_without_wallets.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('All patients already have wallets.')
            )
            return
        
        created_count = 0
        for patient in patients_without_wallets:
            try:
                Wallet.objects.create(
                    patient=patient,
                    balance=Decimal('0.00'),
                    currency='NGN',
                    is_active=True
                )
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created wallet for patient {patient.patient_id} ({patient.get_full_name()})')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Failed to create wallet for patient {patient.patient_id}: {e}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nCreated {created_count} wallet(s) for {count} patient(s) without wallets.'
            )
        )
