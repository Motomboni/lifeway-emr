"""
Email Notification Serializers.
"""
from rest_framework import serializers
from .models import EmailNotification


class EmailNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for EmailNotification.
    """
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = EmailNotification
        fields = [
            'id',
            'notification_type',
            'status',
            'recipient_email',
            'recipient_name',
            'appointment',
            'visit',
            'subject',
            'sent_at',
            'error_message',
            'created_by',
            'created_by_name',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'sent_at',
            'error_message',
            'created_by',
            'created_by_name',
            'created_at',
        ]
    
    def get_created_by_name(self, obj):
        """Get created by user's full name."""
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return None
