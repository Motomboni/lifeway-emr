"""
Admin configuration for Discharge Summaries and Admissions.
"""
from django.contrib import admin
from .models import DischargeSummary
from .admission_models import Ward, Bed, Admission


@admin.register(DischargeSummary)
class DischargeSummaryAdmin(admin.ModelAdmin):
    """Admin interface for DischargeSummary model."""
    
    list_display = [
        'id',
        'visit',
        'condition_at_discharge',
        'discharge_disposition',
        'created_by',
        'created_at',
    ]
    
    list_filter = [
        'condition_at_discharge',
        'discharge_disposition',
        'created_at',
    ]
    
    search_fields = [
        'visit__patient__first_name',
        'visit__patient__last_name',
        'diagnosis',
        'chief_complaint',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Visit Information', {
            'fields': ('visit', 'consultation', 'created_by')
        }),
        ('Admission Details', {
            'fields': (
                'admission_date',
                'chief_complaint',
            )
        }),
        ('Discharge Details', {
            'fields': (
                'discharge_date',
                'condition_at_discharge',
                'discharge_disposition',
            )
        }),
        ('Clinical Information', {
            'fields': (
                'diagnosis',
                'procedures_performed',
                'treatment_summary',
            )
        }),
        ('Discharge Instructions', {
            'fields': (
                'medications_on_discharge',
                'follow_up_instructions',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('visit', 'consultation', 'created_by', 'visit__patient')


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    """Admin interface for Ward model."""
    
    list_display = [
        'name', 'code', 'capacity', 'is_active',
        'get_available_beds_count', 'get_occupied_beds_count'
    ]
    
    list_filter = ['is_active', 'created_at']
    
    search_fields = ['name', 'code', 'description']
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_available_beds_count(self, obj):
        return obj.get_available_beds_count()
    get_available_beds_count.short_description = 'Available Beds'
    
    def get_occupied_beds_count(self, obj):
        return obj.get_occupied_beds_count()
    get_occupied_beds_count.short_description = 'Occupied Beds'


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    """Admin interface for Bed model."""
    
    list_display = [
        'bed_number', 'ward', 'bed_type', 'is_available', 'is_active'
    ]
    
    list_filter = ['ward', 'bed_type', 'is_available', 'is_active']
    
    search_fields = ['bed_number', 'ward__name', 'ward__code']
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    """Admin interface for Admission model."""
    
    list_display = [
        'visit', 'ward', 'bed', 'admission_type',
        'admission_status', 'admission_date', 'discharge_date'
    ]
    
    list_filter = [
        'ward', 'admission_type', 'admission_source',
        'admission_status', 'admission_date'
    ]
    
    search_fields = [
        'visit__patient__first_name',
        'visit__patient__last_name',
        'ward__name',
        'bed__bed_number',
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Visit Information', {
            'fields': ('visit', 'admitting_doctor')
        }),
        ('Ward and Bed', {
            'fields': ('ward', 'bed')
        }),
        ('Admission Details', {
            'fields': (
                'admission_type', 'admission_source',
                'admission_date', 'admission_status'
            )
        }),
        ('Clinical Information', {
            'fields': ('chief_complaint', 'admission_notes')
        }),
        ('Discharge Information', {
            'fields': ('discharge_date', 'discharge_summary')
        }),
        ('Transfer Information', {
            'fields': ('transferred_from',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related(
            'visit', 'ward', 'bed', 'admitting_doctor',
            'visit__patient', 'discharge_summary'
        )
