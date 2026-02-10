"""
OTP Authentication Models

Passwordless authentication for patient portal.
- OTP-based login (email, SMS, WhatsApp)
- 6-digit codes
- 5-minute expiry
- Audit logging
"""
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from datetime import timedelta
import random
import string


class LoginOTP(models.Model):
    """
    OTP for passwordless login.
    
    Features:
    - 6-digit numeric code
    - Multiple channels (email, SMS, WhatsApp)
    - 5-minute expiry
    - Single use only
    - One active OTP per user
    """
    
    CHANNEL_CHOICES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('WHATSAPP', 'WhatsApp'),
    ]
    
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='login_otps',
        help_text="User this OTP is for"
    )
    
    otp_code = models.CharField(
        max_length=6,
        validators=[RegexValidator(r'^\d{6}$', 'OTP must be 6 digits')],
        help_text="6-digit OTP code"
    )
    
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        help_text="Channel OTP was sent through"
    )
    
    recipient = models.CharField(
        max_length=255,
        help_text="Email or phone number OTP was sent to"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When OTP was generated"
    )
    
    expires_at = models.DateTimeField(
        help_text="When OTP expires (5 minutes from creation)"
    )
    
    is_used = models.BooleanField(
        default=False,
        help_text="Whether OTP has been used"
    )
    
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When OTP was used"
    )
    
    # Security tracking
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address that requested OTP"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
    )
    
    class Meta:
        db_table = 'login_otps'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['otp_code']),
            models.Index(fields=['is_used']),
            models.Index(fields=['expires_at']),
        ]
        verbose_name = 'Login OTP'
        verbose_name_plural = 'Login OTPs'
    
    def __str__(self):
        return f"OTP for {self.user.username} via {self.channel} - {'Used' if self.is_used else 'Active'}"
    
    def is_valid(self):
        """Check if OTP is still valid (not expired, not used)."""
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True
    
    def mark_as_used(self):
        """Mark OTP as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
    
    @staticmethod
    def generate_otp_code():
        """Generate random 6-digit OTP code."""
        return ''.join(random.choices(string.digits, k=6))
    
    @classmethod
    def create_otp(cls, user, channel, recipient, ip_address=None, user_agent=''):
        """
        Create OTP for user.
        
        Invalidates any existing active OTPs for this user.
        """
        # Invalidate existing active OTPs for this user
        cls.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now()
        ).update(is_used=True)
        
        # Generate new OTP
        otp_code = cls.generate_otp_code()
        expires_at = timezone.now() + timedelta(minutes=5)
        
        otp = cls.objects.create(
            user=user,
            otp_code=otp_code,
            channel=channel,
            recipient=recipient,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return otp


class LoginAuditLog(models.Model):
    """
    Audit log for authentication events.
    
    Tracks:
    - Login attempts (success/failure)
    - OTP requests
    - Password resets
    - Account lockouts
    """
    
    ACTION_CHOICES = [
        ('OTP_REQUESTED', 'OTP Requested'),
        ('OTP_SENT', 'OTP Sent'),
        ('OTP_VERIFIED', 'OTP Verified'),
        ('OTP_FAILED', 'OTP Verification Failed'),
        ('LOGIN_SUCCESS', 'Login Success'),
        ('LOGIN_FAILED', 'Login Failed'),
        ('LOGOUT', 'Logout'),
        ('TOKEN_REFRESHED', 'Token Refreshed'),
        ('ACCOUNT_LOCKED', 'Account Locked'),
        ('ACCOUNT_UNLOCKED', 'Account Unlocked'),
        ('BIOMETRIC_REGISTERED', 'Biometric Registered'),
        ('BIOMETRIC_LOGIN_SUCCESS', 'Biometric Login Success'),
        ('BIOMETRIC_LOGIN_FAILED', 'Biometric Login Failed'),
    ]
    
    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='auth_audit_logs',
        help_text="User (null if login failed before user identified)"
    )
    
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text="Action that was performed"
    )
    
    identifier = models.CharField(
        max_length=255,
        blank=True,
        help_text="Email or phone used for login attempt"
    )
    
    success = models.BooleanField(
        default=True,
        help_text="Whether action was successful"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of request"
    )
    
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string"
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
        help_text="Device type"
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata"
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="When action occurred"
    )
    
    class Meta:
        db_table = 'login_audit_logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['ip_address']),
            models.Index(fields=['-timestamp']),
        ]
        verbose_name = 'Login Audit Log'
        verbose_name_plural = 'Login Audit Logs'
    
    def __str__(self):
        user_str = self.user.username if self.user else self.identifier
        return f"{self.action} by {user_str} at {self.timestamp}"
    
    @classmethod
    def log_action(cls, action, user=None, identifier='', ip_address=None,
                   user_agent='', device_type='unknown', success=True, **metadata):
        """Create audit log entry."""
        return cls.objects.create(
            user=user,
            action=action,
            identifier=identifier,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            device_type=device_type,
            metadata=metadata
        )
