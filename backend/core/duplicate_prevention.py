"""
Duplicate Prevention Utility

Provides centralized duplicate checking logic for various entities in the EMR system.
"""
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError


class DuplicatePreventionMixin:
    """
    Mixin class to add duplicate prevention methods to models.
    """
    
    @classmethod
    def check_duplicate_window(cls, **kwargs):
        """
        Check for duplicates within a time window.
        
        Args:
            **kwargs: Filter criteria and optional 'window_minutes' (default: 5)
        
        Returns:
            QuerySet of potential duplicates
        """
        window_minutes = kwargs.pop('window_minutes', 5)
        time_field = kwargs.pop('time_field', 'created_at')
        
        # Get the most recent record matching the criteria
        recent = cls.objects.filter(**kwargs).order_by(f'-{time_field}').first()
        
        if not recent:
            return cls.objects.none()
        
        # Check for duplicates within the time window
        window_start = getattr(recent, time_field) - timedelta(minutes=window_minutes)
        window_end = getattr(recent, time_field) + timedelta(minutes=window_minutes)
        
        return cls.objects.filter(
            **kwargs,
            **{f'{time_field}__gte': window_start, f'{time_field}__lte': window_end}
        ).exclude(pk=recent.pk)


def check_patient_duplicate(first_name, last_name, date_of_birth=None, phone=None, email=None, national_id=None, exclude_id=None):
    """
    Check if a patient with similar information already exists.
    
    Args:
        first_name: Patient first name
        last_name: Patient last name
        date_of_birth: Patient date of birth (optional)
        phone: Patient phone number (optional)
        email: Patient email (optional)
        national_id: National ID (optional)
        exclude_id: Patient ID to exclude from check (for updates)
    
    Returns:
        Patient object if duplicate found, None otherwise
    
    Raises:
        ValidationError if duplicate found
    """
    from apps.patients.models import Patient
    
    # Normalize inputs
    first_name = first_name.strip().upper() if first_name else None
    last_name = last_name.strip().upper() if last_name else None
    phone = phone.strip() if phone else None
    email = email.strip().lower() if email else None
    national_id = national_id.strip() if national_id else None
    
    if not first_name or not last_name:
        return None
    
    # Check by national_id (most reliable)
    if national_id:
        duplicate = Patient.objects.filter(
            national_id=national_id,
            is_active=True
        ).exclude(pk=exclude_id).first()
        if duplicate:
            raise ValidationError(
                f"A patient with National ID {national_id} already exists: "
                f"{duplicate.get_full_name()} (ID: {duplicate.patient_id})"
            )
    
    # Check by phone (if provided)
    if phone:
        duplicate = Patient.objects.filter(
            phone=phone,
            is_active=True
        ).exclude(pk=exclude_id).first()
        if duplicate:
            raise ValidationError(
                f"A patient with phone number {phone} already exists: "
                f"{duplicate.get_full_name()} (ID: {duplicate.patient_id})"
            )
    
    # Check by email (if provided)
    if email:
        duplicate = Patient.objects.filter(
            email=email,
            is_active=True
        ).exclude(pk=exclude_id).first()
        if duplicate:
            raise ValidationError(
                f"A patient with email {email} already exists: "
                f"{duplicate.get_full_name()} (ID: {duplicate.patient_id})"
            )
    
    # Check by name + date of birth (if DOB provided)
    if date_of_birth:
        duplicate = Patient.objects.filter(
            first_name__iexact=first_name,
            last_name__iexact=last_name,
            date_of_birth=date_of_birth,
            is_active=True
        ).exclude(pk=exclude_id).first()
        if duplicate:
            raise ValidationError(
                f"A patient with name {first_name} {last_name} and date of birth "
                f"{date_of_birth} already exists: {duplicate.get_full_name()} "
                f"(ID: {duplicate.patient_id})"
            )
    
    return None


def check_visit_duplicate(patient, visit_type, visit_date=None, exclude_id=None):
    """
    Check if a duplicate visit exists for the same patient.
    
    Args:
        patient: Patient instance
        visit_type: Visit type (e.g., 'CONSULTATION')
        visit_date: Visit date (defaults to today)
        exclude_id: Visit ID to exclude from check (for updates)
    
    Returns:
        Visit object if duplicate found, None otherwise
    
    Raises:
        ValidationError if duplicate found
    """
    from apps.visits.models import Visit
    
    if not visit_date:
        visit_date = timezone.now().date()
    
    # Check for same patient, same type, same date, OPEN status
    duplicate = Visit.objects.filter(
        patient=patient,
        visit_type=visit_type,
        created_at__date=visit_date,
        status='OPEN'
    ).exclude(pk=exclude_id).first()
    
    if duplicate:
        raise ValidationError(
            f"An open {visit_type} visit already exists for patient "
            f"{patient.get_full_name()} on {visit_date}. "
            f"Visit ID: {duplicate.id}"
        )
    
    return None


