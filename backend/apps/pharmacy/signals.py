"""
Signals for Drug model to automatically sync with ServiceCatalog.

When a Drug is created or updated, automatically create/update
a corresponding ServiceCatalog entry so the drug appears in
the Service Catalog for ordering.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Drug
from apps.billing.service_catalog_models import ServiceCatalog

logger = logging.getLogger(__name__)


def generate_drug_service_code(drug: Drug) -> str:
    """
    Generate a unique service code for a drug.
    
    Format: DRUG-{drug_code} or DRUG-{drug_id} if drug_code is not available.
    """
    if drug.drug_code and drug.drug_code.strip():
        # Use drug_code if available, but ensure it's prefixed with DRUG-
        code = drug.drug_code.strip().upper()
        if not code.startswith('DRUG-'):
            code = f"DRUG-{code}"
        return code
    else:
        # Use drug ID if drug_code is not available
        # Note: This will only work after the drug is saved (has an ID)
        if drug.pk:
            return f"DRUG-{drug.pk:06d}"
        else:
            # Fallback for new drugs without ID yet - use sanitized name
            # This will be updated after the drug is saved
            sanitized_name = drug.name[:20].upper().replace(' ', '-').replace('/', '-')
            # Remove any special characters
            sanitized_name = ''.join(c for c in sanitized_name if c.isalnum() or c == '-')
            return f"DRUG-{sanitized_name}"


def create_service_catalog_from_drug(drug: Drug) -> ServiceCatalog:
    """
    Create a ServiceCatalog entry from a Drug.
    
    Args:
        drug: Drug instance
        
    Returns:
        ServiceCatalog instance
    """
    # Generate service code
    service_code = generate_drug_service_code(drug)
    
    # Ensure uniqueness - if code exists, append drug ID
    original_code = service_code
    counter = 1
    while ServiceCatalog.objects.filter(service_code=service_code).exclude(
        # Exclude the service catalog that might be linked to this drug
        # We'll use a metadata field or description to track the link
    ).exists():
        service_code = f"{original_code}-{counter}"
        counter += 1
    
    # Use sales_price if available, otherwise use cost_price, otherwise default to 0
    amount = Decimal('0.00')
    if drug.sales_price:
        amount = drug.sales_price
    elif drug.cost_price:
        # If no sales_price, use cost_price (can be adjusted later)
        amount = drug.cost_price
    
    # Build description from drug information
    description_parts = []
    if drug.generic_name:
        description_parts.append(f"Generic: {drug.generic_name}")
    if drug.drug_class:
        description_parts.append(f"Class: {drug.drug_class}")
    if drug.dosage_forms:
        description_parts.append(f"Dosage Forms: {drug.dosage_forms}")
    if drug.common_dosages:
        description_parts.append(f"Common Dosages: {drug.common_dosages}")
    if drug.description:
        description_parts.append(drug.description)
    
    description = "\n".join(description_parts) if description_parts else ""
    
    # Create ServiceCatalog entry
    service_catalog = ServiceCatalog.objects.create(
        department='PHARMACY',
        service_code=service_code,
        name=drug.name,
        amount=amount,
        description=description,
        category='DRUG',
        workflow_type='DRUG_DISPENSE',
        requires_visit=True,
        requires_consultation=True,  # Drugs require consultation
        auto_bill=True,
        bill_timing='AFTER',  # Bill after dispensing
        allowed_roles=['DOCTOR', 'NURSE'],  # Default roles for drug ordering
        is_active=drug.is_active,
    )
    
    logger.info(f"Created ServiceCatalog entry {service_code} for drug {drug.name}")
    return service_catalog


def update_service_catalog_from_drug(drug: Drug, service_catalog: ServiceCatalog):
    """
    Update a ServiceCatalog entry from a Drug.
    
    Args:
        drug: Drug instance
        service_catalog: ServiceCatalog instance to update
    """
    # Update basic fields
    service_catalog.name = drug.name
    service_catalog.is_active = drug.is_active
    
    # Update amount (use sales_price if available)
    if drug.sales_price:
        service_catalog.amount = drug.sales_price
    elif drug.cost_price:
        service_catalog.amount = drug.cost_price
    
    # Update description
    description_parts = []
    if drug.generic_name:
        description_parts.append(f"Generic: {drug.generic_name}")
    if drug.drug_class:
        description_parts.append(f"Class: {drug.drug_class}")
    if drug.dosage_forms:
        description_parts.append(f"Dosage Forms: {drug.dosage_forms}")
    if drug.common_dosages:
        description_parts.append(f"Common Dosages: {drug.common_dosages}")
    if drug.description:
        description_parts.append(drug.description)
    
    service_catalog.description = "\n".join(description_parts) if description_parts else ""
    
    # Update service_code if drug_code changed
    new_service_code = generate_drug_service_code(drug)
    if new_service_code != service_catalog.service_code:
        # Check if new code is available
        if not ServiceCatalog.objects.filter(service_code=new_service_code).exclude(pk=service_catalog.pk).exists():
            service_catalog.service_code = new_service_code
    
    service_catalog.save()
    logger.info(f"Updated ServiceCatalog entry {service_catalog.service_code} for drug {drug.name}")


@receiver(post_save, sender=Drug)
def sync_drug_to_service_catalog(sender, instance, created, **kwargs):
    """
    Signal handler to sync Drug to ServiceCatalog.
    
    When a Drug is created, create a corresponding ServiceCatalog entry.
    When a Drug is updated, update the corresponding ServiceCatalog entry.
    """
    # Skip if this is a raw save (e.g., during migrations)
    if kwargs.get('raw', False):
        return
    
    try:
        # Try to find existing service catalog linked to this drug
        # We'll identify it by matching service_code pattern or name
        service_code_pattern = generate_drug_service_code(instance)
        
        # Try to find by service_code pattern
        existing_service = None
        if instance.pk:
            # Try exact match first
            existing_service = ServiceCatalog.objects.filter(
                service_code=service_code_pattern,
                department='PHARMACY',
                category='DRUG'
            ).first()
            
            # If not found, try by name (for existing drugs)
            if not existing_service:
                existing_service = ServiceCatalog.objects.filter(
                    name=instance.name,
                    department='PHARMACY',
                    category='DRUG'
                ).first()
        
        if created:
            # Create new ServiceCatalog entry
            if not existing_service:
                create_service_catalog_from_drug(instance)
            else:
                # Update existing entry instead of creating duplicate
                logger.warning(
                    f"ServiceCatalog entry already exists for drug {instance.name}. "
                    f"Updating existing entry instead of creating duplicate."
                )
                update_service_catalog_from_drug(instance, existing_service)
        else:
            # Update existing ServiceCatalog entry
            if existing_service:
                update_service_catalog_from_drug(instance, existing_service)
            else:
                # If no existing service found, create one
                logger.warning(
                    f"No ServiceCatalog entry found for drug {instance.name}. "
                    f"Creating new entry."
                )
                create_service_catalog_from_drug(instance)
                
    except Exception as e:
        logger.error(
            f"Error syncing drug {instance.name} to ServiceCatalog: {e}",
            exc_info=True
        )
        # Don't raise exception - we don't want to break drug creation/update
        # Just log the error


@receiver(post_delete, sender=Drug)
def deactivate_service_catalog_on_drug_delete(sender, instance, **kwargs):
    """
    Signal handler to deactivate ServiceCatalog entry when Drug is deleted.
    
    Instead of deleting the ServiceCatalog entry (which might have billing history),
    we deactivate it.
    """
    try:
        service_code_pattern = generate_drug_service_code(instance)
        
        # Find and deactivate matching service catalog entries
        services = ServiceCatalog.objects.filter(
            name=instance.name,
            department='PHARMACY',
            category='DRUG'
        )
        
        for service in services:
            service.is_active = False
            service.save(update_fields=['is_active'])
            logger.info(f"Deactivated ServiceCatalog entry {service.service_code} for deleted drug {instance.name}")
            
    except Exception as e:
        logger.error(
            f"Error deactivating ServiceCatalog entry for deleted drug {instance.name}: {e}",
            exc_info=True
        )
