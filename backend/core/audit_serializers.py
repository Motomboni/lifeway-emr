"""
Audit Log Serializers - read-only serialization.
"""
from rest_framework import serializers
from .audit import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for Audit Log (read-only).
    """
    
    user_name = serializers.SerializerMethodField()
    user_email = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditLog
        fields = [
            'id',
            'user',
            'user_name',
            'user_email',
            'user_role',
            'action',
            'visit_id',
            'resource_type',
            'resource_id',
            'ip_address',
            'user_agent',
            'timestamp',
            'metadata',
        ]
        read_only_fields = fields
    
    def get_user_name(self, obj):
        """Get user's full name."""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return None
    
    def get_user_email(self, obj):
        """Get user's email (if available)."""
        if obj.user:
            return getattr(obj.user, 'email', None)
        return None
