"""
Admin configuration for Referrals.
"""
from django.contrib import admin
from .models import Referral


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    """Admin interface for Referral model."""
    
    list_display = [
        'id',
        'visit',
        'specialty',
        'specialist_name',
        'status',
        'urgency',
        'referred_by',
        'created_at',
    ]
    
    list_filter = [
        'status',
        'specialty',
        'urgency',
        'created_at',
    ]
    
    search_fields = [
        'specialist_name',
        'specialist_contact',
        'reason',
        'visit__patient__first_name',
        'visit__patient__last_name',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'accepted_at',
        'completed_at',
    ]
    
    fieldsets = (
        ('Visit Information', {
            'fields': ('visit', 'consultation', 'referred_by')
        }),
        ('Referral Details', {
            'fields': (
                'specialty',
                'specialist_name',
                'specialist_contact',
                'reason',
                'clinical_summary',
                'urgency',
                'status',
            )
        }),
        ('Specialist Response', {
            'fields': (
                'specialist_notes',
                'accepted_at',
                'completed_at',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('visit', 'consultation', 'referred_by')
