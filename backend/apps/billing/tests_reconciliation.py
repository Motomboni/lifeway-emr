"""
Tests for End-of-Day Reconciliation.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.billing.billing_line_item_models import BillingLineItem
from apps.billing.models import Payment
from apps.billing.reconciliation_service import ReconciliationService
from apps.billing.service_catalog_models import ServiceCatalog
from apps.patients.models import Patient
from apps.users.models import User
from apps.visits.models import Visit
from tests.test_utils import get_or_create_test_org


class ReconciliationTestCase(TestCase):
    """Test cases for End-of-Day Reconciliation."""

    def setUp(self):
        """Set up test data."""
        self.org = get_or_create_test_org()
        # Create users
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="testpass", role="ADMIN"
        )

        self.receptionist = User.objects.create_user(
            username="receptionist",
            email="receptionist@test.com",
            password="testpass",
            role="RECEPTIONIST",
        )

        # Create patient
        self.patient = Patient.objects.create(
            first_name="Test",
            last_name="Patient",
            patient_id="TEST001",
            date_of_birth="1990-01-01",
            gender="MALE",
            phone="1234567890",
            organization=self.org,
        )

        # Create service catalog
        self.service = ServiceCatalog.objects.create(
            organization=self.org,
            service_code="CONSULT",
            name="Consultation",
            department="CONSULTATION",
            category="CONSULTATION",
            workflow_type="GOPD_CONSULT",
            amount=Decimal("5000.00"),
            is_active=True,
            auto_bill=True,
            bill_timing="BEFORE",
            requires_visit=True,
            requires_consultation=False,
            allowed_roles=["DOCTOR"],
        )

    def test_create_reconciliation(self):
        """Test creating a reconciliation."""
        today = timezone.now().date()

        reconciliation = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            close_active_visits=False,
            organization_id=self.org.id,
        )

        self.assertIsNotNone(reconciliation)
        self.assertEqual(reconciliation.reconciliation_date, today)
        self.assertEqual(reconciliation.status, "DRAFT")
        self.assertEqual(reconciliation.prepared_by, self.admin)
        self.assertEqual(reconciliation.total_revenue, Decimal("0.00"))

    def test_one_reconciliation_per_day(self):
        """Test that only one reconciliation can exist per day."""
        today = timezone.now().date()

        # Create first reconciliation
        reconciliation1 = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            organization_id=self.org.id,
        )

        # Try to create another for the same day
        reconciliation2 = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            organization_id=self.org.id,
        )

        # Should return the same reconciliation
        self.assertEqual(reconciliation1.id, reconciliation2.id)

    def test_reconciliation_with_visits(self):
        """Test reconciliation with visits and payments."""
        today = timezone.now().date()
        now = timezone.now()

        # Create visit (timestamp must match reconciliation date filter)
        visit = Visit.objects.create(
            patient=self.patient,
            organization=self.org,
            visit_type="CONSULTATION",
            status="OPEN",
            payment_status="PAID",
        )
        Visit.objects.filter(pk=visit.pk).update(created_at=now)

        # Create billing line item
        billing_item = BillingLineItem.objects.create(
            service_catalog=self.service,
            visit=visit,
            amount=Decimal("5000.00"),
            bill_status="PAID",
            payment_method="CASH",
            amount_paid=Decimal("5000.00"),
            outstanding_amount=Decimal("0.00"),
            created_by=self.admin,
        )
        payment = Payment.objects.create(
            visit=visit,
            amount=Decimal("5000.00"),
            payment_method="CASH",
            status="CLEARED",
            processed_by=self.admin,
        )
        Payment.objects.filter(pk=payment.pk).update(created_at=now)

        # Create reconciliation
        reconciliation = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            close_active_visits=True,
            organization_id=self.org.id,
        )

        # Check totals
        self.assertEqual(reconciliation.total_revenue, Decimal("5000.00"))
        self.assertEqual(reconciliation.total_cash, Decimal("5000.00"))
        self.assertEqual(reconciliation.total_visits, 1)
        self.assertEqual(reconciliation.active_visits_closed, 1)

    def test_reconciliation_finalize(self):
        """Test finalizing a reconciliation."""
        today = timezone.now().date()

        reconciliation = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            organization_id=self.org.id,
        )

        # Finalize
        reconciliation.finalize(self.admin)

        self.assertEqual(reconciliation.status, "FINALIZED")
        self.assertEqual(reconciliation.finalized_by, self.admin)
        self.assertIsNotNone(reconciliation.finalized_at)

    def test_cannot_edit_finalized_reconciliation(self):
        """Test that finalized reconciliations cannot be edited."""
        today = timezone.now().date()

        reconciliation = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            organization_id=self.org.id,
        )

        reconciliation.finalize(self.admin)

        # Try to modify
        reconciliation.total_revenue = Decimal("10000.00")

        with self.assertRaises(Exception):
            reconciliation.save()

    def test_reconciliation_idempotent(self):
        """Test that reconciliation is idempotent."""
        today = timezone.now().date()

        # Create reconciliation multiple times
        reconciliation1 = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            organization_id=self.org.id,
        )

        reconciliation2 = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            organization_id=self.org.id,
        )

        # Should be the same
        self.assertEqual(reconciliation1.id, reconciliation2.id)

    def test_refresh_reconciliation(self):
        """Test refreshing reconciliation calculations."""
        today = timezone.now().date()
        now = timezone.now()

        reconciliation = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            organization_id=self.org.id,
        )

        initial_revenue = reconciliation.total_revenue

        # Add more billing items
        visit = Visit.objects.create(
            patient=self.patient,
            organization=self.org,
            visit_type="CONSULTATION",
            status="OPEN",
            payment_status="PAID",
        )
        Visit.objects.filter(pk=visit.pk).update(created_at=now)

        BillingLineItem.objects.create(
            service_catalog=self.service,
            visit=visit,
            amount=Decimal("3000.00"),
            bill_status="PAID",
            payment_method="WALLET",
            amount_paid=Decimal("3000.00"),
            outstanding_amount=Decimal("0.00"),
            created_by=self.admin,
        )
        wallet_payment = Payment.objects.create(
            visit=visit,
            amount=Decimal("3000.00"),
            payment_method="WALLET",
            status="CLEARED",
            processed_by=self.admin,
        )
        Payment.objects.filter(pk=wallet_payment.pk).update(created_at=now)

        # Refresh
        updated = ReconciliationService.refresh_reconciliation(reconciliation.id)

        # Revenue should be updated
        self.assertGreater(updated.total_revenue, initial_revenue)
        self.assertEqual(updated.total_wallet, Decimal("3000.00"))

    def test_cannot_refresh_finalized(self):
        """Test that finalized reconciliations cannot be refreshed."""
        today = timezone.now().date()

        reconciliation = ReconciliationService.create_reconciliation(
            reconciliation_date=today,
            prepared_by_id=self.admin.id,
            organization_id=self.org.id,
        )

        reconciliation.finalize(self.admin)

        # Try to refresh
        with self.assertRaises(Exception):
            ReconciliationService.refresh_reconciliation(reconciliation.id)
