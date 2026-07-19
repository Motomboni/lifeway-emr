"""
Telemedicine Permissions.

Per EMR Rules:
- Doctor: Can create and manage telemedicine sessions
- Patient / invited staff: Join via visit / invite context
- All sessions must be visit-scoped
"""

from rest_framework import permissions

from .access import user_can_join_session, user_can_view_session


class CanManageTelemedicine(permissions.BasePermission):
    """
    Permission: Only Doctors can create and manage telemedicine sessions.
    """

    def has_permission(self, request, view):
        """Check if user is a doctor."""
        if not request.user or not request.user.is_authenticated:
            return False

        user_role = getattr(request.user, "role", None)
        if not user_role:
            user_role = getattr(request.user, "get_role", lambda: None)()

        return user_role == "DOCTOR"


class CanManageTelemedicinePricing(permissions.BasePermission):
    """Admin (or staff) can set telemedicine consultation price."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, "is_staff", False) or getattr(
            request.user, "is_superuser", False
        ):
            return True
        user_role = getattr(request.user, "role", None)
        if not user_role:
            user_role = getattr(request.user, "get_role", lambda: None)()
        return user_role == "ADMIN"


class CanJoinTelemedicineSession(permissions.BasePermission):
    """
    Permission: Host doctor, patient, or actively invited staff can join.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if view.action in ("get_recording",):
            return user_can_view_session(request.user, obj)
        return user_can_join_session(request.user, obj)
