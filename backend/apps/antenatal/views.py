"""
Antenatal Module API Views

Comprehensive API endpoints for antenatal clinic management.
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import (
    AntenatalRecord, AntenatalVisit, AntenatalUltrasound,
    AntenatalLab, AntenatalMedication, AntenatalOutcome
)
from .serializers import (
    AntenatalRecordListSerializer, AntenatalRecordDetailSerializer,
    AntenatalRecordCreateSerializer, AntenatalRecordUpdateSerializer,
    AntenatalVisitSerializer, AntenatalVisitCreateSerializer,
    AntenatalUltrasoundSerializer, AntenatalUltrasoundCreateSerializer,
    AntenatalLabSerializer, AntenatalLabCreateSerializer,
    AntenatalMedicationSerializer, AntenatalMedicationCreateSerializer,
    AntenatalOutcomeSerializer, AntenatalOutcomeCreateSerializer
)
from .permissions import (
    CanManageAntenatalRecords, CanRecordAntenatalVisits,
    CanManageAntenatalOutcomes
)


class AntenatalRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Antenatal Record management.
    
    Provides CRUD operations for antenatal records.
    
    Permissions:
    - DOCTOR/ADMIN: Full access (create, update records)
    - NURSE: Read-only access
    """
    
    queryset = AntenatalRecord.objects.select_related(
        'patient', 'created_by'
    ).prefetch_related('visits', 'delivery_outcome')
    
    permission_classes = [IsAuthenticated, CanManageAntenatalRecords]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['outcome', 'high_risk', 'patient', 'parity', 'pregnancy_type']
    search_fields = ['patient__first_name', 'patient__last_name', 'patient__mrn']
    ordering_fields = ['booking_date', 'created_at', 'pregnancy_number']
    ordering = ['-booking_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AntenatalRecordListSerializer
        elif self.action == 'create':
            return AntenatalRecordCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AntenatalRecordUpdateSerializer
        return AntenatalRecordDetailSerializer
    
    @action(detail=True, methods=['get'])
    def visits(self, request, pk=None):
        """Get all visits for this antenatal record."""
        record = self.get_object()
        visits = AntenatalVisit.objects.filter(antenatal_record=record).order_by('-visit_date')
        serializer = AntenatalVisitSerializer(visits, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """Get summary statistics for this antenatal record."""
        record = self.get_object()
        visits_count = AntenatalVisit.objects.filter(antenatal_record=record).count()
        ultrasounds_count = AntenatalUltrasound.objects.filter(
            antenatal_visit__antenatal_record=record
        ).count()
        labs_count = AntenatalLab.objects.filter(
            antenatal_visit__antenatal_record=record
        ).count()
        
        return Response({
            'record_id': record.id,
            'patient_name': f"{record.patient.first_name} {record.patient.last_name}",
            'pregnancy_number': record.pregnancy_number,
            'booking_date': record.booking_date,
            'lmp': record.lmp,
            'edd': record.edd,
            'current_gestational_age_weeks': record.current_gestational_age_weeks,
            'current_gestational_age_days': record.current_gestational_age_days,
            'outcome': record.outcome,
            'high_risk': record.high_risk,
            'visits_count': visits_count,
            'ultrasounds_count': ultrasounds_count,
            'labs_count': labs_count,
        })


class AntenatalVisitViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Antenatal Visit management.
    
    Permissions:
    - DOCTOR/ADMIN: Full access
    - NURSE: Can create and update visits
    """
    
    queryset = AntenatalVisit.objects.select_related(
        'antenatal_record', 'visit', 'recorded_by'
    )
    
    permission_classes = [IsAuthenticated, CanRecordAntenatalVisits]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['antenatal_record', 'visit', 'visit_type', 'visit_date']
    ordering_fields = ['visit_date', 'created_at']
    ordering = ['-visit_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AntenatalVisitCreateSerializer
        return AntenatalVisitSerializer
    
    @action(detail=True, methods=['get'])
    def ultrasounds(self, request, pk=None):
        """Get all ultrasounds for this visit."""
        visit = self.get_object()
        ultrasounds = AntenatalUltrasound.objects.filter(antenatal_visit=visit).order_by('-scan_date')
        serializer = AntenatalUltrasoundSerializer(ultrasounds, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def labs(self, request, pk=None):
        """Get all lab tests for this visit."""
        visit = self.get_object()
        labs = AntenatalLab.objects.filter(antenatal_visit=visit).order_by('-test_date')
        serializer = AntenatalLabSerializer(labs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def medications(self, request, pk=None):
        """Get all medications for this visit."""
        visit = self.get_object()
        medications = AntenatalMedication.objects.filter(antenatal_visit=visit).order_by('-start_date')
        serializer = AntenatalMedicationSerializer(medications, many=True)
        return Response(serializer.data)


class AntenatalUltrasoundViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Antenatal Ultrasound management.
    """
    
    queryset = AntenatalUltrasound.objects.select_related(
        'antenatal_visit', 'performed_by'
    )
    
    permission_classes = [IsAuthenticated, CanRecordAntenatalVisits]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['antenatal_visit', 'scan_type', 'scan_date']
    ordering_fields = ['scan_date', 'created_at']
    ordering = ['-scan_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AntenatalUltrasoundCreateSerializer
        return AntenatalUltrasoundSerializer


class AntenatalLabViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Antenatal Lab Test management.
    """
    
    queryset = AntenatalLab.objects.select_related(
        'antenatal_visit', 'ordered_by'
    )
    
    permission_classes = [IsAuthenticated, CanRecordAntenatalVisits]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['antenatal_visit', 'test_date', 'blood_group', 'rhesus']
    search_fields = ['test_name']
    ordering_fields = ['test_date', 'created_at']
    ordering = ['-test_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AntenatalLabCreateSerializer
        return AntenatalLabSerializer


class AntenatalMedicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Antenatal Medication management.
    """
    
    queryset = AntenatalMedication.objects.select_related(
        'antenatal_visit', 'prescribed_by'
    )
    
    permission_classes = [IsAuthenticated, CanRecordAntenatalVisits]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['antenatal_visit', 'category', 'start_date']
    search_fields = ['medication_name']
    ordering_fields = ['start_date', 'created_at']
    ordering = ['-start_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AntenatalMedicationCreateSerializer
        return AntenatalMedicationSerializer


class AntenatalOutcomeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Antenatal Outcome management.
    
    Permissions:
    - DOCTOR/ADMIN: Full access
    - NURSE: Read-only access
    """
    
    queryset = AntenatalOutcome.objects.select_related(
        'antenatal_record', 'recorded_by'
    )
    
    permission_classes = [IsAuthenticated, CanManageAntenatalOutcomes]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['antenatal_record', 'delivery_type', 'delivery_date']
    ordering_fields = ['delivery_date', 'created_at']
    ordering = ['-delivery_date']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AntenatalOutcomeCreateSerializer
        return AntenatalOutcomeSerializer
