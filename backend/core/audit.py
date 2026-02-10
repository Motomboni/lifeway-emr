"""
Audit logging utility for EMR compliance (HIPAA/NHIA).

Audit logs are append-only, immutable records of all clinical actions.
They are NOT exposed via APIs and are used for compliance and security.
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditLog(models.Model):
    """
    Append-only audit log for all clinical actions.
    
    Per EMR rules:
    - Append-only (no edits/deletes)
    - Records: User ID, Role, Action, Visit ID, Timestamp, IP
    - Required for: Consultations, Lab orders, Radiology, Prescriptions, Payments
    """
    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='audit_logs',
        help_text="User who performed the action"
    )
    user_role = models.CharField(
        max_length=50,
        help_text="Role of the user at time of action"
    )
    action = models.CharField(
        max_length=100,
        help_text="Action performed (e.g., 'consultation.create', 'consultation.update')"
    )
    visit_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Visit ID if action is visit-scoped"
    )
    resource_type = models.CharField(
        max_length=50,
        help_text="Resource type (e.g., 'consultation', 'lab_order')"
    )
    resource_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of the resource affected"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the request"
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent / device fingerprint"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the action occurred"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (no PHI)"
    )
    
    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['visit_id', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
    
    def __str__(self):
        return f"{self.action} by {self.user} on {self.timestamp}"
    
    def save(self, *args, **kwargs):
        """Prevent updates - audit logs are append-only."""
        if self.pk:
            raise ValueError("Audit logs are append-only and cannot be modified.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Prevent deletion - audit logs are immutable."""
        raise ValueError("Audit logs cannot be deleted.")
    
    @classmethod
    def log(cls, user, role, action, visit_id, resource_type=None, resource_id=None, request=None, metadata=None):
        """
        Convenience class method to create audit log entries.
        
        Args:
            user: User performing the action
            role: Role of the user (string)
            action: Action type (e.g., 'LAB_ORDER_CREATED')
            visit_id: Visit ID (required for visit-scoped actions)
            resource_type: Resource type (e.g., 'lab_order')
            resource_id: Resource ID if applicable
            request: Django request object (for IP/user agent)
            metadata: Additional metadata dict (no PHI)
        
        Returns:
            AuditLog instance
        """
        ip_address = None
        user_agent = ''
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        audit_log = cls(
            user=user,
            user_role=role,
            action=action,
            visit_id=visit_id,
            resource_type=resource_type or 'unknown',
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        audit_log.save()
        return audit_log


def log_consultation_action(
    user,
    action,
    visit_id,
    consultation_id=None,
    request=None,
    metadata=None
):
    """
    Log a consultation action to audit log.
    
    Args:
        user: User performing the action
        action: Action type (e.g., 'create', 'update', 'read')
        visit_id: Visit ID (required)
        consultation_id: Consultation ID if applicable
        request: Django request object (for IP/user agent)
        metadata: Additional metadata dict (no PHI)
    
    Returns:
        AuditLog instance
    """
    # Get user role (assumes User model has role field or method)
    user_role = getattr(user, 'role', None) or getattr(user, 'get_role', lambda: 'UNKNOWN')()
    
    # Ensure user_role is a string (required by AuditLog model)
    if not user_role:
        user_role = 'UNKNOWN'
    
    # Extract IP and user agent from request
    ip_address = None
    user_agent = ''
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length
    
    audit_log = AuditLog(
        user=user,
        user_role=user_role,
        action=f'consultation.{action}',
        visit_id=visit_id,
        resource_type='consultation',
        resource_id=consultation_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )
    audit_log.save()
    return audit_log


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_nurse_action(
    user,
    action,
    visit_id,
    resource_type,
    resource_id=None,
    request=None,
    metadata=None
):
    """
    Log a Nurse action to audit log.
    
    Per NHIA/medico-legal requirements:
    - All Nurse actions must be auditable
    - Captures: user_id, role, visit_id, action, timestamp, IP/device
    - No PHI in metadata
    
    Args:
        user: User performing the action (must be Nurse)
        action: Action type (e.g., 'vital_signs.create', 'nursing_note.create')
        visit_id: Visit ID (required for visit-scoped actions)
        resource_type: Resource type (e.g., 'vital_signs', 'nursing_note', 'medication_administration', 'lab_sample_collection')
        resource_id: Resource ID if applicable
        request: Django request object (for IP/user agent)
        metadata: Additional metadata dict (NO PHI allowed)
    
    Returns:
        AuditLog instance
    
    Example:
        log_nurse_action(
            user=request.user,
            action='vital_signs.create',
            visit_id=visit.id,
            resource_type='vital_signs',
            resource_id=vital_signs.id,
            request=request,
            metadata={'systolic_bp': 120, 'diastolic_bp': 80}  # No PHI
        )
    """
    # Get user role (assumes User model has role field or method)
    user_role = getattr(user, 'role', None) or getattr(user, 'get_role', lambda: 'UNKNOWN')()
    
    # Ensure user_role is a string (required by AuditLog model)
    if not user_role:
        user_role = 'UNKNOWN'
    
    # Validate that user is a Nurse (for safety, but permission should already be checked)
    if user_role != 'NURSE':
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"log_nurse_action called for non-Nurse user: {user.username} (role: {user_role})")
    
    # Extract IP and user agent from request
    ip_address = None
    user_agent = ''
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]  # Limit length
    
    # Ensure metadata doesn't contain PHI
    safe_metadata = metadata or {}
    # Remove any potential PHI fields (patient names, addresses, etc.)
    phi_fields = ['patient_name', 'patient_id', 'first_name', 'last_name', 'address', 'phone', 'email', 'national_id']
    for field in phi_fields:
        safe_metadata.pop(field, None)
    
    audit_log = AuditLog(
        user=user,
        user_role=user_role,
        action=f'nurse.{action}',
        visit_id=visit_id,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=safe_metadata
    )
    audit_log.save()
    return audit_log
