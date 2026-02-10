"""
Create Test Radiology Services for Service Catalog

Run this script in Django shell:
cd backend
python manage.py shell < CREATE_TEST_RADIOLOGY_SERVICES.py

Or copy-paste the code below into Django shell.
"""

from apps.billing.service_catalog_models import ServiceCatalog
from decimal import Decimal

def create_radiology_services():
    """Create common radiology services for testing."""
    
    radiology_services = [
        {
            'service_code': 'RAD-XRAY-CHEST',
            'name': 'Chest X-Ray PA',
            'amount': Decimal('7500.00'),
            'description': 'Chest X-Ray - Posteroanterior view'
        },
        {
            'service_code': 'RAD-XRAY-CHEST-LAT',
            'name': 'Chest X-Ray Lateral',
            'amount': Decimal('8000.00'),
            'description': 'Chest X-Ray - Lateral view'
        },
        {
            'service_code': 'RAD-XRAY-ABDOMEN',
            'name': 'Abdominal X-Ray',
            'amount': Decimal('8500.00'),
            'description': 'Abdominal X-Ray'
        },
        {
            'service_code': 'RAD-XRAY-SPINE',
            'name': 'Spine X-Ray',
            'amount': Decimal('9000.00'),
            'description': 'Spine X-Ray (cervical, thoracic, or lumbar)'
        },
        {
            'service_code': 'RAD-XRAY-PELVIS',
            'name': 'Pelvis X-Ray',
            'amount': Decimal('8500.00'),
            'description': 'Pelvis X-Ray'
        },
        {
            'service_code': 'RAD-XRAY-EXTREMITY',
            'name': 'Extremity X-Ray',
            'amount': Decimal('7000.00'),
            'description': 'X-Ray of arm, leg, hand, or foot'
        },
        {
            'service_code': 'RAD-US-ABDOMEN',
            'name': 'Ultrasound Abdomen',
            'amount': Decimal('12000.00'),
            'description': 'Abdominal ultrasound scan'
        },
        {
            'service_code': 'RAD-US-PELVIS',
            'name': 'Ultrasound Pelvis',
            'amount': Decimal('12000.00'),
            'description': 'Pelvic ultrasound scan'
        },
        {
            'service_code': 'RAD-US-OBSTETRIC',
            'name': 'Obstetric Ultrasound',
            'amount': Decimal('15000.00'),
            'description': 'Pregnancy ultrasound scan'
        },
        {
            'service_code': 'RAD-US-BREAST',
            'name': 'Breast Ultrasound',
            'amount': Decimal('13000.00'),
            'description': 'Breast ultrasound scan'
        },
        {
            'service_code': 'RAD-CT-HEAD',
            'name': 'CT Scan Head',
            'amount': Decimal('45000.00'),
            'description': 'CT scan of the head'
        },
        {
            'service_code': 'RAD-CT-CHEST',
            'name': 'CT Scan Chest',
            'amount': Decimal('50000.00'),
            'description': 'CT scan of the chest'
        },
        {
            'service_code': 'RAD-CT-ABDOMEN',
            'name': 'CT Scan Abdomen',
            'amount': Decimal('50000.00'),
            'description': 'CT scan of the abdomen'
        },
        {
            'service_code': 'RAD-MRI-BRAIN',
            'name': 'MRI Brain',
            'amount': Decimal('85000.00'),
            'description': 'MRI scan of the brain'
        },
        {
            'service_code': 'RAD-MRI-SPINE',
            'name': 'MRI Spine',
            'amount': Decimal('90000.00'),
            'description': 'MRI scan of the spine'
        },
    ]
    
    created_count = 0
    skipped_count = 0
    
    for service_data in radiology_services:
        # Check if service already exists
        existing = ServiceCatalog.objects.filter(
            service_code=service_data['service_code']
        ).first()
        
        if existing:
            print(f"⏭️  Skipped (already exists): {service_data['name']}")
            skipped_count += 1
            continue
        
        # Create the service
        service = ServiceCatalog.objects.create(
            department='RADIOLOGY',
            service_code=service_data['service_code'],
            name=service_data['name'],
            amount=service_data['amount'],
            description=service_data['description'],
            category='RADIOLOGY',
            workflow_type='RADIOLOGY_STUDY',
            requires_visit=True,
            requires_consultation=True,
            auto_bill=True,
            bill_timing='BEFORE',  # Patient pays before study
            allowed_roles=['DOCTOR'],
            is_active=True,
        )
        print(f"✅ Created: {service.name} - ₦{service.amount}")
        created_count += 1
    
    print("\n" + "="*60)
    print(f"Summary:")
    print(f"  ✅ Created: {created_count} services")
    print(f"  ⏭️  Skipped: {skipped_count} services (already exist)")
    print(f"  📊 Total: {created_count + skipped_count} radiology services")
    print("="*60)
    
    # Verify
    all_rad_services = ServiceCatalog.objects.filter(
        department='RADIOLOGY',
        is_active=True
    )
    print(f"\n✅ Active RADIOLOGY services in database: {all_rad_services.count()}")
    
    return created_count, skipped_count

# Run the function
if __name__ == '__main__':
    created, skipped = create_radiology_services()
    print(f"\n🎉 Done! Created {created} new radiology services.")
    print("\n📝 Next steps:")
    print("1. Go to consultation workspace")
    print("2. Click 'Search & Order Service'")
    print("3. Type 'X-Ray' or 'Ultrasound' or 'CT' or 'MRI'")
    print("4. Select a radiology service")
    print("5. Fill in the Radiology Order Details form")
    print("6. Submit the order")
    print("7. Check 'Radiology Orders & Results' section")

