"""
Admin for Organizations (multi-tenancy).
"""

from django.contrib import admin

from .models import (
    Organization,
    OrganizationUser,
    Plan,
    SaasSubscriptionPayment,
    Subscription,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]


@admin.register(OrganizationUser)
class OrganizationUserAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "role", "is_default"]
    list_filter = ["organization", "role"]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "price_monthly", "currency", "is_active"]


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["organization", "plan", "status", "current_period_end"]


@admin.register(SaasSubscriptionPayment)
class SaasSubscriptionPaymentAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "organization",
        "plan",
        "amount",
        "currency",
        "provider",
        "status",
        "verified_at",
    ]
    list_filter = ["provider", "status"]
    search_fields = ["reference", "organization__name"]
