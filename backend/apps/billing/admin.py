"""
Admin configuration for billing app.
"""
from django.contrib import admin
from .models import Payment, VisitCharge, PaymentIntent
from .insurance_models import HMOProvider, VisitInsurance
from .bill_models import Bill, BillItem, BillPayment, InsuranceProvider, InsurancePolicy
from .price_lists import (
    LabServicePriceList,
    PharmacyServicePriceList,
    RadiologyServicePriceList,
    ProcedureServicePriceList,
)
from .service_catalog_models import ServiceCatalog
from .billing_line_item_models import BillingLineItem
from .leak_detection_models import LeakRecord
from .reconciliation_models import EndOfDayReconciliation


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'visit', 'amount', 'payment_method', 'status', 'created_at')
    search_fields = ('transaction_reference', 'visit__id', 'visit__patient__patient_id')


@admin.register(HMOProvider)
class HMOProviderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'contact_person')


@admin.register(VisitInsurance)
class VisitInsuranceAdmin(admin.ModelAdmin):
    list_display = ('id', 'visit', 'provider', 'policy_number', 'approval_status', 'created_at')
    search_fields = ('visit__id', 'provider__name', 'policy_number')


@admin.register(VisitCharge)
class VisitChargeAdmin(admin.ModelAdmin):
    """
    Admin interface for Visit Charge model.
    
    Note: VisitCharges are system-generated and should not be manually created.
    This admin interface is read-only for audit purposes.
    """
    list_display = [
        'id',
        'visit',
        'category',
        'description',
        'amount',
        'created_by_system',
        'created_at',
    ]
    list_filter = [
        'category',
        'created_by_system',
        'created_at',
    ]
    search_fields = [
        'visit__id',
        'description',
        'category',
    ]
    readonly_fields = [
        'visit',
        'category',
        'description',
        'amount',
        'consultation',
        'lab_order',
        'radiology_order',
        'prescription',
        'created_by_system',
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        """Disable manual creation - charges are system-generated only."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable manual editing - charges are system-generated only."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deletion - charges are immutable for audit compliance."""
        return False


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    """
    Admin interface for Payment Intent model.
    
    PaymentIntents track Paystack transactions for Visit billing.
    """
    list_display = [
        'id',
        'visit',
        'paystack_reference',
        'amount',
        'status',
        'paystack_transaction_id',
        'verified_at',
        'created_by',
        'created_at',
    ]
    list_filter = [
        'status',
        'created_at',
        'verified_at',
    ]
    search_fields = [
        'visit__id',
        'paystack_reference',
        'paystack_transaction_id',
    ]
    readonly_fields = [
        'visit',
        'paystack_reference',
        'amount',
        'status',
        'paystack_authorization_url',
        'paystack_access_code',
        'paystack_transaction_id',
        'paystack_customer_email',
        'verified_at',
        'payment',
        'created_by',
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        """Disable manual creation - use API endpoint."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable manual editing - payment intents are immutable after creation."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deletion - payment intents are immutable for audit compliance."""
        return False


# Bill Models Admin
@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('id', 'visit', 'total_amount', 'amount_paid', 'status', 'created_at')
    search_fields = ('visit__id', 'visit__patient__patient_id')


@admin.register(BillItem)
class BillItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'bill', 'service_name', 'amount', 'created_at')
    search_fields = ('service_name', 'bill__visit__id')


@admin.register(BillPayment)
class BillPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'bill', 'amount', 'payment_method', 'created_at')
    search_fields = ('transaction_reference', 'bill__visit__id')


@admin.register(InsuranceProvider)
class InsuranceProviderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'contact_person')


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'provider', 'policy_number', 'is_active', 'created_at')
    search_fields = ('policy_number', 'patient__patient_id', 'patient__first_name', 'patient__last_name')


