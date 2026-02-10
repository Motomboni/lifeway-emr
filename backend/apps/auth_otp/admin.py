"""
OTP Authentication Admin
"""
from django.contrib import admin
from .models import LoginOTP, LoginAuditLog


@admin.register(LoginOTP)
class LoginOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'channel', 'recipient', 'is_used', 'created_at', 'expires_at']
    list_filter = ['channel', 'is_used', 'created_at']
    search_fields = ['user__username', 'user__email', 'recipient', 'otp_code']
    readonly_fields = ['created_at', 'used_at']
    date_hierarchy = 'created_at'


@admin.register(LoginAuditLog)
class LoginAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'identifier', 'success', 'ip_address', 'device_type', 'timestamp']
    list_filter = ['action', 'success', 'device_type', 'timestamp']
    search_fields = ['user__username', 'identifier', 'ip_address']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
