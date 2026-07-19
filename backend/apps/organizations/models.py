"""
Organization and clinic-scoping models for Lifeway Medical Centre.

- Organization = clinic (single production tenant; org FK on patient/visit data)
- OrganizationUser = staff membership in the clinic
- Plan / Subscription = optional usage limits (disabled when ENFORCE_PLAN_LIMITS=false)
"""

from decimal import Decimal

from django.db import models


class Organization(models.Model):
    """
    Clinic organization — Lifeway Medical Centre (single-clinic deployment).

    Patient, visit, and billing records reference organization_id for scoping.
    """

    name = models.CharField(
        max_length=255, help_text="Organization display name (e.g., clinic name)"
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-safe identifier (e.g., clinic1, city-hospital)",
    )

    # Optional branding
    logo_url = models.URLField(
        blank=True, null=True, help_text="Organization logo URL (optional)"
    )

    # Contact info
    email = models.EmailField(blank=True, null=True, help_text="Primary contact email")

    phone = models.CharField(
        max_length=20, blank=True, null=True, help_text="Primary contact phone"
    )

    address = models.TextField(blank=True, null=True, help_text="Physical address")

    # Patient ID prefix (e.g., LMC -> LMC000001, or custom per org)
    patient_id_prefix = models.CharField(
        max_length=10,
        default="LMC",
        help_text="Prefix for patient IDs (e.g., LMC, ABC). Default: LMC.",
    )

    # Status
    is_active = models.BooleanField(
        default=True, help_text="Whether organization is active (can log in)"
    )

    guide_modules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Enabled Guide modules (laboratory, pharmacy, radiology, nhia, anc, telemedicine)",
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"
        ordering = ["name"]
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name


class OrganizationUser(models.Model):
    """
    Links users to organizations.

    Users can belong to multiple organizations (e.g., locum doctor).
    Each membership has a role within that organization.
    """

    ROLE_CHOICES = [
        ("OWNER", "Owner"),
        ("ADMIN", "Administrator"),
        ("MEMBER", "Member"),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="members"
    )

    user = models.ForeignKey(
        "users.User", on_delete=models.CASCADE, related_name="organization_memberships"
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="MEMBER")

    is_default = models.BooleanField(
        default=False, help_text="Whether this is the user's default organization"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organization_users"
        unique_together = [["organization", "user"]]
        ordering = ["-is_default", "organization__name"]
        verbose_name = "Organization User"
        verbose_name_plural = "Organization Users"

    def __str__(self):
        return f"{self.user.username} @ {self.organization.name}"

    def save(self, *args, **kwargs):
        if self.is_default:
            OrganizationUser.objects.filter(user=self.user, is_default=True).exclude(
                pk=self.pk
            ).update(is_default=False)
        super().save(*args, **kwargs)


class Plan(models.Model):
    """
    Optional usage tier for staff/patient limits (not used for online billing).
    """

    name = models.CharField(max_length=100, help_text="Plan display name")

    slug = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Plan identifier (e.g., starter, professional)",
    )

    description = models.TextField(blank=True, null=True, help_text="Plan description")

    # Limits (null = unlimited)
    max_users = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max staff users (null = unlimited)"
    )

    max_patients = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max patients (null = unlimited)"
    )

    max_storage_mb = models.PositiveIntegerField(
        null=True, blank=True, help_text="Max storage in MB (null = unlimited)"
    )

    # Pricing
    price_monthly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Monthly price in base currency",
    )

    price_yearly = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Yearly price (if different from monthly * 12)",
    )

    currency = models.CharField(max_length=3, default="NGN")

    # Legacy Stripe price IDs (unused in Lifeway deployment)
    stripe_price_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Legacy Stripe Price ID (optional)",
    )

    stripe_price_id_yearly = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Legacy Stripe yearly Price ID (optional)",
    )

    # Paystack recurring plan code (legacy; visit billing uses apps.billing)
    paystack_plan_code = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Paystack Plan code (PLN_xxx) for monthly auto-renew",
    )

    # Feature flags
    features = models.JSONField(
        default=dict,
        blank=True,
        help_text="Plan features (e.g., {'ivf': True, 'telemedicine': True})",
    )

    is_active = models.BooleanField(default=True)

    sort_order = models.PositiveIntegerField(
        default=0, help_text="Display order (lower = first)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "plans"
        ordering = ["sort_order", "price_monthly"]
        verbose_name = "Plan"
        verbose_name_plural = "Plans"

    def __str__(self):
        return f"{self.name} ({self.currency} {self.price_monthly}/mo)"


class Subscription(models.Model):
    """
    Organization's active subscription to a plan.
    """

    STATUS_CHOICES = [
        ("TRIAL", "Trial"),
        ("ACTIVE", "Active"),
        ("PAST_DUE", "Past Due"),
        ("CANCELLED", "Cancelled"),
        ("EXPIRED", "Expired"),
    ]

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="subscription"
    )

    plan = models.ForeignKey(
        Plan, on_delete=models.PROTECT, related_name="subscriptions"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="TRIAL")

    # Legacy Stripe IDs (unused in Lifeway deployment)
    stripe_subscription_id = models.CharField(
        max_length=255, blank=True, null=True, help_text="Legacy Stripe Subscription ID"
    )

    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Legacy Stripe Customer ID",
    )

    # Paystack subscription code (legacy; visit billing uses apps.billing)
    paystack_subscription_code = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Paystack Subscription code (SUB_xxx)",
    )

    paystack_customer_code = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Paystack Customer code (CUS_xxx)",
    )

    paystack_email_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="Paystack subscription email_token (required to disable auto-renew)",
    )

    auto_renew_enabled = models.BooleanField(
        default=False,
        help_text="Whether Paystack auto-renewal is active for this subscription",
    )

    # Billing
    current_period_start = models.DateTimeField(
        null=True, blank=True, help_text="Current billing period start"
    )

    current_period_end = models.DateTimeField(
        null=True, blank=True, help_text="Current billing period end"
    )

    cancel_at_period_end = models.BooleanField(
        default=False, help_text="Whether to cancel at period end"
    )

    cancel_at = models.DateTimeField(
        null=True, blank=True, help_text="When subscription will be cancelled"
    )

    # Trial
    trial_ends_at = models.DateTimeField(
        null=True, blank=True, help_text="When trial ends (null = no trial)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscriptions"
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        return f"{self.organization.name} - {self.plan.name} ({self.status})"

    def is_active(self):
        """Check if subscription allows usage."""
        if self.status in ("CANCELLED", "EXPIRED"):
            return False
        if self.trial_ends_at:
            from django.utils import timezone

            if timezone.now() > self.trial_ends_at and self.status == "TRIAL":
                return False
        return True


class SaasSubscriptionPayment(models.Model):
    """
    Legacy subscription payment records (historical table; no active checkout flow).
    """

    PROVIDER_CHOICES = [
        ("PAYSTACK", "Paystack"),
        ("FLUTTERWAVE", "Flutterwave"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("VERIFIED", "Verified"),
        ("FAILED", "Failed"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="saas_payments",
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        related_name="saas_payments",
    )
    reference = models.CharField(max_length=100, unique=True, db_index=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="NGN")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="PENDING"
    )
    provider_transaction_id = models.CharField(
        max_length=255, blank=True, null=True
    )
    customer_email = models.EmailField(blank=True, null=True)
    authorization_url = models.URLField(blank=True, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saas_subscription_payments"
        ordering = ["-created_at"]
        verbose_name = "Legacy subscription payment"
        verbose_name_plural = "Legacy subscription payments"

    def __str__(self):
        return f"{self.reference} ({self.status})"
