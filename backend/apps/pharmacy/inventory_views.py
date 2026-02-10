"""
Inventory ViewSets - inventory management.

Endpoint: /api/v1/inventory/

Enforcement:
1. Pharmacist-only access (create, update, delete)
2. All authenticated users can view (for reference)
3. Audit logging mandatory
4. Low stock alerts
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q, F
from django.utils import timezone

from .models import DrugInventory, StockMovement
from .serializers import (
    DrugInventorySerializer,
    DrugInventoryCreateSerializer,
    DrugInventoryUpdateSerializer,
    StockMovementSerializer,
    StockMovementCreateSerializer,
)
from .permissions import CanManageDrugs
from core.audit import AuditLog


def log_inventory_action(
    user,
    action,
    inventory_id,
    request=None,
    metadata=None
):
    """
    Log an inventory action to audit log.
    """
    user_role = getattr(user, 'role', None)
    if not user_role:
        user_role = getattr(user, 'get_role', lambda: None)()
    if not user_role:
        user_role = 'UNKNOWN'
    
    ip_address = None
    user_agent = ''
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    AuditLog.objects.create(
        user=user,
        user_role=user_role,
        action=f'inventory.{action}',
        resource_type='drug_inventory',
        resource_id=inventory_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata or {}
    )


class DrugInventoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Drug Inventory management.
    
    Rules enforced:
    - Pharmacist: Full access (create, update, delete)
    - All authenticated users: Read-only access
    - Audit logging
    - Low stock alerts
    """
    
    queryset = DrugInventory.objects.all().select_related(
        'drug', 'last_restocked_by'
    )
    permission_classes = [CanManageDrugs]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return DrugInventoryCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DrugInventoryUpdateSerializer
        return DrugInventorySerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [CanManageDrugs()]
        else:
            # Read operations: Allow all authenticated users
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by drug
        drug_id = self.request.query_params.get('drug', None)
        if drug_id:
            queryset = queryset.filter(drug_id=drug_id)
        
        # Filter by low stock
        low_stock = self.request.query_params.get('low_stock', None)
        if low_stock == 'true':
            queryset = queryset.filter(current_stock__lte=F('reorder_level'))
        
        # Filter by out of stock
        out_of_stock = self.request.query_params.get('out_of_stock', None)
        if out_of_stock == 'true':
            queryset = queryset.filter(current_stock__lte=0)
        
        # Search by drug name
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(drug__name__icontains=search) |
                Q(drug__drug_code__icontains=search) |
                Q(batch_number__icontains=search)
            )
        
        return queryset.order_by('drug__name')
    
    def perform_create(self, serializer):
        """Create inventory record with audit logging."""
        inventory = serializer.save()
        
        log_inventory_action(
            user=self.request.user,
            action='create',
            inventory_id=inventory.id,
            request=self.request,
            metadata={
                'drug_id': inventory.drug_id,
                'current_stock': str(inventory.current_stock),
                'reorder_level': str(inventory.reorder_level),
            }
        )
        
        return inventory
    
    def perform_update(self, serializer):
        """Update inventory record with audit logging."""
        old_stock = serializer.instance.current_stock
        inventory = serializer.save()
        
        log_inventory_action(
            user=self.request.user,
            action='update',
            inventory_id=inventory.id,
            request=self.request,
            metadata={
                'drug_id': inventory.drug_id,
                'old_stock': str(old_stock),
                'new_stock': str(inventory.current_stock),
            }
        )
        
        return inventory
    
    def perform_destroy(self, instance):
        """Delete inventory record with audit logging."""
        log_inventory_action(
            user=self.request.user,
            action='delete',
            inventory_id=instance.id,
            request=self.request,
            metadata={
                'drug_id': instance.drug_id,
            }
        )
        
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get all inventory items with low stock."""
        queryset = self.get_queryset().filter(
            current_stock__lte=F('reorder_level')
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        """Get all inventory items that are out of stock."""
        queryset = self.get_queryset().filter(
            current_stock__lte=0
        )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def restock(self, request, pk=None):
        """Restock inventory (add stock)."""
        inventory = self.get_object()
        quantity = request.data.get('quantity', None)
        reference_number = request.data.get('reference_number', '')
        notes = request.data.get('notes', '')
        
        if not quantity or float(quantity) <= 0:
            return Response(
                {'error': 'Quantity must be positive.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create stock movement
        movement = StockMovement.objects.create(
            inventory=inventory,
            movement_type='IN',
            quantity=abs(float(quantity)),
            reference_number=reference_number,
            notes=notes,
            created_by=request.user
        )
        
        log_inventory_action(
            user=request.user,
            action='restock',
            inventory_id=inventory.id,
            request=request,
            metadata={
                'quantity': str(quantity),
                'movement_id': movement.id,
            }
        )
        
        serializer = self.get_serializer(inventory)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def adjust(self, request, pk=None):
        """Adjust inventory (can be positive or negative)."""
        inventory = self.get_object()
        quantity = request.data.get('quantity', None)
        reason = request.data.get('reason', '')
        notes = request.data.get('notes', '')
        
        if quantity is None or float(quantity) == 0:
            return Response(
                {'error': 'Quantity cannot be zero.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create stock movement
        movement = StockMovement.objects.create(
            inventory=inventory,
            movement_type='ADJUSTMENT',
            quantity=float(quantity),
            reference_number=reason,
            notes=notes,
            created_by=request.user
        )
        
        log_inventory_action(
            user=request.user,
            action='adjust',
            inventory_id=inventory.id,
            request=request,
            metadata={
                'quantity': str(quantity),
                'movement_id': movement.id,
            }
        )
        
        serializer = self.get_serializer(inventory)
        return Response(serializer.data)


class StockMovementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Stock Movement (read-only, movements created via inventory actions).
    
    Rules enforced:
    - All authenticated users: Read-only access
    - Movements are immutable (created via inventory actions)
    """
    
    queryset = StockMovement.objects.all().select_related(
        'inventory', 'inventory__drug', 'prescription', 'created_by'
    )
    serializer_class = StockMovementSerializer
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by inventory
        inventory_id = self.request.query_params.get('inventory', None)
        if inventory_id:
            queryset = queryset.filter(inventory_id=inventory_id)
        
        # Filter by movement type
        movement_type = self.request.query_params.get('movement_type', None)
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        
        # Filter by prescription
        prescription_id = self.request.query_params.get('prescription', None)
        if prescription_id:
            queryset = queryset.filter(prescription_id=prescription_id)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        
        date_to = self.request.query_params.get('date_to', None)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.order_by('-created_at')
