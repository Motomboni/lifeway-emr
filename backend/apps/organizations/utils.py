"""
Organization utilities - plan limits enforcement for SaaS.
"""

from rest_framework.exceptions import ValidationError


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
