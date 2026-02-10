"""
Admin configuration for AI Integration app.
"""
from django.contrib import admin
from .models import AIRequest, AIConfiguration, AICache


@admin.register(AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    """Admin for AI request tracking."""
    list_display = [
        'id',
        'visit',
        'user',
        'user_role',
        'feature_type',
        'provider',
        'model_name',
        'total_tokens',
        'cost_usd',
        'success',
        'response_time_ms',
        'timestamp',
    ]
    list_filter = [
        'feature_type',
        'provider',
        'success',
        'user_role',
        'timestamp',
    ]
    search_fields = [
        'visit__id',
        'user__username',
        'user__email',
        'model_name',
    ]
    readonly_fields = [
        'visit',
        'user',
        'user_role',
        'feature_type',
        'provider',
        'model_name',
        'prompt_tokens',
        'completion_tokens',
        'total_tokens',
        'cost_usd',
        'request_payload',
        'response_payload',
        'success',
        'error_message',
        'response_time_ms',
        'timestamp',
        'ip_address',
        'metadata',
    ]
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        """AI requests are created automatically, not via admin."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """AI requests are immutable for audit compliance."""
        return False


@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    """Admin for AI configuration."""
    list_display = [
        'feature_type',
        'default_provider',
        'default_model',
        'enabled',
        'max_tokens',
        'temperature',
        'rate_limit_per_minute',
        'updated_at',
    ]
    list_filter = [
        'enabled',
        'default_provider',
        'feature_type',
    ]
    search_fields = [
        'feature_type',
        'default_model',
    ]


@admin.register(AICache)
class AICacheAdmin(admin.ModelAdmin):
    """Admin for AI cache."""
    list_display = [
        'id',
        'feature_type',
        'prompt_hash',
        'hit_count',
        'expires_at',
        'created_at',
    ]
    list_filter = [
        'feature_type',
        'expires_at',
    ]
    search_fields = [
        'prompt_hash',
    ]
    readonly_fields = [
        'prompt_hash',
        'hit_count',
        'created_at',
    ]
