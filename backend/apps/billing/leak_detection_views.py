"""
API views for Revenue Leak Detection.

Admin-only endpoints for leak detection and management.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import date

from core.permissions import IsStaffOrAdminRole
from .leak_detection_models import LeakRecord
from .leak_detection_service import LeakDetectionService
from .leak_detection_serializers import (
    LeakRecordSerializer,
    LeakRecordResolveSerializer,
    DailyAggregationSerializer
)


class LeakRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Revenue Leak Records.
    
    Admin-only access (staff or role ADMIN).
    """
    queryset = LeakRecord.objects.all()
    serializer_class = LeakRecordSerializer
    permission_classes = [IsAuthenticated, IsStaffOrAdminRole]
    
    def get_queryset(self):
        """Filter queryset based on query parameters."""
        queryset = super().get_queryset().select_related('visit', 'visit__patient', 'resolved_by')
        
        # Filter by resolved status
        resolved = self.request.query_params.get('resolved')
        if resolved is not None:
            if resolved.lower() == 'true':
                queryset = queryset.exclude(resolved_at__isnull=True)
            else:
                queryset = queryset.filter(resolved_at__isnull=True)
        
        # Filter by entity type
        entity_type = self.request.query_params.get('entity_type')
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        
        # Filter by visit
        visit_id = self.request.query_params.get('visit_id')
        if visit_id:
            queryset = queryset.filter(visit_id=visit_id)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(detected_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(detected_at__date__lte=date_to)
        
        return queryset.order_by('-detected_at')
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """
        Manually resolve a leak.
        
        POST /api/v1/billing/leaks/{id}/resolve/
        {
            "resolution_notes": "Bill was created and paid"
        }
        """
        leak = self.get_object()
        
        if leak.is_resolved():
            return Response(
                {'detail': 'Leak is already resolved.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = LeakRecordResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        leak.resolve(
            user=request.user,
            notes=serializer.validated_data.get('resolution_notes', '')
        )
        
        return Response(
            LeakRecordSerializer(leak).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def detect_all(self, request):
        """
        Run leak detection for all entities.
        
        POST /api/v1/billing/leaks/detect_all/
        """
        results = LeakDetectionService.detect_all_leaks()
        
        return Response({
            'message': 'Leak detection completed',
            'results': results
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def daily_aggregation(self, request):
        """
        Get daily aggregation of leaks.
        
        GET /api/v1/billing/leaks/daily_aggregation/?date=2026-01-10
        """
        date_param = request.query_params.get('date')
        
        if date_param:
            try:
                date_obj = date.fromisoformat(date_param)
            except ValueError:
                return Response(
                    {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            date_obj = timezone.now().date()
        
        aggregation = LeakDetectionService.get_daily_aggregation(date_obj)
        
        serializer = DailyAggregationSerializer(aggregation)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        Get summary statistics of leaks.
        
        GET /api/v1/billing/leaks/summary/
        """
        from django.db.models import Sum, Count, Q
        
        # Total leaks
        total_leaks = LeakRecord.objects.count()
        
        # Unresolved leaks
        unresolved = LeakRecord.objects.filter(resolved_at__isnull=True).aggregate(
            count=Count('id'),
            total_amount=Sum('estimated_amount')
        )
        
        # Resolved leaks
        resolved = LeakRecord.objects.filter(resolved_at__isnull=False).aggregate(
            count=Count('id'),
            total_amount=Sum('estimated_amount')
        )
        
        # By entity type
        by_entity_type = LeakRecord.objects.values('entity_type').annotate(
            count=Count('id'),
            total_amount=Sum('estimated_amount'),
            unresolved_count=Count('id', filter=Q(resolved_at__isnull=True)),
            unresolved_amount=Sum('estimated_amount', filter=Q(resolved_at__isnull=True))
        )
        
        return Response({
            'total_leaks': total_leaks,
            'unresolved': {
                'count': unresolved['count'] or 0,
                'total_amount': float(unresolved['total_amount'] or 0)
            },
            'resolved': {
                'count': resolved['count'] or 0,
                'total_amount': float(resolved['total_amount'] or 0)
            },
            'by_entity_type': list(by_entity_type)
        }, status=status.HTTP_200_OK)

