"""
Management command to import services into ServiceCatalog from CSV, Excel, or JSON.

Usage:
    python manage.py import_service_catalog /path/to/services.csv
    python manage.py import_service_catalog /path/to/services.xlsx
    python manage.py import_service_catalog /path/to/services.json

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
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.billing.service_catalog_models import ServiceCatalog

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class Command(BaseCommand):
    help = 'Import services into ServiceCatalog from CSV, Excel, or JSON file'
    
    # Field mappings (case-insensitive)
    FIELD_MAPPINGS = {
        'department': ['department', 'dept'],
        'service_code': ['service code', 'service_code', 'code'],
        'name': ['service name', 'name', 'service_name'],
        'amount': ['amount', 'price', 'cost'],
        'description': ['description', 'desc'],
        'category': ['category', 'cat'],
        'workflow_type': ['workflow type', 'workflow_type', 'workflow'],
        'requires_visit': ['requires visit', 'requires_visit', 'needs visit'],
        'requires_consultation': ['requires consultation', 'requires_consultation', 'needs consultation'],
        'auto_bill': ['auto bill', 'auto_bill', 'auto bill'],
        'bill_timing': ['bill timing', 'bill_timing', 'billing timing'],
        'allowed_roles': ['allowed roles', 'allowed_roles', 'roles'],
        'is_active': ['is active', 'is_active', 'active'],
    }
    
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
        
        # Process and import data
        stats = self._import_services(data, dry_run, update_existing)
        
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
    
    def _normalize_field_name(self, field_name):
        """Normalize field name to match our mappings."""
        if not field_name:
            return None
        field_name = str(field_name).strip().lower()
        
        # Check direct match first
        if field_name in self.FIELD_MAPPINGS:
            return field_name
        
        # Check if it matches any of the aliases
        for key, aliases in self.FIELD_MAPPINGS.items():
            if field_name in aliases:
                return key
        
        return None
    
    def _parse_boolean(self, value, default=None):
        """Parse boolean value from various formats."""
        if value is None or value == '':
            return default
        
        if isinstance(value, bool):
            return value
        
        value_str = str(value).strip().lower()
        if value_str in ['true', '1', 'yes', 'y', 't']:
            return True
        elif value_str in ['false', '0', 'no', 'n', 'f']:
            return False
        
        return default
    
    def _parse_allowed_roles(self, value):
        """Parse allowed roles from comma-separated string or list."""
        if not value:
            return []
        
        if isinstance(value, list):
            return [str(r).strip().upper() for r in value]
        
        # Comma-separated string
        roles = [r.strip().upper() for r in str(value).split(',')]
        return [r for r in roles if r]
    
    def _import_services(self, data, dry_run, update_existing):
        """Import services from data list."""
        stats = {
            'total': len(data),
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
        
        with transaction.atomic():
            for index, row in enumerate(data, start=1):
                try:
                    # Normalize field names
                    normalized_row = {}
                    for key, value in row.items():
                        normalized_key = self._normalize_field_name(key)
                        if normalized_key:
                            normalized_row[normalized_key] = value
                    
                    # Extract and validate required fields
                    department = normalized_row.get('department', '').strip().upper()
                    service_code = normalized_row.get('service_code', '').strip()
                    name = normalized_row.get('name', '').strip()
                    amount_str = normalized_row.get('amount', '0')
                    category = normalized_row.get('category', '').strip().upper()
                    workflow_type = normalized_row.get('workflow_type', '').strip().upper()
                    allowed_roles_str = normalized_row.get('allowed_roles', '')
                    
                    # Validate required fields
                    if not department:
                        stats['errors'].append(f"Row {index}: Missing 'department'")
                        stats['skipped'] += 1
                        continue
                    
                    if not service_code:
                        stats['errors'].append(f"Row {index}: Missing 'service_code'")
                        stats['skipped'] += 1
                        continue
                    
                    if not name:
                        stats['errors'].append(f"Row {index}: Missing 'name'")
                        stats['skipped'] += 1
                        continue
                    
                    # Parse amount
                    try:
                        amount = Decimal(str(amount_str))
                        if amount <= 0:
                            stats['errors'].append(f"Row {index}: Amount must be greater than zero")
                            stats['skipped'] += 1
                            continue
                    except (InvalidOperation, ValueError):
                        stats['errors'].append(f"Row {index}: Invalid amount '{amount_str}'")
                        stats['skipped'] += 1
                        continue
                    
                    # Parse optional fields with defaults
                    description = normalized_row.get('description', '').strip()
                    requires_visit = self._parse_boolean(normalized_row.get('requires_visit'), default=True)
                    requires_consultation = self._parse_boolean(normalized_row.get('requires_consultation'), default=False)
                    auto_bill = self._parse_boolean(normalized_row.get('auto_bill'), default=True)
                    bill_timing = normalized_row.get('bill_timing', 'AFTER').strip().upper()
                    is_active = self._parse_boolean(normalized_row.get('is_active'), default=True)
                    allowed_roles = self._parse_allowed_roles(allowed_roles_str)
                    
                    # Validate department
                    valid_departments = [choice[0] for choice in ServiceCatalog.DEPARTMENT_CHOICES]
                    if department not in valid_departments:
                        stats['errors'].append(
                            f"Row {index}: Invalid department '{department}'. "
                            f"Must be one of: {', '.join(valid_departments)}"
                        )
                        stats['skipped'] += 1
                        continue
                    
                    # Validate category
                    if not category:
                        # Try to infer from department
                        category_map = {
                            'CONSULTATION': 'CONSULTATION',
                            'LAB': 'LAB',
                            'PHARMACY': 'DRUG',
                            'RADIOLOGY': 'RADIOLOGY',
                            'PROCEDURE': 'PROCEDURE',
                        }
                        category = category_map.get(department, 'CONSULTATION')
                    
                    valid_categories = [choice[0] for choice in ServiceCatalog.CATEGORY_CHOICES]
                    if category not in valid_categories:
                        stats['errors'].append(
                            f"Row {index}: Invalid category '{category}'. "
                            f"Must be one of: {', '.join(valid_categories)}"
                        )
                        stats['skipped'] += 1
                        continue
                    
                    # Validate workflow_type
                    if not workflow_type:
                        # Try to infer from department
                        workflow_map = {
                            'CONSULTATION': 'GOPD_CONSULT',
                            'LAB': 'LAB_ORDER',
                            'PHARMACY': 'DRUG_DISPENSE',
                            'RADIOLOGY': 'RADIOLOGY_STUDY',
                            'PROCEDURE': 'PROCEDURE',
                        }
                        workflow_type = workflow_map.get(department, 'OTHER')
                    
                    valid_workflows = [choice[0] for choice in ServiceCatalog.WORKFLOW_TYPE_CHOICES]
                    if workflow_type not in valid_workflows:
                        stats['errors'].append(
                            f"Row {index}: Invalid workflow_type '{workflow_type}'. "
                            f"Must be one of: {', '.join(valid_workflows)}"
                        )
                        stats['skipped'] += 1
                        continue
                    
                    # Validate bill_timing
                    if bill_timing not in ['BEFORE', 'AFTER']:
                        bill_timing = 'AFTER'
                    
                    # Validate allowed_roles
                    if not allowed_roles:
                        # Default to DOCTOR if not specified
                        allowed_roles = ['DOCTOR']
                    
                    valid_roles = ['ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH', 'RADIOLOGY_TECH', 
                                  'PHARMACIST', 'RECEPTIONIST', 'PATIENT']
                    invalid_roles = [r for r in allowed_roles if r not in valid_roles]
                    if invalid_roles:
                        stats['errors'].append(
                            f"Row {index}: Invalid roles: {', '.join(invalid_roles)}. "
                            f"Valid roles: {', '.join(valid_roles)}"
                        )
                        stats['skipped'] += 1
                        continue
                    
                    # Check if service already exists
                    existing = ServiceCatalog.objects.filter(service_code=service_code).first()
                    
                    service_data = {
                        'department': department,
                        'service_code': service_code,
                        'name': name,
                        'amount': amount,
                        'description': description,
                        'category': category,
                        'workflow_type': workflow_type,
                        'requires_visit': requires_visit,
                        'requires_consultation': requires_consultation,
                        'auto_bill': auto_bill,
                        'bill_timing': bill_timing,
                        'allowed_roles': allowed_roles,
                        'is_active': is_active,
                    }
                    
                    if existing:
                        if update_existing:
                            if not dry_run:
                                for key, value in service_data.items():
                                    setattr(existing, key, value)
                                try:
                                    existing.full_clean()
                                    existing.save()
                                except ValidationError as e:
                                    stats['errors'].append(f"Row {index}: Validation error: {str(e)}")
                                    stats['skipped'] += 1
                                    continue
                            stats['updated'] += 1
                            self.stdout.write(
                                f"  Updated: {service_code} - {name} ({department})"
                            )
                        else:
                            stats['skipped'] += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  Skipped (exists): {service_code} - {name}"
                                )
                            )
                    else:
                        if not dry_run:
                            try:
                                ServiceCatalog.objects.create(**service_data)
                            except ValidationError as e:
                                stats['errors'].append(f"Row {index}: Validation error: {str(e)}")
                                stats['skipped'] += 1
                                continue
                        stats['created'] += 1
                        self.stdout.write(
                            f"  Created: {service_code} - {name} - N{amount:,.2f} ({department})"
                        )
                
                except Exception as e:
                    stats['errors'].append(f"Row {index}: {str(e)}")
                    stats['skipped'] += 1
                    self.stdout.write(
                        self.style.ERROR(f"  Error on row {index}: {str(e)}")
                    )
            
            if dry_run:
                transaction.set_rollback(True)
        
        return stats
    
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