def check_lab_order_duplicate(visit, test_code, window_minutes=5, exclude_id=None):
    """
    Check if a duplicate lab order exists within a time window.
    
    Args:
        visit: Visit instance
        test_code: Lab test code (string) or list of test codes
        window_minutes: Time window in minutes (default: 5)
        exclude_id: Lab order ID to exclude from check (for updates)
    
    Returns:
        LabOrder object if duplicate found, None otherwise
    
    Raises:
        ValidationError if duplicate found
    """
    from apps.laboratory.models import LabOrder
    import json
    
    # Normalize test_code to a list
    if isinstance(test_code, str):
        try:
            test_codes = json.loads(test_code)
            if not isinstance(test_codes, list):
                test_codes = [test_codes]
        except (json.JSONDecodeError, ValueError):
            test_codes = [test_code]
    elif isinstance(test_code, list):
        test_codes = test_code
    else:
        test_codes = [str(test_code)]
    
    # Normalize test codes to strings for comparison
    test_codes = [str(tc).strip().upper() for tc in test_codes]
    
    # Get recent orders for this visit
    recent_orders = LabOrder.objects.filter(
        visit=visit
    ).exclude(pk=exclude_id).order_by('-created_at')[:10]  # Check last 10 orders
    
    for recent_order in recent_orders:
        # Check if within time window
        time_diff = (timezone.now() - recent_order.created_at).total_seconds()
        if time_diff > (window_minutes * 60):
            continue  # Outside time window
        
        # Get tests from recent order (stored as JSONField)
        recent_tests = recent_order.tests_requested
        if isinstance(recent_tests, str):
            try:
                recent_tests = json.loads(recent_tests)
            except (json.JSONDecodeError, ValueError):
                recent_tests = [recent_tests]
        if not isinstance(recent_tests, list):
            recent_tests = [recent_tests]
        
        # Normalize recent tests to strings for comparison
        recent_tests = [str(rt).strip().upper() for rt in recent_tests]
        
        # Check if any test codes overlap
        overlapping_tests = set(test_codes) & set(recent_tests)
        if overlapping_tests:
            raise ValidationError(
                f"A lab order with test(s) {', '.join(overlapping_tests)} was already created "
                f"for this visit within the last {window_minutes} minutes. Order ID: {recent_order.id}"
            )
    
    return None


def check_radiology_order_duplicate(visit, study_code, window_minutes=5, exclude_id=None):
    """
    Check if a duplicate radiology order exists within a time window.
    
    Args:
        visit: Visit instance
        study_code: Radiology study code
        window_minutes: Time window in minutes (default: 5)
        exclude_id: Radiology order ID to exclude from check (for updates)
    
    Returns:
        RadiologyOrder object if duplicate found, None otherwise
    
    Raises:
        ValidationError if duplicate found
    """
    from apps.radiology.models import RadiologyOrder
    
    recent_order = RadiologyOrder.objects.filter(
        visit=visit,
        study_code=study_code
    ).exclude(pk=exclude_id).order_by('-created_at').first()
    
    if not recent_order:
        return None
    
    window_start = recent_order.created_at - timedelta(minutes=window_minutes)
    window_end = recent_order.created_at + timedelta(minutes=window_minutes)
    
    duplicate = RadiologyOrder.objects.filter(
        visit=visit,
        study_code=study_code,
        created_at__gte=window_start,
        created_at__lte=window_end
    ).exclude(pk=exclude_id).exclude(pk=recent_order.pk).first()
    
    if duplicate or (timezone.now() - recent_order.created_at).total_seconds() < (window_minutes * 60):
        raise ValidationError(
            f"A radiology order for {study_code} was already created for this visit "
            f"within the last {window_minutes} minutes. Order ID: {recent_order.id}"
        )
    
    return None


