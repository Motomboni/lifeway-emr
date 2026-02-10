"""
Django admin configuration for clinical models.
"""
from django.contrib import admin
from .models import VitalSigns, ClinicalTemplate, ClinicalAlert
from .procedure_models import ProcedureTask
from .operation_models import OperationNote


@admin.register(VitalSigns)
class VitalSignsAdmin(admin.ModelAdmin):
    list_display = ['visit', 'recorded_by', 'temperature', 'systolic_bp', 'diastolic_bp', 'pulse', 'recorded_at']
    list_filter = ['recorded_at', 'visit__status']
    search_fields = ['visit__patient__first_name', 'visit__patient__last_name', 'visit__patient__patient_id']
    readonly_fields = ['recorded_at', 'bmi']
    fieldsets = (
        ('Visit Information', {
            'fields': ('visit', 'recorded_by', 'recorded_at')
        }),
        ('Vital Signs', {
            'fields': (
                'temperature',
                ('systolic_bp', 'diastolic_bp'),
                'pulse',
                'respiratory_rate',
                'oxygen_saturation',
                ('weight', 'height', 'bmi'),
            )
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
    )


@admin.register(ClinicalTemplate)
class ClinicalTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'usage_count', 'created_by', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'category', 'description']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'category', 'description', 'is_active', 'created_by')
        }),
        ('Template Content', {
            'fields': ('history_template', 'examination_template', 'diagnosis_template', 'clinical_notes_template')
        }),
        ('Metadata', {
            'fields': ('usage_count', 'created_at', 'updated_at')
        }),
    )


@admin.register(ClinicalAlert)
class ClinicalAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'alert_type', 'severity', 'visit', 'is_resolved', 'acknowledged_by', 'created_at']
    list_filter = ['alert_type', 'severity', 'is_resolved', 'created_at']
    search_fields = ['title', 'message', 'visit__patient__first_name', 'visit__patient__last_name']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Alert Information', {
            'fields': ('visit', 'alert_type', 'severity', 'title', 'message')
        }),
        ('Related Resource', {
            'fields': ('related_resource_type', 'related_resource_id')
        }),
        ('Status', {
            'fields': ('is_resolved', 'acknowledged_by', 'acknowledged_at', 'created_at')
        }),
    )


@admin.register(ProcedureTask)
class ProcedureTaskAdmin(admin.ModelAdmin):
    list_display = ['procedure_name', 'visit', 'consultation', 'ordered_by', 'executed_by', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'execution_date']
    search_fields = ['procedure_name', 'visit__patient__first_name', 'visit__patient__last_name', 'visit__patient__patient_id']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Visit & Consultation', {
            'fields': ('visit', 'consultation', 'service_catalog')
        }),
        ('Procedure Information', {
            'fields': ('procedure_name', 'procedure_description', 'clinical_indication')
        }),
        ('Ordering', {
            'fields': ('ordered_by', 'status')
        }),
        ('Execution', {
            'fields': ('executed_by', 'execution_date', 'execution_notes')
        }),
            ('Timestamps', {
                'fields': ('created_at', 'updated_at')
            }),
        )


@admin.register(OperationNote)
class OperationNoteAdmin(admin.ModelAdmin):
    list_display = ['operation_name', 'visit', 'surgeon', 'operation_type', 'operation_date', 'created_at']
    list_filter = ['operation_type', 'anesthesia_type', 'operation_date', 'created_at']
    search_fields = ['operation_name', 'visit__patient__first_name', 'visit__patient__last_name', 'visit__patient__patient_id']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Visit & Consultation', {
            'fields': ('visit', 'consultation')
        }),
        ('Surgeons & Anesthesia', {
            'fields': ('surgeon', 'assistant_surgeon', 'anesthetist')
        }),
        ('Operation Details', {
            'fields': ('operation_type', 'operation_name', 'operation_date', 'operation_duration_minutes')
        }),
        ('Diagnosis', {
            'fields': ('preoperative_diagnosis', 'postoperative_diagnosis', 'indication')
        }),
        ('Anesthesia', {
            'fields': ('anesthesia_type', 'anesthesia_notes')
        }),
        ('Procedure', {
            'fields': ('procedure_description', 'findings', 'technique', 'complications')
        }),
        ('Additional Details', {
            'fields': ('estimated_blood_loss', 'specimens_sent')
        }),
        ('Postoperative', {
            'fields': ('postoperative_plan', 'postoperative_instructions')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
