"""Tests for registration/consultation payment gate accuracy."""
from decimal import Decimal

from django.test import TestCase

from apps.billing.billing_line_item_models import BillingLineItem
from apps.billing.billing_service import BillingService
from apps.billing.payment_gates_service import get_payment_gates_status
from apps.billing.service_catalog_models import ServiceCatalog
from apps.patients.models import Patient
from apps.visits.models import Visit
from tests.test_utils import get_or_create_test_org


class PaymentGatesServiceTests(TestCase):
    def setUp(self):
        self.org = get_or_create_test_org()
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            patient_id="GATE001",
            date_of_birth="1990-01-01",
            gender="MALE",
            phone="08012345678",
            organization=self.org,
        )
        self.visit = Visit.objects.create(
            patient=self.patient,
            organization=self.org,
            visit_type="CONSULTATION",
            status="OPEN",
            payment_type="CASH",
            payment_status="UNPAID",
        )
        self.reg_service = ServiceCatalog.objects.create(
            organization=self.org,
            service_code="REG-001",
            name="REGISTRATION",
            department="PROCEDURE",
            workflow_type="OTHER",
            category="PROCEDURE",
            amount=Decimal("5000.00"),
            is_active=True,
            allowed_roles=["RECEPTIONIST", "DOCTOR"],
        )
        self.cons_service = ServiceCatalog.objects.create(
            organization=self.org,
            service_code="CONS-001",
            name="GOPD CONSULTATION",
            department="CONSULTATION",
            workflow_type="GOPD_CONSULT",
            category="CONSULTATION",
            amount=Decimal("15000.00"),
            is_active=True,
            allowed_roles=["RECEPTIONIST", "DOCTOR"],
        )

    def _add_line_item(self, service, amount=None):
        return BillingLineItem.objects.create(
            service_catalog=service,
            visit=self.visit,
            source_service_code=service.service_code,
            source_service_name=service.name,
            amount=amount if amount is not None else service.amount,
        )

    def test_unpaid_registration_and_consultation_show_unpaid(self):
        self._add_line_item(self.reg_service)
        self._add_line_item(self.cons_service)

        gates = get_payment_gates_status(self.visit)
        self.assertFalse(gates["registration_paid"])
        self.assertFalse(gates["consultation_paid"])

    def test_partial_visit_payment_does_not_clear_gates(self):
        self._add_line_item(self.reg_service)
        self._add_line_item(self.cons_service)
        self.visit.payment_status = "PARTIALLY_PAID"
        self.visit.save(update_fields=["payment_status"])

        gates = get_payment_gates_status(self.visit)
        self.assertFalse(gates["registration_paid"])
        self.assertFalse(gates["consultation_paid"])

    def test_paid_registration_line_item_clears_registration_gate_only(self):
        reg = self._add_line_item(self.reg_service)
        self._add_line_item(self.cons_service)
        reg.amount_paid = reg.amount
        reg.save()

        gates = get_payment_gates_status(self.visit)
        self.assertTrue(gates["registration_paid"])
        self.assertFalse(gates["consultation_paid"])

    def test_zero_charges_billing_summary_is_unpaid(self):
        summary = BillingService.compute_billing_summary(self.visit)
        self.assertEqual(summary.payment_status, "UNPAID")
        self.assertFalse(summary.payment_gates["registration_paid"])
        self.assertFalse(summary.payment_gates["consultation_paid"])

    def test_unpaid_charges_billing_summary_gates_stay_unpaid(self):
        self._add_line_item(self.reg_service)
        self._add_line_item(self.cons_service)

        summary = BillingService.compute_billing_summary(self.visit)
        self.assertEqual(summary.payment_status, "UNPAID")
        self.assertFalse(summary.payment_gates["registration_paid"])
        self.assertFalse(summary.payment_gates["consultation_paid"])

    def test_legacy_visit_charge_registration_paid_via_payment(self):
        """MISC VisitCharge + Payment (no BillingLineItem) should clear registration gate."""
        from apps.billing.models import Payment, VisitCharge
        from apps.users.models import User

        VisitCharge.objects.create(
            visit=self.visit,
            category="MISC",
            description="Registration",
            amount=Decimal("5000.00"),
        )
        user = User.objects.filter(is_superuser=True).first() or User.objects.create_user(
            username="gate-admin",
            password="Admin123!",
            role="ADMIN",
        )
        Payment.objects.create(
            visit=self.visit,
            amount=Decimal("5000.00"),
            payment_method="CASH",
            status="CLEARED",
            processed_by=user,
        )

        gates = get_payment_gates_status(self.visit)
        self.assertTrue(gates["registration_paid"])
        self.assertFalse(gates["consultation_paid"])
