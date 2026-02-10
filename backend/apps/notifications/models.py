"""
Email Notification models - for tracking email notifications sent.

Per EMR Rules:
- All notifications must be logged
- PHI data must be protected in emails
- Audit logging mandatory
"""
from django.db import models
from django.utils import timezone


class EmailNotification(models.Model):
    """
    Email Notification model - tracks email notifications sent.
    
    Design Principles:
    1. Tracks notification metadata (not email content)
    2. Links to related resources (appointments, results, etc.)
    3. Status tracking for delivery
    4. Audit logging mandatory
    """
    
    NOTIFICATION_TYPES = [
        ('APPOINTMENT_REMINDER', 'Appointment Reminder'),
        ('APPOINTMENT_CONFIRMED', 'Appointment Confirmed'),
        ('APPOINTMENT_CANCELLED', 'Appointment Cancelled'),
        ('LAB_RESULT_READY', 'Lab Result Ready'),
        ('RADIOLOGY_RESULT_READY', 'Radiology Result Ready'),
        ('PRESCRIPTION_READY', 'Prescription Ready'),
        ('PAYMENT_RECEIPT', 'Payment Receipt'),
        ('PATIENT_VERIFIED', 'Patient Account Verified'),
        ('SYSTEM_ALERT', 'System Alert'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
        ('BOUNCED', 'Bounced'),
    ]
    
    # Notification information
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        help_text="Type of notification"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Status of the notification"
    )
    
    # Recipient information
    recipient_email = models.EmailField(
        help_text="Email address of the recipient"
    )
    
    recipient_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of the recipient"
    )
    
    # Related resources (optional, for linking to appointments, results, etc.)
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_notifications',
        help_text="Related appointment (if applicable)"
    )
    
    visit = models.ForeignKey(
        'visits.Visit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_notifications',
        help_text="Related visit (if applicable)"
    )
    
    # Email metadata
    subject = models.CharField(
        max_length=500,
        help_text="Email subject"
    )
    
    email_body = models.TextField(
        help_text="Email body content (stored for audit)"
    )
    
    # Delivery information
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the email was sent"
    )
    
    error_message = models.TextField(
        blank=True,
        help_text="Error message if sending failed"
    )
    
    # User tracking
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_notifications_created',
        help_text="User who triggered this notification (if applicable)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the notification was created"
    )
    
    class Meta:
        db_table = 'email_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification_type']),
            models.Index(fields=['status']),
            models.Index(fields=['recipient_email']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = 'Email Notification'
        verbose_name_plural = 'Email Notifications'
    
    def __str__(self):
        return f"Email {self.id} - {self.notification_type} to {self.recipient_email} ({self.status})"


class AppointmentReminder(models.Model):
    """
    Tracks appointment reminders sent (e.g. WhatsApp).
    Auto-send: 24 hours and 2 hours before appointment.
    """
    CHANNEL_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('email', 'Email'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    ]
    
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        related_name='reminders',
        help_text="Appointment this reminder is for",
    )
    sent_at = models.DateTimeField(null=True, blank=True, help_text="When the reminder was sent")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Delivery status",
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        default='whatsapp',
        help_text="Channel used (whatsapp, sms, email)",
    )
    hours_before = models.IntegerField(
        null=True,
        blank=True,
        help_text="Reminder sent this many hours before appointment (e.g. 24 or 2)",
    )
    error_message = models.TextField(blank=True, help_text="Error if sending failed")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'appointment_reminders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['appointment']),
            models.Index(fields=['status']),
            models.Index(fields=['channel']),
        ]
        verbose_name = 'Appointment Reminder'
        verbose_name_plural = 'Appointment Reminders'
    
    def __str__(self):
        return f"Reminder #{self.id} – {self.appointment_id} ({self.channel}) {self.status}"
