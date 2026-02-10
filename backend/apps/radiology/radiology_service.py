"""
Radiology Report Posting Service.

Per Nigerian Clinic Operational Realities:
- Reports can only be posted for active radiology requests
- Only Radiology Tech can post reports
- Clear audit trail for report posting
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import RadiologyRequest
from apps.core.validators import validate_active_radiology_request


def post_radiology_report(
    radiology_request: RadiologyRequest,
    radiology_tech,
    report_text: str,
    image_count: int = 0,
    image_metadata: dict = None,
) -> RadiologyRequest:
    """
    Post a radiology report for a radiology request.
    
    Nigerian Clinic Governance Rules:
    - Radiology request must be ACTIVE (PENDING or IN_PROGRESS)
    - Only Radiology Tech can post reports
    - Reports are immutable once posted
    
    Args:
        radiology_request: RadiologyRequest instance
        radiology_tech: User (must be RADIOLOGY_TECH role)
        report_text: Report text/interpretation
        image_count: Number of images (optional)
        image_metadata: Image metadata dictionary (optional)
    
    Returns:
        Updated RadiologyRequest instance
    
    Raises:
        ValidationError: If validation fails
    """
    # Validate radiology tech role
    if radiology_tech.role != 'RADIOLOGY_TECH':
        raise ValidationError(
            "Only radiology technicians can post radiology reports. "
            "User role '%(role)s' is not authorized."
        ) % {'role': radiology_tech.role}
    
    # Validate radiology request is active
    validate_active_radiology_request(radiology_request)
    
    # Validate request hasn't been completed
    if radiology_request.status == 'COMPLETED':
        raise ValidationError(
            "Radiology report has already been posted for this request. "
            "Request ID: %(request_id)s is COMPLETED. "
            "Reports are immutable once posted."
        ) % {'request_id': radiology_request.id}
    
    with transaction.atomic():
        # Update radiology request
        radiology_request.report = report_text
        radiology_request.reported_by = radiology_tech
        radiology_request.report_date = timezone.now()
        radiology_request.status = 'COMPLETED'
        
        if image_count:
            radiology_request.image_count = image_count
        if image_metadata:
            radiology_request.image_metadata = image_metadata
        
        radiology_request.save()
        
        return radiology_request

