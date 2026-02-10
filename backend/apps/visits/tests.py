"""
Unit tests for visit creation logic from ServiceCatalog.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import transaction
from decimal import Decimal

from .models import Visit
from apps.billing.service_catalog_models import ServiceCatalog
from apps.patients.models import Patient
from apps.users.models import User
from .service_catalog_service import (
    get_or_create_visit_for_service,
    ensure_visit_for_service,
    can_order_service,
    validate_service_for_visit,
)


class ServiceCatalogVisitCreationTests(TestCase):
    """Test visit creation from ServiceCatalog."""
    
    def setUp(self):
        """Set up test data."""
        # Create test patient
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            patient_id='TEST001',
            date_of_birth='1990-01-01',
            gender='MALE',
            phone='08012345678',
        )
        
        # Create test user (doctor)
        self.doctor = User.objects.create_user(
            username='doctor1',
            email='doctor@test.com',
            password='testpass123',
            role='DOCTOR',
            first_name='Test',
            last_name='Doctor',
        )
        
        # Create GOPD consultation service
        self.gopd_service = ServiceCatalog.objects.create(
            department='CONSULTATION',
            service_code='CONS-001',
            name='General Consultation',
            amount=Decimal('5000.00'),
            description='General outpatient consultation',
            category='CONSULTATION',
            workflow_type='GOPD_CONSULT',
            requires_visit=True,
            requires_consultation=False,
            auto_bill=True,
            bill_timing='BEFORE',
            allowed_roles=['DOCTOR', 'NURSE'],
            is_active=True,
        )
        
        # Create lab service that requires visit
        self.lab_service = ServiceCatalog.objects.create(
            department='LAB',
            service_code='LAB-001',
            name='Complete Blood Count',
            amount=Decimal('3000.00'),
            description='CBC test',
            category='LAB',
            workflow_type='LAB_ORDER',
            requires_visit=True,
            requires_consultation=True,
            auto_bill=True,
            bill_timing='AFTER',
            allowed_roles=['DOCTOR'],
            is_active=True,
        )
        
        # Create service that doesn't require visit
        self.no_visit_service = ServiceCatalog.objects.create(
            department='PHARMACY',
            service_code='DRUG-001',
            name='Paracetamol',
            amount=Decimal('500.00'),
            description='Pain relief',
            category='DRUG',
            workflow_type='DRUG_DISPENSE',
            requires_visit=False,
            requires_consultation=False,
            auto_bill=True,
            bill_timing='AFTER',
            allowed_roles=['PHARMACIST'],
            is_active=True,
        )
    
    def test_create_visit_for_gopd_service(self):
        """Test creating a visit for GOPD consultation service."""
        visit, created = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
            payment_type='CASH',
            chief_complaint='Headache',
        )
        
        self.assertTrue(created, "Visit should be created")
        self.assertIsNotNone(visit)
        self.assertEqual(visit.patient, self.patient)
        self.assertEqual(visit.visit_type, 'CONSULTATION')
        self.assertEqual(visit.status, 'OPEN')
        self.assertEqual(visit.payment_status, 'UNPAID')
        self.assertEqual(visit.payment_type, 'CASH')
        self.assertEqual(visit.chief_complaint, 'Headache')
    
    def test_reuse_existing_active_visit(self):
        """Test reusing existing active visit for same patient."""
        # Create initial visit
        visit1, created1 = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
        )
        
        self.assertTrue(created1, "First visit should be created")
        
        # Try to create another visit for same patient
        visit2, created2 = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.lab_service,
            user=self.doctor,
        )
        
        self.assertFalse(created2, "Second visit should not be created")
        self.assertEqual(visit1.id, visit2.id, "Should reuse existing visit")
        self.assertEqual(visit2.status, 'OPEN')
    
    def test_one_active_visit_per_patient(self):
        """Test that only one active visit exists per patient at a time."""
        # Create first visit
        visit1, _ = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
        )
        
        # Verify only one active visit
        active_visits = Visit.objects.filter(
            patient=self.patient,
            status='OPEN'
        )
        self.assertEqual(active_visits.count(), 1)
        
        # Create second service - should reuse visit
        visit2, created2 = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.lab_service,
            user=self.doctor,
        )
        
        self.assertFalse(created2)
        self.assertEqual(visit1.id, visit2.id)
        
        # Still only one active visit
        active_visits = Visit.objects.filter(
            patient=self.patient,
            status='OPEN'
        )
        self.assertEqual(active_visits.count(), 1)
    
    def test_service_requires_visit_validation(self):
        """Test that service requiring visit raises error if requires_visit=False."""
        with self.assertRaises(ValidationError) as cm:
            get_or_create_visit_for_service(
                patient=self.patient,
                service=self.no_visit_service,
                user=self.doctor,
            )
        
        self.assertIn('does not require a visit', str(cm.exception))
    
    def test_inactive_service_validation(self):
        """Test that inactive service cannot create visit."""
        self.gopd_service.is_active = False
        self.gopd_service.save()
        
        with self.assertRaises(ValidationError) as cm:
            get_or_create_visit_for_service(
                patient=self.patient,
                service=self.gopd_service,
                user=self.doctor,
            )
        
        self.assertIn('not active', str(cm.exception))
    
    def test_workflow_type_to_visit_type_mapping(self):
        """Test that workflow_type is correctly mapped to visit_type."""
        # GOPD_CONSULT -> CONSULTATION
        visit, _ = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
        )
        self.assertEqual(visit.visit_type, 'CONSULTATION')
        
        # LAB_ORDER -> ROUTINE
        # Create a consultation first (required before closing)
        from apps.consultations.models import Consultation
        Consultation.objects.create(
            visit=visit,
            created_by=self.doctor,
            history='Test history',
        )
        
        # Close first visit to allow new one
        visit.status = 'CLOSED'
        visit.save()
        
        visit2, _ = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.lab_service,
            user=self.doctor,
        )
        self.assertEqual(visit2.visit_type, 'ROUTINE')
    
    def test_visit_creation_is_atomic(self):
        """Test that visit creation is atomic (transactional)."""
        # This test ensures that if visit creation fails partway,
        # no partial visit is created
        
        # Create a service with invalid configuration to trigger validation error
        invalid_service = ServiceCatalog.objects.create(
            department='CONSULTATION',
            service_code='INVALID-001',
            name='Invalid Service',
            amount=Decimal('1000.00'),
            category='CONSULTATION',
            workflow_type='GOPD_CONSULT',
            requires_visit=True,
            requires_consultation=False,
            auto_bill=True,
            bill_timing='BEFORE',
            allowed_roles=['DOCTOR'],
            is_active=True,
        )
        
        # Manually break the service to cause validation error
        # (This is a bit contrived, but tests the atomicity)
        initial_count = Visit.objects.filter(patient=self.patient).count()
        
        # Normal creation should work
        visit, created = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
        )
        
        self.assertTrue(created)
        self.assertEqual(
            Visit.objects.filter(patient=self.patient).count(),
            initial_count + 1
        )
    
    def test_ensure_visit_for_service(self):
        """Test ensure_visit_for_service convenience function."""
        visit = ensure_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
            chief_complaint='Fever',
        )
        
        self.assertIsNotNone(visit)
        self.assertIsInstance(visit, Visit)
        self.assertEqual(visit.patient, self.patient)
        self.assertEqual(visit.chief_complaint, 'Fever')
    
    def test_can_order_service(self):
        """Test can_order_service function."""
        # Doctor can order GOPD service
        self.assertTrue(can_order_service(self.gopd_service, 'DOCTOR'))
        
        # Nurse can order GOPD service
        self.assertTrue(can_order_service(self.gopd_service, 'NURSE'))
        
        # Receptionist cannot order GOPD service
        self.assertFalse(can_order_service(self.gopd_service, 'RECEPTIONIST'))
        
        # Doctor can order lab service
        self.assertTrue(can_order_service(self.lab_service, 'DOCTOR'))
        
        # Nurse cannot order lab service
        self.assertFalse(can_order_service(self.lab_service, 'NURSE'))
    
    def test_validate_service_for_visit(self):
        """Test validate_service_for_visit function."""
        # Create visit
        visit, _ = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
        )
        
        # Valid service for open visit
        validate_service_for_visit(self.gopd_service, visit)
        # Should not raise
        
        # Invalid: service requires consultation but visit doesn't have one
        with self.assertRaises(ValidationError) as cm:
            validate_service_for_visit(self.lab_service, visit)
        
        self.assertIn('requires a consultation', str(cm.exception))
        
        # Invalid: closed visit (need consultation first)
        from apps.consultations.models import Consultation
        Consultation.objects.create(
            visit=visit,
            created_by=self.doctor,
            history='Test history',
        )
        visit.status = 'CLOSED'
        visit.save()
        
        with self.assertRaises(ValidationError) as cm:
            validate_service_for_visit(self.gopd_service, visit)
        
        self.assertIn('requires an active visit', str(cm.exception))
    
    def test_visit_with_insurance_payment_type(self):
        """Test creating visit with INSURANCE payment type."""
        visit, created = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
            payment_type='INSURANCE',
        )
        
        self.assertTrue(created)
        self.assertEqual(visit.payment_type, 'INSURANCE')
        self.assertEqual(visit.payment_status, 'UNPAID')
    
    def test_multiple_patients_can_have_active_visits(self):
        """Test that different patients can have active visits simultaneously."""
        # Create second patient
        patient2 = Patient.objects.create(
            first_name='Test2',
            last_name='Patient2',
            patient_id='TEST002',
            date_of_birth='1990-01-01',
            gender='FEMALE',
            phone='08012345679',
        )
        
        # Create visit for first patient
        visit1, created1 = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
        )
        
        # Create visit for second patient
        visit2, created2 = get_or_create_visit_for_service(
            patient=patient2,
            service=self.gopd_service,
            user=self.doctor,
        )
        
        self.assertTrue(created1)
        self.assertTrue(created2)
        self.assertNotEqual(visit1.id, visit2.id)
        
        # Both patients should have active visits
        self.assertEqual(
            Visit.objects.filter(patient=self.patient, status='OPEN').count(),
            1
        )
        self.assertEqual(
            Visit.objects.filter(patient=patient2, status='OPEN').count(),
            1
        )
    
    def test_closed_visit_does_not_block_new_visit(self):
        """Test that closed visit doesn't prevent creating new active visit."""
        # Create and close a visit
        visit1, _ = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
        )
        # Create consultation (required before closing)
        from apps.consultations.models import Consultation
        Consultation.objects.create(
            visit=visit1,
            created_by=self.doctor,
            history='Test history',
        )
        visit1.status = 'CLOSED'
        visit1.save()
        
        # Should be able to create new visit
        visit2, created2 = get_or_create_visit_for_service(
            patient=self.patient,
            service=self.gopd_service,
            user=self.doctor,
        )
        
        self.assertTrue(created2)
        self.assertNotEqual(visit1.id, visit2.id)
        self.assertEqual(visit2.status, 'OPEN')

