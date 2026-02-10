"""
Serializers for Timeline Events.
"""
from rest_framework import serializers
from .timeline_models import TimelineEvent


class TimelineEventSerializer(serializers.ModelSerializer):
    """Serializer for TimelineEvent."""
    
    event_type_display = serializers.CharField(
        source='get_event_type_display',
        read_only=True
    )
    
    actor_name = serializers.SerializerMethodField()
    source_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TimelineEvent
        fields = [
            'id',
            'event_type',
            'event_type_display',
            'timestamp',
            'actor',
            'actor_name',
            'actor_role',
            'description',
            'source_type',
            'source_id',
            'source_url',
            'metadata',
        ]
        read_only_fields = fields
    
    def get_actor_name(self, obj):
        """Get actor's full name."""
        if obj.actor:
            return obj.actor.get_full_name()
        return None
    
    def get_source_url(self, obj):
        """Get URL to source object."""
        return obj.get_source_url()

