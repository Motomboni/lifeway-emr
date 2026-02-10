"""
Email Notification ViewSet.

Endpoint: /api/v1/notifications/

Enforcement:
1. Authenticated users can view their own notifications
2. Superusers can view all notifications
3. Read-only access (notifications are created by system)
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import EmailNotification
from .serializers import EmailNotificationSerializer


class EmailNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Email Notifications - read-only.
    
    Rules enforced:
    - Authenticated users can view notifications
    - Users see notifications related to their appointments/visits
    - Superusers see all notifications
    """
    
    serializer_class = EmailNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter notifications based on user role."""
        user = self.request.user
        
        # Superusers see all notifications
        if user.is_superuser:
            return EmailNotification.objects.all().select_related(
                'appointment',
                'visit',
                'created_by'
            )
        
        # Regular users see notifications related to their appointments/visits
        # This is a simplified implementation - in production, you'd want
        # more sophisticated filtering based on user role and relationships
        queryset = EmailNotification.objects.none()
        
        # If user is a doctor, show notifications for their appointments
        if hasattr(user, 'role') and user.role == 'DOCTOR':
            queryset = EmailNotification.objects.filter(
                Q(appointment__doctor=user) | Q(visit__doctor=user)
            )
        
        # If user is a patient (if you have patient users), show their notifications
        # For now, we'll return empty as patients don't have user accounts
        
        return queryset.select_related(
            'appointment',
            'visit',
            'created_by'
        ).order_by('-created_at')
