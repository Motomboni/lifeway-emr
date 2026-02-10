"""
Test script for PACS-lite API endpoints.

This script tests:
1. Offline image upload flow (metadata → binary → ACK)
2. Viewer URL generation
3. Study/Series grouping
4. Image URL generation

Run with: python manage.py shell < test_pacs_lite_api.py
Or: python manage.py shell, then copy-paste the code
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.radiology.models import RadiologyOrder
from apps.radiology.pacs_lite_models import RadiologyStudy, RadiologySeries, RadiologyImage
from apps.radiology.pacs_lite_service import PACSLiteService
from apps.radiology.offline_sync_service import OfflineImageSyncService
from apps.visits.models import Visit
from apps.patients.models import Patient
from apps.consultations.models import Consultation
import uuid
import hashlib

User = get_user_model()

def test_pacs_lite_integration():
    """Test PACS-lite integration end-to-end."""
    print("=" * 80)
    print("PACS-lite Integration Test")
    print("=" * 80)
    
    # 1. Create test data
    print("\n1. Creating test data...")
    
    # Get or create test user (Radiology Tech)
    try:
        radiology_tech = User.objects.filter(role='RADIOLOGY_TECH').first()
        if not radiology_tech:
            radiology_tech = User.objects.create_user(
                username='radiology_tech_test',
                email='radtech@test.com',
                password='test123',
                role='RADIOLOGY_TECH',
                first_name='Radiology',
                last_name='Tech'
            )
        print(f"✓ Radiology Tech: {radiology_tech.get_full_name()}")
    except Exception as e:
        print(f"✗ Error creating user: {e}")
        return
    
    # Get or create test patient
    try:
        patient = Patient.objects.first()
        if not patient:
            patient = Patient.objects.create(
                first_name='Test',
                last_name='Patient',
                phone='08012345678',
                date_of_birth='1990-01-01',
                gender='MALE'
            )
        print(f"✓ Patient: {patient.get_full_name()}")
    except Exception as e:
        print(f"✗ Error creating patient: {e}")
        return
    
    # Get or create test visit
    try:
        visit = Visit.objects.filter(patient=patient, status='OPEN').first()
        if not visit:
            visit = Visit.objects.create(
                patient=patient,
                visit_type='CONSULTATION',
                status='OPEN',
                payment_type='CASH',
                payment_status='PAID'
            )
        print(f"✓ Visit: {visit.id}")
    except Exception as e:
        print(f"✗ Error creating visit: {e}")
        return
    
    # Get or create consultation
    try:
        consultation = Consultation.objects.filter(visit=visit).first()
        if not consultation:
            consultation = Consultation.objects.create(
                visit=visit,
                created_by=radiology_tech,
                history='Test history',
                examination='Test examination',
                diagnosis='Test diagnosis',
                clinical_notes='Test notes',
                status='ACTIVE'
            )
        print(f"✓ Consultation: {consultation.id}")
    except Exception as e:
        print(f"✗ Error creating consultation: {e}")
        return
    
    # Get or create radiology order
    try:
        radiology_order = RadiologyOrder.objects.filter(visit=visit).first()
        if not radiology_order:
            from apps.users.models import User as UserModel
            doctor = User.objects.filter(role='DOCTOR').first()
            if not doctor:
                doctor = User.objects.create_user(
                    username='doctor_test',
                    email='doctor@test.com',
                    password='test123',
                    role='DOCTOR',
                    first_name='Test',
                    last_name='Doctor'
                )
            
            radiology_order = RadiologyOrder.objects.create(
                visit=visit,
                ordered_by=doctor,
                imaging_type='XRAY',
                body_part='Chest',
                clinical_indication='Chest pain',
                priority='ROUTINE',
                status='ORDERED'
            )
        print(f"✓ Radiology Order: {radiology_order.id}")
    except Exception as e:
        print(f"✗ Error creating radiology order: {e}")
        return
    
    # 2. Test Study Creation
    print("\n2. Testing Study Creation...")
    try:
        study = PACSLiteService.create_study_for_order(
            radiology_order=radiology_order,
            study_description='Chest X-Ray',
            modality='CR'
        )
        print(f"✓ Study created: {study.study_uid}")
        print(f"  - Study Description: {study.study_description}")
        print(f"  - Modality: {study.modality}")
        print(f"  - Patient: {study.patient_name}")
    except Exception as e:
        print(f"✗ Error creating study: {e}")
        return
    
    # 3. Test Series Creation
    print("\n3. Testing Series Creation...")
    try:
        series = PACSLiteService.create_series_for_study(
            study=study,
            series_number=1,
            series_description='PA View',
            modality='CR'
        )
        print(f"✓ Series created: {series.series_uid}")
        print(f"  - Series Number: {series.series_number}")
        print(f"  - Series Description: {series.series_description}")
    except Exception as e:
        print(f"✗ Error creating series: {e}")
        return
    
    # 4. Test File Key Generation
    print("\n4. Testing File Key Generation...")
    try:
        image_uid = str(uuid.uuid4())
        file_key = PACSLiteService.generate_file_key(
            study_uid=study.study_uid,
            series_uid=series.series_uid,
            image_uid=image_uid,
            filename='chest_pa_test.dcm'
        )
        print(f"✓ File key generated: {file_key}")
    except Exception as e:
        print(f"✗ Error generating file key: {e}")
        return
    
    # 5. Test Offline Image Upload (Metadata)
    print("\n5. Testing Offline Image Upload - Metadata...")
    try:
        image_uuid = str(uuid.uuid4())
        test_file_content = b"Test DICOM file content for PACS-lite testing"
        checksum = hashlib.sha256(test_file_content).hexdigest()
        
        metadata = OfflineImageSyncService.upload_metadata(
            image_uuid=image_uuid,
            radiology_order_id=radiology_order.id,
            filename='chest_pa_test.dcm',
            file_size=len(test_file_content),
            mime_type='application/dicom',
            checksum=checksum,
            image_metadata={
                'study_uid': study.study_uid,
                'series_uid': series.series_uid,
                'image_uid': image_uid,
                'modality': 'CR',
                'study_description': 'Chest X-Ray',
                'series_description': 'PA View',
            },
            user=radiology_tech
        )
        print(f"✓ Metadata uploaded: {metadata.image_uuid}")
        print(f"  - Status: {metadata.status}")
        print(f"  - Filename: {metadata.filename}")
        print(f"  - File Size: {metadata.file_size} bytes")
    except Exception as e:
        print(f"✗ Error uploading metadata: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 6. Test Offline Image Upload (Binary)
    print("\n6. Testing Offline Image Upload - Binary...")
    try:
        image = OfflineImageSyncService.upload_binary(
            image_uuid=image_uuid,
            file_content=test_file_content,
            user=radiology_tech
        )
        print(f"✓ Binary uploaded: {image.image_uid}")
        print(f"  - File Key: {image.file_key}")
        print(f"  - Series: {image.series.series_uid}")
        print(f"  - Study: {image.series.study.study_uid}")
    except Exception as e:
        print(f"✗ Error uploading binary: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 7. Test ACK
    print("\n7. Testing ACK...")
    try:
        ack_metadata = OfflineImageSyncService.acknowledge_upload(
            image_uuid=image_uuid
        )
        print(f"✓ ACK received: {ack_metadata.status}")
        print(f"  - ACK received at: {ack_metadata.ack_received_at}")
    except Exception as e:
        print(f"✗ Error acknowledging upload: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 8. Test Viewer URL Generation
    print("\n8. Testing Viewer URL Generation...")
    try:
        viewer_url = PACSLiteService.generate_viewer_url(
            study_uid=study.study_uid,
            user=radiology_tech,
            expires_in=3600
        )
        print(f"✓ Viewer URL generated: {viewer_url}")
    except Exception as e:
        print(f"✗ Error generating viewer URL: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 9. Test Image URL Generation
    print("\n9. Testing Image URL Generation...")
    try:
        image_url = PACSLiteService.generate_image_url(
            image=image,
            user=radiology_tech,
            expires_in=3600
        )
        print(f"✓ Image URL generated: {image_url}")
    except Exception as e:
        print(f"✗ Error generating image URL: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 10. Test Study Images Retrieval
    print("\n10. Testing Study Images Retrieval...")
    try:
        study_images = PACSLiteService.get_study_images(study.study_uid)
        print(f"✓ Retrieved {len(study_images)} images for study")
        for img in study_images:
            print(f"  - Image: {img.image_uid} ({img.filename})")
    except Exception as e:
        print(f"✗ Error retrieving study images: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 11. Test Series Images Retrieval
    print("\n11. Testing Series Images Retrieval...")
    try:
        series_images = PACSLiteService.get_series_images(series.series_uid)
        print(f"✓ Retrieved {len(series_images)} images for series")
        for img in series_images:
            print(f"  - Image: {img.image_uid} ({img.filename})")
    except Exception as e:
        print(f"✗ Error retrieving series images: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 80)
    print("✅ All PACS-lite Integration Tests Passed!")
    print("=" * 80)
    print(f"\nTest Summary:")
    print(f"  - Study UID: {study.study_uid}")
    print(f"  - Series UID: {series.series_uid}")
    print(f"  - Image UID: {image.image_uid}")
    print(f"  - File Key: {image.file_key}")
    print(f"  - Viewer URL: {viewer_url}")
    print(f"  - Image URL: {image_url}")

if __name__ == '__main__':
    test_pacs_lite_integration()

