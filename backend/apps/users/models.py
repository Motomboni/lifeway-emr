"""
User model for EMR system.

Per EMR Rules:
- Strong authentication (JWT, password hashing)
- Role-based access control (RBAC)
- Account lockout after repeated failures
"""
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class CustomUserManager(UserManager):
    """Custom UserManager that handles role field in create_superuser."""
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Create and save a superuser with role field."""
        # Set role to ADMIN if not provided
        if 'role' not in extra_fields:
            extra_fields['role'] = 'ADMIN'
        
        # Ensure is_staff and is_superuser are True
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model with role-based access control.
    
    Roles:
    - DOCTOR: Can create consultations, orders, prescriptions
    - NURSE: Can assist with patient care and clinical tasks
    - LAB_TECH: Can post lab results only
    - RADIOLOGY_TECH: Can post radiology results only
    - PHARMACIST: Can dispense prescriptions only
    - RECEPTIONIST: Can register patients, process payments only
    - PATIENT: Can view own medical records and appointments
    """
    
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('DOCTOR', 'Doctor'),
        ('NURSE', 'Nurse'),
        ('LAB_TECH', 'Lab Technician'),
        ('RADIOLOGY_TECH', 'Radiology Technician'),
        ('PHARMACIST', 'Pharmacist'),
        ('RECEPTIONIST', 'Receptionist'),
        ('PATIENT', 'Patient'),
        # IVF Module Roles
        ('IVF_SPECIALIST', 'IVF Specialist'),
        ('EMBRYOLOGIST', 'Embryologist'),
    ]
    
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='DOCTOR',  # Default role, but should be set explicitly for superusers
        blank=False,  # Required field
        help_text="User role for RBAC enforcement"
    )
    
    # Patient Portal Link (for PATIENT role users)
    patient = models.OneToOneField(
        'patients.Patient',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='portal_user',
        help_text="Linked patient record (only for PATIENT role users)"
    )
    
    # Mobile/Device tracking
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Phone number for SMS/WhatsApp OTP"
    )
    
    portal_enabled = models.BooleanField(
        default=False,
        help_text="Whether user has portal access enabled"
    )
    
    last_login_device = models.CharField(
        max_length=255,
        blank=True,
        help_text="Last device used for login"
    )
    
    device_type = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('web', 'Web'),
            ('ios', 'iOS'),
            ('android', 'Android'),
            ('unknown', 'Unknown'),
        ],
        help_text="Type of device last used"
    )
    
    # Account lockout fields
    failed_login_attempts = models.IntegerField(
        default=0,
        help_text="Number of consecutive failed login attempts"
    )
    
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Account locked until this time (null if not locked)"
    )
    
    last_login_attempt = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last login attempt"
    )
    
    # Biometric authentication (device secure enclave; no raw biometric data stored)
    biometric_enabled = models.BooleanField(
        default=False,
        help_text="Whether biometric login is enabled for this user"
    )
    biometric_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Public key or secure token reference for biometric validation (not raw biometric data)"
    )
    device_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Device identifier for biometric / session tracking"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Use custom manager
    objects = CustomUserManager()
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['username']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    def get_role(self):
        """Get user role (for compatibility with permission checks)."""
        return self.role
    
    def is_locked(self):
        """Check if account is currently locked."""
        if not self.locked_until:
            return False
        return timezone.now() < self.locked_until
    
    def lock_account(self, duration_minutes=30):
        """Lock account for specified duration."""
        self.locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
        self.save(update_fields=['locked_until'])
    
    def unlock_account(self):
        """Unlock account and reset failed attempts."""
        self.locked_until = None
        self.failed_login_attempts = 0
        self.save(update_fields=['locked_until', 'failed_login_attempts'])
    
    def record_failed_login(self):
        """Record a failed login attempt and lock if threshold reached."""
        self.failed_login_attempts += 1
        self.last_login_attempt = timezone.now()
        
        # Lock after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.lock_account(duration_minutes=30)
        
        self.save(update_fields=['failed_login_attempts', 'last_login_attempt', 'locked_until'])
    
    def record_successful_login(self):
        """Reset failed login attempts on successful login."""
        self.failed_login_attempts = 0
        self.last_login_attempt = timezone.now()
        self.save(update_fields=['failed_login_attempts', 'last_login_attempt'])
    
    def clean(self):
        """Validate user data."""
        # Only validate role if it's set and not empty
        if hasattr(self, 'role') and self.role:
            valid_roles = [choice[0] for choice in self.ROLE_CHOICES]
            if self.role not in valid_roles:
                raise ValidationError(f"Invalid role: {self.role}. Valid roles are: {', '.join(valid_roles)}")
        
        # Validate patient portal relationship (only for existing users; new PATIENT gets patient in RegisterSerializer.create)
        if self.role == 'PATIENT' and not self.patient and self.pk is not None:
            raise ValidationError("PATIENT role users must be linked to a patient record")
        
        if self.role != 'PATIENT' and self.patient:
            raise ValidationError("Only PATIENT role users can be linked to a patient record")
        
        # PATIENT role: username not required (OTP-based login)
        # Non-PATIENT roles: username required
        if self.role != 'PATIENT' and not self.username:
            raise ValidationError("Username is required for non-PATIENT users")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        # Only run full_clean if not using update_fields
        # When using update_fields, Django handles validation differently
        if 'update_fields' not in kwargs:
            self.full_clean()
        super().save(*args, **kwargs)
