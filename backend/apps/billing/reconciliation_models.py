"""
End-of-Day Reconciliation Models.

This module provides models for tracking daily reconciliation of clinic operations,
including revenue, payments, outstanding balances, and revenue leaks.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import json


class EndOfDayReconciliation(models.Model):
    """
    End-of-Day Reconciliation record.
    
    One record per day, cannot be edited once finalized.
    """
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('FINALIZED', 'Finalized'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    # Date and status
    reconciliation_date = models.DateField(
        unique=True,
        db_index=True,
        help_text="Date of reconciliation (one per day)"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        db_index=True,
        help_text="Reconciliation status"
    )
    
    # Totals
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total revenue for the day"
    )
    
    total_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total cash payments"
    )
    
    total_wallet = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total wallet payments"
    )
    
    total_paystack = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total Paystack payments"
    )
    
    total_hmo = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total HMO payments"
    )
    
    total_insurance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total insurance payments"
    )
    
    # Outstanding balances
    total_outstanding = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total outstanding balances"
    )
    
    outstanding_visits_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of visits with outstanding balances"
    )
    
    # Revenue leaks
    revenue_leaks_detected = models.PositiveIntegerField(
        default=0,
        help_text="Number of revenue leaks detected"
    )
    
    revenue_leaks_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Total amount of revenue leaks"
    )
    
    # Visit statistics
    total_visits = models.PositiveIntegerField(
        default=0,
        help_text="Total number of visits for the day"
    )
    
    active_visits_closed = models.PositiveIntegerField(
        default=0,
        help_text="Number of active visits closed during reconciliation"
    )
    
    # Mismatches
    has_mismatches = models.BooleanField(
        default=False,
        help_text="Whether there are payment mismatches"
    )
    
    mismatch_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Details of payment mismatches"
    )
    
    # Staff sign-off
    prepared_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='reconciliations_prepared',
        help_text="User who prepared the reconciliation"
    )
    
    reviewed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliations_reviewed',
        help_text="User who reviewed the reconciliation"
    )
    
    finalized_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reconciliations_finalized',
        help_text="User who finalized the reconciliation"
    )
    
    # Timestamps
    prepared_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the reconciliation was prepared"
    )
    
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the reconciliation was reviewed"
    )
    
    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the reconciliation was finalized"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the reconciliation"
    )
    
    # Reconciliation details (JSON)
    reconciliation_details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed breakdown of reconciliation"
    )
    
    class Meta:
        db_table = 'end_of_day_reconciliation'
        ordering = ['-reconciliation_date']
        indexes = [
            models.Index(fields=['reconciliation_date']),
            models.Index(fields=['status']),
            models.Index(fields=['prepared_at']),
        ]
        verbose_name = 'End of Day Reconciliation'
        verbose_name_plural = 'End of Day Reconciliations'
    
    def __str__(self):
        return f"Reconciliation for {self.reconciliation_date} - {self.status}"
    
    def clean(self):
        """Validate reconciliation."""
        errors = {}
        
        # Cannot edit finalized reconciliations
        if self.pk and self.status == 'FINALIZED':
            old_instance = EndOfDayReconciliation.objects.get(pk=self.pk)
            if old_instance.status == 'FINALIZED':
                # Check if any fields have changed
                for field in self._meta.fields:
                    if field.name in ['status', 'finalized_at', 'finalized_by', 'notes']:
                        continue  # These can be updated even when finalized
                    if getattr(self, field.name) != getattr(old_instance, field.name):
                        errors[field.name] = f"Cannot modify {field.name} after finalization."
        
        # Validate totals
        # NOTE: total_insurance is NOT included in total_revenue because it's already included in total_hmo
        # This prevents double-counting insurance payments
        calculated_total = (
            self.total_cash + self.total_wallet + self.total_paystack +
            self.total_hmo
            # total_insurance is NOT added here because it's already in total_hmo
        )
        if abs(calculated_total - self.total_revenue) > Decimal('0.01'):
            errors['total_revenue'] = (
                f"Total revenue ({self.total_revenue}) does not match sum of payment methods "
                f"({calculated_total}). Note: total_insurance is not included as it's already in total_hmo."
            )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to validate and update timestamps."""
        self.full_clean()
        
        # Update timestamps based on status
        if self.status == 'FINALIZED' and not self.finalized_at:
            self.finalized_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def finalize(self, user):
        """Finalize the reconciliation."""
        if self.status == 'FINALIZED':
            raise ValidationError("Reconciliation is already finalized.")
        
        if self.status == 'CANCELLED':
            raise ValidationError("Cannot finalize a cancelled reconciliation.")
        
        self.status = 'FINALIZED'
        self.finalized_by = user
        self.finalized_at = timezone.now()
        self.save()
    
    def cancel(self, user):
        """Cancel the reconciliation."""
        if self.status == 'FINALIZED':
            raise ValidationError("Cannot cancel a finalized reconciliation.")
        
        self.status = 'CANCELLED'
        self.save()
    
    def is_finalized(self) -> bool:
        """Check if reconciliation is finalized."""
        return self.status == 'FINALIZED'
    
    def can_edit(self) -> bool:
        """Check if reconciliation can be edited."""
        return self.status != 'FINALIZED'
    
    def get_payment_method_breakdown(self) -> dict:
        """Get breakdown of payments by method."""
        return {
            'cash': float(self.total_cash),
            'wallet': float(self.total_wallet),
            'paystack': float(self.total_paystack),
            'hmo': float(self.total_hmo),
            'insurance': float(self.total_insurance),
        }
    
    def get_summary(self) -> dict:
        """Get summary of reconciliation."""
        return {
            'date': str(self.reconciliation_date),
            'status': self.status,
            'total_revenue': float(self.total_revenue),
            'payment_methods': self.get_payment_method_breakdown(),
            'outstanding_balances': float(self.total_outstanding),
            'outstanding_visits': self.outstanding_visits_count,
            'revenue_leaks': {
                'count': self.revenue_leaks_detected,
                'amount': float(self.revenue_leaks_amount),
            },
            'visits': {
                'total': self.total_visits,
                'active_closed': self.active_visits_closed,
            },
            'has_mismatches': self.has_mismatches,
            'prepared_by': self.prepared_by.get_full_name() if self.prepared_by else None,
            'finalized_by': self.finalized_by.get_full_name() if self.finalized_by else None,
            'finalized_at': self.finalized_at.isoformat() if self.finalized_at else None,
        }

