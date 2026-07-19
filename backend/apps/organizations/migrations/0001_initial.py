# Generated for SaaS multi-tenancy

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Organization display name (e.g., clinic name)",
                        max_length=255,
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="URL-safe identifier (e.g., clinic1, city-hospital)",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "logo_url",
                    models.URLField(
                        blank=True,
                        help_text="Organization logo URL (optional)",
                        null=True,
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        help_text="Primary contact email",
                        max_length=254,
                        null=True,
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        blank=True,
                        help_text="Primary contact phone",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "address",
                    models.TextField(
                        blank=True, help_text="Physical address", null=True
                    ),
                ),
                (
                    "patient_id_prefix",
                    models.CharField(
                        default="LMC",
                        help_text="Prefix for patient IDs (e.g., LMC, ABC). Default: LMC.",
                        max_length=10,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether organization is active (can log in)",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
                "db_table": "organizations",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Plan",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Plan display name", max_length=100),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="Plan identifier (e.g., starter, professional)",
                        max_length=50,
                        unique=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Plan description", null=True
                    ),
                ),
                (
                    "max_users",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Max staff users (null = unlimited)",
                        null=True,
                    ),
                ),
                (
                    "max_patients",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Max patients (null = unlimited)",
                        null=True,
                    ),
                ),
                (
                    "max_storage_mb",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Max storage in MB (null = unlimited)",
                        null=True,
                    ),
                ),
                (
                    "price_monthly",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Monthly price in base currency",
                        max_digits=10,
                    ),
                ),
                (
                    "price_yearly",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Yearly price (if different from monthly * 12)",
                        max_digits=10,
                        null=True,
                    ),
                ),
                ("currency", models.CharField(default="NGN", max_length=3)),
                (
                    "stripe_price_id",
                    models.CharField(
                        blank=True,
                        help_text="Stripe Price ID for monthly billing",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "stripe_price_id_yearly",
                    models.CharField(
                        blank=True,
                        help_text="Stripe Price ID for yearly billing",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "features",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Plan features (e.g., {'ivf': True, 'telemedicine': True})",
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "sort_order",
                    models.PositiveIntegerField(
                        default=0, help_text="Display order (lower = first)"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Plan",
                "verbose_name_plural": "Plans",
                "db_table": "plans",
                "ordering": ["sort_order", "price_monthly"],
            },
        ),
        migrations.CreateModel(
            name="OrganizationUser",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("OWNER", "Owner"),
                            ("ADMIN", "Administrator"),
                            ("MEMBER", "Member"),
                        ],
                        default="MEMBER",
                        max_length=20,
                    ),
                ),
                (
                    "is_default",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this is the user's default organization",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="organizations.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organization_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Organization User",
                "verbose_name_plural": "Organization Users",
                "db_table": "organization_users",
                "ordering": ["-is_default", "organization__name"],
                "unique_together": {("organization", "user")},
            },
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("TRIAL", "Trial"),
                            ("ACTIVE", "Active"),
                            ("PAST_DUE", "Past Due"),
                            ("CANCELLED", "Cancelled"),
                            ("EXPIRED", "Expired"),
                        ],
                        default="TRIAL",
                        max_length=20,
                    ),
                ),
                (
                    "stripe_subscription_id",
                    models.CharField(
                        blank=True,
                        help_text="Stripe Subscription ID",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "stripe_customer_id",
                    models.CharField(
                        blank=True,
                        help_text="Stripe Customer ID for billing",
                        max_length=255,
                        null=True,
                    ),
                ),
                (
                    "current_period_start",
                    models.DateTimeField(
                        blank=True, help_text="Current billing period start", null=True
                    ),
                ),
                (
                    "current_period_end",
                    models.DateTimeField(
                        blank=True, help_text="Current billing period end", null=True
                    ),
                ),
                (
                    "cancel_at_period_end",
                    models.BooleanField(
                        default=False, help_text="Whether to cancel at period end"
                    ),
                ),
                (
                    "cancel_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When subscription will be cancelled",
                        null=True,
                    ),
                ),
                (
                    "trial_ends_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When trial ends (null = no trial)",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscription",
                        to="organizations.organization",
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subscriptions",
                        to="organizations.plan",
                    ),
                ),
            ],
            options={
                "verbose_name": "Subscription",
                "verbose_name_plural": "Subscriptions",
                "db_table": "subscriptions",
            },
        ),
    ]
