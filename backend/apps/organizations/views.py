"""
Organization views — single-clinic Lifeway (memberships and clinic settings).

Endpoints:
- GET /api/v1/organizations/ - List organizations user belongs to
- GET /api/v1/organizations/me/ - Current organization (from request)
- GET /api/v1/organizations/memberships/ - User's clinic memberships
- PATCH /api/v1/organizations/{id}/settings/ - Update clinic branding
"""

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Organization, OrganizationUser
from .serializers import (
    AddMemberSerializer,
    OrganizationSerializer,
    OrganizationUpdateSerializer,
    OrganizationUserSerializer,
)
from .utils import check_user_limit


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """Clinic organization — list, settings, and staff membership."""

    allow_no_organization = True
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return only organizations the user is a member of."""
        return Organization.objects.filter(
            members__user=self.request.user, is_active=True
        ).distinct()

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Return current organization from request.organization."""
        org = getattr(request, "organization", None)
        if not org:
            return Response(
                {
                    "detail": "No organization selected. Set X-Organization-Id or X-Organization-Slug header."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = OrganizationSerializer(org)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def memberships(self, request):
        """Return user's organization memberships."""
        memberships = (
            OrganizationUser.objects.filter(user=request.user)
            .select_related("organization")
            .order_by("-is_default", "organization__name")
        )
        serializer = OrganizationUserSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        """
        GET: List members of this organization.
        POST: Add a member (user_id, role).
        """
        org = self.get_object()
        membership = OrganizationUser.objects.filter(
            organization=org, user=request.user
        ).first()
        if not membership:
            return Response(
                {"detail": "You are not a member of this organization."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if membership.role not in ("OWNER", "ADMIN"):
            return Response(
                {"detail": "Only owners and admins can manage members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == "GET":
            memberships = (
                OrganizationUser.objects.filter(organization=org)
                .select_related("user")
                .order_by("-role", "user__first_name")
            )
            data = [
                {
                    "id": m.id,
                    "user_id": m.user_id,
                    "username": m.user.username,
                    "first_name": m.user.first_name,
                    "last_name": m.user.last_name,
                    "role": m.role,
                    "is_default": m.is_default,
                }
                for m in memberships
            ]
            return Response(data)

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]

        from django.contrib.auth import get_user_model

        User = get_user_model()
        user_id = serializer.validated_data.get("user_id")
        email = serializer.validated_data.get("email")
        try:
            if user_id:
                user = User.objects.get(pk=user_id)
            else:
                user = User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            return Response(
                {
                    "detail": (
                        "No staff account found with that email. "
                        "Ask them to register at /register first."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if OrganizationUser.objects.filter(organization=org, user=user).exists():
            return Response(
                {"detail": "User is already a member of this organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            check_user_limit(org)
        except Exception as e:
            detail = getattr(e, "detail", str(e))
            if isinstance(detail, list):
                detail = " ".join(str(d) for d in detail)
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        OrganizationUser.objects.create(
            organization=org, user=user, role=role, is_default=False
        )

        from core.notifications import send_transactional_email

        base = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        if user.email:
            send_transactional_email(
                user.email,
                f"You've been added to {org.name} on {settings.CLINIC_NAME}",
                (
                    f"Hello {user.first_name or user.username},\n\n"
                    f"You have been added to {org.name} as {role}.\n"
                    f"Sign in at {base}/login\n\n"
                    f"— {org.name}"
                ),
            )

        return Response(
            {"detail": f"User {user.username} added to organization."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"], url_path="settings")
    def update_settings(self, request, pk=None):
        """Update clinic branding and contact (OWNER/ADMIN of this org)."""
        org = self.get_object()
        membership = OrganizationUser.objects.filter(
            organization=org, user=request.user
        ).first()
        if not membership or membership.role not in ("OWNER", "ADMIN"):
            return Response(
                {"detail": "Only owners and admins can update clinic settings."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = OrganizationUpdateSerializer(
            org, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrganizationSerializer(org).data)

    @action(detail=True, methods=["post"], url_path="set-default")
    def set_default(self, request, pk=None):
        """Set this organization as the user's default."""
        org = self.get_object()
        membership = OrganizationUser.objects.filter(
            organization=org, user=request.user
        ).first()
        if not membership:
            return Response(
                {"detail": "You are not a member of this organization."},
                status=status.HTTP_403_FORBIDDEN,
            )
        OrganizationUser.objects.filter(user=request.user).update(is_default=False)
        membership.is_default = True
        membership.save()
        return Response({"detail": "Default organization updated."})
