"""
Management command to check wallet access for patient users.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.patients.models import Patient
from apps.wallet.models import Wallet

User = get_user_model()


class Command(BaseCommand):
    help = 'Check wallet access for patient users'

    def handle(self, *args, **options):
        patient_users = User.objects.filter(role='PATIENT')
        
        self.stdout.write(f'Found {patient_users.count()} users with PATIENT role:\n')
        
        for user in patient_users:
            try:
                patient = Patient.objects.get(user=user)
                wallet = Wallet.objects.filter(patient=patient).first()
                
                if wallet:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'OK {user.username}: Has Patient record and Wallet (ID: {wallet.id})'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'WARN {user.username}: Has Patient record but NO Wallet'
                        )
                    )
            except Patient.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'ERROR {user.username}: NO Patient record linked to user account'
                    )
                )
