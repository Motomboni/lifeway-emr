"""
Reporting Views

Provides advanced reporting and analytics endpoints.
Per EMR Rules: Visit-scoped, role-based access.
"""

from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.appointments.models import Appointment
from apps.billing.models import Payment
from apps.consultations.models import Consultation
from apps.laboratory.models import LabOrder, LabResult
from apps.patients.models import Patient
from apps.pharmacy.models import Prescription
from apps.radiology.models import RadiologyOrder, RadiologyResult
from apps.visits.models import Visit


class ReportViewSet(viewsets.ViewSet):
    """
    ViewSet for generating reports.

    Endpoint: /api/v1/reports/
    Multi-tenant: all reports scoped by request.organization
    """

    permission_classes = [IsAuthenticated]

    def _org_filter(self, request):
        """Return Q filter for organization when org scoping is enabled."""
        if hasattr(request, "organization") and request.organization:
            return {"organization": request.organization}
        return {}

    def _parse_date_range(self, request):
        """
        Accepts either start_date/end_date or date_from/date_to.
        Returns (from_datetime, to_datetime, raw_from, raw_to).
        """
        date_from = request.query_params.get("date_from") or request.query_params.get(
            "start_date"
        )
        date_to = request.query_params.get("date_to") or request.query_params.get(
            "end_date"
        )

        from_datetime = None
        to_datetime = None
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                from_datetime = timezone.make_aware(
                    datetime.combine(from_date, datetime.min.time())
                )
            except ValueError:
                from_datetime = None
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                to_datetime = timezone.make_aware(
                    datetime.combine(to_date, datetime.max.time())
                )
            except ValueError:
                to_datetime = None

        return from_datetime, to_datetime, date_from, date_to

    def _filtered_payments(self, request):
        """Cleared payments scoped by org and optional date range."""
        from_datetime, to_datetime, _, _ = self._parse_date_range(request)
        org_filter = self._org_filter(request)
        payments_qs = Payment.objects.filter(status="CLEARED")
        if org_filter:
            payments_qs = payments_qs.filter(visit__organization=request.organization)
        if from_datetime:
            payments_qs = payments_qs.filter(created_at__gte=from_datetime)
        if to_datetime:
            payments_qs = payments_qs.filter(created_at__lte=to_datetime)
        return payments_qs

    def _filtered_visits(self, request):
        """Visits scoped by org and optional date range."""
        from_datetime, to_datetime, _, _ = self._parse_date_range(request)
        org_filter = self._org_filter(request)
        visits_qs = Visit.objects.filter(**org_filter)
        if from_datetime:
            visits_qs = visits_qs.filter(created_at__gte=from_datetime)
        if to_datetime:
            visits_qs = visits_qs.filter(created_at__lte=to_datetime)
        return visits_qs

    def _build_revenue_by_method(self, payments_qs):
        revenue_by_method = {}
        for row in payments_qs.values("payment_method").annotate(total=Sum("amount")):
            revenue_by_method[row["payment_method"]] = float(row["total"] or 0)
        return revenue_by_method

    def _build_visits_by_status(self, visits_qs):
        visits_by_status = {}
        for row in visits_qs.values("status").annotate(count=Count("id")):
            visits_by_status[row["status"]] = int(row["count"] or 0)
        return visits_by_status

    def _build_revenue_trend(self, payments_qs):
        revenue_trend = []
        for row in (
            payments_qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("amount"))
            .order_by("day")
        ):
            revenue_trend.append(
                {
                    "date": row["day"].isoformat(),
                    "revenue": float(row["total"] or 0),
                }
            )
        return revenue_trend

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        Summary report used by Reports & Analytics page.
        Query params:
        - start_date / end_date (preferred by frontend)
        - or date_from / date_to
        """
        from_datetime, to_datetime, date_from, date_to = self._parse_date_range(request)
        visits_qs = self._filtered_visits(request)
        payments_qs = self._filtered_payments(request)
        org_filter = self._org_filter(request)
        patients_qs = Patient.objects.filter(**org_filter)

        if from_datetime:
            patients_qs = patients_qs.filter(created_at__gte=from_datetime)
        if to_datetime:
            patients_qs = patients_qs.filter(created_at__lte=to_datetime)

        total_revenue = payments_qs.aggregate(total=Sum("amount"))["total"] or Decimal(
            "0"
        )
        total_visits = visits_qs.count()
        total_patients = patients_qs.count()

        revenue_by_method = self._build_revenue_by_method(payments_qs)
        visits_by_status = self._build_visits_by_status(visits_qs)
        revenue_trend = self._build_revenue_trend(payments_qs)

        return Response(
            {
                "total_revenue": float(total_revenue),
                "total_visits": total_visits,
                "total_patients": total_patients,
                "revenue_by_method": revenue_by_method,
                "visits_by_status": visits_by_status,
                "revenue_trend": revenue_trend,
                "period": {
                    "from": date_from,
                    "to": date_to,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="revenue-by-method")
    def revenue_by_method(self, request):
        """Revenue grouped by payment method for the selected date range."""
        payments_qs = self._filtered_payments(request)
        return Response(self._build_revenue_by_method(payments_qs))

    @action(detail=False, methods=["get"], url_path="revenue-trend")
    def revenue_trend(self, request):
        """Daily revenue trend for the selected date range."""
        payments_qs = self._filtered_payments(request)
        return Response(self._build_revenue_trend(payments_qs))

    @action(detail=False, methods=["get"], url_path="visits-by-status")
    def visits_by_status(self, request):
        """Visit counts grouped by status for the selected date range."""
        visits_qs = self._filtered_visits(request)
        return Response(self._build_visits_by_status(visits_qs))

    @action(detail=False, methods=["get"], url_path="visits-summary")
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

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        status_filter = request.query_params.get("status")

        logger.info(
            f"Visits summary request - date_from: {date_from}, date_to: {date_to}, status: {status_filter}"
        )

        org_filter = self._org_filter(request)
        queryset = Visit.objects.filter(**org_filter)

        # Parse and filter by date range
        if date_from:
            try:
                # Parse date and set to start of day in UTC
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                from_datetime = timezone.make_aware(
                    datetime.combine(from_date, datetime.min.time())
                )
                queryset = queryset.filter(created_at__gte=from_datetime)
                logger.info(f"Filtered visits from: {from_datetime} (UTC)")
            except ValueError as e:
                logger.warning(f"Invalid date_from format: {date_from}, error: {e}")

        if date_to:
            try:
                # Parse date and set to end of day (23:59:59.999999) in UTC
                to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                to_datetime = timezone.make_aware(
                    datetime.combine(to_date, datetime.max.time())
                )
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
        open_visits = queryset.filter(status="OPEN").count()
        closed_visits = queryset.filter(status="CLOSED").count()

        # Log sample visit dates for debugging
        sample_visits = queryset[:5]
        logger.info(f"Sample visit dates: {[v.created_at for v in sample_visits]}")
        logger.info(
            f"Visits summary result - total: {total_visits}, open: {open_visits}, closed: {closed_visits}"
        )

        return Response(
            {
                "total_visits": total_visits,
                "open_visits": open_visits,
                "closed_visits": closed_visits,
                "period": {
                    "from": date_from,
                    "to": date_to,
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="payments-summary")
    def payments_summary(self, request):
        """
        Generate payments summary report.

        Query params:
        - date_from: Start date (YYYY-MM-DD)
        - date_to: End date (YYYY-MM-DD)
        """
        import logging

        logger = logging.getLogger(__name__)

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        logger.info(
            f"Payments summary request - date_from: {date_from}, date_to: {date_to}"
        )

        org = getattr(request, "organization", None)
        queryset = Payment.objects.all()
        if org:
            queryset = queryset.filter(visit__organization=org)
        logger.info(f"Total payments in database: {queryset.count()}")

        # Parse and filter by date range
        if date_from:
            try:
                # Parse date and set to start of day
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                from_datetime = timezone.make_aware(
                    datetime.combine(from_date, datetime.min.time())
                )
                queryset = queryset.filter(created_at__gte=from_datetime)
            except ValueError:
                pass  # Invalid date format, ignore filter

        if date_to:
            try:
                # Parse date and set to end of day (23:59:59.999999)
                to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                to_datetime = timezone.make_aware(
                    datetime.combine(to_date, datetime.max.time())
                )
                queryset = queryset.filter(created_at__lte=to_datetime)
            except ValueError:
                pass  # Invalid date format, ignore filter

        total_payments = queryset.count()
        total_amount = queryset.aggregate(Sum("amount"))["amount__sum"] or Decimal("0")
        cleared_payments = queryset.filter(status="CLEARED").count()
        pending_payments = queryset.filter(status__in=["PENDING", "PARTIAL"]).count()

        logger.info(
            f"Payments summary result - total: {total_payments}, amount: {total_amount}, cleared: {cleared_payments}, pending: {pending_payments}"
        )

        # Group by payment method
        by_method = queryset.values("payment_method").annotate(
            count=Count("id"), total=Sum("amount")
        )

        # Convert Decimal to string for JSON serialization
        by_method_list = []
        for method in by_method:
            by_method_list.append(
                {
                    "payment_method": method["payment_method"],
                    "count": method["count"],
                    "total": str(method["total"] or "0"),
                }
            )

        return Response(
            {
                "total_payments": total_payments,
                "total_amount": str(total_amount),
                "cleared_payments": cleared_payments,
                "pending_payments": pending_payments,
                "by_method": by_method_list,
                "period": {
                    "from": date_from,
                    "to": date_to,
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="consultations-summary")
    def consultations_summary(self, request):
        """
        Generate consultations summary report.
        """
        import logging

        logger = logging.getLogger(__name__)

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        logger.info(
            f"Consultations summary request - date_from: {date_from}, date_to: {date_to}"
        )

        org = getattr(request, "organization", None)
        queryset = Consultation.objects.all()
        if org:
            queryset = queryset.filter(visit__organization=org)
        logger.info(f"Total consultations in database: {queryset.count()}")

        # Parse and filter by date range
        if date_from:
            try:
                # Parse date and set to start of day
                from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
                from_datetime = timezone.make_aware(
                    datetime.combine(from_date, datetime.min.time())
                )
                queryset = queryset.filter(created_at__gte=from_datetime)
            except ValueError:
                pass  # Invalid date format, ignore filter

        if date_to:
            try:
                # Parse date and set to end of day (23:59:59.999999)
                to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
                to_datetime = timezone.make_aware(
                    datetime.combine(to_date, datetime.max.time())
                )
                queryset = queryset.filter(created_at__lte=to_datetime)
            except ValueError:
                pass  # Invalid date format, ignore filter

        total_consultations = queryset.count()

        logger.info(f"Consultations summary result - total: {total_consultations}")

        # Group by doctor
        by_doctor = queryset.values(
            "created_by__first_name", "created_by__last_name"
        ).annotate(count=Count("id"))

        return Response(
            {
                "total_consultations": total_consultations,
                "by_doctor": list(by_doctor),
                "period": {
                    "from": date_from,
                    "to": date_to,
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="dashboard-stats")
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
        org_filter = self._org_filter(request)
        org = getattr(request, "organization", None)

        # Overall statistics
        total_patients = Patient.objects.filter(is_active=True, **org_filter).count()
        total_visits = Visit.objects.filter(**org_filter).count()
        open_visits = Visit.objects.filter(status="OPEN", **org_filter).count()
        closed_visits = Visit.objects.filter(status="CLOSED", **org_filter).count()

        # Today's statistics
        today_visits = Visit.objects.filter(
            created_at__date=today, **org_filter
        ).count()
        today_consultations_qs = Consultation.objects.filter(created_at__date=today)
        today_appointments_qs = Appointment.objects.filter(appointment_date__date=today)
        if org:
            today_consultations_qs = today_consultations_qs.filter(
                visit__organization=org
            )
            today_appointments_qs = today_appointments_qs.filter(
                patient__organization=org
            )
        today_consultations = today_consultations_qs.count()
        today_appointments = today_appointments_qs.count()

        # Weekly statistics
        week_visits = Visit.objects.filter(
            created_at__gte=week_ago, **org_filter
        ).count()
        week_consultations_qs = Consultation.objects.filter(created_at__gte=week_ago)
        week_payments_qs = Payment.objects.filter(created_at__gte=week_ago)
        if org:
            week_consultations_qs = week_consultations_qs.filter(
                visit__organization=org
            )
            week_payments_qs = week_payments_qs.filter(visit__organization=org)
        week_consultations = week_consultations_qs.count()
        week_payments = week_payments_qs.aggregate(
            total=Sum("amount"), count=Count("id")
        )

        # Monthly statistics
        month_visits = Visit.objects.filter(
            created_at__gte=month_ago, **org_filter
        ).count()
        month_consultations_qs = Consultation.objects.filter(created_at__gte=month_ago)
        month_payments_qs = Payment.objects.filter(created_at__gte=month_ago)
        if org:
            month_consultations_qs = month_consultations_qs.filter(
                visit__organization=org
            )
            month_payments_qs = month_payments_qs.filter(visit__organization=org)
        month_consultations = month_consultations_qs.count()
        month_payments = month_payments_qs.aggregate(
            total=Sum("amount"), count=Count("id")
        )

        # Pending orders (visit-scoped)
        pend_filter = {"visit__organization": org} if org else {}
        pending_lab_orders = LabOrder.objects.filter(
            status__in=["ORDERED", "SAMPLE_COLLECTED"], **pend_filter
        ).count()
        pending_radiology_orders = RadiologyOrder.objects.filter(
            status__in=["ORDERED", "SCHEDULED"], **pend_filter
        ).count()
        pending_prescriptions = Prescription.objects.filter(
            status="PENDING", **pend_filter
        ).count()

        # Upcoming appointments
        appt_filter = {"patient__organization": org} if org else {}
        upcoming_appointments = Appointment.objects.filter(
            appointment_date__gte=now,
            status__in=["SCHEDULED", "CONFIRMED"],
            **appt_filter,
        ).count()

        # Daily trend (last 7 days)
        daily_visits = []
        for i in range(7):
            date = today - timedelta(days=i)
            count = Visit.objects.filter(created_at__date=date, **org_filter).count()
            daily_visits.append({"date": date.isoformat(), "count": count})
        daily_visits.reverse()

        return Response(
            {
                "overall": {
                    "total_patients": total_patients,
                    "total_visits": total_visits,
                    "open_visits": open_visits,
                    "closed_visits": closed_visits,
                },
                "today": {
                    "visits": today_visits,
                    "consultations": today_consultations,
                    "appointments": today_appointments,
                },
                "weekly": {
                    "visits": week_visits,
                    "consultations": week_consultations,
                    "payments": week_payments,
                },
                "monthly": {
                    "visits": month_visits,
                    "consultations": month_consultations,
                    "payments": month_payments,
                },
                "pending": {
                    "lab_orders": pending_lab_orders,
                    "radiology_orders": pending_radiology_orders,
                    "prescriptions": pending_prescriptions,
                },
                "appointments": {
                    "upcoming": upcoming_appointments,
                },
                "trends": {
                    "daily_visits": daily_visits,
                },
            }
        )

    @action(detail=False, methods=["get"], url_path="patient-statistics")
    def patient_statistics(self, request):
        """
        Generate patient statistics.
        """
        org_filter = self._org_filter(request)
        base = Patient.objects.filter(is_active=True, **org_filter)
        total_patients = base.count()
        new_patients_today = base.filter(created_at__date=timezone.now().date()).count()
        new_patients_week = base.filter(
            created_at__gte=timezone.now().date() - timedelta(days=7)
        ).count()
        new_patients_month = base.filter(
            created_at__gte=timezone.now().date() - timedelta(days=30)
        ).count()

        # Age distribution
        age_groups = {
            "0-18": base.filter(
                date_of_birth__gte=timezone.now().date() - timedelta(days=365 * 18)
            ).count(),
            "19-35": base.filter(
                date_of_birth__gte=timezone.now().date() - timedelta(days=365 * 35),
                date_of_birth__lt=timezone.now().date() - timedelta(days=365 * 18),
            ).count(),
            "36-50": base.filter(
                date_of_birth__gte=timezone.now().date() - timedelta(days=365 * 50),
                date_of_birth__lt=timezone.now().date() - timedelta(days=365 * 35),
            ).count(),
            "51-65": base.filter(
                date_of_birth__gte=timezone.now().date() - timedelta(days=365 * 65),
                date_of_birth__lt=timezone.now().date() - timedelta(days=365 * 50),
            ).count(),
            "65+": base.filter(
                date_of_birth__lt=timezone.now().date() - timedelta(days=365 * 65)
            ).count(),
        }

        # Gender distribution
        gender_dist = base.values("gender").annotate(count=Count("id"))

        return Response(
            {
                "total_patients": total_patients,
                "new_patients": {
                    "today": new_patients_today,
                    "week": new_patients_week,
                    "month": new_patients_month,
                },
                "age_distribution": age_groups,
                "gender_distribution": list(gender_dist),
            }
        )

    @action(detail=False, methods=["get"], url_path="clinical-statistics")
    def clinical_statistics(self, request):
        """
        Generate clinical statistics (lab, radiology, prescriptions).
        """
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        org = getattr(request, "organization", None)
        visit_filter = {"visit__organization": org} if org else {}

        # Lab statistics
        lab_queryset = LabOrder.objects.filter(**visit_filter)
        if date_from:
            lab_queryset = lab_queryset.filter(created_at__gte=date_from)
        if date_to:
            lab_queryset = lab_queryset.filter(created_at__lte=date_to)

        total_lab_orders = lab_queryset.count()
        lab_orders_by_status = lab_queryset.values("status").annotate(count=Count("id"))
        total_lab_results = LabResult.objects.filter(lab_order__in=lab_queryset).count()

        # Radiology statistics
        radiology_queryset = RadiologyOrder.objects.filter(**visit_filter)
        if date_from:
            radiology_queryset = radiology_queryset.filter(created_at__gte=date_from)
        if date_to:
            radiology_queryset = radiology_queryset.filter(created_at__lte=date_to)

        total_radiology_orders = radiology_queryset.count()
        radiology_orders_by_status = radiology_queryset.values("status").annotate(
            count=Count("id")
        )
        total_radiology_results = RadiologyResult.objects.filter(
            radiology_order__in=radiology_queryset
        ).count()

        # Prescription statistics
        prescription_queryset = Prescription.objects.filter(**visit_filter)
        if date_from:
            prescription_queryset = prescription_queryset.filter(
                created_at__gte=date_from
            )
        if date_to:
            prescription_queryset = prescription_queryset.filter(
                created_at__lte=date_to
            )

        total_prescriptions = prescription_queryset.count()
        prescriptions_by_status = prescription_queryset.values("status").annotate(
            count=Count("id")
        )

        return Response(
            {
                "lab": {
                    "total_orders": total_lab_orders,
                    "total_results": total_lab_results,
                    "by_status": list(lab_orders_by_status),
                },
                "radiology": {
                    "total_orders": total_radiology_orders,
                    "total_results": total_radiology_results,
                    "by_status": list(radiology_orders_by_status),
                },
                "prescriptions": {
                    "total": total_prescriptions,
                    "by_status": list(prescriptions_by_status),
                },
                "period": {
                    "from": date_from,
                    "to": date_to,
                },
            }
        )
