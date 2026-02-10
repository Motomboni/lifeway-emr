"""
Reporting Views

Provides advanced reporting and analytics endpoints.
Per EMR Rules: Visit-scoped, role-based access.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal
from apps.visits.models import Visit
from apps.consultations.models import Consultation
from apps.billing.models import Payment
from apps.laboratory.models import LabOrder, LabResult
from apps.radiology.models import RadiologyOrder, RadiologyResult
from apps.pharmacy.models import Prescription
from apps.appointments.models import Appointment
from apps.patients.models import Patient


class ReportViewSet(viewsets.ViewSet):
    """
    ViewSet for generating reports.
    
    Endpoint: /api/v1/reports/
    """
    permission_classes = [IsAuthenticated]

    def _parse_date_range(self, request):
        """
        Accepts either start_date/end_date or date_from/date_to.
        Returns (from_datetime, to_datetime, raw_from, raw_to).
        """
        date_from = request.query_params.get('date_from') or request.query_params.get('start_date')
        date_to = request.query_params.get('date_to') or request.query_params.get('end_date')

        from_datetime = None
        to_datetime = None
        if date_from:
            try:
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                from_datetime = timezone.make_aware(datetime.combine(from_date, datetime.min.time()))
            except ValueError:
                from_datetime = None
        if date_to:
            try:
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                to_datetime = timezone.make_aware(datetime.combine(to_date, datetime.max.time()))
            except ValueError:
                to_datetime = None

        return from_datetime, to_datetime, date_from, date_to

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """
        Summary report used by Reports & Analytics page.
        Query params:
        - start_date / end_date (preferred by frontend)
        - or date_from / date_to
        """
        from_datetime, to_datetime, date_from, date_to = self._parse_date_range(request)

        visits_qs = Visit.objects.all()
        payments_qs = Payment.objects.filter(status='CLEARED')
        patients_qs = Patient.objects.all()

        if from_datetime:
            visits_qs = visits_qs.filter(created_at__gte=from_datetime)
            payments_qs = payments_qs.filter(created_at__gte=from_datetime)
            patients_qs = patients_qs.filter(created_at__gte=from_datetime)
        if to_datetime:
            visits_qs = visits_qs.filter(created_at__lte=to_datetime)
            payments_qs = payments_qs.filter(created_at__lte=to_datetime)
            patients_qs = patients_qs.filter(created_at__lte=to_datetime)

        total_revenue = payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0')
        total_visits = visits_qs.count()
        total_patients = patients_qs.count()

        revenue_by_method = {}
        for row in payments_qs.values('payment_method').annotate(total=Sum('amount')):
            revenue_by_method[row['payment_method']] = float(row['total'] or 0)

        visits_by_status = {}
        for row in visits_qs.values('status').annotate(count=Count('id')):
            visits_by_status[row['status']] = int(row['count'] or 0)

        revenue_trend = []
        for row in (
            payments_qs
            .annotate(day=TruncDate('created_at'))
            .values('day')
            .annotate(total=Sum('amount'))
            .order_by('day')
        ):
            revenue_trend.append({
                'date': row['day'].isoformat(),
                'revenue': float(row['total'] or 0),
            })

        return Response({
            'total_revenue': float(total_revenue),
            'total_visits': total_visits,
            'total_patients': total_patients,
            'revenue_by_method': revenue_by_method,
            'visits_by_status': visits_by_status,
            'revenue_trend': revenue_trend,
            'period': {
                'from': date_from,
                'to': date_to,
            }
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='visits-summary')
    def visits_summary(self, request):
        """
        Generate visits summary report.
        
        Query params:
        - date_from: Start date (YYYY-MM-DD)
        - date_to: End date (YYYY-MM-DD)
        - status: Filter by status
        """
        import logging
        logger = logging.getLogger(__name__)
        
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        status_filter = request.query_params.get('status')
        
        logger.info(f"Visits summary request - date_from: {date_from}, date_to: {date_to}, status: {status_filter}")
        
        queryset = Visit.objects.all()
        
        # Parse and filter by date range
        if date_from:
            try:
                # Parse date and set to start of day in UTC
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                from_datetime = timezone.make_aware(datetime.combine(from_date, datetime.min.time()))
                queryset = queryset.filter(created_at__gte=from_datetime)
                logger.info(f"Filtered visits from: {from_datetime} (UTC)")
            except ValueError as e:
                logger.warning(f"Invalid date_from format: {date_from}, error: {e}")
        
        if date_to:
            try:
                # Parse date and set to end of day (23:59:59.999999) in UTC
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                to_datetime = timezone.make_aware(datetime.combine(to_date, datetime.max.time()))
                queryset = queryset.filter(created_at__lte=to_datetime)
                logger.info(f"Filtered visits to: {to_datetime} (UTC)")
            except ValueError as e:
                logger.warning(f"Invalid date_to format: {date_to}, error: {e}")
        
        # Log the actual queryset count before filtering by status
        logger.info(f"Queryset count after date filtering: {queryset.count()}")
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            logger.debug(f"Filtered visits by status: {status_filter}")
        
        total_visits = queryset.count()
        open_visits = queryset.filter(status='OPEN').count()
        closed_visits = queryset.filter(status='CLOSED').count()
        
        # Log sample visit dates for debugging
        sample_visits = queryset[:5]
        logger.info(f"Sample visit dates: {[v.created_at for v in sample_visits]}")
        logger.info(f"Visits summary result - total: {total_visits}, open: {open_visits}, closed: {closed_visits}")
        
        return Response({
            'total_visits': total_visits,
            'open_visits': open_visits,
            'closed_visits': closed_visits,
            'period': {
                'from': date_from,
                'to': date_to,
            }
        })
    
    @action(detail=False, methods=['get'], url_path='payments-summary')
    def payments_summary(self, request):
        """
        Generate payments summary report.
        
        Query params:
        - date_from: Start date (YYYY-MM-DD)
        - date_to: End date (YYYY-MM-DD)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        logger.info(f"Payments summary request - date_from: {date_from}, date_to: {date_to}")
        
        queryset = Payment.objects.all()
        logger.info(f"Total payments in database: {queryset.count()}")
        
        # Parse and filter by date range
        if date_from:
            try:
                # Parse date and set to start of day
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                from_datetime = timezone.make_aware(datetime.combine(from_date, datetime.min.time()))
                queryset = queryset.filter(created_at__gte=from_datetime)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        if date_to:
            try:
                # Parse date and set to end of day (23:59:59.999999)
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                to_datetime = timezone.make_aware(datetime.combine(to_date, datetime.max.time()))
                queryset = queryset.filter(created_at__lte=to_datetime)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        total_payments = queryset.count()
        total_amount = queryset.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
        cleared_payments = queryset.filter(status='CLEARED').count()
        pending_payments = queryset.filter(status__in=['PENDING', 'PARTIAL']).count()
        
        logger.info(f"Payments summary result - total: {total_payments}, amount: {total_amount}, cleared: {cleared_payments}, pending: {pending_payments}")
        
        # Group by payment method
        by_method = queryset.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount')
        )
        
        # Convert Decimal to string for JSON serialization
        by_method_list = []
        for method in by_method:
            by_method_list.append({
                'payment_method': method['payment_method'],
                'count': method['count'],
                'total': str(method['total'] or '0'),
            })
        
        return Response({
            'total_payments': total_payments,
            'total_amount': str(total_amount),
            'cleared_payments': cleared_payments,
            'pending_payments': pending_payments,
            'by_method': by_method_list,
            'period': {
                'from': date_from,
                'to': date_to,
            }
        })
    
    @action(detail=False, methods=['get'], url_path='consultations-summary')
    def consultations_summary(self, request):
        """
        Generate consultations summary report.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        logger.info(f"Consultations summary request - date_from: {date_from}, date_to: {date_to}")
        
        queryset = Consultation.objects.all()
        logger.info(f"Total consultations in database: {queryset.count()}")
        
        # Parse and filter by date range
        if date_from:
            try:
                # Parse date and set to start of day
                from_date = datetime.strptime(date_from, '%Y-%m-%d').date()
                from_datetime = timezone.make_aware(datetime.combine(from_date, datetime.min.time()))
                queryset = queryset.filter(created_at__gte=from_datetime)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        if date_to:
            try:
                # Parse date and set to end of day (23:59:59.999999)
                to_date = datetime.strptime(date_to, '%Y-%m-%d').date()
                to_datetime = timezone.make_aware(datetime.combine(to_date, datetime.max.time()))
                queryset = queryset.filter(created_at__lte=to_datetime)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        total_consultations = queryset.count()
        
        logger.info(f"Consultations summary result - total: {total_consultations}")
        
        # Group by doctor
        by_doctor = queryset.values('created_by__first_name', 'created_by__last_name').annotate(
            count=Count('id')
        )
        
        return Response({
            'total_consultations': total_consultations,
            'by_doctor': list(by_doctor),
            'period': {
                'from': date_from,
                'to': date_to,
            }
        })
    
    @action(detail=False, methods=['get'], url_path='dashboard-stats')
    def dashboard_stats(self, request):
        """
        Generate comprehensive dashboard statistics.
        
        Returns:
        - Overall statistics
        - Daily/weekly/monthly trends
        - Role-specific metrics
        """
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Overall statistics
        total_patients = Patient.objects.filter(is_active=True).count()
        total_visits = Visit.objects.count()
        open_visits = Visit.objects.filter(status='OPEN').count()
        closed_visits = Visit.objects.filter(status='CLOSED').count()
        
        # Today's statistics
        today_visits = Visit.objects.filter(created_at__date=today).count()
        today_consultations = Consultation.objects.filter(created_at__date=today).count()
        today_appointments = Appointment.objects.filter(appointment_date__date=today).count()
        
        # Weekly statistics
        week_visits = Visit.objects.filter(created_at__gte=week_ago).count()
        week_consultations = Consultation.objects.filter(created_at__gte=week_ago).count()
        week_payments = Payment.objects.filter(created_at__gte=week_ago).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # Monthly statistics
        month_visits = Visit.objects.filter(created_at__gte=month_ago).count()
        month_consultations = Consultation.objects.filter(created_at__gte=month_ago).count()
        month_payments = Payment.objects.filter(created_at__gte=month_ago).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        
        # Pending orders
        pending_lab_orders = LabOrder.objects.filter(status__in=['ORDERED', 'SAMPLE_COLLECTED']).count()
        pending_radiology_orders = RadiologyOrder.objects.filter(status__in=['ORDERED', 'SCHEDULED']).count()
        pending_prescriptions = Prescription.objects.filter(status='PENDING').count()
        
        # Upcoming appointments
        upcoming_appointments = Appointment.objects.filter(
            appointment_date__gte=now,
            status__in=['SCHEDULED', 'CONFIRMED']
        ).count()
        
        # Daily trend (last 7 days)
        daily_visits = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = Visit.objects.filter(created_at__date=date).count()
            daily_visits.append({
                'date': date.isoformat(),
                'count': count
            })
        daily_visits.reverse()
        
        return Response({
            'overall': {
                'total_patients': total_patients,
                'total_visits': total_visits,
                'open_visits': open_visits,
                'closed_visits': closed_visits,
            },
            'today': {
                'visits': today_visits,
                'consultations': today_consultations,
                'appointments': today_appointments,
            },
            'weekly': {
                'visits': week_visits,
                'consultations': week_consultations,
                'payments': week_payments,
            },
            'monthly': {
                'visits': month_visits,
                'consultations': month_consultations,
                'payments': month_payments,
            },
            'pending': {
                'lab_orders': pending_lab_orders,
                'radiology_orders': pending_radiology_orders,
                'prescriptions': pending_prescriptions,
            },
            'appointments': {
                'upcoming': upcoming_appointments,
            },
            'trends': {
                'daily_visits': daily_visits,
            }
        })
    
    @action(detail=False, methods=['get'], url_path='patient-statistics')
    def patient_statistics(self, request):
        """
        Generate patient statistics.
        """
        total_patients = Patient.objects.filter(is_active=True).count()
        new_patients_today = Patient.objects.filter(created_at__date=timezone.now().date()).count()
        new_patients_week = Patient.objects.filter(created_at__gte=timezone.now().date() - timedelta(days=7)).count()
        new_patients_month = Patient.objects.filter(created_at__gte=timezone.now().date() - timedelta(days=30)).count()
        
        # Age distribution
        age_groups = {
            '0-18': Patient.objects.filter(
                date_of_birth__gte=timezone.now().date() - timedelta(days=365*18)
            ).count(),
            '19-35': Patient.objects.filter(
                date_of_birth__gte=timezone.now().date() - timedelta(days=365*35),
                date_of_birth__lt=timezone.now().date() - timedelta(days=365*18)
            ).count(),
            '36-50': Patient.objects.filter(
                date_of_birth__gte=timezone.now().date() - timedelta(days=365*50),
                date_of_birth__lt=timezone.now().date() - timedelta(days=365*35)
            ).count(),
            '51-65': Patient.objects.filter(
                date_of_birth__gte=timezone.now().date() - timedelta(days=365*65),
                date_of_birth__lt=timezone.now().date() - timedelta(days=365*50)
            ).count(),
            '65+': Patient.objects.filter(
                date_of_birth__lt=timezone.now().date() - timedelta(days=365*65)
            ).count(),
        }
        
        # Gender distribution
        gender_dist = Patient.objects.values('gender').annotate(count=Count('id'))
        
        return Response({
            'total_patients': total_patients,
            'new_patients': {
                'today': new_patients_today,
                'week': new_patients_week,
                'month': new_patients_month,
            },
            'age_distribution': age_groups,
            'gender_distribution': list(gender_dist),
        })
    
    @action(detail=False, methods=['get'], url_path='clinical-statistics')
    def clinical_statistics(self, request):
        """
        Generate clinical statistics (lab, radiology, prescriptions).
        """
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        # Lab statistics
        lab_queryset = LabOrder.objects.all()
        if date_from:
            lab_queryset = lab_queryset.filter(created_at__gte=date_from)
        if date_to:
            lab_queryset = lab_queryset.filter(created_at__lte=date_to)
        
        total_lab_orders = lab_queryset.count()
        lab_orders_by_status = lab_queryset.values('status').annotate(count=Count('id'))
        total_lab_results = LabResult.objects.filter(
            lab_order__in=lab_queryset
        ).count()
        
        # Radiology statistics
        radiology_queryset = RadiologyOrder.objects.all()
        if date_from:
            radiology_queryset = radiology_queryset.filter(created_at__gte=date_from)
        if date_to:
            radiology_queryset = radiology_queryset.filter(created_at__lte=date_to)
        
        total_radiology_orders = radiology_queryset.count()
        radiology_orders_by_status = radiology_queryset.values('status').annotate(count=Count('id'))
        total_radiology_results = RadiologyResult.objects.filter(
            radiology_order__in=radiology_queryset
        ).count()
        
        # Prescription statistics
        prescription_queryset = Prescription.objects.all()
        if date_from:
            prescription_queryset = prescription_queryset.filter(created_at__gte=date_from)
        if date_to:
            prescription_queryset = prescription_queryset.filter(created_at__lte=date_to)
        
        total_prescriptions = prescription_queryset.count()
        prescriptions_by_status = prescription_queryset.values('status').annotate(count=Count('id'))
        
        return Response({
            'lab': {
                'total_orders': total_lab_orders,
                'total_results': total_lab_results,
                'by_status': list(lab_orders_by_status),
            },
            'radiology': {
                'total_orders': total_radiology_orders,
                'total_results': total_radiology_results,
                'by_status': list(radiology_orders_by_status),
            },
            'prescriptions': {
                'total': total_prescriptions,
                'by_status': list(prescriptions_by_status),
            },
            'period': {
                'from': date_from,
                'to': date_to,
            }
        })

