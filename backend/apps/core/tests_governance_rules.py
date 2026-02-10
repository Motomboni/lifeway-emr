"""
Unit tests for EMR Governance Rules.

Tests ensure:
- No LabOrder without Consultation
- No Consultation without Visit
- No Result posting without active order
- No drug dispensing without paid bill (unless emergency)
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from apps.laboratory.models import LabOrder, LabResult
from apps.consultations.models import Consultation
from apps.pharmacy.models import Prescription
from apps.pharmacy.prescription_service import dispense_prescription
from apps.radiology.models import RadiologyRequest
from apps.radiology.radiology_service import post_radiology_report
from apps.visits.models import Visit
from apps.patients.models import Patient
from apps.users.models import User
from apps.billing.service_catalog_models import ServiceCatalog
from apps.billing.billing_line_item_models import BillingLineItem


class GovernanceRulesTests(TestCase):
    """Test EMR governance rules."""
    
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
        
        # Create test users
        self.doctor = User.objects.create_user(
            username='doctor1',
            email='doctor@test.com',
            password='testpass123',
            role='DOCTOR',
            first_name='Test',
            last_name='Doctor',
        )
        
        self.lab_tech = User.objects.create_user(
            username='labtech1',
            email='labtech@test.com',
            password='testpass123',
            role='LAB_TECH',
            first_name='Test',
            last_name='LabTech',
        )
        
        self.pharmacist = User.objects.create_user(
            username='pharmacist1',
            email='pharmacist@test.com',
            password='testpass123',
            role='PHARMACIST',
            first_name='Test',
            last_name='Pharmacist',
        )
        
        self.radiology_tech = User.objects.create_user(
            username='radtech1',
            email='radtech@test.com',
            password='testpass123',
            role='RADIOLOGY_TECH',
            first_name='Test',
            last_name='RadiologyTech',
        )
        
        # Create visit
        self.visit = Visit.objects.create(
            patient=self.patient,
            visit_type='CONSULTATION',
            status='OPEN',
            payment_type='CASH',
            payment_status='PAID',  # Payment cleared
        )
        
        # Create consultation
        self.consultation = Consultation.objects.create(
            visit=self.visit,
            created_by=self.doctor,
            status='ACTIVE',
        )
        
        # Create pharmacy service for billing
        self.pharmacy_service = ServiceCatalog.objects.create(
            department='PHARMACY',
            service_code='PHARM-001',
            name='Medication Dispensing',
            amount=Decimal('3000.00'),
            description='Medication dispensing service',
            category='DRUG',
            workflow_type='DRUG_DISPENSE',
            requires_visit=True,
            requires_consultation=True,
            auto_bill=True,
            bill_timing='AFTER',
            allowed_roles=['DOCTOR'],
            is_active=True,
        )
    
    def test_lab_order_requires_consultation(self):
        """Test that LabOrder cannot be created without consultation."""
        # ❌ Should fail: No consultation
        with self.assertRaises(ValidationError) as cm:
            lab_order = LabOrder(
                visit=self.visit,
                consultation=None,  # Missing consultation
                ordered_by=self.doctor,
                tests_requested=['CBC'],
            )
            lab_order.full_clean()
        
        self.assertIn('consultation', str(cm.exception).lower())
        self.assertIn('required', str(cm.exception).lower())
    
    def test_consultation_requires_visit(self):
        """Test that Consultation cannot be created without visit."""
        # ❌ Should fail: No visit (OneToOneField prevents this at database level)
        # This is enforced by OneToOneField, but we test model validation
        with self.assertRaises(ValidationError):
            consultation = Consultation(
                visit=None,  # Missing visit
                created_by=self.doctor,
                status='ACTIVE',
            )
            consultation.full_clean()
    
    def test_lab_result_requires_active_order(self):
        """Test that LabResult cannot be posted for inactive order."""
        # Create lab order
        lab_order = LabOrder.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            tests_requested=['CBC'],
            status=LabOrder.Status.ORDERED,
        )
        
        # ✅ Valid: Active order
        lab_result = LabResult.objects.create(
            lab_order=lab_order,
            result_data='Normal values',
            recorded_by=self.lab_tech,
        )
        self.assertIsNotNone(lab_result)
        
        # ❌ Invalid: Inactive order
        lab_order.status = LabOrder.Status.RESULT_READY
        lab_order.save()
        
        # Try to create another result (should fail due to OneToOneField)
        # But test validation
        lab_order2 = LabOrder.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            tests_requested=['Hemoglobin'],
            status=LabOrder.Status.RESULT_READY,  # Already has result
        )
        
        with self.assertRaises(ValidationError) as cm:
            lab_result2 = LabResult(
                lab_order=lab_order2,
                result_data='Normal values',
                recorded_by=self.lab_tech,
            )
            lab_result2.full_clean()
        
        self.assertIn('active', str(cm.exception).lower())
    
    def test_prescription_dispensing_requires_payment(self):
        """Test that prescription cannot be dispensed without payment."""
        # Create prescription
        prescription = Prescription.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            drug='Paracetamol',
            prescribed_by=self.doctor,
            dosage='500mg',
            status='PENDING',
        )
        
        # Create unpaid billing
        billing_line_item = BillingLineItem.objects.create(
            service_catalog=self.pharmacy_service,
            visit=self.visit,
            consultation=self.consultation,
            source_service_code=self.pharmacy_service.service_code,
            source_service_name=self.pharmacy_service.name,
            amount=self.pharmacy_service.amount,
            bill_status='PENDING',  # Not paid
            amount_paid=Decimal('0.00'),
            outstanding_amount=self.pharmacy_service.amount,
        )
        
        # ❌ Should fail: Billing not paid
        with self.assertRaises(ValidationError) as cm:
            dispense_prescription(
                prescription=prescription,
                pharmacist=self.pharmacist,
                emergency_override=False,
            )
        
        self.assertIn('payment', str(cm.exception).lower())
    
    def test_prescription_dispensing_with_payment(self):
        """Test that prescription can be dispensed when billing is paid."""
        # Create prescription
        prescription = Prescription.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            drug='Paracetamol',
            prescribed_by=self.doctor,
            dosage='500mg',
            status='PENDING',
        )
        
        # Create paid billing
        billing_line_item = BillingLineItem.objects.create(
            service_catalog=self.pharmacy_service,
            visit=self.visit,
            consultation=self.consultation,
            source_service_code=self.pharmacy_service.service_code,
            source_service_name=self.pharmacy_service.name,
            amount=self.pharmacy_service.amount,
            bill_status='PENDING',
            amount_paid=Decimal('0.00'),
            outstanding_amount=self.pharmacy_service.amount,
        )
        
        # Pay billing
        billing_line_item.apply_payment(
            payment_amount=self.pharmacy_service.amount,
            payment_method='CASH'
        )
        
        # ✅ Should succeed: Billing is paid
        dispensed_prescription = dispense_prescription(
            prescription=prescription,
            pharmacist=self.pharmacist,
            emergency_override=False,
        )
        
        self.assertEqual(dispensed_prescription.status, 'DISPENSED')
        self.assertTrue(dispensed_prescription.dispensed)
    
    def test_prescription_emergency_dispensing(self):
        """Test that prescription can be dispensed with emergency override."""
        # Create prescription
        prescription = Prescription.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            drug='Paracetamol',
            prescribed_by=self.doctor,
            dosage='500mg',
            status='PENDING',
            is_emergency=True,  # Emergency flag
        )
        
        # Create unpaid billing
        billing_line_item = BillingLineItem.objects.create(
            service_catalog=self.pharmacy_service,
            visit=self.visit,
            consultation=self.consultation,
            source_service_code=self.pharmacy_service.service_code,
            source_service_name=self.pharmacy_service.name,
            amount=self.pharmacy_service.amount,
            bill_status='PENDING',  # Not paid
            amount_paid=Decimal('0.00'),
            outstanding_amount=self.pharmacy_service.amount,
        )
        
        # ✅ Should succeed: Emergency override
        dispensed_prescription = dispense_prescription(
            prescription=prescription,
            pharmacist=self.pharmacist,
            emergency_override=True,  # Emergency override
        )
        
        self.assertEqual(dispensed_prescription.status, 'DISPENSED')
        self.assertTrue(dispensed_prescription.dispensed)
        self.assertTrue(dispensed_prescription.is_emergency)
    
    def test_radiology_request_requires_consultation(self):
        """Test that RadiologyRequest cannot be created without consultation."""
        # ❌ Should fail: No consultation
        with self.assertRaises(ValidationError) as cm:
            radiology_request = RadiologyRequest(
                visit=self.visit,
                consultation=None,  # Missing consultation
                ordered_by=self.doctor,
                study_type='Chest X-Ray',
            )
            radiology_request.full_clean()
        
        self.assertIn('consultation', str(cm.exception).lower())
        self.assertIn('required', str(cm.exception).lower())
    
    def test_radiology_report_requires_active_request(self):
        """Test that radiology report cannot be posted for inactive request."""
        # Create radiology request
        radiology_request = RadiologyRequest.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            study_type='Chest X-Ray',
            status='PENDING',
        )
        
        # ✅ Valid: Active request
        updated_request = post_radiology_report(
            radiology_request=radiology_request,
            radiology_tech=self.radiology_tech,
            report_text='Normal chest X-ray',
        )
        self.assertEqual(updated_request.status, 'COMPLETED')
        
        # ❌ Invalid: Already completed request
        radiology_request2 = RadiologyRequest.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            ordered_by=self.doctor,
            study_type='CT Scan',
            status='COMPLETED',  # Already completed
        )
        
        with self.assertRaises(ValidationError) as cm:
            post_radiology_report(
                radiology_request=radiology_request2,
                radiology_tech=self.radiology_tech,
                report_text='Normal CT scan',
            )
        
        self.assertIn('completed', str(cm.exception).lower())

