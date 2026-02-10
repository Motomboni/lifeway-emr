"""
Django admin configuration for Nursing models.
"""
from django.contrib import admin
from .models import NursingNote, MedicationAdministration, LabSampleCollection


@admin.register(NursingNote)
class NursingNoteAdmin(admin.ModelAdmin):
    """Admin interface for Nursing Notes."""
    list_display = ['id', 'visit', 'note_type', 'recorded_by', 'recorded_at']
    list_filter = ['note_type', 'recorded_at']
    search_fields = ['note_content', 'visit__id', 'recorded_by__username']
    readonly_fields = ['recorded_at']
    date_hierarchy = 'recorded_at'
    
    fieldsets = (
        ('Visit Information', {
            'fields': ('visit', 'recorded_by', 'recorded_at')
        }),
        ('Note Content', {
            'fields': ('note_type', 'note_content', 'patient_condition', 'care_provided', 'patient_response')
        }),
    )


@admin.register(MedicationAdministration)
class MedicationAdministrationAdmin(admin.ModelAdmin):
    """Admin interface for Medication Administration."""
    list_display = ['id', 'visit', 'prescription', 'administered_by', 'administration_time', 'status']
    list_filter = ['status', 'route', 'administration_time']
    search_fields = ['prescription__drug', 'visit__id', 'administered_by__username']
    readonly_fields = ['recorded_at']
    date_hierarchy = 'administration_time'
    
    fieldsets = (
        ('Visit and Prescription', {
            'fields': ('visit', 'prescription', 'administered_by', 'recorded_at')
        }),
        ('Administration Details', {
            'fields': ('administration_time', 'dose_administered', 'route', 'site', 'status')
        }),
        ('Notes', {
            'fields': ('administration_notes', 'reason_if_held')
        }),
    )


@admin.register(LabSampleCollection)
class LabSampleCollectionAdmin(admin.ModelAdmin):
    """Admin interface for Lab Sample Collection."""
    list_display = ['id', 'visit', 'lab_order', 'collected_by', 'collection_time', 'status']
    list_filter = ['status', 'sample_type', 'collection_time']
    search_fields = ['lab_order__id', 'visit__id', 'collected_by__username', 'sample_type']
    readonly_fields = ['recorded_at']
    date_hierarchy = 'collection_time'
    
    fieldsets = (
        ('Visit and Lab Order', {
            'fields': ('visit', 'lab_order', 'collected_by', 'recorded_at')
        }),
        ('Collection Details', {
            'fields': ('collection_time', 'sample_type', 'collection_site', 'status', 'sample_volume', 'container_type')
        }),
        ('Notes', {
            'fields': ('collection_notes', 'reason_if_failed')
        }),
    )
