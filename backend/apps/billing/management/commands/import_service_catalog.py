"""
Management command to import services into ServiceCatalog from CSV, Excel, or JSON.

Usage:
    python manage.py import_service_catalog /path/to/services.csv
    python manage.py import_service_catalog /path/to/services.xlsx
    python manage.py import_service_catalog /path/to/services.json
    python manage.py import_service_catalog services.xlsx --update   # Merge/update existing

Supported Formats:
    - CSV: Comma-separated values
    - Excel: .xlsx or .xls files
    - JSON: Array of service objects

Required Columns/Fields:
    - Department: CONSULTATION, LAB, PHARMACY, RADIOLOGY, PROCEDURE
    - Service Code: Unique identifier (e.g., "CONS-001", "CBC-001")
    - Service Name: Display name
    - Amount: Price (numeric)
    - Category: CONSULTATION, LAB, DRUG, PROCEDURE, RADIOLOGY
    - Workflow Type: GOPD_CONSULT, LAB_ORDER, DRUG_DISPENSE, PROCEDURE, RADIOLOGY_STUDY, etc.
    - Allowed Roles: Comma-separated list (e.g., "DOCTOR, NURSE")

Optional Columns/Fields:
    - Description: Detailed description
    - Requires Visit: true/false (default: true)
    - Requires Consultation: true/false (default: false)
    - Auto Bill: true/false (default: true)
    - Bill Timing: BEFORE or AFTER (default: AFTER)
    - Is Active: true/false (default: true)
"""
import csv
import json
import os
from django.core.management.base import BaseCommand, CommandError

from apps.billing.service_catalog_import import import_services

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class Command(BaseCommand):
    help = 'Import services into ServiceCatalog from CSV, Excel, or JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to CSV, Excel, or JSON file containing services'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving to database'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing services if they already exist (by service_code)'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            default=0,
            help='Sheet name or index for Excel files (default: first sheet)'
        )
    
    def handle(self, *args, **options):
        file_path = options['file_path']
        dry_run = options['dry_run']
        update_existing = options['update']
        sheet = options['sheet']
        
        if not os.path.exists(file_path):
            raise CommandError(f"File not found: {file_path}")
        
        # Detect file type
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.json':
            data = self._read_json(file_path)
        elif file_ext in ['.xlsx', '.xls']:
            if not PANDAS_AVAILABLE:
                raise CommandError("pandas is required for Excel files. Install with: pip install pandas openpyxl")
            data = self._read_excel(file_path, sheet)
        elif file_ext == '.csv':
            data = self._read_csv(file_path)
        else:
            raise CommandError(f"Unsupported file format: {file_ext}. Supported: .csv, .xlsx, .xls, .json")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be saved"))
        
        # Process and import data (shared logic with web API)
        stats = import_services(data, update_existing=update_existing, dry_run=dry_run)
        
        # Print summary
        self._print_summary(stats, dry_run)
    
    def _read_json(self, file_path):
        """Read JSON file and return list of dictionaries."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # If it's a single object, wrap it in a list
            if isinstance(data, dict):
                data = [data]
            
            return data
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON file: {str(e)}")
        except Exception as e:
            raise CommandError(f"Error reading JSON file: {str(e)}")
    
    def _read_excel(self, file_path, sheet):
        """Read Excel file and return list of dictionaries."""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet)
            # Normalize column names (strip whitespace, lowercase)
            df.columns = df.columns.str.strip().str.lower()
            # Convert to list of dictionaries
            return df.to_dict('records')
        except Exception as e:
            raise CommandError(f"Error reading Excel file: {str(e)}")
    
    def _read_csv(self, file_path):
        """Read CSV file and return list of dictionaries."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # First try with comma delimiter (most common)
                sample = f.read(1024)
                f.seek(0)
                
                # Check if comma is present in the first line
                first_line = f.readline()
                f.seek(0)
                
                if ',' in first_line:
                    # Use comma delimiter
                    reader = csv.DictReader(f, delimiter=',')
                else:
                    # Try to detect delimiter
                    try:
                        sniffer = csv.Sniffer()
                        delimiter = sniffer.sniff(sample).delimiter
                        f.seek(0)
                        reader = csv.DictReader(f, delimiter=delimiter)
                    except csv.Error:
                        # Fall back to comma
                        f.seek(0)
                        reader = csv.DictReader(f, delimiter=',')
                
                return list(reader)
        except Exception as e:
            raise CommandError(f"Error reading CSV file: {str(e)}")

    def _print_summary(self, stats, dry_run):
        """Print import summary."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Import Summary"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total rows processed: {stats['total']}")
        self.stdout.write(self.style.SUCCESS(f"Created: {stats['created']}"))
        self.stdout.write(self.style.SUCCESS(f"Updated: {stats['updated']}"))
        self.stdout.write(self.style.WARNING(f"Skipped: {stats['skipped']}"))
        
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

