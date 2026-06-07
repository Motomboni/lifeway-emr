"""
Email Notification ViewSet.

Endpoint: /api/v1/notifications/

Enforcement:
1. Authenticated users can view their own notifications
2. Superusers can view all notifications
3. Read-only access (notifications are created by system)
"""

from django.db.models import Q
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from core.tenant import get_request_organization

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

    def _scope_by_organization(self, queryset):
        org = get_request_organization(self.request)
        if org:
            return queryset.filter(
                Q(visit__organization=org)
                | Q(appointment__patient__organization=org)
            )
        return queryset

    def get_queryset(self):
        """Filter notifications based on user role and organization."""
        user = self.request.user
        base = EmailNotification.objects.select_related(
            "appointment", "visit", "created_by"
        )

        if user.is_superuser:
            return self._scope_by_organization(base).order_by("-created_at")

        queryset = EmailNotification.objects.none()
        if hasattr(user, "role") and user.role == "DOCTOR":
            queryset = EmailNotification.objects.filter(
                Q(appointment__doctor=user) | Q(visit__doctor=user)
            )

        return self._scope_by_organization(queryset).order_by("-created_at")
