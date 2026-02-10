"""
One-time fix: update payment_status to SETTLED for visits that have approved insurance
but are still marked INSURANCE_PENDING.
"""
from django.core.management.base import BaseCommand
from apps.visits.models import Visit
from apps.billing.insurance_models import VisitInsurance


class Command(BaseCommand):
    help = 'Fix visits with approved insurance that are still INSURANCE_PENDING'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
        parser.add_argument(
            '--visit-id',
            type=int,
            help='Fix a specific visit by ID',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        visit_id = options.get('visit_id')

        # Find visits that are INSURANCE_PENDING but have approved insurance
        visits_qs = Visit.objects.filter(payment_status='INSURANCE_PENDING')
        if visit_id:
            visits_qs = visits_qs.filter(pk=visit_id)

        updated = 0
        for visit in visits_qs:
            has_approved = VisitInsurance.objects.filter(
                visit_id=visit.pk,
                approval_status='APPROVED'
            ).exists()

            if has_approved:
                self.stdout.write(
                    f"Visit {visit.pk}: INSURANCE_PENDING with approved insurance"
                )
                if not dry_run:
                    Visit.objects.filter(pk=visit.pk).update(payment_status='SETTLED')
                    self.stdout.write(self.style.SUCCESS(f"  -> Updated to SETTLED"))
                    updated += 1
                else:
                    self.stdout.write("  -> Would update to SETTLED (dry-run)")

        if updated:
            self.stdout.write(self.style.SUCCESS(f"\nUpdated {updated} visit(s)."))
        elif dry_run:
            self.stdout.write("\nDry-run complete. No changes made.")
        else:
            self.stdout.write("\nNo visits needed updating.")
