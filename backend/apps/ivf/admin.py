"""
IVF Module Admin Configuration
"""
from django.contrib import admin
from .models import (
    IVFCycle, OvarianStimulation, OocyteRetrieval, SpermAnalysis,
    Embryo, EmbryoTransfer, IVFMedication, IVFOutcome, IVFConsent
)


class OvarianStimulationInline(admin.TabularInline):
    model = OvarianStimulation
    extra = 0
    readonly_fields = ['created_at']


class EmbryoInline(admin.TabularInline):
    model = Embryo
    extra = 0
    readonly_fields = ['lab_id', 'created_at']


class IVFMedicationInline(admin.TabularInline):
    model = IVFMedication
    extra = 0


class IVFConsentInline(admin.TabularInline):
    model = IVFConsent
    extra = 0
    readonly_fields = ['created_at']


@admin.register(IVFCycle)
class IVFCycleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'patient', 'cycle_number', 'cycle_type', 'status',
        'actual_start_date', 'consent_signed', 'created_at'
    ]
    list_filter = ['status', 'cycle_type', 'consent_signed', 'created_at']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__mrn']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient', 'partner', 'cycle_number')
        }),
        ('Cycle Details', {
            'fields': ('cycle_type', 'status', 'protocol', 'diagnosis')
        }),
        ('Dates', {
            'fields': ('planned_start_date', 'actual_start_date', 'lmp_date')
        }),
        ('Consent (Nigerian Legal Requirement)', {
            'fields': (
                'consent_signed', 'consent_date',
                'partner_consent_signed', 'partner_consent_date'
            )
        }),
        ('Financial', {
            'fields': (
                'estimated_cost', 'insurance_pre_auth',
                'insurance_pre_auth_number'
            )
        }),
        ('Outcome', {
            'fields': (
                'pregnancy_test_date', 'beta_hcg_result', 'pregnancy_outcome'
            )
        }),
        ('Cancellation', {
            'fields': (
                'cancellation_reason', 'cancellation_notes', 'cancelled_at'
            ),
            'classes': ['collapse']
        }),
        ('Notes', {
            'fields': ('clinical_notes',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )
    
    inlines = [OvarianStimulationInline, EmbryoInline, IVFMedicationInline, IVFConsentInline]


@admin.register(OvarianStimulation)
class OvarianStimulationAdmin(admin.ModelAdmin):
    list_display = [
        'cycle', 'day', 'date', 'estradiol', 'endometrial_thickness',
        'total_follicle_count', 'recorded_by'
    ]
    list_filter = ['date', 'recorded_by']
    search_fields = ['cycle__patient__first_name', 'cycle__patient__last_name']
    readonly_fields = ['created_at']


@admin.register(OocyteRetrieval)
class OocyteRetrievalAdmin(admin.ModelAdmin):
    list_display = [
        'cycle', 'procedure_date', 'total_oocytes_retrieved',
        'mature_oocytes', 'performed_by'
    ]
    list_filter = ['procedure_date', 'anesthesia_type', 'performed_by']
    search_fields = ['cycle__patient__first_name', 'cycle__patient__last_name']
    readonly_fields = ['created_at', 'updated_at', 'total_oocytes_retrieved']


@admin.register(SpermAnalysis)
class SpermAnalysisAdmin(admin.ModelAdmin):
    list_display = [
        'patient', 'collection_date', 'concentration',
        'total_motility', 'normal_forms', 'assessment'
    ]
    list_filter = ['collection_date', 'sample_source', 'assessment']
    search_fields = ['patient__first_name', 'patient__last_name']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Sample Information', {
            'fields': (
                'patient', 'cycle', 'collection_date', 'collection_time',
                'abstinence_days', 'sample_source'
            )
        }),
        ('Macroscopic Parameters', {
            'fields': (
                'volume', 'appearance', 'liquefaction_time', 'ph', 'viscosity'
            )
        }),
        ('Concentration & Count', {
            'fields': ('concentration', 'total_sperm_count')
        }),
        ('Motility', {
            'fields': (
                'progressive_motility', 'non_progressive_motility',
                'immotile', 'total_motility'
            )
        }),
        ('Morphology', {
            'fields': (
                'normal_forms', 'head_defects', 'midpiece_defects', 'tail_defects'
            )
        }),
        ('Other Parameters', {
            'fields': ('vitality', 'round_cells', 'wbc_count', 'dna_fragmentation_index')
        }),
        ('Assessment', {
            'fields': ('assessment', 'recommendation', 'notes')
        }),
        ('Audit', {
            'fields': ('analyzed_by', 'created_at'),
            'classes': ['collapse']
        }),
    )


