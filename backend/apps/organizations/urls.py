"""
Organization URLs for SaaS multi-tenancy.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .flutterwave_webhook_views import flutterwave_webhook
from .views import OrganizationViewSet, PlanViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register(r"organizations", OrganizationViewSet, basename="organization")
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscription")

urlpatterns = [
    path("subscriptions/stripe/webhook/", include("apps.organizations.stripe_urls")),
    path(
        "subscriptions/flutterwave/webhook/",
        flutterwave_webhook,
        name="flutterwave-saas-webhook",
    ),
    path("", include(router.urls)),
]