def check_payment_duplicate(visit, amount, payment_method, window_minutes=2, exclude_id=None):
    """
    Check if a duplicate payment exists within a time window.
    
    Args:
        visit: Visit instance
        amount: Payment amount
        payment_method: Payment method (e.g., 'CASH', 'POS')
        window_minutes: Time window in minutes (default: 2)
        exclude_id: Payment ID to exclude from check (for updates)
    
    Returns:
        Payment object if duplicate found, None otherwise
    
    Raises:
        ValidationError if duplicate found
    """
    from apps.billing.models import Payment
    
    recent_payment = Payment.objects.filter(
        visit=visit,
        amount=amount,
        payment_method=payment_method
    ).exclude(pk=exclude_id).order_by('-created_at').first()
    
    if not recent_payment:
        return None
    
    window_start = recent_payment.created_at - timedelta(minutes=window_minutes)
    window_end = recent_payment.created_at + timedelta(minutes=window_minutes)
    
    duplicate = Payment.objects.filter(
        visit=visit,
        amount=amount,
        payment_method=payment_method,
        created_at__gte=window_start,
        created_at__lte=window_end
    ).exclude(pk=exclude_id).exclude(pk=recent_payment.pk).first()
    
    if duplicate or (timezone.now() - recent_payment.created_at).total_seconds() < (window_minutes * 60):
        raise ValidationError(
            f"A payment of {amount} via {payment_method} was already recorded for this visit "
            f"within the last {window_minutes} minutes. Payment ID: {recent_payment.id}"
        )
    
    return None


def check_vital_signs_duplicate(visit, window_minutes=3, exclude_id=None):
    """
    Check if duplicate vital signs were recorded within a time window.
    
    Args:
        visit: Visit instance
        window_minutes: Time window in minutes (default: 3)
        exclude_id: Vital signs ID to exclude from check (for updates)
    
    Returns:
        VitalSigns object if duplicate found, None otherwise
    
    Raises:
        ValidationError if duplicate found
    """
    from apps.clinical.models import VitalSigns
    
    # Get the most recent vital signs for this visit
    recent_vitals = VitalSigns.objects.filter(
        visit=visit
    ).exclude(pk=exclude_id).order_by('-recorded_at').first()
    
    if not recent_vitals:
        return None
    
    # Check if the most recent vital signs were recorded within the time window
    now = timezone.now()
    time_since_last = (now - recent_vitals.recorded_at).total_seconds()
    window_seconds = window_minutes * 60
    
    if time_since_last < window_seconds:
        # Calculate remaining wait time
        remaining_seconds = int(window_seconds - time_since_last)
        remaining_minutes = remaining_seconds // 60
        remaining_secs = remaining_seconds % 60
        
        raise ValidationError(
            f"Vital signs were already recorded for this visit within the last "
            f"{window_minutes} minutes. Please wait {remaining_minutes} minute(s) and "
            f"{remaining_secs} second(s) before recording again. "
            f"Last record ID: {recent_vitals.id}, recorded at: {recent_vitals.recorded_at}"
        )
    
    # Also check for any other vital signs within the time window (defense in depth)
    # This catches edge cases where multiple records might exist
    window_start = now - timedelta(minutes=window_minutes)
    
    recent_count = VitalSigns.objects.filter(
        visit=visit,
        recorded_at__gte=window_start
    ).exclude(pk=exclude_id).count()
    
    if recent_count > 0:
        raise ValidationError(
            f"Vital signs were already recorded for this visit within the last "
            f"{window_minutes} minutes. Found {recent_count} record(s) in this time window. "
            f"Last record ID: {recent_vitals.id}, recorded at: {recent_vitals.recorded_at}"
        )
    
    return None


def check_appointment_duplicate(patient, appointment_date, appointment_time=None, exclude_id=None):
    """
    Check if a duplicate appointment exists.
    
    Args:
        patient: Patient instance
        appointment_date: Appointment datetime (DateTimeField)
        appointment_time: Not used (kept for compatibility, appointment_date is datetime)
        exclude_id: Appointment ID to exclude from check (for updates)
    
    Returns:
        Appointment object if duplicate found, None otherwise
    
    Raises:
        ValidationError if duplicate found
    """
    from apps.appointments.models import Appointment
    from datetime import datetime
    
    # appointment_date is a DateTimeField, so we check within a 30-minute window
    if isinstance(appointment_date, datetime):
        window_start = appointment_date - timedelta(minutes=30)
        window_end = appointment_date + timedelta(minutes=30)
    else:
        # If it's not a datetime, convert it
        window_start = appointment_date - timedelta(minutes=30)
        window_end = appointment_date + timedelta(minutes=30)
    
    # Check for same patient, same datetime (within 30 minutes)
    duplicate = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=window_start,
        appointment_date__lte=window_end,
        status__in=['SCHEDULED', 'CONFIRMED']
    ).exclude(pk=exclude_id).first()
    
    if duplicate:
        raise ValidationError(
            f"An appointment already exists for patient {patient.get_full_name()} "
            f"on {duplicate.appointment_date.strftime('%Y-%m-%d %H:%M')}. Appointment ID: {duplicate.id}"
        )
    
    return None

