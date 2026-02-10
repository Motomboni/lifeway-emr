"""
Admin configuration for Lab Test Catalog.
"""
from django.contrib import admin
from .catalog_models import LabTestCatalog


@admin.register(LabTestCatalog)
class LabTestCatalogAdmin(admin.ModelAdmin):
    """Admin interface for LabTestCatalog model."""
    
    list_display = [
        'test_code',
        'test_name',
        'category',
        'unit',
        'is_active',
        'requires_fasting',
        'created_by',
        'created_at',
    ]
    
    list_filter = [
        'category',
        'is_active',
        'requires_fasting',
        'created_at',
    ]
    
    search_fields = [
        'test_code',
        'test_name',
        'description',
        'category',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Test Information', {
            'fields': (
                'test_code',
                'test_name',
                'category',
                'description',
            )
        }),
        ('Reference Ranges', {
            'fields': (
                'reference_range_min',
                'reference_range_max',
                'reference_range_text',
                'unit',
            )
        }),
        ('Test Requirements', {
            'fields': (
                'specimen_type',
                'requires_fasting',
                'turnaround_time_hours',
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
