"""
Antenatal Module Admin Configuration
"""
from django.contrib import admin
from .models import (
    AntenatalRecord, AntenatalVisit, AntenatalUltrasound,
    AntenatalLab, AntenatalMedication, AntenatalOutcome
)


class AntenatalVisitInline(admin.TabularInline):
    model = AntenatalVisit
    extra = 0
    readonly_fields = ['created_at']


class AntenatalOutcomeInline(admin.StackedInline):
    model = AntenatalOutcome
    extra = 0
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AntenatalRecord)
class AntenatalRecordAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'patient', 'pregnancy_number', 'booking_date', 'lmp', 'edd',
        'outcome', 'high_risk', 'created_at'
    ]
    list_filter = ['outcome', 'high_risk', 'parity', 'pregnancy_type', 'booking_date']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__mrn']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'booking_date'
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'pregnancy_number')
        }),
        ('Pregnancy Details', {
            'fields': ('booking_date', 'lmp', 'edd', 'parity', 'gravida', 'para', 'abortions', 'living_children')
        }),
        ('Medical History', {
            'fields': ('past_medical_history', 'past_surgical_history', 'family_history', 'allergies')
        }),
        ('Obstetric History', {
            'fields': ('previous_cs', 'previous_cs_count', 'previous_complications')
        }),
        ('Current Pregnancy', {
            'fields': ('pregnancy_type', 'high_risk', 'risk_factors')
        }),
        ('Outcome', {
            'fields': ('outcome', 'delivery_date', 'delivery_gestational_age_weeks', 'delivery_gestational_age_days')
        }),
        ('Notes', {
            'fields': ('clinical_notes',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )
    
    inlines = [AntenatalVisitInline]


@admin.register(AntenatalVisit)
class AntenatalVisitAdmin(admin.ModelAdmin):
    list_display = [
        'antenatal_record', 'visit_date', 'visit_type', 'gestational_age_weeks',
        'blood_pressure_systolic', 'blood_pressure_diastolic', 'recorded_by'
    ]
    list_filter = ['visit_type', 'visit_date']
    search_fields = ['antenatal_record__patient__first_name', 'antenatal_record__patient__last_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AntenatalUltrasound)
class AntenatalUltrasoundAdmin(admin.ModelAdmin):
    list_display = [
        'antenatal_visit', 'scan_date', 'scan_type', 'gestational_age_weeks',
        'estimated_fetal_weight', 'performed_by'
    ]
    list_filter = ['scan_type', 'scan_date']
    search_fields = ['antenatal_visit__antenatal_record__patient__first_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AntenatalLab)
class AntenatalLabAdmin(admin.ModelAdmin):
    list_display = [
        'antenatal_visit', 'test_name', 'test_date', 'hb', 'blood_group',
        'rhesus', 'ordered_by'
    ]
    list_filter = ['test_date']
    search_fields = ['test_name', 'antenatal_visit__antenatal_record__patient__first_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AntenatalMedication)
class AntenatalMedicationAdmin(admin.ModelAdmin):
    list_display = [
        'antenatal_visit', 'medication_name', 'category', 'dose', 'frequency',
        'start_date', 'prescribed_by'
    ]
    list_filter = ['category', 'start_date']
    search_fields = ['medication_name', 'antenatal_visit__antenatal_record__patient__first_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AntenatalOutcome)
class AntenatalOutcomeAdmin(admin.ModelAdmin):
    list_display = [
        'antenatal_record', 'delivery_date', 'delivery_type',
        'number_of_babies', 'live_births', 'recorded_by'
    ]
    list_filter = ['delivery_type', 'delivery_date']
    search_fields = ['antenatal_record__patient__first_name', 'antenatal_record__patient__last_name']
    readonly_fields = ['created_at', 'updated_at']
