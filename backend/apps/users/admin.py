"""
Admin configuration for User model.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for User model."""
    
    list_display = ['username', 'email', 'role', 'is_active', 'is_locked', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff', 'is_superuser']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('EMR Information', {
            'fields': ('role', 'failed_login_attempts', 'locked_until', 'last_login_attempt')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('EMR Information', {
            'fields': ('role',)
        }),
    )
    
    def is_locked(self, obj):
        """Display if account is locked."""
        return obj.is_locked()
    is_locked.boolean = True
    is_locked.short_description = 'Locked'
