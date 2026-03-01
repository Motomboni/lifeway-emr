"""
Management command to import drugs into the Drug Catalog from CSV or Excel.

Usage:
    python manage.py import_drug_catalog /path/to/drugs.csv
    python manage.py import_drug_catalog /path/to/drugs.xlsx
    python manage.py import_drug_catalog drugs.csv --dry-run
    python manage.py import_drug_catalog drugs.xlsx --with-inventory --user admin

Supported Formats:
    - CSV: Comma-separated values
    - Excel: .xlsx or .xls files

Required Columns:
    - name: Drug name (required, unique)
    - sales_price or price: Selling price (required for pricing)

Optional Columns:
    - generic_name, drug_code, drug_class
    - dosage_forms, common_dosages
    - cost_price
    - description
    - current_stock, unit, reorder_level (for inventory)
"""
import csv
import os
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.pharmacy.models import Drug, DrugInventory

User = get_user_model()

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class Command(BaseCommand):
    help = 'Import drugs into Drug Catalog from CSV or Excel file'

    FIELD_MAPPINGS = {
        'name': ['name', 'drug name', 'drug_name', 'product'],
        'generic_name': ['generic name', 'generic_name', 'generic', 'active_ingredient'],
        'drug_code': ['drug code', 'drug_code', 'code', 'ndc', 'sku'],
        'drug_class': ['drug class', 'drug_class', 'class', 'category'],
        'dosage_forms': ['dosage forms', 'dosage_forms', 'form', 'forms'],
        'common_dosages': ['common dosages', 'common_dosages', 'dosage', 'strength'],
        'cost_price': ['cost price', 'cost_price', 'cost', 'purchase_price'],
        'sales_price': ['sales price', 'sales_price', 'price', 'selling_price', 'amount'],
        'description': ['description', 'desc', 'notes'],
        'current_stock': ['current stock', 'current_stock', 'stock', 'quantity', 'qty'],
        'unit': ['unit', 'units', 'uom'],
        'reorder_level': ['reorder level', 'reorder_level', 'reorder', 'min_stock'],
        'is_active': ['is active', 'is_active', 'active'],
    }

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to CSV or Excel file containing drugs'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview import without saving to database'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing drugs (by name or drug_code)'
        )
        parser.add_argument(
            '--with-inventory',
            action='store_true',
            help='Create DrugInventory records for drugs that have stock/reorder_level in the file'
        )
        parser.add_argument(
            '--user',
            type=str,
            default=None,
            help='Username for created_by (default: first superuser)'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            default=0,
            help='Sheet name or index for Excel files'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        dry_run = options['dry_run']
        update_existing = options['update']
        with_inventory = options['with_inventory']
        user_ident = options['user']
        sheet = options['sheet']

        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")

        # Resolve user for created_by
        user = self._get_user(user_ident)
        if not user and not dry_run:
            raise CommandError(
                "No user found for created_by. Create a superuser or use --user <username>"
            )

        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext in ['.xlsx', '.xls']:
            if not PANDAS_AVAILABLE:
                raise CommandError(
                    "pandas is required for Excel. Install: pip install pandas openpyxl"
                )
            data = self._read_excel(file_path, sheet)
        elif file_ext == '.csv':
            data = self._read_csv(file_path)
        else:
            raise CommandError(
                f"Unsupported format: {file_ext}. Use .csv or .xlsx"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be saved"))

        stats = self._import_drugs(
            data, dry_run, update_existing, with_inventory, user
        )
        self._print_summary(stats, dry_run)

    def _get_user(self, username):
        if username:
            return User.objects.filter(username=username).first()
        return User.objects.filter(is_superuser=True).order_by('id').first()

    def _read_csv(self, file_path):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(1024)
            f.seek(0)
            try:
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
            except csv.Error:
                delimiter = ','
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = list(reader)
            if not rows:
                raise CommandError("CSV file is empty")
            return rows

    def _read_excel(self, file_path, sheet):
        df = pd.read_excel(file_path, sheet_name=sheet)
        df.columns = df.columns.astype(str).str.strip().str.lower()
        return df.to_dict('records')

    def _normalize_field(self, row):
        out = {}
        for raw_key, value in row.items():
            key = str(raw_key).strip().lower()
            for our_key, aliases in self.FIELD_MAPPINGS.items():
                if key == our_key or key in aliases:
                    out[our_key] = value if value is None else str(value).strip()
                    break
        return out

    def _parse_decimal(self, value, default=None):
        if value is None or value == '':
            return default
        try:
            s = str(value).strip().replace(',', '')
            return Decimal(s) if s else default
        except (InvalidOperation, ValueError):
            return default

    def _parse_bool(self, value, default=True):
        if value is None or value == '':
            return default
        v = str(value).strip().lower()
        if v in ('true', '1', 'yes', 'y', 't'):
            return True
        if v in ('false', '0', 'no', 'n', 'f'):
            return False
        return default

    def _import_drugs(self, data, dry_run, update_existing, with_inventory, user):
        stats = {'total': len(data), 'created': 0, 'updated': 0, 'skipped': 0, 'errors': []}

        with transaction.atomic():
            for idx, row in enumerate(data, start=1):
                try:
                    r = self._normalize_field(row)
                    name = (r.get('name') or '').strip()
                    if not name:
                        stats['errors'].append(f"Row {idx}: Missing drug name")
                        stats['skipped'] += 1
                        continue

                    cost_price = self._parse_decimal(r.get('cost_price'))
                    sales_price = self._parse_decimal(r.get('sales_price'))
                    if sales_price is None and cost_price is not None:
                        sales_price = cost_price

                    drug_code = (r.get('drug_code') or '').strip() or None
                    generic_name = (r.get('generic_name') or '').strip()
                    drug_class = (r.get('drug_class') or '').strip()
                    dosage_forms = (r.get('dosage_forms') or '').strip()
                    common_dosages = (r.get('common_dosages') or '').strip()
                    description = (r.get('description') or '').strip()
                    is_active = self._parse_bool(r.get('is_active'), True)

                    existing = Drug.objects.filter(name__iexact=name).first()
                    if not existing and drug_code:
                        existing = Drug.objects.filter(drug_code=drug_code).first()

                    drug_data = {
                        'name': name,
                        'generic_name': generic_name,
                        'drug_code': drug_code,
                        'drug_class': drug_class,
                        'dosage_forms': dosage_forms,
                        'common_dosages': common_dosages,
                        'cost_price': cost_price,
                        'sales_price': sales_price,
                        'description': description,
                        'is_active': is_active,
                        'created_by': user,
                    }

                    if existing:
                        if update_existing:
                            if not dry_run:
                                for k, v in drug_data.items():
                                    if k != 'created_by':
                                        setattr(existing, k, v)
                                try:
                                    existing.full_clean()
                                    existing.save()
                                except ValidationError as e:
                                    stats['errors'].append(f"Row {idx}: {e}")
                                    stats['skipped'] += 1
                                    continue
                            stats['updated'] += 1
                            self.stdout.write(f"  Updated: {name} - N{sales_price or 0:,.2f}")
                            drug = existing
                        else:
                            stats['skipped'] += 1
                            self.stdout.write(self.style.WARNING(f"  Skipped (exists): {name}"))
                            drug = None
                    else:
                        if not dry_run:
                            try:
                                drug = Drug.objects.create(**drug_data)
                            except ValidationError as e:
                                stats['errors'].append(f"Row {idx}: {e}")
                                stats['skipped'] += 1
                                continue
                        else:
                            drug = None
                        stats['created'] += 1
                        self.stdout.write(f"  Created: {name} - N{sales_price or 0:,.2f}")

                    # Create inventory if requested and we have stock data
                    if drug and with_inventory and not dry_run:
                        stock = self._parse_decimal(r.get('current_stock'), 0)
                        reorder = self._parse_decimal(r.get('reorder_level'), 0)
                        unit = (r.get('unit') or 'units').strip()

                        if not DrugInventory.objects.filter(drug=drug).exists():
                            DrugInventory.objects.create(
                                drug=drug,
                                current_stock=stock,
                                reorder_level=reorder,
                                unit=unit or 'units',
                            )
                            self.stdout.write(f"      + Inventory: {stock} {unit}")

                except Exception as e:
                    stats['errors'].append(f"Row {idx}: {str(e)}")
                    stats['skipped'] += 1
                    self.stdout.write(self.style.ERROR(f"  Error row {idx}: {e}"))

            if dry_run:
                transaction.set_rollback(True)

        return stats

    def _print_summary(self, stats, dry_run):
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Import Summary"))
        self.stdout.write("=" * 50)
        self.stdout.write(f"Total: {stats['total']}")
        self.stdout.write(self.style.SUCCESS(f"Created: {stats['created']}"))
        self.stdout.write(self.style.SUCCESS(f"Updated: {stats['updated']}"))
        self.stdout.write(self.style.WARNING(f"Skipped: {stats['skipped']}"))
        for e in stats['errors'][:15]:
            self.stdout.write(self.style.ERROR(f"  - {e}"))
        if len(stats['errors']) > 15:
            self.stdout.write(self.style.ERROR(f"  ... +{len(stats['errors']) - 15} more"))
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDry run. Run without --dry-run to apply."))
