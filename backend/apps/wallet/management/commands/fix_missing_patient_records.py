"""
Management command to create Patient records for PATIENT users that don't have one.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.wallet.models import Wallet

User = get_user_model()


class Command(BaseCommand):
    help = 'Create Patient records for PATIENT users that don\'t have one'

    def handle(self, *args, **options):
        patient_users = User.objects.filter(role='PATIENT')
        
        created_count = 0
        for user in patient_users:
            if not Patient.objects.filter(user=user).exists():
                # Generate patient_id using the new LMC format
                patient_id = Patient.generate_patient_id()
                
                # Create Patient record
                patient = Patient.objects.create(
                    first_name=user.first_name or 'Unknown',
                    last_name=user.last_name or 'Patient',
                    email=user.email,
                    user=user,
                    patient_id=patient_id,
                    is_active=True,
                    is_verified=False
                )
                
                # Create wallet for the patient
                wallet, wallet_created = Wallet.objects.get_or_create(
                    patient=patient,
                    defaults={
                        'balance': 0.00,
                        'currency': 'NGN',
                        'is_active': True
                    }
                )
                
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created Patient record ({patient.patient_id}) and Wallet (ID: {wallet.id}) for user {user.username}'
                    )
                )
        
        if created_count == 0:
            self.stdout.write(
                self.style.SUCCESS('All PATIENT users already have Patient records.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nCreated {created_count} Patient record(s) with wallets.')
            )
