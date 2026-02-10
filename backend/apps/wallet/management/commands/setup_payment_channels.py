"""
Management command to set up default payment channels.
"""
from django.core.management.base import BaseCommand
from apps.wallet.models import PaymentChannel


class Command(BaseCommand):
    help = 'Set up default payment channels'

    def handle(self, *args, **options):
        channels = [
            {
                'name': 'Paystack',
                'channel_type': 'PAYSTACK',
                'is_active': True,
                'config': {
                    'description': 'Pay with card, bank transfer, or USSD',
                    'supported_currencies': ['NGN'],
                }
            },
            {
                'name': 'Mobile Money',
                'channel_type': 'MOBILE_MONEY',
                'is_active': True,
                'config': {
                    'description': 'Pay with mobile money',
                    'supported_networks': ['MTN', 'Airtel', 'Glo', '9mobile'],
                }
            },
            {
                'name': 'Bank Transfer',
                'channel_type': 'BANK_TRANSFER',
                'is_active': True,
                'config': {
                    'description': 'Direct bank transfer',
                }
            },
            {
                'name': 'Cash',
                'channel_type': 'CASH',
                'is_active': True,
                'config': {
                    'description': 'Cash payment at facility',
                }
            },
        ]

        created_count = 0
        updated_count = 0

        for channel_data in channels:
            channel, created = PaymentChannel.objects.update_or_create(
                name=channel_data['name'],
                defaults={
                    'channel_type': channel_data['channel_type'],
                    'is_active': channel_data['is_active'],
                    'config': channel_data['config'],
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created payment channel: {channel.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Updated payment channel: {channel.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPayment channels setup complete. '
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )
