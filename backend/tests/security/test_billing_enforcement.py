"""
Billing Enforcement Tests - Rule-Locked EMR

Tests ensure billing rules are strictly enforced:
- Non-receptionist cannot create charges
- Insurance does not bypass visit scope
- Wallet cannot overdraft
- Paystack payment must be verified
- Visit cannot close with balance
- Insurance + wallet + payment compute correctly
"""
import pytest
import json
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APIClient
from django.core.exceptions import ValidationError

from apps.visits.models import Visit
from apps.billing.models import Payment, VisitCharge, PaymentIntent
from apps.billing.insurance_models import VisitInsurance, HMOProvider
from apps.billing.billing_service import BillingService
from apps.wallet.models import Wallet, WalletTransaction
from apps.consultations.models import Consultation


def get_response_data(response):
    """Helper to get response data from both DRF Response and JsonResponse."""
    if hasattr(response, 'data'):
        return response.data
    else:
        return json.loads(response.content.decode())


@pytest.fixture
def patient(db):
    """Create a test patient."""
    from apps.patients.models import Patient
    return Patient.objects.create(
        first_name="Test",
        last_name="Patient",
        patient_id="TEST001",
        is_active=True
    )


@pytest.fixture
def doctor_user(db):
    """Create a doctor user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='doctor',
        email='doctor@test.com',
        password='testpass123',
        role='DOCTOR'
    )


@pytest.fixture
def receptionist_user(db):
    """Create a receptionist user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='receptionist',
        email='receptionist@test.com',
        password='testpass123',
        role='RECEPTIONIST'
    )


@pytest.fixture
def nurse_user(db):
    """Create a nurse user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='nurse',
        email='nurse@test.com',
        password='testpass123',
        role='NURSE'
    )


@pytest.fixture
def open_visit(db, patient, receptionist_user):
    """Create an open visit."""
    return Visit.objects.create(
        patient=patient,
        status='OPEN',
        payment_status='PENDING'
    )


@pytest.fixture
def hmo_provider(db, receptionist_user):
    """Create an HMO provider."""
    return HMOProvider.objects.create(
        name='Test HMO',
        code='THMO001',
        contact_person='Test Contact',
        contact_phone='1234567890',
        contact_email='hmo@test.com',
        is_active=True,
        created_by=receptionist_user
    )


@pytest.fixture
def wallet(db, patient):
    """Create or get wallet for patient."""
    wallet, created = Wallet.objects.get_or_create(
        patient=patient,
        defaults={
            'balance': Decimal('10000.00'),
            'currency': 'NGN',
            'is_active': True
        }
    )
    # If wallet already exists, update balance for testing
    if not created:
        wallet.balance = Decimal('10000.00')
        wallet.save()
    return wallet


class TestChargeCreationEnforcement:
    """Test that only Receptionist can create charges."""
    
    def test_receptionist_can_create_misc_charge(self, receptionist_user, open_visit):
        """Receptionist should be able to create MISC charges."""
        charge = VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('5000.00'),
            description='Test MISC charge'
        )
        
        assert charge is not None
        assert charge.category == 'MISC'
        assert charge.amount == Decimal('5000.00')
        assert charge.visit == open_visit
    
    def test_doctor_cannot_create_charge_via_api(self, doctor_user, open_visit):
        """Doctor should be denied from creating charges via API."""
        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        url = f'/api/v1/visits/{open_visit.id}/billing/charges/'
        response = client.post(url, {
            'amount': '5000.00',
            'description': 'Test charge'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Receptionist' in str(response.data) or 'permission' in str(response.data).lower()
    
    def test_nurse_cannot_create_charge_via_api(self, nurse_user, open_visit):
        """Nurse should be denied from creating charges via API."""
        client = APIClient()
        client.force_authenticate(user=nurse_user)
        
        url = f'/api/v1/visits/{open_visit.id}/billing/charges/'
        response = client.post(url, {
            'amount': '5000.00',
            'description': 'Test charge'
        })
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_charge_creation_requires_visit_open(self, receptionist_user, doctor_user, patient):
        """Charges cannot be created for CLOSED visits."""
        # Create and close a visit
        visit = Visit.objects.create(
            patient=patient,
            status='OPEN',
            payment_status='CLEARED'
        )
        
        # Create consultation to allow closure (must be created by doctor)
        Consultation.objects.create(
            visit=visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        visit.status = 'CLOSED'
        visit.save()
        
        # Try to create charge
        with pytest.raises(ValidationError) as exc_info:
            VisitCharge.create_misc_charge(
                visit=visit,
                amount=Decimal('5000.00'),
                description='Test charge'
            )
        
        assert 'CLOSED' in str(exc_info.value) or 'closed' in str(exc_info.value).lower()


class TestInsuranceVisitScopeEnforcement:
    """Test that insurance does not bypass visit scope."""
    
    def test_insurance_is_visit_scoped(self, receptionist_user, open_visit, hmo_provider):
        """Insurance must be associated with a visit."""
        insurance = VisitInsurance.objects.create(
            visit=open_visit,
            provider=hmo_provider,
            policy_number='POL123',
            coverage_type='FULL',
            coverage_percentage=100,
            approval_status='APPROVED',
            approved_amount=Decimal('10000.00'),
            created_by=receptionist_user
        )
        
        assert insurance.visit == open_visit
        assert insurance.visit_id == open_visit.id
    
    def test_insurance_cannot_bypass_payment_enforcement(self, receptionist_user, open_visit, hmo_provider, doctor_user):
        """Insurance does not bypass payment enforcement - clinical actions still require payment_status == CLEARED."""
        # Ensure visit payment_status is PENDING
        open_visit.payment_status = 'PENDING'
        open_visit.save()
        
        # Create insurance with full coverage
        VisitInsurance.objects.create(
            visit=open_visit,
            provider=hmo_provider,
            policy_number='POL123',
            coverage_type='FULL',
            coverage_percentage=100,
            approval_status='APPROVED',
            approved_amount=Decimal('10000.00'),
            created_by=receptionist_user
        )
        
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('5000.00'),
            description='Test charge'
        )
        
        # Verify visit payment_status is still PENDING (insurance doesn't auto-clear)
        open_visit.refresh_from_db()
        assert open_visit.payment_status == 'PENDING', "Insurance should not automatically clear payment_status"
        
        # Verify is_payment_cleared() returns False when payment_status is PENDING
        # (This was fixed to check payment_status field first)
        assert not open_visit.is_payment_cleared(), \
            "is_payment_cleared() should return False when payment_status is PENDING"
        
        # Compute billing summary for verification
        summary = BillingService.compute_billing_summary(open_visit)
        # BillingService may compute payment_status='CLEARED' due to insurance,
        # but visit.payment_status field is still PENDING and is authoritative
        
        # Try to create consultation (should fail - payment_status field is PENDING)
        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        url = f'/api/v1/visits/{open_visit.id}/consultation/'
        response = client.post(url, {
            'history': 'Test',
            'examination': 'Test',
            'diagnosis': 'Test',
            'clinical_notes': 'Test'
        })
        
        # Should fail because visit.payment_status is PENDING
        # Even if BillingService computes payment_status='CLEARED' due to insurance,
        # the visit's payment_status field must be explicitly set to 'CLEARED'
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST], \
            f"Expected 403 or 400, got {response.status_code}. " \
            f"Consultation was created despite visit.payment_status='PENDING'. " \
            f"This indicates payment enforcement is not working correctly. " \
            f"Response: {get_response_data(response)}"
        
        response_data = get_response_data(response)
        assert 'payment' in str(response_data).lower() or 'cleared' in str(response_data).lower()
    
    def test_insurance_computation_is_visit_scoped(self, receptionist_user, open_visit, hmo_provider):
        """Insurance coverage computation uses visit-scoped charges only."""
        # Create charges for this visit
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Visit charge'
        )
        
        # Create insurance
        insurance = VisitInsurance.objects.create(
            visit=open_visit,
            provider=hmo_provider,
            policy_number='POL123',
            coverage_type='FULL',
            coverage_percentage=100,
            approval_status='APPROVED',
            approved_amount=Decimal('10000.00'),
            created_by=receptionist_user
        )
        
        # Compute billing summary
        summary = BillingService.compute_billing_summary(open_visit)
        
        # Insurance should cover visit charges
        assert summary.total_charges == Decimal('10000.00')
        assert summary.insurance_amount == Decimal('10000.00')
        assert summary.patient_payable == Decimal('0.00')
        assert summary.is_fully_covered_by_insurance is True


class TestWalletOverdraftPrevention:
    """Test that wallet cannot overdraft."""
    
    def test_wallet_cannot_debit_more_than_balance(self, receptionist_user, open_visit, wallet):
        """Wallet debit should fail if amount exceeds balance."""
        # Wallet balance is 10000.00
        # Try to debit 15000.00
        
        with pytest.raises(ValidationError) as exc_info:
            wallet.debit(
                amount=Decimal('15000.00'),
                visit=open_visit,
                description='Test debit',
                created_by=receptionist_user
            )
        
        assert 'balance' in str(exc_info.value).lower() or 'insufficient' in str(exc_info.value).lower()
    
    def test_wallet_debit_via_api_prevents_overdraft(self, receptionist_user, open_visit, wallet):
        """Wallet debit via API should prevent overdraft."""
        client = APIClient()
        client.force_authenticate(user=receptionist_user)
        
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('5000.00'),
            description='Test charge'
        )
        
        url = f'/api/v1/visits/{open_visit.id}/billing/wallet-debit/'
        response = client.post(url, {
            'wallet_id': wallet.id,
            'amount': '15000.00',  # More than wallet balance
            'description': 'Test payment'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'balance' in str(response.data).lower() or 'insufficient' in str(response.data).lower()
    
    def test_wallet_can_debit_exact_balance(self, receptionist_user, open_visit, wallet):
        """Wallet should allow debit of exact balance."""
        # Wallet balance is 10000.00
        # Debit exactly 10000.00
        
        transaction = wallet.debit(
            amount=Decimal('10000.00'),
            visit=open_visit,
            description='Test debit',
            created_by=receptionist_user
        )
        
        assert transaction is not None
        assert transaction.amount == Decimal('10000.00')
        assert transaction.balance_after == Decimal('0.00')
        
        # Refresh wallet
        wallet.refresh_from_db()
        assert wallet.balance == Decimal('0.00')
    
    def test_wallet_cannot_go_negative(self, receptionist_user, open_visit, wallet):
        """Wallet balance should never go negative."""
        # Try multiple debits that would exceed balance
        wallet.debit(
            amount=Decimal('5000.00'),
            visit=open_visit,
            description='First debit',
            created_by=receptionist_user
        )
        
        # Try another debit that would make total > balance
        with pytest.raises(ValidationError):
            wallet.debit(
                amount=Decimal('6000.00'),  # Would make total 11000 > 10000
                visit=open_visit,
                description='Second debit',
                created_by=receptionist_user
            )


class TestPaystackVerificationEnforcement:
    """Test that Paystack payments must be verified."""
    
    def test_payment_intent_requires_verification(self, receptionist_user, open_visit):
        """PaymentIntent cannot create Payment without verification."""
        # Create payment intent
        payment_intent = PaymentIntent.objects.create(
            visit=open_visit,
            paystack_reference='TEST-REF-123',
            amount=Decimal('5000.00'),
            status='INITIALIZED',
            created_by=receptionist_user
        )
        
        # Payment should not exist yet
        assert payment_intent.payment is None
        
        # Try to use unverified payment intent (should fail)
        # PaymentIntent must be verified before Payment is created
        assert payment_intent.status == 'INITIALIZED'
        assert not payment_intent.is_verified()
    
    def test_payment_intent_verification_creates_payment(self, receptionist_user, open_visit):
        """Verified PaymentIntent creates Payment record."""
        # Create payment intent
        payment_intent = PaymentIntent.objects.create(
            visit=open_visit,
            paystack_reference='TEST-REF-123',
            amount=Decimal('5000.00'),
            status='INITIALIZED',
            created_by=receptionist_user
        )
        
        # Mock Paystack verification response
        paystack_response = {
            'status': True,
            'data': {
                'id': '12345',
                'status': 'success',
                'gateway_response': 'Successful',
                'reference': 'TEST-REF-123',
                'amount': 500000,  # In kobo
                'customer': {
                    'email': 'test@example.com'
                },
                'metadata': {
                    'visit_id': open_visit.id
                }
            }
        }
        
        # Verify payment intent
        payment = payment_intent.mark_as_verified(paystack_response)
        
        assert payment is not None
        assert payment.visit == open_visit
        assert payment.amount == Decimal('5000.00')
        assert payment.status == 'CLEARED'
        assert payment.payment_method == 'PAYSTACK'
        
        # PaymentIntent should be linked
        payment_intent.refresh_from_db()
        assert payment_intent.payment == payment
        assert payment_intent.status == 'VERIFIED'
    
    def test_unverified_payment_intent_cannot_be_used(self, receptionist_user, open_visit):
        """Unverified PaymentIntent cannot be used for payment."""
        # Create payment intent
        payment_intent = PaymentIntent.objects.create(
            visit=open_visit,
            paystack_reference='TEST-REF-123',
            amount=Decimal('5000.00'),
            status='INITIALIZED',
            created_by=receptionist_user
        )
        
        # Payment should not exist
        assert payment_intent.payment is None
        
        # Try to access payment (should fail)
        with pytest.raises(AttributeError):
            _ = payment_intent.payment.id
    
    def test_payment_intent_verification_is_idempotent(self, receptionist_user, open_visit):
        """PaymentIntent verification can be called multiple times safely."""
        # Create payment intent
        payment_intent = PaymentIntent.objects.create(
            visit=open_visit,
            paystack_reference='TEST-REF-123',
            amount=Decimal('5000.00'),
            status='INITIALIZED',
            created_by=receptionist_user
        )
        
        # Mock Paystack response
        paystack_response = {
            'status': True,
            'data': {
                'id': '12345',
                'status': 'success',
                'gateway_response': 'Successful',
                'reference': 'TEST-REF-123',
                'amount': 500000,
                'customer': {'email': 'test@example.com'},
                'metadata': {'visit_id': open_visit.id}
            }
        }
        
        # Verify first time
        payment1 = payment_intent.mark_as_verified(paystack_response)
        
        # Verify second time (should return same payment)
        payment2 = payment_intent.mark_as_verified(paystack_response)
        
        assert payment1.id == payment2.id
        assert payment_intent.payment == payment1


class TestVisitClosureBalanceEnforcement:
    """Test that visit cannot close with outstanding balance."""
    
    def test_visit_cannot_close_with_outstanding_balance(self, doctor_user, open_visit, receptionist_user):
        """Visit should be denied closure if outstanding balance > 0."""
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Test charge'
        )
        
        # Create consultation (required for closure)
        Consultation.objects.create(
            visit=open_visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        # Try to close visit
        can_close, reason = BillingService.can_close_visit(open_visit)
        
        assert can_close is False
        assert 'balance' in reason.lower() or 'outstanding' in reason.lower()
        
        # Try via API
        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        url = f'/api/v1/visits/{open_visit.id}/close/'
        response = client.post(url)
        
        # Should be denied (403 Forbidden or 400 Bad Request are both acceptable)
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN], \
            f"Expected 400 or 403, got {response.status_code}. Response: {get_response_data(response)}"
        
        response_data = get_response_data(response)
        assert 'balance' in str(response_data).lower() or 'outstanding' in str(response_data).lower() or 'cleared' in str(response_data).lower()
    
    def test_visit_can_close_when_balance_cleared(self, doctor_user, open_visit, receptionist_user):
        """Visit should be allowed to close when balance is cleared."""
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Test charge'
        )
        
        # Create payment to clear balance
        Payment.objects.create(
            visit=open_visit,
            amount=Decimal('10000.00'),
            payment_method='CASH',
            status='CLEARED',
            processed_by=receptionist_user
        )
        
        # Update visit payment status
        open_visit.payment_status = 'CLEARED'
        open_visit.save()
        
        # Create consultation
        Consultation.objects.create(
            visit=open_visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        # Check if can close
        can_close, reason = BillingService.can_close_visit(open_visit)
        
        assert can_close is True
        
        # Close via API
        client = APIClient()
        client.force_authenticate(user=doctor_user)
        
        url = f'/api/v1/visits/{open_visit.id}/close/'
        response = client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify visit is closed
        open_visit.refresh_from_db()
        assert open_visit.status == 'CLOSED'
    
    def test_visit_can_close_with_insurance_full_coverage(self, doctor_user, open_visit, receptionist_user, hmo_provider):
        """Visit can close when insurance fully covers charges."""
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Test charge'
        )
        
        # Create insurance with full coverage
        VisitInsurance.objects.create(
            visit=open_visit,
            provider=hmo_provider,
            policy_number='POL123',
            coverage_type='FULL',
            coverage_percentage=100,
            approval_status='APPROVED',
            approved_amount=Decimal('10000.00'),
            created_by=receptionist_user
        )
        
        # Compute billing summary
        summary = BillingService.compute_billing_summary(open_visit)
        
        # Patient payable should be 0
        assert summary.patient_payable == Decimal('0.00')
        assert summary.is_fully_covered_by_insurance is True
        
        # Clear payment status (insurance covers all)
        open_visit.payment_status = 'CLEARED'
        open_visit.save()
        
        # Create consultation
        Consultation.objects.create(
            visit=open_visit,
            created_by=doctor_user,
            history='Test',
            examination='Test',
            diagnosis='Test',
            clinical_notes='Test'
        )
        
        # Should be able to close
        can_close, reason = BillingService.can_close_visit(open_visit)
        assert can_close is True


class TestBillingComputationAccuracy:
    """Test that insurance + wallet + payment compute correctly."""
    
    def test_billing_computation_with_insurance_only(self, open_visit, receptionist_user, hmo_provider):
        """Test billing computation with insurance only."""
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Test charge'
        )
        
        # Create insurance (80% coverage)
        VisitInsurance.objects.create(
            visit=open_visit,
            provider=hmo_provider,
            policy_number='POL123',
            coverage_type='PARTIAL',
            coverage_percentage=80,
            approval_status='APPROVED',
            approved_amount=Decimal('8000.00'),
            created_by=receptionist_user
        )
        
        # Compute billing summary
        summary = BillingService.compute_billing_summary(open_visit)
        
        assert summary.total_charges == Decimal('10000.00')
        assert summary.insurance_amount == Decimal('8000.00')
        assert summary.patient_payable == Decimal('2000.00')
        assert summary.outstanding_balance == Decimal('2000.00')
        assert summary.payment_status == 'PENDING'
    
    def test_billing_computation_with_payment_only(self, open_visit, receptionist_user):
        """Test billing computation with payment only."""
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Test charge'
        )
        
        # Create payment
        Payment.objects.create(
            visit=open_visit,
            amount=Decimal('5000.00'),
            payment_method='CASH',
            status='CLEARED',
            processed_by=receptionist_user
        )
        
        # Compute billing summary
        summary = BillingService.compute_billing_summary(open_visit)
        
        assert summary.total_charges == Decimal('10000.00')
        assert summary.total_payments == Decimal('5000.00')
        assert summary.patient_payable == Decimal('10000.00')
        assert summary.outstanding_balance == Decimal('5000.00')
        assert summary.payment_status == 'PARTIAL'
    
    def test_billing_computation_with_wallet_only(self, open_visit, receptionist_user, wallet):
        """Test billing computation with wallet debit only."""
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Test charge'
        )
        
        # Create wallet debit
        wallet.debit(
            amount=Decimal('5000.00'),
            visit=open_visit,
            description='Wallet payment',
            created_by=receptionist_user
        )
        
        # Compute billing summary
        summary = BillingService.compute_billing_summary(open_visit)
        
        assert summary.total_charges == Decimal('10000.00')
        assert summary.total_wallet_debits == Decimal('5000.00')
        assert summary.patient_payable == Decimal('10000.00')
        assert summary.outstanding_balance == Decimal('5000.00')
        assert summary.payment_status == 'PARTIAL'
    
    def test_billing_computation_with_insurance_and_payment(self, open_visit, receptionist_user, hmo_provider):
        """Test billing computation with insurance and payment."""
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Test charge'
        )
        
        # Create insurance (80% coverage)
        VisitInsurance.objects.create(
            visit=open_visit,
            provider=hmo_provider,
            policy_number='POL123',
            coverage_type='PARTIAL',
            coverage_percentage=80,
            approval_status='APPROVED',
            approved_amount=Decimal('8000.00'),
            created_by=receptionist_user
        )
        
        # Create payment for patient portion
        Payment.objects.create(
            visit=open_visit,
            amount=Decimal('2000.00'),
            payment_method='CASH',
            status='CLEARED',
            processed_by=receptionist_user
        )
        
        # Compute billing summary
        summary = BillingService.compute_billing_summary(open_visit)
        
        assert summary.total_charges == Decimal('10000.00')
        assert summary.insurance_amount == Decimal('8000.00')
        assert summary.total_payments == Decimal('2000.00')
        assert summary.patient_payable == Decimal('2000.00')
        assert summary.outstanding_balance == Decimal('0.00')
        assert summary.payment_status == 'CLEARED'
        assert summary.can_be_cleared is True
    
    def test_billing_computation_with_all_payment_methods(self, open_visit, receptionist_user, hmo_provider, wallet):
        """Test billing computation with insurance, wallet, and payment."""
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Test charge'
        )
        
        # Create insurance (50% coverage)
        VisitInsurance.objects.create(
            visit=open_visit,
            provider=hmo_provider,
            policy_number='POL123',
            coverage_type='PARTIAL',
            coverage_percentage=50,
            approval_status='APPROVED',
            approved_amount=Decimal('5000.00'),
            created_by=receptionist_user
        )
        
        # Create wallet debit
        wallet.debit(
            amount=Decimal('2000.00'),
            visit=open_visit,
            description='Wallet payment',
            created_by=receptionist_user
        )
        
        # Create cash payment
        Payment.objects.create(
            visit=open_visit,
            amount=Decimal('3000.00'),
            payment_method='CASH',
            status='CLEARED',
            processed_by=receptionist_user
        )
        
        # Compute billing summary
        summary = BillingService.compute_billing_summary(open_visit)
        
        # Total charges: 10000
        # Insurance: 5000 (50%)
        # Patient payable: 5000
        # Wallet: 2000
        # Payment: 3000
        # Total paid: 5000
        # Outstanding: 0
        
        assert summary.total_charges == Decimal('10000.00')
        assert summary.insurance_amount == Decimal('5000.00')
        assert summary.total_wallet_debits == Decimal('2000.00')
        assert summary.total_payments == Decimal('3000.00')
        assert summary.patient_payable == Decimal('5000.00')
        assert summary.outstanding_balance == Decimal('0.00')
        assert summary.payment_status == 'CLEARED'
        assert summary.can_be_cleared is True
    
    def test_billing_computation_with_overpayment(self, open_visit, receptionist_user):
        """Test billing computation with overpayment (creates credit)."""
        # Add charges
        VisitCharge.create_misc_charge(
            visit=open_visit,
            amount=Decimal('10000.00'),
            description='Test charge'
        )
        
        # Create overpayment
        Payment.objects.create(
            visit=open_visit,
            amount=Decimal('12000.00'),
            payment_method='CASH',
            status='CLEARED',
            processed_by=receptionist_user
        )
        
        # Compute billing summary
        summary = BillingService.compute_billing_summary(open_visit)
        
        assert summary.total_charges == Decimal('10000.00')
        assert summary.total_payments == Decimal('12000.00')
        assert summary.patient_payable == Decimal('10000.00')
        assert summary.outstanding_balance == Decimal('-2000.00')  # Negative = credit
        assert summary.payment_status == 'CLEARED'
        assert summary.can_be_cleared is True
    
    def test_billing_computation_deterministic(self, open_visit, receptionist_user, hmo_provider, wallet):
        """Test that billing computation is deterministic (same inputs = same outputs)."""
        # Setup: charges, insurance, wallet, payment
        VisitCharge.create_misc_charge(visit=open_visit, amount=Decimal('10000.00'), description='Test')
        VisitInsurance.objects.create(
            visit=open_visit, provider=hmo_provider, policy_number='POL123',
            coverage_type='PARTIAL', coverage_percentage=50, approval_status='APPROVED',
            approved_amount=Decimal('5000.00'), created_by=receptionist_user
        )
        wallet.debit(amount=Decimal('2000.00'), visit=open_visit, description='Test', created_by=receptionist_user)
        Payment.objects.create(
            visit=open_visit, amount=Decimal('3000.00'), payment_method='CASH',
            status='CLEARED', processed_by=receptionist_user
        )
        
        # Compute multiple times
        summary1 = BillingService.compute_billing_summary(open_visit)
        summary2 = BillingService.compute_billing_summary(open_visit)
        summary3 = BillingService.compute_billing_summary(open_visit)
        
        # All should be identical
        assert summary1.total_charges == summary2.total_charges == summary3.total_charges
        assert summary1.insurance_amount == summary2.insurance_amount == summary3.insurance_amount
        assert summary1.total_payments == summary2.total_payments == summary3.total_payments
        assert summary1.total_wallet_debits == summary2.total_wallet_debits == summary3.total_wallet_debits
        assert summary1.patient_payable == summary2.patient_payable == summary3.patient_payable
        assert summary1.outstanding_balance == summary2.outstanding_balance == summary3.outstanding_balance
        assert summary1.payment_status == summary2.payment_status == summary3.payment_status

