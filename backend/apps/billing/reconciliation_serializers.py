"""
Serializers for End-of-Day Reconciliation.
"""
from rest_framework import serializers
from .reconciliation_models import EndOfDayReconciliation


class EndOfDayReconciliationSerializer(serializers.ModelSerializer):
    """Serializer for EndOfDayReconciliation."""
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    prepared_by_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    finalized_by_name = serializers.SerializerMethodField()
    
    payment_method_breakdown = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    
    class Meta:
        model = EndOfDayReconciliation
        fields = [
            'id',
            'reconciliation_date',
            'status',
            'status_display',
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
            'prepared_by',
            'prepared_by_name',
            'reviewed_by',
            'reviewed_by_name',
            'finalized_by',
            'finalized_by_name',
            'prepared_at',
            'reviewed_at',
            'finalized_at',
            'notes',
            'reconciliation_details',
            'payment_method_breakdown',
            'summary',
        ]
        read_only_fields = [
            'id',
            'prepared_at',
            'reviewed_at',
            'finalized_at',
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
        ]
    
    def get_prepared_by_name(self, obj):
        """Get prepared by user's full name."""
        return obj.prepared_by.get_full_name() if obj.prepared_by else None
    
    def get_reviewed_by_name(self, obj):
        """Get reviewed by user's full name."""
        return obj.reviewed_by.get_full_name() if obj.reviewed_by else None
    
    def get_finalized_by_name(self, obj):
        """Get finalized by user's full name."""
        return obj.finalized_by.get_full_name() if obj.finalized_by else None
    
    def get_payment_method_breakdown(self, obj):
        """Get payment method breakdown."""
        return obj.get_payment_method_breakdown()
    
    def get_summary(self, obj):
        """Get reconciliation summary."""
        return obj.get_summary()


class ReconciliationCreateSerializer(serializers.Serializer):
    """Serializer for creating reconciliation."""
    
    reconciliation_date = serializers.DateField(required=False)
    close_active_visits = serializers.BooleanField(default=True)


class ReconciliationFinalizeSerializer(serializers.Serializer):
    """Serializer for finalizing reconciliation."""
    
    notes = serializers.CharField(required=False, allow_blank=True)

