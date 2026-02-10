"""
Django Admin for EmailNotification model.
"""
from django.contrib import admin
from .models import EmailNotification, AppointmentReminder


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    """Admin interface for EmailNotification model."""
    
    list_display = [
        'id',
        'notification_type',
        'status',
        'recipient_email',
        'recipient_name',
        'subject',
        'created_at',
        'sent_at',
    ]
    
    list_filter = [
        'notification_type',
        'status',
        'created_at',
        'sent_at',
    ]
    
    search_fields = [
        'id',
        'recipient_email',
        'recipient_name',
        'subject',
        'email_body',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'sent_at',
    ]
    
    fieldsets = (
        ('Notification Information', {
            'fields': (
                'id',
                'notification_type',
                'status',
            )
        }),
        ('Recipient Information', {
            'fields': (
                'recipient_email',
                'recipient_name',
            )
        }),
        ('Email Content', {
            'fields': (
                'subject',
                'email_body',
            )
        }),
        ('Related Resources', {
            'fields': (
                'appointment',
                'visit',
            )
        }),
        ('Delivery Information', {
            'fields': (
                'sent_at',
                'error_message',
            )
        }),
        ('Metadata', {
            'fields': (
                'created_by',
                'created_at',
            )
        }),
    )


@admin.register(AppointmentReminder)
class AppointmentReminderAdmin(admin.ModelAdmin):
    list_display = ['id', 'appointment', 'channel', 'hours_before', 'status', 'sent_at', 'created_at']
    list_filter = ['channel', 'status', 'hours_before']
    search_fields = ['appointment__id']
    readonly_fields = ['sent_at', 'created_at']
