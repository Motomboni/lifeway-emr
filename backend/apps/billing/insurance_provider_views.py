"""
Insurance Provider ViewSet - for managing insurance providers.

Per EMR Rules:
- Receptionist-only access
- Used for patient registration and billing
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from .bill_models import InsuranceProvider
from .permissions import CanProcessPayment
from core.audit import AuditLog


class InsuranceProviderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Insurance Provider - read-only for most users.
    
    Endpoint: /api/v1/billing/insurance-providers/
    
    Rules enforced:
    - List/Retrieve: Authenticated users (for patient registration)
    - Create/Update/Delete: Receptionist only (via admin or separate endpoint)
    """
    
    queryset = InsuranceProvider.objects.filter(is_active=True).order_by('name')
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ['list', 'retrieve']:
            # Allow authenticated users to view providers (needed for registration)
            permission_classes = [IsAuthenticated]
        else:
            # Create/Update/Delete: Receptionist only
            permission_classes = [CanProcessPayment]
        
        return [permission() for permission in permission_classes]
    
    def get_serializer_class(self):
        """Return serializer for InsuranceProvider."""
        from rest_framework import serializers
        
        class InsuranceProviderSerializer(serializers.ModelSerializer):
            class Meta:
                model = InsuranceProvider
                fields = ['id', 'name', 'code', 'contact_person', 'contact_phone', 'contact_email', 'is_active']
                read_only_fields = fields
        
        return InsuranceProviderSerializer

