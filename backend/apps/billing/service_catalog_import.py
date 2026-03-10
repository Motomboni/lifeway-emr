"""
Shared logic for importing ServiceCatalog from CSV, Excel, or JSON.
Used by both the management command and the web API.
"""
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.core.exceptions import ValidationError

from .service_catalog_models import ServiceCatalog

FIELD_MAPPINGS = {
    'department': ['department', 'dept', 'department_name'],
    'service_code': ['service code', 'service_code', 'servicecode', 'code', 'sku', 'item_code'],
    'name': ['service name', 'name', 'service_name', 'servicename', 'item_name', 'itemname', 'product'],
    'amount': ['amount', 'price', 'cost', 'selling_price', 'selling price', 'unit_price', 'unit price', 'fee'],
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


def _normalize_field_name(field_name):
    if not field_name:
        return None
    name = str(field_name).strip().lower()
    if name in FIELD_MAPPINGS:
        return name
    for key, aliases in FIELD_MAPPINGS.items():
        if name in aliases:
            return key
    return None


def _parse_boolean(value, default=None):
    if value is None or value == '':
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ['true', '1', 'yes', 'y', 't']:
        return True
    if s in ['false', '0', 'no', 'n', 'f']:
        return False
    return default


def _parse_allowed_roles(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(r).strip().upper() for r in value]
    roles = [r.strip().upper() for r in str(value).split(',')]
    return [r for r in roles if r]


def import_services(data: list, update_existing: bool = False, dry_run: bool = False) -> dict:
    """
    Import services from a list of row dicts (e.g. from pandas df.to_dict('records')).
    Returns stats: {total, created, updated, skipped, errors}.
    """
    stats = {'total': len(data), 'created': 0, 'updated': 0, 'skipped': 0, 'errors': []}

    # Upfront check: if first row lacks required fields, likely column/delimiter mismatch
    if data:
        first = data[0]
        normalized_first = {}
        for key, value in first.items():
            nk = _normalize_field_name(key)
            if nk:
                normalized_first[nk] = value
        has_dept = str(normalized_first.get('department') or '').strip()
        has_code = str(normalized_first.get('service_code') or '').strip()
        has_name = str(normalized_first.get('name') or '').strip()
        has_amt = str(normalized_first.get('amount') or '').strip()
        if not has_dept or not has_code or not has_name or not has_amt:
            raw_cols = list(first.keys())[:15]
            stats['errors'].append(
                f"Column headers may not match. Required: Department, Service Code, Service Name, Amount. "
                f"Your columns: {raw_cols}"
            )
            stats['skipped'] = len(data)
            return stats  # Skip processing to avoid hundreds of duplicate errors

    with transaction.atomic():
        for index, row in enumerate(data, start=1):
            try:
                normalized_row = {}
                for key, value in row.items():
                    nk = _normalize_field_name(key)
                    if nk:
                        normalized_row[nk] = value

                department = str(normalized_row.get('department', '')).strip().upper()
                service_code = str(normalized_row.get('service_code', '')).strip()
                name = str(normalized_row.get('name', '')).strip()
                amount_str = str(normalized_row.get('amount', '0'))
                category = str(normalized_row.get('category', '')).strip().upper()
                workflow_type = str(normalized_row.get('workflow_type', '')).strip().upper()
                allowed_roles_str = normalized_row.get('allowed_roles', '')

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

                try:
                    amount = Decimal(amount_str)
                    if amount <= 0:
                        stats['errors'].append(f"Row {index}: Amount must be greater than zero")
                        stats['skipped'] += 1
                        continue
                except (InvalidOperation, ValueError):
                    stats['errors'].append(f"Row {index}: Invalid amount '{amount_str}'")
                    stats['skipped'] += 1
                    continue

                description = str(normalized_row.get('description', '')).strip()
                requires_visit = _parse_boolean(normalized_row.get('requires_visit'), default=True)
                requires_consultation = _parse_boolean(normalized_row.get('requires_consultation'), default=False)
                auto_bill = _parse_boolean(normalized_row.get('auto_bill'), default=True)
                bill_timing = str(normalized_row.get('bill_timing', 'AFTER')).strip().upper()
                is_active = _parse_boolean(normalized_row.get('is_active'), default=True)
                allowed_roles = _parse_allowed_roles(allowed_roles_str)

                valid_depts = [c[0] for c in ServiceCatalog.DEPARTMENT_CHOICES]
                if department not in valid_depts:
                    stats['errors'].append(
                        f"Row {index}: Invalid department '{department}'. Must be one of: {', '.join(valid_depts)}"
                    )
                    stats['skipped'] += 1
                    continue

                if not category:
                    category_map = {
                        'CONSULTATION': 'CONSULTATION',
                        'LAB': 'LAB',
                        'PHARMACY': 'DRUG',
                        'RADIOLOGY': 'RADIOLOGY',
                        'PROCEDURE': 'PROCEDURE',
                    }
                    category = category_map.get(department, 'CONSULTATION')
                valid_cats = [c[0] for c in ServiceCatalog.CATEGORY_CHOICES]
                if category not in valid_cats:
                    stats['errors'].append(
                        f"Row {index}: Invalid category '{category}'. Must be one of: {', '.join(valid_cats)}"
                    )
                    stats['skipped'] += 1
                    continue

                if not workflow_type:
                    workflow_map = {
                        'CONSULTATION': 'GOPD_CONSULT',
                        'LAB': 'LAB_ORDER',
                        'PHARMACY': 'DRUG_DISPENSE',
                        'RADIOLOGY': 'RADIOLOGY_STUDY',
                        'PROCEDURE': 'PROCEDURE',
                    }
                    workflow_type = workflow_map.get(department, 'OTHER')
                # Normalize common workflow_type variations
                workflow_aliases = {
                    'PROCEDURE ORDER': 'PROCEDURE',
                    'DENTAL': 'PROCEDURE',
                    'IVF ORDER': 'DRUG_DISPENSE',
                    'CONSUMABLE ORDER': 'DRUG_DISPENSE',
                    'LAB ORDER': 'LAB_ORDER',
                    'DRUG DISPENSE': 'DRUG_DISPENSE',
                    'RADIOLOGY STUDY': 'RADIOLOGY_STUDY',
                    'GOPD CONSULT': 'GOPD_CONSULT',
                }
                workflow_type = workflow_aliases.get(workflow_type, workflow_type)
                valid_wf = [c[0] for c in ServiceCatalog.WORKFLOW_TYPE_CHOICES]
                if workflow_type not in valid_wf:
                    stats['errors'].append(
                        f"Row {index}: Invalid workflow_type '{workflow_type}'. Must be one of: {', '.join(valid_wf)}"
                    )
                    stats['skipped'] += 1
                    continue

                if bill_timing not in ['BEFORE', 'AFTER']:
                    bill_timing = 'AFTER'

                if not allowed_roles:
                    allowed_roles = ['DOCTOR']
                valid_roles = ['ADMIN', 'DOCTOR', 'NURSE', 'LAB_TECH', 'RADIOLOGY_TECH', 'PHARMACIST', 'RECEPTIONIST', 'PATIENT']
                invalid_roles = [r for r in allowed_roles if r not in valid_roles]
                if invalid_roles:
                    stats['errors'].append(
                        f"Row {index}: Invalid roles: {', '.join(invalid_roles)}. Valid: {', '.join(valid_roles)}"
                    )
                    stats['skipped'] += 1
                    continue

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
                            try:
                                for k, v in service_data.items():
                                    setattr(existing, k, v)
                                existing.full_clean()
                                existing.save()
                            except ValidationError as e:
                                stats['errors'].append(f"Row {index}: Validation error: {str(e)}")
                                stats['skipped'] += 1
                                continue
                        stats['updated'] += 1
                    else:
                        stats['skipped'] += 1
                else:
                    if not dry_run:
                        try:
                            ServiceCatalog.objects.create(**service_data)
                        except ValidationError as e:
                            stats['errors'].append(f"Row {index}: Validation error: {str(e)}")
                            stats['skipped'] += 1
                            continue
                    stats['created'] += 1

            except Exception as e:
                stats['errors'].append(f"Row {index}: {str(e)}")
                stats['skipped'] += 1

        if dry_run:
            transaction.set_rollback(True)

    return stats
