"""
Mobile API for Patient Portal – offline-first.

- All responses include last_updated (ISO timestamp).
- Support ?updated_since=ISO8601 to return only records changed after that time.
- Conflict strategy: server wins for medical data; client wins for profile updates.
  Mobile app should store appointments, prescriptions, lab results in SQLite and sync when online.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import timedelta

from .permissions import PatientOnlyAccess
from core.audit import AuditLog


def _last_updated():
    """Current timestamp for response metadata."""
    return timezone.now().isoformat()


class MobilePagination(PageNumberPagination):
    """Pagination for mobile API - smaller page sizes."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


@api_view(['GET'])
@permission_classes([PatientOnlyAccess])
def mobile_profile(request):
    """
    GET /api/mobile/profile/
    
    Returns patient's profile information.
    """
    user = request.user
    patient = user.patient
    
    # Log access
    AuditLog.log(
        user=user,
        role=user.role,
        action="PATIENT_PROFILE_VIEWED",
        resource_type="patient",
        resource_id=patient.id,
        request=request
    )
    
    data = {
        'patient_id': patient.patient_id,
        'name': patient.get_full_name(),
        'date_of_birth': patient.date_of_birth,
        'gender': patient.gender,
        'phone': patient.phone,
        'email': patient.email,
        'blood_group': patient.blood_group,
        'allergies': patient.allergies,
        'last_updated': (patient.updated_at if hasattr(patient, 'updated_at') else timezone.now()).isoformat(),
    }
    return Response(data)


@api_view(['GET'])
@permission_classes([PatientOnlyAccess])
def mobile_appointments(request):
    """
    GET /api/mobile/appointments/?updated_since=ISO8601
    
    Returns patient's appointments. If updated_since is set, only records updated after that time.
    """
    from apps.appointments.models import Appointment
    
    patient = request.user.patient
    qs = Appointment.objects.filter(patient=patient).select_related('doctor').order_by('-appointment_date')
    updated_since = request.query_params.get('updated_since')
    if updated_since:
        try:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(updated_since)
            if dt:
                qs = qs.filter(updated_at__gte=dt)
        except (ValueError, TypeError):
            pass
    
    paginator = MobilePagination()
    page = paginator.paginate_queryset(qs, request)
    data = [
        {
            'id': apt.id,
            'date': apt.appointment_date,
            'time': apt.appointment_date.strftime('%H:%M') if apt.appointment_date else None,
            'doctor': apt.doctor.get_full_name() if apt.doctor else None,
            'status': apt.status,
            'reason': apt.reason,
            'updated_at': apt.updated_at.isoformat() if apt.updated_at else None,
        }
        for apt in page
    ]
    AuditLog.log(
        user=request.user,
        role=request.user.role,
        action="APPOINTMENTS_VIEWED",
        resource_type="appointments",
        resource_id=None,
        request=request
    )
    resp = paginator.get_paginated_response(data)
    resp.data['last_updated'] = _last_updated()
    return resp


@api_view(['GET'])
@permission_classes([PatientOnlyAccess])
def mobile_prescriptions(request):
    """
    GET /api/mobile/prescriptions/
    
    Returns patient's prescriptions.
    """
    from apps.pharmacy.models import Prescription
    
    patient = request.user.patient
    
    # Get prescriptions from visits
    from apps.visits.models import Visit
    visits = Visit.objects.filter(patient=patient).values_list('id', flat=True)
    
    prescriptions = Prescription.objects.filter(
        visit_id__in=visits
    ).select_related('visit', 'prescribed_by').order_by('-created_at')
    updated_since = request.query_params.get('updated_since')
    if updated_since:
        try:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(updated_since)
            if dt:
                prescriptions = prescriptions.filter(updated_at__gte=dt)
        except (ValueError, TypeError):
            pass
    
    paginator = MobilePagination()
    page = paginator.paginate_queryset(prescriptions, request)
    data = [
        {
            'id': rx.id,
            'drug_name': rx.drug_name,
            'dosage': rx.dosage,
            'frequency': rx.frequency,
            'duration': rx.duration,
            'quantity': rx.quantity,
            'instructions': rx.instructions,
            'prescribed_by': rx.prescribed_by.get_full_name() if rx.prescribed_by else None,
            'prescribed_date': rx.created_at.date() if rx.created_at else None,
            'status': rx.status,
            'updated_at': rx.updated_at.isoformat() if getattr(rx, 'updated_at', None) else None,
        }
        for rx in page
    ]
    AuditLog.log(
        user=request.user,
        role=request.user.role,
        action="PRESCRIPTIONS_VIEWED",
        resource_type="prescriptions",
        resource_id=None,
        request=request
    )
    resp = paginator.get_paginated_response(data)
    resp.data['last_updated'] = _last_updated()
    return resp


@api_view(['GET'])
@permission_classes([PatientOnlyAccess])
def mobile_lab_results(request):
    """
    GET /api/mobile/lab-results/
    
    Returns patient's lab results.
    """
    from apps.laboratory.models import LabOrder
    from apps.visits.models import Visit
    
    patient = request.user.patient
    visits = Visit.objects.filter(patient=patient).values_list('id', flat=True)
    
    lab_orders = LabOrder.objects.filter(
        visit_id__in=visits,
        status='COMPLETED'
    ).select_related('ordered_by').order_by('-result_date', '-created_at')
    updated_since = request.query_params.get('updated_since')
    if updated_since:
        try:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(updated_since)
            if dt:
                lab_orders = lab_orders.filter(created_at__gte=dt)
        except (ValueError, TypeError):
            pass
    
    paginator = MobilePagination()
    page = paginator.paginate_queryset(lab_orders, request)
    data = [
        {
            'id': lab.id,
            'test_name': lab.test_name,
            'result': lab.result,
            'result_date': lab.result_date,
            'ordered_by': lab.ordered_by.get_full_name() if lab.ordered_by else None,
            'status': lab.status,
            'notes': lab.notes,
            'updated_at': getattr(lab, 'updated_at', None) and lab.updated_at.isoformat() or (lab.created_at.isoformat() if lab.created_at else None),
        }
        for lab in page
    ]
    AuditLog.log(
        user=request.user,
        role=request.user.role,
        action="LAB_RESULTS_VIEWED",
        resource_type="lab_orders",
        resource_id=None,
        request=request
    )
    resp = paginator.get_paginated_response(data)
    resp.data['last_updated'] = _last_updated()
    return resp