@admin.register(Embryo)
class EmbryoAdmin(admin.ModelAdmin):
    list_display = [
        'lab_id', 'cycle', 'embryo_number', 'status',
        'fertilization_method', 'blastocyst_grade', 'pgt_result'
    ]
    list_filter = ['status', 'fertilization_method', 'pgt_performed', 'pgt_result']
    search_fields = ['lab_id', 'cycle__patient__first_name', 'cycle__patient__last_name']
    readonly_fields = ['lab_id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Identification', {
            'fields': ('cycle', 'embryo_number', 'lab_id', 'status')
        }),
        ('Fertilization', {
            'fields': (
                'fertilization_method', 'fertilization_date', 'fertilization_time',
                'day1_pn_status'
            )
        }),
        ('Cleavage Stage (Day 2-3)', {
            'fields': ('day2_cell_count', 'day3_cell_count', 'day3_grade', 'fragmentation')
        }),
        ('Blastocyst Stage (Day 5-6)', {
            'fields': (
                'blastocyst_day', 'blastocyst_grade', 'expansion_grade',
                'icm_grade', 'trophectoderm_grade'
            )
        }),
        ('Genetic Testing', {
            'fields': ('pgt_performed', 'pgt_result', 'pgt_details')
        }),
        ('Cryopreservation', {
            'fields': (
                'frozen_date', 'storage_location', 'straw_id',
                'thaw_date', 'survived_thaw'
            )
        }),
        ('Disposition', {
            'fields': ('disposition', 'disposition_date', 'disposition_notes')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Audit', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ['collapse']
        }),
    )


@admin.register(EmbryoTransfer)
class EmbryoTransferAdmin(admin.ModelAdmin):
    list_display = [
        'cycle', 'transfer_date', 'transfer_type',
        'embryos_transferred_count', 'difficulty', 'performed_by'
    ]
    list_filter = ['transfer_date', 'transfer_type', 'difficulty']
    search_fields = ['cycle__patient__first_name', 'cycle__patient__last_name']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['embryos']


@admin.register(IVFMedication)
class IVFMedicationAdmin(admin.ModelAdmin):
    list_display = [
        'cycle', 'medication_name', 'category', 'dose', 'unit',
        'route', 'start_date', 'prescribed_by'
    ]
    list_filter = ['category', 'route', 'start_date']
    search_fields = ['medication_name', 'cycle__patient__first_name']
    readonly_fields = ['created_at']


@admin.register(IVFOutcome)
class IVFOutcomeAdmin(admin.ModelAdmin):
    list_display = [
        'cycle', 'clinical_pregnancy', 'live_births',
        'delivery_date', 'recorded_by'
    ]
    list_filter = ['clinical_pregnancy', 'delivery_type', 'miscarriage']
    search_fields = ['cycle__patient__first_name', 'cycle__patient__last_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(IVFConsent)
class IVFConsentAdmin(admin.ModelAdmin):
    list_display = [
        'cycle', 'consent_type', 'patient', 'signed',
        'signed_date', 'revoked', 'recorded_by'
    ]
    list_filter = ['consent_type', 'signed', 'revoked']
    search_fields = ['patient__first_name', 'patient__last_name']
    readonly_fields = ['created_at', 'updated_at']
