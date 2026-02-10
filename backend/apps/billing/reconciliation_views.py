"""
API views for End-of-Day Reconciliation.
"""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.utils import timezone

from .reconciliation_models import EndOfDayReconciliation
from .reconciliation_serializers import (
    EndOfDayReconciliationSerializer,
    ReconciliationCreateSerializer,
    ReconciliationFinalizeSerializer,
)
from .reconciliation_service import ReconciliationService
from rest_framework.permissions import IsAdminUser
from apps.users.models import User

logger = logging.getLogger(__name__)


class EndOfDayReconciliationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for End-of-Day Reconciliation.
    
    Only Admin and Receptionist can create/finalize reconciliations.
    """
    serializer_class = EndOfDayReconciliationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Check permissions and return queryset."""
        # Check if user is Admin or Receptionist
        if not hasattr(self.request.user, 'role') or self.request.user.role not in ['ADMIN', 'RECEPTIONIST']:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only Admin and Receptionist can access reconciliations.")
        
        return super().get_queryset()
    queryset = EndOfDayReconciliation.objects.all()
    filterset_fields = ['reconciliation_date', 'status']
    search_fields = ['notes']
    ordering = ['-reconciliation_date']
    
    def get_queryset(self):
        """Get queryset with optional date filter."""
        queryset = super().get_queryset()
        
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            queryset = queryset.filter(reconciliation_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(reconciliation_date__lte=end_date)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Create a new reconciliation.
        
        This triggers the reconciliation process.
        """
        serializer = ReconciliationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            reconciliation = ReconciliationService.create_reconciliation(
                reconciliation_date=serializer.validated_data.get('reconciliation_date'),
                prepared_by_id=request.user.id,
                close_active_visits=serializer.validated_data.get('close_active_visits', True)
            )
            
            response_serializer = EndOfDayReconciliationSerializer(reconciliation)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating reconciliation: {e}", exc_info=True)
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Full traceback: {error_details}")
            return Response(
                {'error': f'Failed to create reconciliation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """
        Update reconciliation (only notes can be updated if finalized).
        """
        instance = self.get_object()
        
        if instance.status == 'FINALIZED':
            # Only allow updating notes for finalized reconciliations
            notes = request.data.get('notes')
            if notes is not None:
                instance.notes = notes
                instance.save()
                serializer = self.get_serializer(instance)
                return Response(serializer.data)
            else:
                return Response(
                    {'error': 'Only notes can be updated for finalized reconciliations'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete reconciliation (only if not finalized).
        """
        instance = self.get_object()
        
        if instance.status == 'FINALIZED':
            return Response(
                {'error': 'Cannot delete a finalized reconciliation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """
        Finalize a reconciliation.
        
        Once finalized, the reconciliation cannot be edited (except notes).
        """
        serializer = ReconciliationFinalizeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            reconciliation = self.get_object()
            
            # Update notes if provided
            if 'notes' in serializer.validated_data:
                reconciliation.notes = serializer.validated_data['notes']
            
            reconciliation.finalize(request.user)
            
            response_serializer = EndOfDayReconciliationSerializer(reconciliation)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error finalizing reconciliation: {e}")
            return Response(
                {'error': 'Failed to finalize reconciliation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """
        Refresh reconciliation calculations.
        
        This re-calculates all totals and statistics.
        """
        try:
            reconciliation = ReconciliationService.refresh_reconciliation(pk)
            response_serializer = EndOfDayReconciliationSerializer(reconciliation)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error refreshing reconciliation: {e}")
            return Response(
                {'error': 'Failed to refresh reconciliation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get reconciliation for today."""
        reconciliation = ReconciliationService.get_reconciliation_for_date()
        
        if not reconciliation:
            return Response(
                {'message': 'No reconciliation found for today'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = EndOfDayReconciliationSerializer(reconciliation)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary of all reconciliations."""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = self.get_queryset()
        
        if start_date:
            queryset = queryset.filter(reconciliation_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(reconciliation_date__lte=end_date)
        
        reconciliations = queryset.filter(status='FINALIZED')
        
        summary = {
            'total_reconciliations': reconciliations.count(),
            'total_revenue': float(sum(r.total_revenue for r in reconciliations)),
            'total_cash': float(sum(r.total_cash for r in reconciliations)),
            'total_wallet': float(sum(r.total_wallet for r in reconciliations)),
            'total_paystack': float(sum(r.total_paystack for r in reconciliations)),
            'total_hmo': float(sum(r.total_hmo for r in reconciliations)),
            'total_insurance': float(sum(r.total_insurance for r in reconciliations)),
            'total_outstanding': float(sum(r.total_outstanding for r in reconciliations)),
            'total_revenue_leaks': float(sum(r.revenue_leaks_amount for r in reconciliations)),
        }
        
        return Response(summary)

