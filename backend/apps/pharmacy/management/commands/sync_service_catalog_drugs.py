"""
Copy PHARMACY/DRUG ServiceCatalog rows into Drug Catalog and Inventory.

This command is intentionally non-destructive: it does not remove service
catalog rows, because those rows still drive billing and downstream workflows.
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.billing.service_catalog_models import ServiceCatalog
from apps.pharmacy.models import Drug, DrugInventory


User = get_user_model()


class Command(BaseCommand):
    help = "Copy pharmacy ServiceCatalog drugs into Drug Catalog and create inventory records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            default=None,
            help="Username to use for Drug.created_by. Defaults to migration_pharmacist, first pharmacist, then first superuser.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving.",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing Drug price/description/is_active from matching ServiceCatalog rows.",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Also copy inactive ServiceCatalog drug rows.",
        )
        parser.add_argument(
            "--skip-inventory",
            action="store_true",
            help="Do not create missing zero-stock DrugInventory records.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        update_existing = options["update_existing"]
        include_inactive = options["include_inactive"]
        create_inventory = not options["skip_inventory"]
        user = self._get_user(options["user"])

        if not user and not dry_run:
            raise CommandError(
                "No user found for created_by. Create/use a PHARMACIST or pass --user <username>."
            )

        queryset = ServiceCatalog.objects.filter(department="PHARMACY", category="DRUG")
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        queryset = queryset.order_by("name", "service_code")

        stats = {
            "source": queryset.count(),
            "created": 0,
            "updated": 0,
            "matched": 0,
            "inventory_created": 0,
            "skipped": 0,
            "errors": [],
        }

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no database changes will be saved"))

        with transaction.atomic():
            for service in queryset.iterator(chunk_size=500):
                try:
                    drug, created = self._sync_service(
                        service,
                        user=user,
                        update_existing=update_existing,
                        dry_run=dry_run,
                    )
                    if created:
                        stats["created"] += 1
                        self.stdout.write(f"  Create Drug: {service.name} ({self._drug_code_for_service(service)})")
                    elif drug:
                        stats["matched"] += 1
                        if update_existing:
                            stats["updated"] += 1
                            self.stdout.write(f"  Update Drug: {drug.name} ({drug.drug_code or 'no code'})")
                    else:
                        stats["skipped"] += 1
                        continue

                    if create_inventory and drug:
                        inventory_created = self._ensure_inventory(drug, dry_run=dry_run)
                        if inventory_created:
                            stats["inventory_created"] += 1
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    stats["skipped"] += 1
                    stats["errors"].append(f"{service.service_code}: {exc}")

            if dry_run:
                transaction.set_rollback(True)

        self._print_summary(stats, dry_run)

    def _get_user(self, username):
        if username:
            return User.objects.filter(username=username).first()
        return (
            User.objects.filter(username="migration_pharmacist").first()
            or User.objects.filter(role="PHARMACIST").order_by("id").first()
            or User.objects.filter(is_superuser=True).order_by("id").first()
        )

    def _drug_code_candidates(self, service):
        codes = []
        raw = (service.service_code or "").strip()
        if raw:
            codes.append(raw)
        if raw.startswith("DRUG-"):
            codes.append(raw[5:])
        if raw.startswith("DRUG-LIFEWAY-"):
            codes.append(raw.replace("DRUG-LIFEWAY-", "LIFEWAY-", 1))
        return list(dict.fromkeys(c for c in codes if c))

    def _drug_code_for_service(self, service):
        for code in self._drug_code_candidates(service):
            if not Drug.objects.filter(drug_code=code).exists():
                return code
        return None

    def _find_existing_drug(self, service):
        for code in self._drug_code_candidates(service):
            drug = Drug.objects.filter(drug_code=code).first()
            if drug:
                return drug
        return Drug.objects.filter(name__iexact=service.name.strip()).first()

    def _description_for_service(self, service):
        service_note = f"Synced from ServiceCatalog {service.service_code}."
        description = (service.description or "").strip()
        if service_note in description:
            return description
        return f"{description}\n{service_note}".strip()

    def _sync_service(self, service, *, user, update_existing, dry_run):
        name = (service.name or "").strip()
        if not name:
            return None, False

        existing = self._find_existing_drug(service)
        if existing:
            if update_existing and not dry_run:
                existing.sales_price = service.amount
                existing.description = self._description_for_service(service)
                existing.is_active = service.is_active
                if not existing.drug_code:
                    existing.drug_code = self._drug_code_for_service(service)
                existing.save()
            return existing, False

        drug_code = self._drug_code_for_service(service)
        if dry_run:
            return Drug(
                name=name[:255],
                drug_code=drug_code,
                sales_price=service.amount,
                description=self._description_for_service(service),
                is_active=service.is_active,
                created_by=user,
            ), True

        drug = Drug.objects.create(
            name=name[:255],
            drug_code=drug_code,
            cost_price=None,
            sales_price=service.amount if service.amount is not None else Decimal("0.00"),
            description=self._description_for_service(service),
            is_active=service.is_active,
            created_by=user,
        )
        return drug, True

    def _ensure_inventory(self, drug, *, dry_run):
        if getattr(drug, "pk", None) is None:
            return True
        if DrugInventory.objects.filter(drug=drug).exists():
            return False
        if not dry_run:
            DrugInventory.objects.create(
                drug=drug,
                current_stock=Decimal("0.00"),
                reorder_level=Decimal("0.00"),
                unit="units",
            )
        return True

    def _print_summary(self, stats, dry_run):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Service Catalog drug sync summary"))
        self.stdout.write(f"Source pharmacy services: {stats['source']}")
        self.stdout.write(self.style.SUCCESS(f"Drugs created: {stats['created']}"))
        self.stdout.write(f"Existing drugs matched: {stats['matched']}")
        self.stdout.write(self.style.SUCCESS(f"Inventory records created: {stats['inventory_created']}"))
        if stats["updated"]:
            self.stdout.write(self.style.SUCCESS(f"Drugs updated: {stats['updated']}"))
        if stats["skipped"]:
            self.stdout.write(self.style.WARNING(f"Skipped/errors: {stats['skipped']}"))
        for error in stats["errors"][:20]:
            self.stdout.write(self.style.ERROR(f"  - {error}"))
        if len(stats["errors"]) > 20:
            self.stdout.write(self.style.ERROR(f"  ... +{len(stats['errors']) - 20} more"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run only. Re-run without --dry-run to apply."))
