"""
Management command to import services from Excel file.

Usage:
    python manage.py import_services /path/to/services.xlsx

Excel File Format:
    The Excel file should have the following columns:
    - Department: LAB, PHARMACY, RADIOLOGY, or PROCEDURE
    - Service Code: Unique identifier for the service
    - Service Name: Name of the service
    - Amount: Price of the service (numeric)
    - Description: (Optional) Description of the service
    
    Example:
    Department | Service Code | Service Name          | Amount | Description
    LAB       | CBC-001      | Complete Blood Count  | 5000   | Full CBC test
    PHARMACY  | DRUG-001     | Paracetamol 500mg     | 500    | Pain relief
"""
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal, InvalidOperation
from apps.billing.price_lists import (
    LabServicePriceList,
    PharmacyServicePriceList,
    RadiologyServicePriceList,
    ProcedureServicePriceList,
)

# Map department names to models
DEPARTMENT_MODELS = {
    'LAB': LabServicePriceList,
    'PHARMACY': PharmacyServicePriceList,
    'RADIOLOGY': RadiologyServicePriceList,
    'PROCEDURE': ProcedureServicePriceList,
}


class Command(BaseCommand):
    help = 'Import services from Excel file into price lists'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'excel_file',
            type=str,
            help='Path to Excel file containing services'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            default=0,
            help='Sheet name or index (default: first sheet)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving to database'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing services if they already exist'
        )
    
    def handle(self, *args, **options):
        excel_file = options['excel_file']
        sheet = options['sheet']
        dry_run = options['dry_run']
        update_existing = options['update']
        
        try:
            # Read Excel file
            self.stdout.write(f"Reading Excel file: {excel_file}")
            df = pd.read_excel(excel_file, sheet_name=sheet)
            
            # Normalize column names (case-insensitive, strip whitespace)
            df.columns = df.columns.str.strip().str.upper()
            
            # Required columns
            required_columns = ['DEPARTMENT', 'SERVICE CODE', 'SERVICE NAME', 'AMOUNT']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise CommandError(
                    f"Missing required columns: {', '.join(missing_columns)}\n"
                    f"Found columns: {', '.join(df.columns)}"
                )
            
            # Validate and process data
            stats = {
                'total': len(df),
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': []
            }
            
            if dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))
            
            with transaction.atomic():
                for index, row in df.iterrows():
                    try:
                        # Extract data
                        department = str(row['DEPARTMENT']).strip().upper()
                        service_code = str(row['SERVICE CODE']).strip()
                        service_name = str(row['SERVICE NAME']).strip()
                        
                        # Parse amount
                        try:
                            amount = Decimal(str(row['AMOUNT']))
                        except (InvalidOperation, ValueError):
                            stats['errors'].append(
                                f"Row {index + 2}: Invalid amount '{row['AMOUNT']}'"
                            )
                            stats['skipped'] += 1
                            continue
                        
                        # Get description if available
                        description = ''
                        if 'DESCRIPTION' in df.columns:
                            description = str(row['DESCRIPTION']).strip() if pd.notna(row['DESCRIPTION']) else ''
                        
                        # Validate department
                        if department not in DEPARTMENT_MODELS:
                            stats['errors'].append(
                                f"Row {index + 2}: Invalid department '{department}'. "
                                f"Must be one of: {', '.join(DEPARTMENT_MODELS.keys())}"
                            )
                            stats['skipped'] += 1
                            continue
                        
                        # Validate required fields
                        if not service_code:
                            stats['errors'].append(f"Row {index + 2}: Service code is required")
                            stats['skipped'] += 1
                            continue
                        
                        if not service_name:
                            stats['errors'].append(f"Row {index + 2}: Service name is required")
                            stats['skipped'] += 1
                            continue
                        
                        if amount <= 0:
                            stats['errors'].append(
                                f"Row {index + 2}: Amount must be greater than zero"
                            )
                            stats['skipped'] += 1
                            continue
                        
                        # Get model for department
                        Model = DEPARTMENT_MODELS[department]
                        
                        # Check if service already exists
                        existing = Model.objects.filter(service_code=service_code).first()
                        
                        if existing:
                            if update_existing:
                                if not dry_run:
                                    existing.service_name = service_name
                                    existing.amount = amount
                                    existing.description = description
                                    existing.is_active = True
                                    existing.save()
                                stats['updated'] += 1
                                self.stdout.write(
                                    f"  Updated: {department} - {service_code} - {service_name}"
                                )
                            else:
                                stats['skipped'] += 1
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"  Skipped (exists): {department} - {service_code} - {service_name}"
                                    )
                                )
                        else:
                            if not dry_run:
                                Model.objects.create(
                                    service_code=service_code,
                                    service_name=service_name,
                                    amount=amount,
                                    description=description,
                                    is_active=True
                                )
                            stats['created'] += 1
                            self.stdout.write(
                                f"  Created: {department} - {service_code} - {service_name} - ₦{amount:,.2f}"
                            )
                    
                    except Exception as e:
                        stats['errors'].append(f"Row {index + 2}: {str(e)}")
                        stats['skipped'] += 1
                        self.stdout.write(
                            self.style.ERROR(f"  Error on row {index + 2}: {str(e)}")
                        )
                
                if dry_run:
                    # Rollback transaction in dry run mode
                    transaction.set_rollback(True)
            
            # Print summary
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("Import Summary"))
            self.stdout.write("=" * 60)
            self.stdout.write(f"Total rows processed: {stats['total']}")
            self.stdout.write(f"Created: {stats['created']}")
            self.stdout.write(f"Updated: {stats['updated']}")
            self.stdout.write(f"Skipped: {stats['skipped']}")
            
            if stats['errors']:
                self.stdout.write(self.style.ERROR(f"\nErrors ({len(stats['errors'])}):"))
                for error in stats['errors'][:20]:  # Show first 20 errors
                    self.stdout.write(self.style.ERROR(f"  - {error}"))
                if len(stats['errors']) > 20:
                    self.stdout.write(
                        self.style.ERROR(f"  ... and {len(stats['errors']) - 20} more errors")
                    )
            else:
                self.stdout.write(self.style.SUCCESS("\nNo errors!"))
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING("\nThis was a dry run. Use without --dry-run to save changes.")
                )
        
        except FileNotFoundError:
            raise CommandError(f"Excel file not found: {excel_file}")
        except Exception as e:
            raise CommandError(f"Error reading Excel file: {str(e)}")

