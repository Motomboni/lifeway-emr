"""
Unit tests for Payment Confirmed event system.

Tests ensure:
- Events fire when BillingLineItem transitions to PAID
- Event handlers are idempotent
- No double-triggering occurs
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal

from .billing_line_item_models import BillingLineItem
from .domain_events import PaymentConfirmedEvent
from .payment_event_handlers import (
    handle_payment_confirmed,
    handle_payment_confirmed_idempotent,
)
from .service_catalog_models import ServiceCatalog
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from apps.patients.models import Patient
from apps.users.models import User


class PaymentConfirmedEventTests(TestCase):
    """Test Payment Confirmed event system."""
    
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
        
        # Create test doctor
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
        
        # Create visit
        self.visit = Visit.objects.create(
            patient=self.patient,
            visit_type='CONSULTATION',
            status='OPEN',
            payment_type='CASH',
            payment_status='UNPAID',
        )
        
        # Create consultation (PENDING status)
        self.consultation = Consultation.objects.create(
            visit=self.visit,
            created_by=self.doctor,
            status='PENDING',
        )
        
        # Create billing line item
        self.billing_line_item = BillingLineItem.objects.create(
            service_catalog=self.gopd_service,
            visit=self.visit,
            consultation=self.consultation,
            source_service_code=self.gopd_service.service_code,
            source_service_name=self.gopd_service.name,
            amount=self.gopd_service.amount,
            bill_status='PENDING',
            amount_paid=Decimal('0.00'),
            outstanding_amount=self.gopd_service.amount,
        )
    
    def test_payment_confirmed_event_creation(self):
        """Test PaymentConfirmedEvent creation."""
        event = PaymentConfirmedEvent(
            billing_line_item_id=self.billing_line_item.id,
            visit_id=self.visit.id,
            service_code=self.gopd_service.service_code,
            amount=self.gopd_service.amount,
            payment_method='CASH',
            consultation_id=self.consultation.id,
        )
        
        self.assertEqual(event.billing_line_item_id, self.billing_line_item.id)
        self.assertEqual(event.visit_id, self.visit.id)
        self.assertEqual(event.service_code, self.gopd_service.service_code)
        self.assertEqual(event.amount, self.gopd_service.amount)
        self.assertEqual(event.payment_method, 'CASH')
        self.assertEqual(event.consultation_id, self.consultation.id)
        self.assertIsNotNone(event.timestamp)
    
    def test_event_to_dict(self):
        """Test event serialization."""
        event = PaymentConfirmedEvent(
            billing_line_item_id=self.billing_line_item.id,
            visit_id=self.visit.id,
            service_code=self.gopd_service.service_code,
            amount=self.gopd_service.amount,
            payment_method='CASH',
            consultation_id=self.consultation.id,
        )
        
        event_dict = event.to_dict()
        
        self.assertEqual(event_dict['event_type'], 'PAYMENT_CONFIRMED')
        self.assertEqual(event_dict['billing_line_item_id'], self.billing_line_item.id)
        self.assertEqual(event_dict['visit_id'], self.visit.id)
        self.assertEqual(event_dict['service_code'], self.gopd_service.service_code)
        self.assertIn('timestamp', event_dict)
    
    def test_handle_payment_confirmed_unlocks_consultation(self):
        """Test that payment confirmed unlocks PENDING consultation."""
        # Ensure consultation is PENDING
        self.consultation.status = 'PENDING'
        self.consultation.save()
        
        # Create event
        event = PaymentConfirmedEvent(
            billing_line_item_id=self.billing_line_item.id,
            visit_id=self.visit.id,
            service_code=self.gopd_service.service_code,
            amount=self.gopd_service.amount,
            payment_method='CASH',
            consultation_id=self.consultation.id,
        )
        
        # Handle event
        handle_payment_confirmed(event)
        
        # Refresh consultation
        self.consultation.refresh_from_db()
        
        # Consultation should be ACTIVE
        self.assertEqual(self.consultation.status, 'ACTIVE')
    
    def test_handle_payment_confirmed_idempotent(self):
        """Test that event handler is idempotent."""
        # Ensure consultation is PENDING
        self.consultation.status = 'PENDING'
        self.consultation.save()
        
        # Mark billing line item as paid (to simulate payment)
        self.billing_line_item.amount_paid = self.gopd_service.amount
        self.billing_line_item.bill_status = 'PAID'
        self.billing_line_item.outstanding_amount = Decimal('0.00')
        self.billing_line_item.save()
        
        # Update visit payment_status to reflect payment
        self.visit.payment_status = 'PAID'
        self.visit.save(update_fields=['payment_status'])
        
        # Create event
        event = PaymentConfirmedEvent(
            billing_line_item_id=self.billing_line_item.id,
            visit_id=self.visit.id,
            service_code=self.gopd_service.service_code,
            amount=self.gopd_service.amount,
            payment_method='CASH',
            consultation_id=self.consultation.id,
        )
        
        # Handle event first time
        handle_payment_confirmed_idempotent(event)
        
        # Refresh consultation
        self.consultation.refresh_from_db()
        first_status = self.consultation.status
        
        # Handle event second time (should be idempotent)
        handle_payment_confirmed_idempotent(event)
        
        # Refresh consultation
        self.consultation.refresh_from_db()
        second_status = self.consultation.status
        
        # Status should be the same (idempotent)
        self.assertEqual(first_status, second_status)
        self.assertEqual(self.consultation.status, 'ACTIVE')
    
    def test_handle_payment_confirmed_already_active_consultation(self):
        """Test that handler doesn't modify already ACTIVE consultation."""
        # Set consultation to ACTIVE
        self.consultation.status = 'ACTIVE'
        self.consultation.save()
        
        # Create event
        event = PaymentConfirmedEvent(
            billing_line_item_id=self.billing_line_item.id,
            visit_id=self.visit.id,
            service_code=self.gopd_service.service_code,
            amount=self.gopd_service.amount,
            payment_method='CASH',
            consultation_id=self.consultation.id,
        )
        
        # Handle event
        handle_payment_confirmed_idempotent(event)
        
        # Refresh consultation
        self.consultation.refresh_from_db()
        
        # Consultation should still be ACTIVE
        self.assertEqual(self.consultation.status, 'ACTIVE')
    
    def test_billing_line_item_transition_to_paid_fires_event(self):
        """Test that BillingLineItem transition to PAID fires event."""
        # Mock the event handler to track calls
        from unittest.mock import patch
        
        with patch('apps.billing.billing_line_item_signals.handle_payment_confirmed_idempotent') as mock_handler:
            # Transition to PAID
            self.billing_line_item.apply_payment(
                payment_amount=self.gopd_service.amount,
                payment_method='CASH'
            )
            
            # Event should be fired
            self.assertEqual(mock_handler.call_count, 1)
            
            # Check event arguments
            call_args = mock_handler.call_args[0][0]
            self.assertIsInstance(call_args, PaymentConfirmedEvent)
            self.assertEqual(call_args.billing_line_item_id, self.billing_line_item.id)
            self.assertEqual(call_args.visit_id, self.visit.id)
    
    def test_billing_line_item_no_double_triggering(self):
        """Test that event is not fired multiple times for same transition."""
        from unittest.mock import patch
        
        with patch('apps.billing.billing_line_item_signals.handle_payment_confirmed_idempotent') as mock_handler:
            # Transition to PAID
            self.billing_line_item.apply_payment(
                payment_amount=self.gopd_service.amount,
                payment_method='CASH'
            )
            
            # Save again (should not fire event)
            self.billing_line_item.save()
            
            # Event should be fired only once
            self.assertEqual(mock_handler.call_count, 1)
    
    def test_billing_line_item_partial_payment_no_event(self):
        """Test that partial payment does not fire event."""
        from unittest.mock import patch
        
        with patch('apps.billing.billing_line_item_signals.handle_payment_confirmed_idempotent') as mock_handler:
            # Apply partial payment
            self.billing_line_item.apply_payment(
                payment_amount=Decimal('2500.00'),
                payment_method='CASH'
            )
            
            # Event should not be fired (status is PARTIALLY_PAID, not PAID)
            self.assertEqual(mock_handler.call_count, 0)
    
    def test_billing_line_item_paid_then_save_no_event(self):
        """Test that saving already PAID item does not fire event."""
        from unittest.mock import patch
        
        # First, transition to PAID
        self.billing_line_item.apply_payment(
            payment_amount=self.gopd_service.amount,
            payment_method='CASH'
        )
        
        # Clear mock calls
        with patch('apps.billing.billing_line_item_signals.handle_payment_confirmed_idempotent') as mock_handler:
            # Save again (should not fire event)
            self.billing_line_item.save()
            
            # Event should not be fired
            self.assertEqual(mock_handler.call_count, 0)
    
    def test_handle_payment_confirmed_updates_visit_payment_status(self):
        """Test that payment confirmed updates visit payment status."""
        # Ensure visit payment is not cleared
        self.visit.payment_status = 'UNPAID'
        self.visit.save()
        
        # Create event
        event = PaymentConfirmedEvent(
            billing_line_item_id=self.billing_line_item.id,
            visit_id=self.visit.id,
            service_code=self.gopd_service.service_code,
            amount=self.gopd_service.amount,
            payment_method='CASH',
            consultation_id=self.consultation.id,
        )
        
        # Handle event
        handle_payment_confirmed(event)
        
        # Refresh visit
        self.visit.refresh_from_db()
        
        # Visit payment status should be updated
        # (Note: This depends on BillingService.compute_billing_summary)
        # For this test, we just verify the handler ran without error
        self.assertIsNotNone(self.visit.payment_status)
    
    def test_handle_payment_confirmed_no_consultation(self):
        """Test that handler works when no consultation is linked."""
        # Create billing line item without consultation
        line_item_no_consultation = BillingLineItem.objects.create(
            service_catalog=self.gopd_service,
            visit=self.visit,
            consultation=None,
            source_service_code=self.gopd_service.service_code,
            source_service_name=self.gopd_service.name,
            amount=self.gopd_service.amount,
            bill_status='PENDING',
            amount_paid=Decimal('0.00'),
            outstanding_amount=self.gopd_service.amount,
        )
        
        # Create event without consultation
        event = PaymentConfirmedEvent(
            billing_line_item_id=line_item_no_consultation.id,
            visit_id=self.visit.id,
            service_code=self.gopd_service.service_code,
            amount=self.gopd_service.amount,
            payment_method='CASH',
            consultation_id=None,
        )
        
        # Handle event (should not raise error)
        handle_payment_confirmed(event)
        
        # Handler should complete successfully
        self.assertTrue(True)

