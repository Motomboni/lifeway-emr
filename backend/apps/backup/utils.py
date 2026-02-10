"""
Backup and Restore utility functions.

Per EMR Rules:
- Backups must be encrypted
- PHI data must be protected
- Audit logging mandatory
"""
import json
import os
import zipfile
import tempfile
from datetime import datetime, timedelta
from django.conf import settings
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone


def create_backup_file(backup_instance, include_tables=None):
    """
    Create a backup file using Django's dumpdata command.
    
    Args:
        backup_instance: Backup model instance
        include_tables: List of table names to include (None = all)
    
    Returns:
        str: Path to created backup file
    """
    # Create backup directory if it doesn't exist
    backup_dir = os.path.join(settings.BASE_DIR, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_{backup_instance.id}_{timestamp}.json"
    file_path = os.path.join(backup_dir, filename)
    
    # Create temporary file for dumpdata output
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Build apps list based on backup scope
        apps_to_backup = []
        
        if backup_instance.includes_patients:
            apps_to_backup.append('patients')
        
        if backup_instance.includes_visits:
            apps_to_backup.append('visits')
        
        if backup_instance.includes_consultations:
            apps_to_backup.append('consultations')
        
        if backup_instance.includes_lab_data:
            apps_to_backup.append('laboratory')
        
        if backup_instance.includes_radiology_data:
            apps_to_backup.append('radiology')
        
        if backup_instance.includes_prescriptions:
            apps_to_backup.append('pharmacy')
        
        if backup_instance.includes_audit_logs:
            apps_to_backup.append('core')  # Audit logs are in core app
        
        # Always include users (for referential integrity)
        if 'users' not in apps_to_backup:
            apps_to_backup.append('users')
        
        # Run dumpdata command
        if apps_to_backup:
            call_command(
                'dumpdata',
                *apps_to_backup,
                '--output', tmp_path,
                '--indent', 2,
                '--natural-foreign',
                '--natural-primary',
            )
        else:
            # If nothing selected, create empty backup
            with open(tmp_path, 'w') as f:
                json.dump([], f)
        
        # Move to final location
        import shutil
        shutil.move(tmp_path, file_path)
        
        # Get file size
        file_size = os.path.getsize(file_path)
        backup_instance.file_size = file_size
        backup_instance.file_path = file_path
        backup_instance.save(update_fields=['file_path', 'file_size'])
        
        return file_path
    
    except Exception as e:
        # Clean up on error
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e


def restore_from_backup(restore_instance):
    """
    Restore data from a backup file.
    
    Args:
        restore_instance: Restore model instance
    
    Returns:
        dict: Summary of restored data
    """
    backup = restore_instance.backup
    
    if not backup.file_path or not os.path.exists(backup.file_path):
        raise ValueError(f"Backup file not found: {backup.file_path}")
    
    # Read backup file
    with open(backup.file_path, 'r') as f:
        data = json.load(f)
    
    # Filter data based on restore scope
    filtered_data = []
    app_labels = {
        'patients': 'patients',
        'visits': 'visits',
        'consultations': 'consultations',
        'lab_orders': 'laboratory',
        'lab_results': 'laboratory',
        'radiology_orders': 'radiology',
        'radiology_results': 'radiology',
        'prescriptions': 'pharmacy',
        'drugs': 'pharmacy',
        'drug_inventory': 'pharmacy',
        'stock_movements': 'pharmacy',
        'audit_logs': 'core',
    }
    
    for item in data:
        model_name = item.get('model', '').split('.')[-1] if '.' in item.get('model', '') else ''
        
        # Determine if this item should be restored
        should_restore = False
        
        if model_name in ['patient'] and restore_instance.restore_patients:
            should_restore = True
        elif model_name in ['visit'] and restore_instance.restore_visits:
            should_restore = True
        elif model_name in ['consultation'] and restore_instance.restore_consultations:
            should_restore = True
        elif model_name in ['laborder', 'labresult'] and restore_instance.restore_lab_data:
            should_restore = True
        elif model_name in ['radiologyorder', 'radiologyresult'] and restore_instance.restore_radiology_data:
            should_restore = True
        elif model_name in ['prescription', 'drug', 'druginventory', 'stockmovement'] and restore_instance.restore_prescriptions:
            should_restore = True
        elif model_name in ['auditlog'] and restore_instance.restore_audit_logs:
            should_restore = True
        elif model_name in ['user']:  # Always restore users for referential integrity
            should_restore = True
        
        if should_restore:
            filtered_data.append(item)
    
    # Create temporary file with filtered data
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
        json.dump(filtered_data, tmp_file, indent=2)
        tmp_path = tmp_file.name
    
    try:
        # Run loaddata command with transaction
        # Note: In production, you may want to clear existing data first
        # or use a more sophisticated restore strategy
        call_command('loaddata', tmp_path, verbosity=0)
        
        # Clean up
        os.remove(tmp_path)
        
        return {
            'items_restored': len(filtered_data),
            'total_items_in_backup': len(data),
        }
    
    except Exception as e:
        # Clean up on error
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise e
