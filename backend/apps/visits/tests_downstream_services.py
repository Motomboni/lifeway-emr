"""
Unit tests for downstream service workflows (LAB, PHARMACY, PROCEDURES).

Tests ensure:
- LAB services auto-create LabOrder and billing
- PHARMACY services auto-create Prescription and billing
- PROCEDURES services auto-create ProcedureTask and billing
- Role-based access is enforced
- Visit-scoped and consultation-dependent rules are respected
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from apps.visits.downstream_service_workflow import (
    order_downstream_service,
    can_dispense_prescription,
)
from apps.billing.service_catalog_models import ServiceCatalog
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from apps.laboratory.models import LabOrder
from apps.pharmacy.models import Prescription
from apps.clinical.procedure_models import ProcedureTask
from apps.billing.billing_line_item_models import BillingLineItem
from apps.patients.models import Patient
from apps.users.models import User


class DownstreamServiceWorkflowTests(TestCase):
    """Test downstream service workflows."""
    
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
        
        self.nurse = User.objects.create_user(
            username='nurse1',
            email='nurse@test.com',
            password='testpass123',
            role='NURSE',
            first_name='Test',
            last_name='Nurse',
        )
        
        # Create visit (with payment cleared for downstream services)
        self.visit = Visit.objects.create(
            patient=self.patient,
            visit_type='CONSULTATION',
            status='OPEN',
            payment_type='CASH',
            payment_status='PAID',  # Payment cleared for downstream services
        )
        
        # Create consultation
        self.consultation = Consultation.objects.create(
            visit=self.visit,
            created_by=self.doctor,
            status='ACTIVE',
        )
        
        # Create LAB service
        self.lab_service = ServiceCatalog.objects.create(
            department='LAB',
            service_code='LAB-001',
            name='Complete Blood Count',
            amount=Decimal('5000.00'),
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
        
        # Create PHARMACY service
        self.pharmacy_service = ServiceCatalog.objects.create(
            department='PHARMACY',
            service_code='PHARM-001',
            name='Medication Dispensing',
            amount=Decimal('3000.00'),
            description='Medication dispensing service',
            category='DRUG',  # PHARMACY department uses DRUG category
            workflow_type='DRUG_DISPENSE',
            requires_visit=True,
            requires_consultation=True,
            auto_bill=True,
            bill_timing='AFTER',
            allowed_roles=['DOCTOR'],
            is_active=True,
        )
        
        # Create PROCEDURE service
        self.procedure_service = ServiceCatalog.objects.create(
            department='PROCEDURE',
            service_code='PROC-001',
            name='Wound Dressing',
            amount=Decimal('2000.00'),
            description='Wound dressing procedure',
            category='PROCEDURE',
            workflow_type='PROCEDURE',
            requires_visit=True,
            requires_consultation=True,
            auto_bill=True,
            bill_timing='AFTER',
            allowed_roles=['DOCTOR', 'NURSE'],
            is_active=True,
        )
    
    def test_order_lab_service_creates_lab_order_and_billing(self):
        """Test that ordering LAB service creates LabOrder and BillingLineItem."""
        additional_data = {
            'tests_requested': ['CBC', 'Hemoglobin', 'Platelet Count'],
            'clinical_indication': 'Routine checkup',
        }
        
        lab_order, billing_line_item = order_downstream_service(
            service=self.lab_service,
            visit=self.visit,
            consultation=self.consultation,
            user=self.doctor,
            additional_data=additional_data,
        )
        
        # Verify LabOrder was created
        self.assertIsInstance(lab_order, LabOrder)
        self.assertEqual(lab_order.visit, self.visit)
        self.assertEqual(lab_order.consultation, self.consultation)
        self.assertEqual(lab_order.ordered_by, self.doctor)
        self.assertEqual(lab_order.tests_requested, additional_data['tests_requested'])
        self.assertEqual(lab_order.clinical_indication, additional_data['clinical_indication'])
        self.assertEqual(lab_order.status, LabOrder.Status.ORDERED)
        
        # Verify BillingLineItem was created
        self.assertIsInstance(billing_line_item, BillingLineItem)
        self.assertEqual(billing_line_item.service_catalog, self.lab_service)
        self.assertEqual(billing_line_item.visit, self.visit)
        self.assertEqual(billing_line_item.consultation, self.consultation)
        self.assertEqual(billing_line_item.amount, self.lab_service.amount)
    
    def test_order_lab_service_doctor_only(self):
        """Test that only doctors can order LAB services."""
        additional_data = {
            'tests_requested': ['CBC'],
        }
        
        # Nurse should not be able to order
        with self.assertRaises(ValidationError) as cm:
            order_downstream_service(
                service=self.lab_service,
                visit=self.visit,
                consultation=self.consultation,
                user=self.nurse,
                additional_data=additional_data,
            )
        
        self.assertIn('doctor', str(cm.exception).lower())
    
    def test_order_lab_service_requires_consultation(self):
        """Test that LAB service requires consultation."""
        additional_data = {
            'tests_requested': ['CBC'],
        }
        
        # Should fail without consultation
        with self.assertRaises(ValidationError) as cm:
            order_downstream_service(
                service=self.lab_service,
                visit=self.visit,
                consultation=None,
                user=self.doctor,
                additional_data=additional_data,
            )
        
        self.assertIn('consultation', str(cm.exception).lower())
    
    def test_order_pharmacy_service_creates_prescription_and_billing(self):
        """Test that ordering PHARMACY service creates Prescription and BillingLineItem."""
        additional_data = {
            'drug': 'Paracetamol',
            'drug_code': 'PARA-001',
            'dosage': '500mg',
            'frequency': 'BID',
            'duration': '7 days',
            'instructions': 'Take with food',
            'quantity': '14 tablets',
        }
        
        prescription, billing_line_item = order_downstream_service(
            service=self.pharmacy_service,
            visit=self.visit,
            consultation=self.consultation,
            user=self.doctor,
            additional_data=additional_data,
        )
        
        # Verify Prescription was created
        self.assertIsInstance(prescription, Prescription)
        self.assertEqual(prescription.visit, self.visit)
        self.assertEqual(prescription.consultation, self.consultation)
        self.assertEqual(prescription.prescribed_by, self.doctor)
        self.assertEqual(prescription.drug, additional_data['drug'])
        self.assertEqual(prescription.dosage, additional_data['dosage'])
        self.assertEqual(prescription.status, 'PENDING')
        
        # Verify BillingLineItem was created
        self.assertIsInstance(billing_line_item, BillingLineItem)
        self.assertEqual(billing_line_item.service_catalog, self.pharmacy_service)
        self.assertEqual(billing_line_item.visit, self.visit)
        self.assertEqual(billing_line_item.consultation, self.consultation)
    
    def test_order_procedure_service_creates_procedure_task_and_billing(self):
        """Test that ordering PROCEDURE service creates ProcedureTask and BillingLineItem."""
        additional_data = {
            'clinical_indication': 'Wound care',
        }
        
        procedure_task, billing_line_item = order_downstream_service(
            service=self.procedure_service,
            visit=self.visit,
            consultation=self.consultation,
            user=self.doctor,
            additional_data=additional_data,
        )
        
        # Verify ProcedureTask was created
        self.assertIsInstance(procedure_task, ProcedureTask)
        self.assertEqual(procedure_task.visit, self.visit)
        self.assertEqual(procedure_task.consultation, self.consultation)
        self.assertEqual(procedure_task.service_catalog, self.procedure_service)
        self.assertEqual(procedure_task.ordered_by, self.doctor)
        self.assertEqual(procedure_task.procedure_name, self.procedure_service.name)
        self.assertEqual(procedure_task.status, ProcedureTask.Status.ORDERED)
        
        # Verify BillingLineItem was created
        self.assertIsInstance(billing_line_item, BillingLineItem)
        self.assertEqual(billing_line_item.service_catalog, self.procedure_service)
        self.assertEqual(billing_line_item.visit, self.visit)
        self.assertEqual(billing_line_item.consultation, self.consultation)
    
    def test_order_service_pending_consultation_fails(self):
        """Test that ordering service with PENDING consultation fails."""
        # Delete existing consultation and create PENDING one
        self.consultation.delete()
        pending_consultation = Consultation.objects.create(
            visit=self.visit,
            created_by=self.doctor,
            status='PENDING',
        )
        
        additional_data = {
            'tests_requested': ['CBC'],
        }
        
        with self.assertRaises(ValidationError) as cm:
            order_downstream_service(
                service=self.lab_service,
                visit=self.visit,
                consultation=pending_consultation,
                user=self.doctor,
                additional_data=additional_data,
            )
        
        self.assertIn('PENDING', str(cm.exception))
    
    def test_order_service_closed_visit_fails(self):
        """Test that ordering service on closed visit fails."""
        self.visit.status = 'CLOSED'
        self.visit.save()
        
        additional_data = {
            'tests_requested': ['CBC'],
        }
        
        with self.assertRaises(ValidationError) as cm:
            order_downstream_service(
                service=self.lab_service,
                visit=self.visit,
                consultation=self.consultation,
                user=self.doctor,
                additional_data=additional_data,
            )
        
        self.assertIn('closed', str(cm.exception).lower())
    
    def test_can_dispense_prescription_requires_paid_billing(self):
        """Test that prescription can only be dispensed after billing is paid."""
        # Create prescription
        prescription = Prescription.objects.create(
            visit=self.visit,
            consultation=self.consultation,
            drug='Paracetamol',
            prescribed_by=self.doctor,
            dosage='500mg',
            status='PENDING',
        )
        
        # Create billing line item (unpaid)
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
        
        # Should not be able to dispense (billing not paid)
        self.assertFalse(can_dispense_prescription(prescription))
        
        # Pay billing
        billing_line_item.apply_payment(
            payment_amount=self.pharmacy_service.amount,
            payment_method='CASH'
        )
        
        # Refresh prescription
        prescription.refresh_from_db()
        
        # Should be able to dispense now
        self.assertTrue(can_dispense_prescription(prescription))
    
    def test_order_service_role_validation(self):
        """Test that role-based access is enforced."""
        # Create service that only allows DOCTOR
        restricted_service = ServiceCatalog.objects.create(
            department='LAB',
            service_code='LAB-002',
            name='Restricted Lab Test',
            amount=Decimal('5000.00'),
            description='Restricted test',
            category='LAB',
            workflow_type='LAB_ORDER',
            requires_visit=True,
            requires_consultation=True,
            auto_bill=True,
            bill_timing='AFTER',
            allowed_roles=['DOCTOR'],  # Only DOCTOR
            is_active=True,
        )
        
        additional_data = {
            'tests_requested': ['CBC'],
        }
        
        # Nurse should not be able to order
        with self.assertRaises(ValidationError) as cm:
            order_downstream_service(
                service=restricted_service,
                visit=self.visit,
                consultation=self.consultation,
                user=self.nurse,
                additional_data=additional_data,
            )
        
        self.assertIn('role', str(cm.exception).lower())
        
        # Doctor should be able to order
        lab_order, billing_line_item = order_downstream_service(
            service=restricted_service,
            visit=self.visit,
            consultation=self.consultation,
            user=self.doctor,
            additional_data=additional_data,
        )
        
        self.assertIsNotNone(lab_order)
        self.assertIsNotNone(billing_line_item)

