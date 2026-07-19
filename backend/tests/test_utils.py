"""Shared helpers for pytest and Django TestCase suites."""


def get_or_create_test_org():
    """Return the standard test organization used across the suite."""
    from apps.organizations.models import Organization, Plan, Subscription

    org, _ = Organization.objects.get_or_create(
        slug="test-clinic",
        defaults={"name": "Test Clinic"},
    )
    plan, _ = Plan.objects.get_or_create(
        slug="starter",
        defaults={
            "name": "Starter",
            "price_monthly": 0,
            "max_users": 100,
            "max_patients": 1000,
        },
    )
    Subscription.objects.get_or_create(
        organization=org,
        defaults={"plan": plan, "status": "ACTIVE"},
    )
    return org
