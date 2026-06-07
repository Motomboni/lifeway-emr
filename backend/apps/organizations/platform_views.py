"""
Platform super-admin API — cross-tenant metrics and organization management.

Restricted to Django superusers (platform operators, not clinic admins).
"""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients.models import Patient
from core.tenant import is_platform_superuser

from .models import Organization, OrganizationUser, SaasSubscriptionPayment, Subscription


class IsPlatformSuperuser:
    """DRF permission: Django superuser only."""

    def has_permission(self, request, view):
        return is_platform_superuser(request)


class PlatformOverviewView(APIView):
    """
    GET /api/v1/platform/overview/

    Cross-tenant SaaS metrics: organizations, MRR estimate, usage.
    """

    permission_classes = [IsAuthenticated, IsPlatformSuperuser]

    def get(self, request):
        now = timezone.now()
        orgs = Organization.objects.filter(is_active=True)
        total_orgs = orgs.count()

        active_subs = Subscription.objects.filter(
            status__in=["ACTIVE", "TRIAL"],
            organization__is_active=True,
        ).select_related("plan", "organization")

        mrr = Decimal("0")
        for sub in active_subs:
            if sub.status == "ACTIVE" and sub.plan.price_monthly:
                mrr += sub.plan.price_monthly

        total_patients = Patient.objects.count()
        total_users = OrganizationUser.objects.count()

        thirty_days_ago = now - timedelta(days=30)
        recent_payments = SaasSubscriptionPayment.objects.filter(
            status="VERIFIED",
            verified_at__gte=thirty_days_ago,
        )
        revenue_30d = recent_payments.aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0")

        plan_breakdown = (
            Subscription.objects.filter(
                status__in=["ACTIVE", "TRIAL"],
                organization__is_active=True,
            )
            .values("plan__name", "plan__slug")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        expiring_soon = Subscription.objects.filter(
            status="ACTIVE",
            current_period_end__lte=now + timedelta(days=7),
            current_period_end__gte=now,
            organization__is_active=True,
        ).select_related("organization", "plan")[:20]

        return Response(
            {
                "generated_at": now.isoformat(),
                "totals": {
                    "organizations": total_orgs,
                    "active_subscriptions": active_subs.filter(status="ACTIVE").count(),
                    "trial_subscriptions": active_subs.filter(status="TRIAL").count(),
                    "patients": total_patients,
                    "staff_memberships": total_users,
                    "mrr_ngn": str(mrr),
                    "revenue_30d_ngn": str(revenue_30d),
                },
                "plan_breakdown": list(plan_breakdown),
                "expiring_soon": [
                    {
                        "organization_id": s.organization_id,
                        "organization_name": s.organization.name,
                        "organization_slug": s.organization.slug,
                        "plan": s.plan.name,
                        "current_period_end": s.current_period_end.isoformat()
                        if s.current_period_end
                        else None,
                        "auto_renew_enabled": s.auto_renew_enabled,
                    }
                    for s in expiring_soon
                ],
            }
        )


class PlatformOrganizationsView(APIView):
    """
    GET /api/v1/platform/organizations/

    List all tenants with subscription and usage summary.
    """

    permission_classes = [IsAuthenticated, IsPlatformSuperuser]

    def get(self, request):
        orgs = Organization.objects.filter(is_active=True).order_by("name")

        results = []
        for org in orgs:
            try:
                sub = org.subscription
                plan_name = sub.plan.name
                plan_slug = sub.plan.slug
                sub_status = sub.status
                period_end = (
                    sub.current_period_end.isoformat()
                    if sub.current_period_end
                    else None
                )
                auto_renew = sub.auto_renew_enabled
            except Subscription.DoesNotExist:
                plan_name = None
                plan_slug = None
                sub_status = "NONE"
                period_end = None
                auto_renew = False

            patient_count = Patient.objects.filter(organization=org).count()
            user_count = OrganizationUser.objects.filter(organization=org).count()

            results.append(
                {
                    "id": org.id,
                    "name": org.name,
                    "slug": org.slug,
                    "email": org.email,
                    "created_at": org.created_at.isoformat(),
                    "subscription_status": sub_status,
                    "plan_name": plan_name,
                    "plan_slug": plan_slug,
                    "current_period_end": period_end,
                    "auto_renew_enabled": auto_renew,
                    "patients": patient_count,
                    "users": user_count,
                }
            )

        return Response({"count": len(results), "organizations": results})
