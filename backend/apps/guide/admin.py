from django.contrib import admin

from .models import UserGuideProgress, VisitWorkflowProgress


@admin.register(UserGuideProgress)
class UserGuideProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at", "updated_at")


@admin.register(VisitWorkflowProgress)
class VisitWorkflowProgressAdmin(admin.ModelAdmin):
    list_display = ("visit", "pack_id", "updated_by", "updated_at")
    list_filter = ("pack_id",)
    search_fields = ("visit__id",)
