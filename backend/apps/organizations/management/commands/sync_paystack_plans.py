"""
Sync local Plan records to Paystack Plans API for recurring billing.

Usage:
    python manage.py sync_paystack_plans
    python manage.py sync_paystack_plans --plan-slug professional
"""

from django.core.management.base import BaseCommand

from apps.organizations.models import Plan
from apps.organizations.paystack_subscription_service import PaystackSaasService


class Command(BaseCommand):
    help = "Create Paystack plan codes for active EMR subscription plans"

    def add_arguments(self, parser):
        parser.add_argument(
            "--plan-slug",
            type=str,
            help="Sync a single plan by slug",
        )

    def handle(self, *args, **options):
        service = PaystackSaasService()
        if not service.is_configured():
            self.stderr.write(
                self.style.ERROR("PAYSTACK_SECRET_KEY is not configured.")
            )
            return

        qs = Plan.objects.filter(is_active=True, price_monthly__gt=0)
        if options.get("plan_slug"):
            qs = qs.filter(slug=options["plan_slug"])

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No matching plans found."))
            return

        synced = 0
        for plan in qs:
            if plan.paystack_plan_code:
                self.stdout.write(
                    f"  {plan.slug}: already synced ({plan.paystack_plan_code})"
                )
                continue
            try:
                code = service.create_paystack_plan(plan)
                synced += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  {plan.slug}: created {code}")
                )
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(f"  {plan.slug}: failed — {e}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\nSynced {synced} plan(s) to Paystack.")
        )
