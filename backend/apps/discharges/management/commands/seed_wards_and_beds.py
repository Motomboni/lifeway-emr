"""
Management command to seed demo wards and beds.

Usage:
    python manage.py seed_wards_and_beds
"""
from django.core.management.base import BaseCommand
from apps.discharges.admission_models import Ward, Bed


class Command(BaseCommand):
    help = 'Seed demo wards and beds for the admission system'

    def handle(self, *args, **options):
        self.stdout.write('Seeding wards and beds...')
        
        # Define demo wards with their beds
        wards_data = [
            {
                'name': 'General Ward',
                'code': 'GW',
                'description': 'General medical and surgical ward',
                'capacity': 20,
                'beds': [
                    {'bed_number': 'A1', 'bed_type': 'STANDARD'},
                    {'bed_number': 'A2', 'bed_type': 'STANDARD'},
                    {'bed_number': 'A3', 'bed_type': 'STANDARD'},
                    {'bed_number': 'A4', 'bed_type': 'STANDARD'},
                    {'bed_number': 'A5', 'bed_type': 'STANDARD'},
                    {'bed_number': 'B1', 'bed_type': 'STANDARD'},
                    {'bed_number': 'B2', 'bed_type': 'STANDARD'},
                    {'bed_number': 'B3', 'bed_type': 'STANDARD'},
                    {'bed_number': 'B4', 'bed_type': 'STANDARD'},
                    {'bed_number': 'B5', 'bed_type': 'STANDARD'},
                    {'bed_number': 'C1', 'bed_type': 'STANDARD'},
                    {'bed_number': 'C2', 'bed_type': 'STANDARD'},
                    {'bed_number': 'C3', 'bed_type': 'STANDARD'},
                    {'bed_number': 'C4', 'bed_type': 'STANDARD'},
                    {'bed_number': 'C5', 'bed_type': 'STANDARD'},
                    {'bed_number': 'D1', 'bed_type': 'STANDARD'},
                    {'bed_number': 'D2', 'bed_type': 'STANDARD'},
                    {'bed_number': 'D3', 'bed_type': 'STANDARD'},
                    {'bed_number': 'D4', 'bed_type': 'STANDARD'},
                    {'bed_number': 'D5', 'bed_type': 'STANDARD'},
                ]
            },
            {
                'name': 'Intensive Care Unit',
                'code': 'ICU',
                'description': 'Intensive care unit for critical patients',
                'capacity': 8,
                'beds': [
                    {'bed_number': 'ICU-1', 'bed_type': 'ICU'},
                    {'bed_number': 'ICU-2', 'bed_type': 'ICU'},
                    {'bed_number': 'ICU-3', 'bed_type': 'ICU'},
                    {'bed_number': 'ICU-4', 'bed_type': 'ICU'},
                    {'bed_number': 'ICU-5', 'bed_type': 'ICU'},
                    {'bed_number': 'ICU-6', 'bed_type': 'ICU'},
                    {'bed_number': 'ICU-7', 'bed_type': 'ICU'},
                    {'bed_number': 'ICU-8', 'bed_type': 'ICU'},
                ]
            },
            {
                'name': 'Maternity Ward',
                'code': 'MAT',
                'description': 'Maternity and obstetrics ward',
                'capacity': 12,
                'beds': [
                    {'bed_number': 'M1', 'bed_type': 'MATERNITY'},
                    {'bed_number': 'M2', 'bed_type': 'MATERNITY'},
                    {'bed_number': 'M3', 'bed_type': 'MATERNITY'},
                    {'bed_number': 'M4', 'bed_type': 'MATERNITY'},
                    {'bed_number': 'M5', 'bed_type': 'MATERNITY'},
                    {'bed_number': 'M6', 'bed_type': 'MATERNITY'},
                    {'bed_number': 'P1', 'bed_type': 'PRIVATE'},
                    {'bed_number': 'P2', 'bed_type': 'PRIVATE'},
                    {'bed_number': 'P3', 'bed_type': 'PRIVATE'},
                    {'bed_number': 'P4', 'bed_type': 'PRIVATE'},
                    {'bed_number': 'P5', 'bed_type': 'PRIVATE'},
                    {'bed_number': 'P6', 'bed_type': 'PRIVATE'},
                ]
            },
            {
                'name': 'Pediatrics Ward',
                'code': 'PED',
                'description': 'Pediatric ward for children',
                'capacity': 15,
                'beds': [
                    {'bed_number': 'PED-1', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-2', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-3', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-4', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-5', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-6', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-7', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-8', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-9', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-10', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-11', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-12', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-13', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-14', 'bed_type': 'STANDARD'},
                    {'bed_number': 'PED-15', 'bed_type': 'STANDARD'},
                ]
            },
            {
                'name': 'Isolation Ward',
                'code': 'ISO',
                'description': 'Isolation ward for infectious diseases',
                'capacity': 6,
                'beds': [
                    {'bed_number': 'ISO-1', 'bed_type': 'ISOLATION'},
                    {'bed_number': 'ISO-2', 'bed_type': 'ISOLATION'},
                    {'bed_number': 'ISO-3', 'bed_type': 'ISOLATION'},
                    {'bed_number': 'ISO-4', 'bed_type': 'ISOLATION'},
                    {'bed_number': 'ISO-5', 'bed_type': 'ISOLATION'},
                    {'bed_number': 'ISO-6', 'bed_type': 'ISOLATION'},
                ]
            },
        ]
        
        created_wards = 0
        created_beds = 0
        updated_wards = 0
        updated_beds = 0
        
        for ward_data in wards_data:
            beds_data = ward_data.pop('beds')
            
            # Create or update ward
            ward, ward_created = Ward.objects.update_or_create(
                code=ward_data['code'],
                defaults={
                    'name': ward_data['name'],
                    'description': ward_data['description'],
                    'capacity': ward_data['capacity'],
                    'is_active': True,
                }
            )
            
            if ward_created:
                created_wards += 1
                self.stdout.write(self.style.SUCCESS(f'Created ward: {ward.name} ({ward.code})'))
            else:
                updated_wards += 1
                self.stdout.write(self.style.WARNING(f'Updated ward: {ward.name} ({ward.code})'))
            
            # Create or update beds for this ward
            for bed_data in beds_data:
                bed, bed_created = Bed.objects.update_or_create(
                    ward=ward,
                    bed_number=bed_data['bed_number'],
                    defaults={
                        'bed_type': bed_data['bed_type'],
                        'is_active': True,
                        'is_available': True,  # All beds start as available
                    }
                )
                
                if bed_created:
                    created_beds += 1
                    self.stdout.write(self.style.SUCCESS(f'  Created bed: {bed.bed_number} ({bed.bed_type})'))
                else:
                    updated_beds += 1
                    # Only update availability if bed was previously inactive
                    if not bed.is_active:
                        bed.is_active = True
                        bed.is_available = True
                        bed.save()
                        self.stdout.write(self.style.WARNING(f'  Reactivated bed: {bed.bed_number}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSuccessfully seeded:\n'
            f'  - {created_wards} new wards, {updated_wards} updated\n'
            f'  - {created_beds} new beds, {updated_beds} updated\n'
            f'Total: {created_wards + updated_wards} wards, {created_beds + updated_beds} beds'
        ))

