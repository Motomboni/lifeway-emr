"""
Unit tests for Revenue Leak Detection.

Tests each leak scenario:
1. LabResult exists but no PAID bill
2. RadiologyReport exists but no PAID bill
3. DrugDispense exists but no PAID bill
4. Procedure marked completed but unpaid
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import datetime
from django.utils import timezone

from apps.patients.models import Patient
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from apps.laboratory.models import LabOrder, LabResult
from apps.radiology.models import RadiologyRequest
from apps.pharmacy.models import Prescription
from apps.clinical.procedure_models import ProcedureTask
from apps.billing.service_catalog_models import ServiceCatalog
from apps.billing.billing_line_item_models import BillingLineItem
from apps.billing.leak_detection_models import LeakRecord
from apps.billing.leak_detection_service import LeakDetectionService

User = get_user_model()


class LeakDetectionTestCase(TestCase):
    """Base test case for leak detection tests."""
    
    def setUp(self):
        """Set up test data."""
        # Create users
        self.doctor = User.objects.create_user(
            username='doctor',
            email='doctor@test.com',
            password='test123',
            role='DOCTOR',
            first_name='Test',
            last_name='Doctor'
        )
        
        self.lab_tech = User.objects.create_user(
            username='lab_tech',
            email='labtech@test.com',
            password='test123',
            role='LAB_TECH',
            first_name='Test',
            last_name='LabTech'
        )
        
        self.radiology_tech = User.objects.create_user(
            username='radiology_tech',
            email='radtech@test.com',
            password='test123',
            role='RADIOLOGY_TECH',
            first_name='Test',
            last_name='RadiologyTech'
        )
        
        self.pharmacist = User.objects.create_user(
            username='pharmacist',
            email='pharmacist@test.com',
            password='test123',
            role='PHARMACIST',
            first_name='Test',
            last_name='Pharmacist'
        )
        
        self.nurse = User.objects.create_user(
            username='nurse',
            email='nurse@test.com',
            password='test123',
            role='NURSE',
            first_name='Test',
            last_name='Nurse'
        )
        
        # Create patient
        self.patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            phone='08012345678',
            date_of_birth='1990-01-01',
            gender='MALE'
        )
        
        # Create visit - we'll set payment_status to PAID after creating billing items
        # Note: For leak detection tests, we need payment cleared for the visit
        # but we'll test scenarios where specific services don't have paid bills
        self.visit = Visit.objects.create(
            patient=self.patient,
            visit_type='CONSULTATION',
            status='OPEN',
            payment_type='CASH',
            payment_status='UNPAID'  # Will be updated to PAID after billing item creation
        )
        
        # Create consultation
        self.consultation = Consultation.objects.create(
            visit=self.visit,
            created_by=self.doctor,
            history='Test history',
            examination='Test examination',
            diagnosis='Test diagnosis',
            clinical_notes='Test notes',
            status='ACTIVE'
        )
        
        # Create a paid consultation billing item to ensure visit payment is cleared
        # This allows us to create lab orders, etc. while testing leak detection
        # for specific services that don't have paid bills
        consultation_service = ServiceCatalog.objects.create(
            service_code='CONSULT_001',
            name='Consultation',
            department='CONSULTATION',
            category='CONSULTATION',
            workflow_type='GOPD_CONSULT',
            amount=Decimal('2000.00'),
            is_active=True,
            auto_bill=True,
            bill_timing='BEFORE',
            requires_visit=True,
            requires_consultation=True,
            allowed_roles=['DOCTOR']
        )
        
        # Create paid consultation billing item
        BillingLineItem.objects.create(
            service_catalog=consultation_service,
            visit=self.visit,
            consultation=self.consultation,
            source_service_code=consultation_service.service_code,
            source_service_name=consultation_service.name,
            amount=consultation_service.amount,
            bill_status='PAID',
            amount_paid=consultation_service.amount,
            outstanding_amount=Decimal('0.00'),
            payment_method='CASH',
            created_by=self.doctor
        )
        
        # Update visit payment status to PAID using direct database update
        # This ensures the payment_status is persisted before any subsequent operations
        # is_payment_cleared() checks if payment_status is 'PAID', 'SETTLED', or 'PARTIALLY_PAID'
        Visit.objects.filter(pk=self.visit.pk).update(payment_status='PAID')
        self.visit.refresh_from_db()
        
        # Verify payment is cleared
        assert self.visit.payment_status == 'PAID', f"Visit payment_status should be PAID, got {self.visit.payment_status}"
        assert self.visit.is_payment_cleared(), "Visit payment should be cleared"
        
        # Create ServiceCatalog entries
        self.lab_service = ServiceCatalog.objects.create(
            service_code='LAB_TEST_001',
            name='Complete Blood Count',
            department='LAB',
            category='LAB',
            workflow_type='LAB_ORDER',
            amount=Decimal('5000.00'),
            is_active=True,
            auto_bill=True,
            bill_timing='BEFORE',
            requires_visit=True,
            requires_consultation=True,
            allowed_roles=['DOCTOR']
        )
        
        self.radiology_service = ServiceCatalog.objects.create(
            service_code='RAD_STUDY_001',
            name='Chest X-Ray',
            department='RADIOLOGY',
            category='RADIOLOGY',
            workflow_type='RADIOLOGY_STUDY',
            amount=Decimal('10000.00'),
            is_active=True,
            auto_bill=True,
            bill_timing='BEFORE',
            requires_visit=True,
            requires_consultation=True,
            allowed_roles=['DOCTOR']
        )
        
        self.pharmacy_service = ServiceCatalog.objects.create(
            service_code='PHARM_DRUG_001',
            name='Paracetamol 500mg',
            department='PHARMACY',
            category='DRUG',
            workflow_type='DRUG_DISPENSE',
            amount=Decimal('3000.00'),
            is_active=True,
            auto_bill=True,
            bill_timing='BEFORE',
            requires_visit=True,
            requires_consultation=True,
            allowed_roles=['DOCTOR']
        )
        
        self.procedure_service = ServiceCatalog.objects.create(
            service_code='PROC_001',
            name='Wound Dressing',
            department='PROCEDURE',
            category='PROCEDURE',
            workflow_type='PROCEDURE',
            amount=Decimal('5000.00'),
            is_active=True,
            auto_bill=True,
            bill_timing='BEFORE',
            requires_visit=True,
            requires_consultation=True,
            allowed_roles=['DOCTOR']
        )


class LabResultLeakDetectionTest(LeakDetectionTestCase):
    """Test LabResult leak detection."""
    
    def test_lab_result_without_paid_bill_detects_leak(self):
        """Test that LabResult without PAID bill detects leak."""
        # Create LabOrder
        lab_order = LabOrder.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            tests_requested=['CBC', 'Blood Sugar'],
            status=LabOrder.Status.ORDERED
        )
        
        # Create LabResult (without paid bill)
        # Note: LabResult uses result_data field (TextField), not results or test_results
        lab_result = LabResult.objects.create(
            lab_order=lab_order,
            recorded_by=self.lab_tech,
            result_data='CBC: Normal, Blood Sugar: 90 mg/dL'
        )
        
        # Detect leak
        leak = LeakDetectionService.detect_lab_result_leak(lab_result.id)
        
        # Assert leak detected
        self.assertIsNotNone(leak)
        self.assertEqual(leak.entity_type, 'LAB_RESULT')
        self.assertEqual(leak.entity_id, lab_result.id)
        self.assertEqual(leak.visit, self.visit)
        self.assertIsNone(leak.resolved_at)
    
    def test_lab_result_with_paid_bill_no_leak(self):
        """Test that LabResult with PAID bill does not detect leak."""
        # Create BillingLineItem and mark as PAID
        # Note: consultation can only be linked to GOPD_CONSULT services
        # So we don't link consultation for LAB_ORDER services
        billing_item = BillingLineItem.objects.create(
            service_catalog=self.lab_service,
            visit=self.visit,
            consultation=None,  # LAB_ORDER services don't link to consultation
            source_service_code=self.lab_service.service_code,
            source_service_name=self.lab_service.name,
            amount=self.lab_service.amount,
            bill_status='PAID',
            amount_paid=self.lab_service.amount,
            outstanding_amount=Decimal('0.00'),
            payment_method='CASH',
            created_by=self.doctor
        )
        
        # Create LabOrder
        lab_order = LabOrder.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            tests_requested=['CBC'],
            status=LabOrder.Status.ORDERED
        )
        
        # Create LabResult
        lab_result = LabResult.objects.create(
            lab_order=lab_order,
            recorded_by=self.lab_tech,
            result_data='CBC: Normal',
            recorded_at=timezone.now()
        )
        
        # Detect leak
        leak = LeakDetectionService.detect_lab_result_leak(lab_result.id)
        
        # Assert no leak detected
        self.assertIsNone(leak)
    
    def test_lab_result_leak_detection_idempotent(self):
        """Test that leak detection is idempotent."""
        # Create LabOrder and LabResult
        lab_order = LabOrder.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            tests_requested=['CBC'],
            status=LabOrder.Status.ORDERED
        )
        
        lab_result = LabResult.objects.create(
            lab_order=lab_order,
            recorded_by=self.lab_tech,
            result_data='CBC: Normal',
            recorded_at=timezone.now()
        )
        
        # Detect leak twice
        leak1 = LeakDetectionService.detect_lab_result_leak(lab_result.id)
        leak2 = LeakDetectionService.detect_lab_result_leak(lab_result.id)
        
        # Assert same leak record returned
        self.assertIsNotNone(leak1)
        self.assertEqual(leak1.id, leak2.id)


class RadiologyReportLeakDetectionTest(LeakDetectionTestCase):
    """Test RadiologyReport leak detection."""
    
    def test_radiology_report_without_paid_bill_detects_leak(self):
        """Test that RadiologyRequest with report but no PAID bill detects leak."""
        # Create RadiologyRequest
        radiology_request = RadiologyRequest.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            study_type='Chest X-Ray',
            status='COMPLETED',
            report='Normal chest X-ray findings',
            report_date=timezone.now()
        )
        
        # Detect leak
        leak = LeakDetectionService.detect_radiology_report_leak(radiology_request.id)
        
        # Assert leak detected
        self.assertIsNotNone(leak)
        self.assertEqual(leak.entity_type, 'RADIOLOGY_REPORT')
        self.assertEqual(leak.entity_id, radiology_request.id)
        self.assertEqual(leak.visit, self.visit)
    
    def test_radiology_request_without_report_no_leak(self):
        """Test that RadiologyRequest without report does not detect leak."""
        # Create RadiologyRequest without report
        radiology_request = RadiologyRequest.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            study_type='Chest X-Ray',
            status='PENDING'
        )
        
        # Detect leak
        leak = LeakDetectionService.detect_radiology_report_leak(radiology_request.id)
        
        # Assert no leak detected
        self.assertIsNone(leak)


class DrugDispenseLeakDetectionTest(LeakDetectionTestCase):
    """Test DrugDispense leak detection."""
    
    def test_drug_dispense_without_paid_bill_detects_leak(self):
        """Test that dispensed Prescription without PAID bill detects leak."""
        # Create Prescription
        prescription = Prescription.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            prescribed_by=self.doctor,
            drug='Paracetamol 500mg',
            dosage='500mg',
            quantity='30 tablets',
            status='DISPENSED',
            dispensed=True,
            dispensed_date=datetime.now(),
            dispensed_by=self.pharmacist
        )
        
        # Detect leak
        leak = LeakDetectionService.detect_drug_dispense_leak(prescription.id)
        
        # Assert leak detected
        self.assertIsNotNone(leak)
        self.assertEqual(leak.entity_type, 'DRUG_DISPENSE')
        self.assertEqual(leak.entity_id, prescription.id)
        self.assertEqual(leak.visit, self.visit)
    
    def test_emergency_prescription_excluded_from_leak_detection(self):
        """Test that emergency prescriptions are excluded from leak detection."""
        # Create emergency Prescription
        prescription = Prescription.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            prescribed_by=self.doctor,
            drug='Emergency Drug',
            dosage='500mg',
            quantity='10 tablets',
            status='DISPENSED',
            dispensed=True,
            is_emergency=True,
            dispensed_date=datetime.now(),
            dispensed_by=self.pharmacist
        )
        
        # Detect leak
        leak = LeakDetectionService.detect_drug_dispense_leak(prescription.id)
        
        # Assert no leak detected (emergency excluded)
        self.assertIsNone(leak)


class ProcedureLeakDetectionTest(LeakDetectionTestCase):
    """Test Procedure leak detection."""
    
    def test_procedure_completed_without_paid_bill_detects_leak(self):
        """Test that completed ProcedureTask without PAID bill detects leak."""
        # Create ProcedureTask
        procedure_task = ProcedureTask.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            service_catalog=self.procedure_service,
            ordered_by=self.doctor,
            procedure_name='Wound Dressing',
            status='COMPLETED',
            executed_by=self.nurse,
            execution_date=timezone.now()
        )
        
        # Detect leak
        leak = LeakDetectionService.detect_procedure_leak(procedure_task.id)
        
        # Assert leak detected
        self.assertIsNotNone(leak)
        self.assertEqual(leak.entity_type, 'PROCEDURE')
        self.assertEqual(leak.entity_id, procedure_task.id)
        self.assertEqual(leak.visit, self.visit)
    
    def test_procedure_not_completed_no_leak(self):
        """Test that non-completed ProcedureTask does not detect leak."""
        # Create ProcedureTask (not completed)
        procedure_task = ProcedureTask.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            service_catalog=self.procedure_service,
            ordered_by=self.doctor,
            procedure_name='Wound Dressing',
            status='ORDERED'
        )
        
        # Detect leak
        leak = LeakDetectionService.detect_procedure_leak(procedure_task.id)
        
        # Assert no leak detected
        self.assertIsNone(leak)


class LeakResolutionTest(LeakDetectionTestCase):
    """Test leak resolution."""
    
    def test_leak_resolution(self):
        """Test that leaks can be manually resolved."""
        # Create leak
        lab_order = LabOrder.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            tests_requested=['CBC'],
            status=LabOrder.Status.ORDERED
        )
        
        lab_result = LabResult.objects.create(
            lab_order=lab_order,
            recorded_by=self.lab_tech,
            result_data='CBC: Normal',
            recorded_at=timezone.now()
        )
        
        leak = LeakDetectionService.detect_lab_result_leak(lab_result.id)
        
        # Resolve leak
        leak.resolve(
            user=self.doctor,
            notes='Bill was created and paid'
        )
        
        # Assert leak resolved
        self.assertTrue(leak.is_resolved())
        self.assertIsNotNone(leak.resolved_at)
        self.assertEqual(leak.resolved_by, self.doctor)


class DailyAggregationTest(LeakDetectionTestCase):
    """Test daily aggregation."""
    
    def test_daily_aggregation(self):
        """Test daily aggregation function."""
        # Create leaks
        lab_order = LabOrder.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            tests_requested=['CBC'],
            status=LabOrder.Status.ORDERED
        )
        
        lab_result = LabResult.objects.create(
            lab_order=lab_order,
            recorded_by=self.lab_tech,
            result_data='CBC: Normal',
            recorded_at=timezone.now()
        )
        
        LeakDetectionService.detect_lab_result_leak(lab_result.id)
        
        # Get daily aggregation
        aggregation = LeakDetectionService.get_daily_aggregation()
        
        # Assert aggregation data
        self.assertIsNotNone(aggregation)
        self.assertIn('total_leaks', aggregation)
        self.assertIn('total_estimated_loss', aggregation)
        self.assertIn('unresolved', aggregation)
        self.assertIn('resolved', aggregation)

