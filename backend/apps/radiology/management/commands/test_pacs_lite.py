"""
Django management command to test PACS-lite API endpoints.

Usage:
    python manage.py test_pacs_lite
"""
from django.core.management.base import BaseCommand
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


class Command(BaseCommand):
    help = 'Test PACS-lite integration and API endpoints'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("PACS-lite Integration Test"))
        self.stdout.write("=" * 80)
        
        # 1. Create test data
        self.stdout.write("\n1. Creating test data...")
        
        try:
            # Get or create test user (Radiology Tech)
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
            self.stdout.write(self.style.SUCCESS(f"[OK] Radiology Tech: {radiology_tech.get_full_name()}"))
            
            # Get or create test patient
            patient = Patient.objects.first()
            if not patient:
                patient = Patient.objects.create(
                    first_name='Test',
                    last_name='Patient',
                    phone='08012345678',
                    date_of_birth='1990-01-01',
                    gender='MALE'
                )
            self.stdout.write(self.style.SUCCESS(f"[OK] Patient: {patient.get_full_name()}"))
            
            # Get or create test visit
            visit = Visit.objects.filter(patient=patient, status='OPEN').first()
            if not visit:
                visit = Visit.objects.create(
                    patient=patient,
                    visit_type='CONSULTATION',
                    status='OPEN',
                    payment_type='CASH',
                    payment_status='PAID'
                )
            self.stdout.write(self.style.SUCCESS(f"[OK] Visit: {visit.id}"))
            
            # Get or create consultation
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
            self.stdout.write(self.style.SUCCESS(f"[OK] Consultation: {consultation.id}"))
            
            # Get or create radiology order
            radiology_order = RadiologyOrder.objects.filter(visit=visit).first()
            if not radiology_order:
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
            self.stdout.write(self.style.SUCCESS(f"[OK] Radiology Order: {radiology_order.id}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error creating test data: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 2. Test Study Creation
        self.stdout.write("\n2. Testing Study Creation...")
        try:
            study = PACSLiteService.create_study_for_order(
                radiology_order=radiology_order,
                study_description='Chest X-Ray',
                modality='CR'
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Study created: {study.study_uid}"))
            self.stdout.write(f"  - Study Description: {study.study_description}")
            self.stdout.write(f"  - Modality: {study.modality}")
            self.stdout.write(f"  - Patient: {study.patient_name}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error creating study: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 3. Test Series Creation
        self.stdout.write("\n3. Testing Series Creation...")
        try:
            series = PACSLiteService.create_series_for_study(
                study=study,
                series_number=1,
                series_description='PA View',
                modality='CR'
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Series created: {series.series_uid}"))
            self.stdout.write(f"  - Series Number: {series.series_number}")
            self.stdout.write(f"  - Series Description: {series.series_description}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error creating series: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 4. Test File Key Generation
        self.stdout.write("\n4. Testing File Key Generation...")
        try:
            image_uid = str(uuid.uuid4())
            file_key = PACSLiteService.generate_file_key(
                study_uid=study.study_uid,
                series_uid=series.series_uid,
                image_uid=image_uid,
                filename='chest_pa_test.dcm'
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] File key generated: {file_key}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error generating file key: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 5. Test Offline Image Upload (Metadata)
        self.stdout.write("\n5. Testing Offline Image Upload - Metadata...")
        try:
            image_uuid = str(uuid.uuid4())
            test_file_content = b"Test DICOM file content for PACS-lite testing - " + b"X" * 1000
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
            self.stdout.write(self.style.SUCCESS(f"[OK] Metadata uploaded: {metadata.image_uuid}"))
            self.stdout.write(f"  - Status: {metadata.status}")
            self.stdout.write(f"  - Filename: {metadata.filename}")
            self.stdout.write(f"  - File Size: {metadata.file_size} bytes")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error uploading metadata: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 6. Test Offline Image Upload (Binary)
        self.stdout.write("\n6. Testing Offline Image Upload - Binary...")
        try:
            image = OfflineImageSyncService.upload_binary(
                image_uuid=image_uuid,
                file_content=test_file_content,
                user=radiology_tech
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Binary uploaded: {image.image_uid}"))
            self.stdout.write(f"  - File Key: {image.file_key}")
            self.stdout.write(f"  - Series: {image.series.series_uid}")
            self.stdout.write(f"  - Study: {image.series.study.study_uid}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error uploading binary: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 7. Test ACK
        self.stdout.write("\n7. Testing ACK...")
        try:
            ack_metadata = OfflineImageSyncService.acknowledge_upload(
                image_uuid=image_uuid
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] ACK received: {ack_metadata.status}"))
            self.stdout.write(f"  - ACK received at: {ack_metadata.ack_received_at}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error acknowledging upload: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 8. Test Viewer URL Generation
        self.stdout.write("\n8. Testing Viewer URL Generation...")
        try:
            viewer_url = PACSLiteService.generate_viewer_url(
                study_uid=study.study_uid,
                user=radiology_tech,
                expires_in=3600
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Viewer URL generated: {viewer_url}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error generating viewer URL: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 9. Test Image URL Generation
        self.stdout.write("\n9. Testing Image URL Generation...")
        try:
            image_url = PACSLiteService.generate_image_url(
                image=image,
                user=radiology_tech,
                expires_in=3600
            )
            self.stdout.write(self.style.SUCCESS(f"[OK] Image URL generated: {image_url}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error generating image URL: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 10. Test Study Images Retrieval
        self.stdout.write("\n10. Testing Study Images Retrieval...")
        try:
            study_images = PACSLiteService.get_study_images(study.study_uid)
            self.stdout.write(self.style.SUCCESS(f"[OK] Retrieved {len(study_images)} images for study"))
            for img in study_images:
                self.stdout.write(f"  - Image: {img.image_uid} ({img.filename})")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error retrieving study images: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        # 11. Test Series Images Retrieval
        self.stdout.write("\n11. Testing Series Images Retrieval...")
        try:
            series_images = PACSLiteService.get_series_images(series.series_uid)
            self.stdout.write(self.style.SUCCESS(f"[OK] Retrieved {len(series_images)} images for series"))
            for img in series_images:
                self.stdout.write(f"  - Image: {img.image_uid} ({img.filename})")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] Error retrieving series images: {e}"))
            import traceback
            traceback.print_exc()
            return
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("[OK] All PACS-lite Integration Tests Passed!"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"\nTest Summary:")
        self.stdout.write(f"  - Study UID: {study.study_uid}")
        self.stdout.write(f"  - Series UID: {series.series_uid}")
        self.stdout.write(f"  - Image UID: {image.image_uid}")
        self.stdout.write(f"  - File Key: {image.file_key}")
        self.stdout.write(f"  - Viewer URL: {viewer_url}")
        self.stdout.write(f"  - Image URL: {image_url}")
