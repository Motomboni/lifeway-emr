"""
Organization views for SaaS multi-tenancy.

Endpoints:
- GET /api/v1/organizations/ - List organizations user belongs to
- POST /api/v1/organizations/create/ - Create organization (admin only)
- GET /api/v1/organizations/me/ - Current organization (from request)
- POST /api/v1/organizations/{id}/set-default/ - Set default organization
"""

from django.conf import settings
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from core.permissions import IsPlatformAdmin
from rest_framework.response import Response

from .models import Organization, OrganizationUser, Plan, Subscription
from .serializers import (
    AddMemberSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
    OrganizationSignupSerializer,
    OrganizationUpdateSerializer,
    OrganizationUserSerializer,
    PlanSerializer,
    SubscriptionSerializer,
)
from .utils import check_user_limit


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Organization - list organizations user belongs to.
    """

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
        """Return user's organization memberships (for tenant switcher)."""
        memberships = (
            OrganizationUser.objects.filter(user=request.user)
            .select_related("organization")
            .order_by("-is_default", "organization__name")
        )
        serializer = OrganizationUserSerializer(memberships, many=True)
        return Response(serializer.data)

    @action(
        detail=False, methods=["post"], url_path="signup", permission_classes=[AllowAny]
    )
    def signup(self, request):
        """
        Self-serve organization signup (public).
        Creates org + owner user + Starter subscription.
        Only available when ENABLE_ORG_SIGNUP=true.
        """
        if not getattr(settings, "ENABLE_ORG_SIGNUP", False):
            return Response(
                {"detail": "Organization signup is not enabled."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = OrganizationSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        return Response(
            {
                "organization": OrganizationSerializer(result["organization"]).data,
                "user": {
                    "id": result["user"].id,
                    "username": result["user"].username,
                    "first_name": result["user"].first_name,
                    "last_name": result["user"].last_name,
                },
                "message": "Organization created. You can now log in.",
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="create",
        permission_classes=[IsAuthenticated, IsPlatformAdmin],
    )
    def create_organization(self, request):
        """
        Create a new organization (admin only).
        Creates org + Starter plan subscription + adds request user as OWNER.
        """
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = serializer.save(is_active=True)
        # Create subscription with Starter plan
        plan = Plan.objects.filter(slug="starter").first()
        if plan:
            Subscription.objects.get_or_create(
                organization=org, defaults={"plan": plan, "status": "ACTIVE"}
            )
        # Add creator as OWNER
        OrganizationUser.objects.create(
            organization=org, user=request.user, role="OWNER", is_default=False
        )
        return Response(
            OrganizationSerializer(org).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        """
        GET: List members of this organization.
        POST: Add a member (user_id, role). Enforces max_users plan limit.
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

        # POST: Add member
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
                        "Ask them to register at /register → Join existing Clinic first."
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
                f"You've been added to {org.name} on Damianix EMR",
                (
                    f"Hello {user.first_name or user.username},\n\n"
                    f"You have been added to {org.name} as {role}.\n"
                    f"Sign in at {base}/login and select your clinic from the tenant switcher.\n\n"
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
        # Unset other defaults
        OrganizationUser.objects.filter(user=request.user).update(is_default=False)
        membership.is_default = True
        membership.save()
        return Response({"detail": "Default organization updated."})


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Plan - list available subscription plans."""

    queryset = Plan.objects.filter(is_active=True).order_by(
        "sort_order", "price_monthly"
    )
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Subscription - view current org's subscription."""

    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        org = getattr(self.request, "organization", None)
        if not org:
            return Subscription.objects.none()
        return Subscription.objects.filter(organization=org)

    @action(detail=False, methods=["get"], url_path="status")
    def status(self, request):
        """Get subscription status with usage and limits."""
        from .billing_service import get_subscription_status

        org = getattr(request, "organization", None)
        if not org:
            return Response(
                {"detail": "No organization selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = get_subscription_status(org)
        return Response(data)

    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        """
        Initialize Paystack / Flutterwave checkout for plan upgrade.
        Body: { "plan_slug": "professional", "success_url": "...", "cancel_url": "..." }
        Returns: { "checkout_url": "..." } (authorization / payment link).
        """
        from django.conf import settings

        from .billing_service import create_checkout_session

        org = getattr(request, "organization", None)
        if not org:
            return Response(
                {"detail": "No organization selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan_slug = request.data.get("plan_slug")
        success_url = request.data.get("success_url")
        cancel_url = request.data.get("cancel_url")

        if not plan_slug:
            return Response(
                {"detail": "plan_slug is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not success_url or not cancel_url:
            return Response(
                {"detail": "success_url and cancel_url are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        checkout_url = create_checkout_session(
            org, plan_slug, success_url, cancel_url
        )
        if not checkout_url:
            provider = getattr(settings, "SAAS_PAYMENT_PROVIDER", "paystack")
            return Response(
                {
                    "detail": (
                        f"{provider.title()} checkout is not configured or plan has no price. "
                        "Set PAYSTACK_SECRET_KEY (or FLUTTERWAVE_SECRET_KEY) in environment."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"checkout_url": checkout_url})

    @action(detail=False, methods=["post"], url_path="verify-payment")
    def verify_payment(self, request):
        """
        Verify SaaS subscription payment after Paystack/Flutterwave redirect.
        Body: { "reference": "SAAS-..." }
        """
        from django.core.exceptions import ValidationError as DjangoValidationError

        from .saas_payment_handlers import verify_and_activate_subscription

        org = getattr(request, "organization", None)
        if not org:
            return Response(
                {"detail": "No organization selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reference = request.data.get("reference") or request.query_params.get(
            "reference"
        )
        if not reference:
            return Response(
                {"detail": "reference is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment = verify_and_activate_subscription(reference)
        except DjangoValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment.organization_id != org.id:
            return Response(
                {"detail": "Payment does not belong to this organization."},
                status=status.HTTP_403_FORBIDDEN,
            )

        from .billing_service import get_subscription_status

        return Response(
            {
                "detail": "Payment verified. Subscription updated.",
                "subscription": get_subscription_status(org),
            }
        )

    @action(detail=False, methods=["post"], url_path="portal")
    def portal(self, request):
        """
        Billing self-service portal (Stripe only when SAAS_PAYMENT_PROVIDER=stripe).
        """
        from .billing_service import create_billing_portal_session

        org = getattr(request, "organization", None)
        if not org:
            return Response(
                {"detail": "No organization selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return_url = request.data.get("return_url")
        if not return_url:
            return Response(
                {"detail": "return_url is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        portal_url = create_billing_portal_session(org, return_url)
        if not portal_url:
            return Response(
                {
                    "detail": (
                        "Online billing portal is not available for Paystack/Flutterwave. "
                        "Upgrade plans from this page or contact support."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"portal_url": portal_url})

    @action(detail=False, methods=["post"], url_path="cancel-auto-renew")
    def cancel_auto_renew(self, request):
        """Disable Paystack auto-renewal for the current organization's subscription."""
        from django.core.exceptions import ValidationError as DjangoValidationError

        from .billing_service import get_subscription_status
        from .paystack_subscription_service import PaystackSaasService

        org = getattr(request, "organization", None)
        if not org:
            return Response(
                {"detail": "No organization selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sub = org.subscription
        except Exception:
            return Response(
                {"detail": "No active subscription."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not sub.auto_renew_enabled:
            return Response(
                {"detail": "Auto-renew is not enabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if sub.paystack_subscription_code and sub.paystack_email_token:
            try:
                PaystackSaasService().disable_subscription(
                    sub.paystack_subscription_code,
                    sub.paystack_email_token,
                )
            except DjangoValidationError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        sub.auto_renew_enabled = False
        sub.cancel_at_period_end = True
        sub.save(
            update_fields=["auto_renew_enabled", "cancel_at_period_end", "updated_at"]
        )

        return Response(
            {
                "detail": "Auto-renew disabled. Your plan remains active until period end.",
                "subscription": get_subscription_status(org),
            }
        )

    @action(detail=False, methods=["get"], url_path="invoices")
    def invoices(self, request):
        """Recent SaaS subscription payments (Paystack/Flutterwave) or Stripe invoices."""
        from .billing_service import get_billing_invoices

        org = getattr(request, "organization", None)
        if not org:
            return Response(
                {"detail": "No organization selected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(get_billing_invoices(org))
