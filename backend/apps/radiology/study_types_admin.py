"""
Admin configuration for Radiology Study Types Catalog.
"""
from django.contrib import admin
from .study_types_models import RadiologyStudyType


@admin.register(RadiologyStudyType)
class RadiologyStudyTypeAdmin(admin.ModelAdmin):
    """Admin interface for RadiologyStudyType model."""
    
    list_display = [
        'study_code',
        'study_name',
        'category',
        'body_part',
        'is_active',
        'contrast_required',
        'created_by',
        'created_at',
    ]
    
    list_filter = [
        'category',
        'is_active',
        'contrast_required',
        'requires_sedation',
        'created_at',
    ]
    
    search_fields = [
        'study_code',
        'study_name',
        'description',
        'category',
        'body_part',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Study Information', {
            'fields': (
                'study_code',
                'study_name',
                'category',
                'body_part',
                'description',
            )
        }),
        ('Protocol & Instructions', {
            'fields': (
                'protocol',
                'preparation_instructions',
            )
        }),
        ('Study Requirements', {
            'fields': (
                'contrast_required',
                'contrast_type',
                'requires_sedation',
                'estimated_duration_minutes',
                'radiation_dose',
            )
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('created_by')
