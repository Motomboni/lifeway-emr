"""
Service Price List models for departmental billing.

Per EMR Rules:
- Departments CANNOT enter prices manually
- Prices are fetched automatically from price lists
- Each department has its own price list
"""
from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal


class BasePriceList(models.Model):
    """
    Abstract base model for service price lists.
    
    All departmental price lists inherit from this.
    """
    
    service_code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique service code/identifier"
    )
    
    service_name = models.CharField(
        max_length=255,
        help_text="Name of the service"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Service price"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Service description"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the service is currently available"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When service was added to price list"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When service was last updated"
    )
    
    class Meta:
        abstract = True
        ordering = ['service_code']
    
    def __str__(self):
        return f"{self.service_code} - {self.service_name} ({self.amount} NGN)"
    
    def clean(self):
        """Validate price list item."""
        if self.amount <= 0:
            raise ValidationError("Service amount must be greater than zero.")
        
        if not self.service_code or not self.service_code.strip():
            raise ValidationError("Service code is required.")
        
        if not self.service_name or not self.service_name.strip():
            raise ValidationError("Service name is required.")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class LabServicePriceList(BasePriceList):
    """
    Laboratory service price list.
    
    Stores prices for lab tests/services.
    """
    
    class Meta:
        db_table = 'lab_service_prices'
        verbose_name = 'Lab Service Price'
        verbose_name_plural = 'Lab Service Prices'
        indexes = [
            models.Index(fields=['service_code']),
            models.Index(fields=['is_active']),
        ]


class PharmacyServicePriceList(BasePriceList):
    """
    Pharmacy service price list.
    
    Stores prices for medications/drugs.
    """
    
    class Meta:
        db_table = 'pharmacy_service_prices'
        verbose_name = 'Pharmacy Service Price'
        verbose_name_plural = 'Pharmacy Service Prices'
        indexes = [
            models.Index(fields=['service_code']),
            models.Index(fields=['is_active']),
        ]


class RadiologyServicePriceList(BasePriceList):
    """
    Radiology service price list.
    
    Stores prices for radiology studies/tests.
    """
    
    class Meta:
        db_table = 'radiology_service_prices'
        verbose_name = 'Radiology Service Price'
        verbose_name_plural = 'Radiology Service Prices'
        indexes = [
            models.Index(fields=['service_code']),
            models.Index(fields=['is_active']),
        ]


class ProcedureServicePriceList(BasePriceList):
    """
    Procedure service price list.
    
    Stores prices for procedures (injections, dressings, etc.).
    """
    
    class Meta:
        db_table = 'procedure_service_prices'
        verbose_name = 'Procedure Service Price'
        verbose_name_plural = 'Procedure Service Prices'
        indexes = [
            models.Index(fields=['service_code']),
            models.Index(fields=['is_active']),
        ]


class ServicePriceListManager:
    """
    Manager class for fetching service prices by department.
    
    Provides a unified interface for accessing price lists.
    """
    
    PRICE_LIST_MODELS = {
        'LAB': LabServicePriceList,
        'PHARMACY': PharmacyServicePriceList,
        'RADIOLOGY': RadiologyServicePriceList,
        'PROCEDURE': ProcedureServicePriceList,
    }
    
    @classmethod
    def get_price(cls, department: str, service_code: str) -> dict:
        """
        Get service price by department and service code.
        
        Args:
            department: Department name (LAB, PHARMACY, RADIOLOGY, PROCEDURE)
            service_code: Service code/identifier
        
        Returns:
            dict with:
                - service_code: Service code
                - service_name: Service name
                - amount: Service price
                - description: Service description
        
        Raises:
            ValidationError: If department is invalid or service not found
        """
        department = department.upper()
        
        if department not in cls.PRICE_LIST_MODELS:
            raise ValidationError(
                f"Invalid department: {department}. "
                f"Valid departments: {', '.join(cls.PRICE_LIST_MODELS.keys())}"
            )
        
        PriceListModel = cls.PRICE_LIST_MODELS[department]
        
        try:
            service = PriceListModel.objects.get(
                service_code=service_code,
                is_active=True
            )
            return {
                'service_code': service.service_code,
                'service_name': service.service_name,
                'amount': service.amount,
                'description': service.description,
            }
        except PriceListModel.DoesNotExist:
            raise ValidationError(
                f"Service with code '{service_code}' not found in {department} price list "
                "or service is inactive."
            )
    
    @classmethod
    def list_services(cls, department: str, active_only: bool = True) -> list:
        """
        List all services for a department.
        
        Args:
            department: Department name (LAB, PHARMACY, RADIOLOGY, PROCEDURE)
            active_only: Whether to return only active services
        
        Returns:
            list of service dicts
        """
        department = department.upper()
        
        if department not in cls.PRICE_LIST_MODELS:
            raise ValidationError(
                f"Invalid department: {department}. "
                f"Valid departments: {', '.join(cls.PRICE_LIST_MODELS.keys())}"
            )
        
        PriceListModel = cls.PRICE_LIST_MODELS[department]
        
        queryset = PriceListModel.objects.all()
        if active_only:
            queryset = queryset.filter(is_active=True)
        
        return [
            {
                'service_code': service.service_code,
                'service_name': service.service_name,
                'amount': str(service.amount),
                'description': service.description,
                'is_active': service.is_active,
            }
            for service in queryset.order_by('service_code')
        ]

