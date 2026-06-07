"""
Patient Permissions - Receptionist can register and search.

Per EMR Rules:
- Receptionist: Can register patients, search patients
- Other roles: Can view patient data (for clinical context)
- All patient data is PHI - must be protected
"""

from rest_framework import permissions


class CanRegisterPatient(permissions.BasePermission):
    """
    Permission: Receptionist and Admin can register new patients.
    """

    def has_permission(self, request, view):
        """Check if user is a receptionist or admin."""
        if not request.user or not request.user.is_authenticated:
            return False

        user_role = getattr(request.user, "role", None)
        if not user_role:
            user_role = getattr(request.user, "get_role", lambda: None)()

        return user_role in ["RECEPTIONIST", "ADMIN"]


class CanSearchPatient(permissions.BasePermission):
    """
    Permission: Receptionist, Admin, and clinical staff can search patients.
    Patients cannot access staff patient search/list endpoints.
    """

    STAFF_ROLES = [
        "RECEPTIONIST",
        "ADMIN",
        "DOCTOR",
        "NURSE",
        "LAB_TECH",
        "RADIOLOGY_TECH",
        "PHARMACIST",
        "IVF_SPECIALIST",
        "EMBRYOLOGIST",
    ]

    def has_permission(self, request, view):
        """Check if user can search patients."""
        if not request.user or not request.user.is_authenticated:
            return False

        user_role = getattr(request.user, "role", None)
        if not user_role:
            user_role = getattr(request.user, "get_role", lambda: None)()

        if user_role == "PATIENT":
            return False

        if getattr(request.user, "is_superuser", False):
            return True

        return user_role in self.STAFF_ROLES


class CanViewPatient(permissions.BasePermission):
    """Staff can retrieve individual patient records; patients use the portal."""

    def has_permission(self, request, view):
        return CanSearchPatient().has_permission(request, view)


class CanManagePatients(permissions.BasePermission):
    """
    Permission: Receptionist and Admin can manage patients (register, bulk operations).
    """

    def has_permission(self, request, view):
        """Check if user is a receptionist or admin."""
        if not request.user or not request.user.is_authenticated:
            return False

        user_role = getattr(request.user, "role", None)
        if not user_role:
            user_role = getattr(request.user, "get_role", lambda: None)()

        return user_role in ["RECEPTIONIST", "ADMIN"]


class CanDeletePatient(permissions.BasePermission):
    """
    Permission: Admin, Receptionist, or Superuser can archive/delete patients.
    Per EMR rules: soft-delete only (is_active=False).
    """

    def has_permission(self, request, view):
        """Check if user can delete (archive) patients."""
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        user_role = getattr(request.user, "role", None)
        return user_role in ["RECEPTIONIST", "ADMIN"]
