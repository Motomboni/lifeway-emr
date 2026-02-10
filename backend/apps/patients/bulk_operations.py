"""
Bulk operations for patient management.

Per EMR Rules:
- PHI data must be protected
- All operations must be audited
- Validation required for all imports
"""
import csv
import json
from io import StringIO
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Patient
from core.audit import AuditLog


def import_patients_from_csv(csv_content, created_by, request=None):
    """
    Import patients from CSV content.
    
    Expected CSV format:
    first_name,last_name,middle_name,date_of_birth,gender,phone,email,address,national_id
    
    Args:
        csv_content: CSV file content (string)
        created_by: User performing the import
        request: Django request object (for audit logging)
    
    Returns:
        dict: Summary of import results
    """
    reader = csv.DictReader(StringIO(csv_content))
    
    imported = 0
    failed = 0
    errors = []
    
    with transaction.atomic():
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (row 1 is header)
            try:
                # Validate required fields
                if not row.get('first_name') or not row.get('last_name'):
                    raise ValidationError("first_name and last_name are required")
                
                # Create patient
                patient = Patient.objects.create(
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    middle_name=row.get('middle_name', ''),
                    date_of_birth=row.get('date_of_birth') or None,
                    gender=row.get('gender', ''),
                    phone=row.get('phone', ''),
                    email=row.get('email', ''),
                    address=row.get('address', ''),
                    national_id=row.get('national_id', ''),
                )
                
                imported += 1
                
                # Audit log
                user_role = getattr(created_by, 'role', None) or \
                           getattr(created_by, 'get_role', lambda: None)()
                if not user_role:
                    user_role = 'UNKNOWN'
                
                AuditLog.log(
                    user=created_by,
                    role=user_role,
                    action="PATIENT_BULK_IMPORT",
                    resource_type="patient",
                    resource_id=patient.id,
                    request=request,
                    metadata={'import_row': row_num}
                )
                
            except Exception as e:
                failed += 1
                errors.append({
                    'row': row_num,
                    'error': str(e),
                    'data': row
                })
    
    return {
        'imported': imported,
        'failed': failed,
        'errors': errors,
        'total': imported + failed
    }


def export_patients_to_csv(patients_queryset):
    """
    Export patients to CSV format.
    
    Args:
        patients_queryset: QuerySet of Patient objects
    
    Returns:
        str: CSV content
    """
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'patient_id',
        'first_name',
        'last_name',
        'middle_name',
        'date_of_birth',
        'gender',
        'phone',
        'email',
        'address',
        'national_id',
        'blood_group',
        'allergies',
        'created_at',
    ])
    
    # Write data
    for patient in patients_queryset:
        writer.writerow([
            patient.patient_id,
            patient.first_name,
            patient.last_name,
            patient.middle_name or '',
            patient.date_of_birth.isoformat() if patient.date_of_birth else '',
            patient.gender or '',
            patient.phone or '',
            patient.email or '',
            patient.address or '',
            patient.national_id or '',
            patient.blood_group or '',
            patient.allergies or '',
            patient.created_at.isoformat(),
        ])
    
    return output.getvalue()


def export_patients_to_json(patients_queryset):
    """
    Export patients to JSON format.
    
    Args:
        patients_queryset: QuerySet of Patient objects
    
    Returns:
        str: JSON content
    """
    patients_data = []
    
    for patient in patients_queryset:
        patients_data.append({
            'patient_id': patient.patient_id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'middle_name': patient.middle_name,
            'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
            'gender': patient.gender,
            'phone': patient.phone,
            'email': patient.email,
            'address': patient.address,
            'national_id': patient.national_id,
            'blood_group': patient.blood_group,
            'allergies': patient.allergies,
            'created_at': patient.created_at.isoformat(),
        })
    
    return json.dumps(patients_data, indent=2)
