"""
API views for Timeline Events.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .timeline_models import TimelineEvent
from .timeline_serializers import TimelineEventSerializer
from .models import Visit


class TimelineEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for Timeline Events.
    
    Timeline events are immutable and can only be viewed, not created, edited, or deleted.
    """
    serializer_class = TimelineEventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get timeline events for a specific visit."""
        visit_id = self.kwargs.get('visit_id')
        if visit_id:
            visit = get_object_or_404(Visit, pk=visit_id)
            # Check if user has access to this visit
            # For now, allow any authenticated user (can be restricted later)
            return TimelineEvent.objects.filter(visit=visit).select_related('actor', 'visit').order_by('timestamp')
        return TimelineEvent.objects.none()
    
    def list(self, request, visit_id=None):
        """List all timeline events for a visit."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None, visit_id=None):
        """Retrieve a specific timeline event."""
        queryset = self.get_queryset()
        event = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(event)
        return Response(serializer.data)