@api_view(['GET'])
@permission_classes([PatientOnlyAccess])
def mobile_bills(request):
    """
    GET /api/mobile/bills/
    
    Returns patient's billing information.
    """
    from apps.visits.models import Visit
    from apps.billing.models import VisitCharge, Payment
    
    patient = request.user.patient
    
    # Get visits with billing info
    visits = Visit.objects.filter(
        patient=patient
    ).prefetch_related('charges', 'payments').order_by('-created_at')
    updated_since = request.query_params.get('updated_since')
    if updated_since:
        try:
            from django.utils.dateparse import parse_datetime
            dt = parse_datetime(updated_since)
            if dt:
                visits = visits.filter(updated_at__gte=dt)
        except (ValueError, TypeError):
            pass
    
    paginator = MobilePagination()
    page = paginator.paginate_queryset(visits, request)
    data = []
    for visit in page:
        charges_total = sum(c.total_amount for c in visit.charges.all())
        payments_total = sum(p.amount for p in visit.payments.all())
        balance = charges_total - payments_total
        data.append({
            'visit_id': visit.id,
            'visit_date': visit.created_at.date(),
            'status': visit.status,
            'payment_status': visit.payment_status,
            'total_charges': float(charges_total),
            'total_paid': float(payments_total),
            'balance': float(balance),
            'updated_at': getattr(visit, 'updated_at', None) and visit.updated_at.isoformat(),
            'charges': [
                {'description': c.description, 'amount': float(c.total_amount)}
                for c in visit.charges.all()
            ]
        })
    AuditLog.log(
        user=request.user,
        role=request.user.role,
        action="BILLS_VIEWED",
        resource_type="visits",
        resource_id=None,
        request=request
    )
    resp = paginator.get_paginated_response(data)
    resp.data['last_updated'] = _last_updated()
    return resp


@api_view(['GET'])
@permission_classes([PatientOnlyAccess])
def mobile_dashboard(request):
    """
    GET /api/mobile/dashboard/
    
    Returns dashboard summary for mobile app.
    """
    from apps.visits.models import Visit
    from apps.appointments.models import Appointment
    
    patient = request.user.patient
    now = timezone.now()
    
    # Upcoming appointments (next 30 days)
    upcoming_appointments = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=now.date(),
        appointment_date__lte=(now + timedelta(days=30)).date(),
        status='SCHEDULED'
    ).count()
    
    # Open visits
    open_visits = Visit.objects.filter(
        patient=patient,
        status='OPEN'
    ).count()
    
    # Unpaid bills
    visits_with_balance = Visit.objects.filter(
        patient=patient,
        payment_status__in=['UNPAID', 'PARTIALLY_PAID']
    ).count()
    
    # Recent lab results (last 30 days)
    from apps.laboratory.models import LabOrder
    visits = Visit.objects.filter(patient=patient).values_list('id', flat=True)
    recent_lab_results = LabOrder.objects.filter(
        visit_id__in=visits,
        status='COMPLETED',
        result_date__gte=(now - timedelta(days=30)).date()
    ).count()
    
    data = {
        'patient_name': patient.get_full_name(),
        'patient_id': patient.patient_id,
        'summary': {
            'upcoming_appointments': upcoming_appointments,
            'open_visits': open_visits,
            'unpaid_bills': visits_with_balance,
            'recent_lab_results': recent_lab_results,
        },
        'last_login': request.user.last_login,
        'device_type': request.user.device_type,
        'last_updated': _last_updated(),
    }
    return Response(data)


@api_view(['POST', 'GET'])
@permission_classes([PatientOnlyAccess])
def mobile_sync(request):
    """
    POST /api/mobile/sync/ – record last sync time (body: { "device_id": "..." }).
    GET /api/mobile/sync/ – return last sync time for device (query: device_id).
    """
    from apps.offline.models import SyncLog
    
    if request.method == 'POST':
        device_id = (request.data.get('device_id') or '').strip()
        if not device_id:
            return Response(
                {'error': 'device_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        log, _ = SyncLog.objects.update_or_create(
            user=request.user,
            device_id=device_id,
            defaults={'last_sync_time': timezone.now()},
        )
        return Response({
            'device_id': device_id,
            'last_sync_time': log.last_sync_time.isoformat(),
            'last_updated': _last_updated(),
        })
    device_id = request.query_params.get('device_id', '').strip()
    if not device_id:
        return Response(
            {'error': 'device_id query required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        log = SyncLog.objects.get(user=request.user, device_id=device_id)
        return Response({
            'device_id': device_id,
            'last_sync_time': log.last_sync_time.isoformat(),
            'last_updated': _last_updated(),
        })
    except SyncLog.DoesNotExist:
        return Response({
            'device_id': device_id,
            'last_sync_time': None,
            'last_updated': _last_updated(),
        })