# Price List Admin
@admin.register(LabServicePriceList)
class LabServicePriceListAdmin(admin.ModelAdmin):
    """Admin interface for Lab Service Price List."""
    list_display = ['service_code', 'service_name', 'amount', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['service_code', 'service_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PharmacyServicePriceList)
class PharmacyServicePriceListAdmin(admin.ModelAdmin):
    """Admin interface for Pharmacy Service Price List."""
    list_display = ['service_code', 'service_name', 'amount', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['service_code', 'service_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(RadiologyServicePriceList)
class RadiologyServicePriceListAdmin(admin.ModelAdmin):
    """Admin interface for Radiology Service Price List."""
    list_display = ['service_code', 'service_name', 'amount', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['service_code', 'service_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProcedureServicePriceList)
class ProcedureServicePriceListAdmin(admin.ModelAdmin):
    """Admin interface for Procedure Service Price List."""
    list_display = ['service_code', 'service_name', 'amount', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['service_code', 'service_name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(BillingLineItem)
class BillingLineItemAdmin(admin.ModelAdmin):
    """
    Admin interface for Billing Line Item.
    
    BillingLineItems are generated from ServiceCatalog and are immutable once paid.
    """
    list_display = [
        'id',
        'source_service_code',
        'source_service_name',
        'visit',
        'amount',
        'bill_status',
        'amount_paid',
        'outstanding_amount',
        'payment_method',
        'created_at',
    ]
    list_filter = [
        'bill_status',
        'payment_method',
        'created_at',
    ]
    search_fields = [
        'source_service_code',
        'source_service_name',
        'visit__id',
        'visit__patient__patient_id',
    ]
    readonly_fields = [
        'source_service_code',
        'source_service_name',
        'outstanding_amount',
        'bill_status',
        'paid_at',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Service Information', {
            'fields': (
                'service_catalog',
                'source_service_code',
                'source_service_name',
            )
        }),
        ('Relationships', {
            'fields': (
                'visit',
                'consultation',
            )
        }),
        ('Billing Details', {
            'fields': (
                'amount',
                'bill_status',
                'amount_paid',
                'outstanding_amount',
                'payment_method',
            )
        }),
        ('Audit', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
                'paid_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of paid items."""
        if obj and obj.is_immutable():
            return False
        return super().has_delete_permission(request, obj)
    
    def has_change_permission(self, request, obj=None):
        """Prevent modification of paid items."""
        if obj and obj.is_immutable():
            return False
        return super().has_change_permission(request, obj)


@admin.register(ServiceCatalog)
class ServiceCatalogAdmin(admin.ModelAdmin):
    """
    Admin interface for Service Catalog.
    
    ServiceCatalog defines billable and workflow-triggering services.
    """
    list_display = [
        'service_code',
        'name',
        'department',
        'category',
        'workflow_type',
        'amount',
        'is_active',
        'auto_bill',
        'bill_timing',
        'created_at',
    ]
    list_filter = [
        'department',
        'category',
        'workflow_type',
        'is_active',
        'auto_bill',
        'bill_timing',
        'requires_visit',
        'requires_consultation',
        'created_at',
    ]
    search_fields = [
        'service_code',
        'name',
        'description',
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'service_code',
                'name',
                'description',
                'department',
                'category',
                'amount',
            )
        }),
        ('Workflow Configuration', {
            'fields': (
                'workflow_type',
                'requires_visit',
                'requires_consultation',
            )
        }),
        ('Billing Configuration', {
            'fields': (
                'auto_bill',
                'bill_timing',
            )
        }),
        ('Access Control', {
            'fields': (
                'allowed_roles',
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
            )
        }),
        ('Metadata', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make created_at and updated_at readonly."""
        return self.readonly_fields


@admin.register(LeakRecord)
class LeakRecordAdmin(admin.ModelAdmin):
    """
    Admin interface for Revenue Leak Records.
    
    LeakRecords track revenue leaks detected in the system.
    """
    list_display = [
        'id',
        'entity_type',
        'entity_id',
        'service_code',
        'service_name',
        'estimated_amount',
        'visit',
        'detected_at',
        'resolved_at',
        'resolved_by',
        'is_resolved_display',
    ]
    list_filter = [
        'entity_type',
        'detected_at',
        'resolved_at',
    ]
    search_fields = [
        'service_code',
        'service_name',
        'visit__id',
        'entity_id',
    ]
    readonly_fields = [
        'entity_type',
        'entity_id',
        'service_code',
        'service_name',
        'estimated_amount',
        'visit',
        'detected_at',
        'detection_context',
    ]
    date_hierarchy = 'detected_at'
    
    fieldsets = (
        ('Leak Information', {
            'fields': (
                'entity_type',
                'entity_id',
                'service_code',
                'service_name',
                'estimated_amount',
            )
        }),
        ('Visit Context', {
            'fields': (
                'visit',
            )
        }),
        ('Detection', {
            'fields': (
                'detected_at',
                'detection_context',
            )
        }),
        ('Resolution', {
            'fields': (
                'resolved_at',
                'resolved_by',
                'resolution_notes',
            )
        }),
    )
    
    def is_resolved_display(self, obj):
        """Display resolved status."""
        return "Yes" if obj.is_resolved() else "No"
    is_resolved_display.short_description = "Resolved"
    
    def has_add_permission(self, request):
        """Disable manual creation - leaks are detected automatically."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deletion - leaks are immutable for audit compliance."""
        return False
    
    actions = ['mark_as_resolved']
    
    def mark_as_resolved(self, request, queryset):
        """Mark selected leaks as resolved."""
        from django.utils import timezone
        
        unresolved = queryset.filter(resolved_at__isnull=True)
        count = 0
        
        for leak in unresolved:
            leak.resolve(
                user=request.user,
                notes=f"Bulk resolved by {request.user.get_full_name()}"
            )
            count += 1
        
        self.message_user(
            request,
            f"{count} leak(s) marked as resolved."
        )
    mark_as_resolved.short_description = "Mark selected leaks as resolved"


@admin.register(EndOfDayReconciliation)
class EndOfDayReconciliationAdmin(admin.ModelAdmin):
    """
    Admin interface for End-of-Day Reconciliation.
    
    Reconciliations are immutable once finalized.
    """
    list_display = [
        'id',
        'reconciliation_date',
        'status',
        'total_revenue',
        'total_cash',
        'total_wallet',
        'total_paystack',
        'total_hmo',
        'total_outstanding',
        'revenue_leaks_detected',
        'prepared_by',
        'finalized_by',
        'finalized_at',
    ]
    list_filter = [
        'status',
        'reconciliation_date',
        'has_mismatches',
        'finalized_at',
    ]
    search_fields = [
        'reconciliation_date',
        'notes',
        'prepared_by__username',
        'finalized_by__username',
    ]
    readonly_fields = [
        'reconciliation_date',
        'total_revenue',
        'total_cash',
        'total_wallet',
        'total_paystack',
        'total_hmo',
        'total_insurance',
        'total_outstanding',
        'outstanding_visits_count',
        'revenue_leaks_detected',
        'revenue_leaks_amount',
        'total_visits',
        'active_visits_closed',
        'has_mismatches',
        'mismatch_details',
        'reconciliation_details',
        'prepared_by',
        'prepared_at',
        'reviewed_by',
        'reviewed_at',
        'finalized_by',
        'finalized_at',
    ]
    date_hierarchy = 'reconciliation_date'
    
    fieldsets = (
        ('Date and Status', {
            'fields': (
                'reconciliation_date',
                'status',
            )
        }),
        ('Revenue Totals', {
            'fields': (
                'total_revenue',
                'total_cash',
                'total_wallet',
                'total_paystack',
                'total_hmo',
                'total_insurance',
            )
        }),
        ('Outstanding Balances', {
            'fields': (
                'total_outstanding',
                'outstanding_visits_count',
            )
        }),
        ('Revenue Leaks', {
            'fields': (
                'revenue_leaks_detected',
                'revenue_leaks_amount',
            )
        }),
        ('Visit Statistics', {
            'fields': (
                'total_visits',
                'active_visits_closed',
            )
        }),
        ('Mismatches', {
            'fields': (
                'has_mismatches',
                'mismatch_details',
            )
        }),
        ('Staff Sign-off', {
            'fields': (
                'prepared_by',
                'prepared_at',
                'reviewed_by',
                'reviewed_at',
                'finalized_by',
                'finalized_at',
            )
        }),
        ('Details', {
            'fields': (
                'reconciliation_details',
                'notes',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation - use API endpoint."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Only allow editing notes for finalized reconciliations."""
        if obj and obj.status == 'FINALIZED':
            # Only notes can be edited
            return True
        return super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of finalized reconciliations."""
        if obj and obj.status == 'FINALIZED':
            return False
        return super().has_delete_permission(request, obj)
