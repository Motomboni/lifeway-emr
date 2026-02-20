"""
Empty the Service Catalog by deactivating all services.

Deactivating (rather than deleting) preserves billing history - BillingLineItems
and ProcedureTasks reference ServiceCatalog. After running this command:
- No services will appear in the catalog (API returns active_only by default)
- Newly added drugs will auto-create ServiceCatalog entries via pharmacy signals
- New services can be added manually via admin or import

Usage:
    python manage.py empty_service_catalog
    python manage.py empty_service_catalog --dry-run
"""
from django.core.management.base import BaseCommand

from apps.billing.service_catalog_models import ServiceCatalog


class Command(BaseCommand):
    help = (
        "Deactivate all ServiceCatalog entries. The catalog will appear empty; "
        "only newly added drugs (via Drug Catalog) or manually added services will be available."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what would be deactivated, do not update.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        active_count = ServiceCatalog.objects.filter(is_active=True).count()
        total_count = ServiceCatalog.objects.count()

        if active_count == 0:
            self.stdout.write(
                self.style.SUCCESS("Service catalog is already empty (no active services).")
            )
            return

        if dry_run:
            self.stdout.write(
                f"DRY RUN: Would deactivate {active_count} of {total_count} services."
            )
            return

        updated = ServiceCatalog.objects.filter(is_active=True).update(is_active=False)
        self.stdout.write(
            self.style.SUCCESS(f"Deactivated {updated} service(s). Catalog is now empty.")
        )
        self.stdout.write(
            "New drugs added via Drug Catalog & Inventory will automatically appear. "
            "New services can be added via admin or import_service_catalog."
        )
