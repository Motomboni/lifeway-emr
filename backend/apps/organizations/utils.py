"""
Organization utilities — optional plan limits (disabled for Lifeway single-clinic).
"""

from django.conf import settings
from rest_framework.exceptions import ValidationError


def _plan_limits_enforced() -> bool:
    """Off for Lifeway single-clinic; enable via ENFORCE_PLAN_LIMITS if needed."""
    return getattr(settings, "ENFORCE_PLAN_LIMITS", False)


def get_subscription_for_org(organization):
    """
    Get active subscription for organization.
    Returns None if no subscription or subscription is inactive.
    """
    from .models import Subscription

    try:
        sub = organization.subscription
        if sub and sub.is_active():
            return sub
    except Subscription.DoesNotExist:
        pass
    return None


def check_patient_limit(organization):
    """
    Raise ValidationError if organization has reached max_patients limit.
    Call before creating a new patient.
    """
    if not _plan_limits_enforced():
        return

    from apps.patients.models import Patient

    from .models import Subscription

    try:
        sub = organization.subscription
        if not sub or not sub.is_active():
            return  # No active subscription = no limit
        plan = sub.plan
        if plan.max_patients is None:
            return  # Unlimited
        current = Patient.objects.filter(organization=organization).count()
        if current >= plan.max_patients:
            raise ValidationError(
                f"Patient limit reached ({plan.max_patients}). "
                f"Upgrade your plan to add more patients."
            )
    except Subscription.DoesNotExist:
        pass


def check_user_limit(organization):
    """
    Raise ValidationError if organization has reached max_users limit.
    Call before adding a new OrganizationUser (staff member).
    """
    if not _plan_limits_enforced():
        return

    from .models import OrganizationUser, Subscription

    try:
        sub = organization.subscription
        if not sub or not sub.is_active():
            return
        plan = sub.plan
        if plan.max_users is None:
            return
        current = OrganizationUser.objects.filter(organization=organization).count()
        if current >= plan.max_users:
            raise ValidationError(
                f"User limit reached ({plan.max_users}). "
                f"Upgrade your plan to add more staff."
            )
    except Subscription.DoesNotExist:
        pass


def get_default_clinic_organization():
    """
    Return the active clinic organization for single-clinic (Lifeway) deployments.

    Public registration and other unauthenticated flows use this instead of
    request-scoped tenant headers, which are only relevant for multi-tenant SaaS.
    """
    from apps.organizations.models import Organization

    return Organization.objects.filter(is_active=True).order_by("pk").first()


def _resolve_organization_arg(organization):
    """
    Return a concrete Organization instance or None.

    Middleware sets request.organization as SimpleLazyObject; passing that
    directly into ORM filters raises TypeError when it wraps None.
    """
    if organization is None:
        return None
    try:
        pk = getattr(organization, "pk", None)
    except Exception:
        return None
    if not pk:
        return None
    return organization


def ensure_staff_organization_membership(user, organization=None, role=None):
    """
    Ensure a staff user belongs to a clinic organization for tenant-scoped API access.
    Uses the given organization, or the first active organization in single-clinic setups.
    """
    from apps.organizations.models import Organization, OrganizationUser

    staff_roles = {
        "ADMIN",
        "DOCTOR",
        "NURSE",
        "LAB_TECH",
        "RADIOLOGY_TECH",
        "PHARMACIST",
        "RECEPTIONIST",
        "IVF_SPECIALIST",
        "EMBRYOLOGIST",
    }
    user_role = getattr(user, "role", None)
    if user_role not in staff_roles:
        return None

    organization = _resolve_organization_arg(organization)

    if organization is None:
        organization = get_default_clinic_organization()
    if organization is None:
        return None

    membership_role = "MEMBER"
    has_default = OrganizationUser.objects.filter(user=user, is_default=True).exists()
    membership, _created = OrganizationUser.objects.get_or_create(
        organization=organization,
        user=user,
        defaults={
            "role": membership_role,
            "is_default": not has_default,
        },
    )
    return membership
