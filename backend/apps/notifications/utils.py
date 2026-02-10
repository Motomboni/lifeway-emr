"""
Email notification utilities.

Per EMR Rules:
- PHI data must be protected
- All notifications must be logged
- Audit logging mandatory
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import EmailNotification


def send_email_notification(
    notification_type,
    recipient_email,
    recipient_name,
    subject,
    template_name=None,
    context=None,
    appointment=None,
    visit=None,
    created_by=None,
):
    """
    Send an email notification and log it.
    
    Args:
        notification_type: Type of notification (from EmailNotification.NOTIFICATION_TYPES)
        recipient_email: Email address of recipient
        recipient_name: Name of recipient
        subject: Email subject
        template_name: Optional HTML template name
        context: Template context dictionary
        appointment: Optional related appointment
        visit: Optional related visit
        created_by: Optional user who triggered the notification
    
    Returns:
        EmailNotification: The created notification record
    """
    from django.utils import timezone
    
    # Render email body
    if template_name and context:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
    else:
        html_message = context.get('message', '') if context else ''
        plain_message = strip_tags(html_message)
    
    # Create notification record
    notification = EmailNotification.objects.create(
        notification_type=notification_type,
        status='PENDING',
        recipient_email=recipient_email,
        recipient_name=recipient_name,
        appointment=appointment,
        visit=visit,
        subject=subject,
        email_body=plain_message,
        created_by=created_by,
    )
    
    try:
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message if html_message else None,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        # Update notification status
        notification.status = 'SENT'
        notification.sent_at = timezone.now()
        notification.save(update_fields=['status', 'sent_at'])
        
    except Exception as e:
        # Log failure
        notification.status = 'FAILED'
        notification.error_message = str(e)
        notification.save(update_fields=['status', 'error_message'])
        raise
    
    return notification


def send_appointment_reminder(appointment):
    """Send appointment reminder email."""
    from django.utils import timezone
    patient = appointment.patient
    doctor = appointment.doctor
    
    context = {
        'patient_name': patient.full_name,
        'doctor_name': f"{doctor.first_name} {doctor.last_name}",
        'appointment_date': appointment.appointment_date.strftime('%B %d, %Y'),
        'appointment_time': appointment.appointment_date.strftime('%I:%M %p'),
        'reason': appointment.reason or 'General consultation',
        'current_year': timezone.now().year,
    }
    
    return send_email_notification(
        notification_type='APPOINTMENT_REMINDER',
        recipient_email=patient.email or patient.phone,  # Fallback to phone if no email
        recipient_name=patient.full_name,
        subject=f'Appointment Reminder - {context["appointment_date"]}',
        template_name='notifications/appointment_reminder.html',
        context=context,
        appointment=appointment,
        created_by=appointment.created_by,
    )


def send_appointment_confirmation(appointment):
    """Send appointment confirmation email."""
    from django.utils import timezone
    patient = appointment.patient
    doctor = appointment.doctor
    
    patient_name = patient.get_full_name()
    context = {
        'patient_name': patient_name,
        'doctor_name': f"{doctor.first_name} {doctor.last_name}",
        'appointment_date': appointment.appointment_date.strftime('%B %d, %Y'),
        'appointment_time': appointment.appointment_date.strftime('%I:%M %p'),
        'reason': appointment.reason or 'General consultation',
        'current_year': timezone.now().year,
    }
    
    # Only send if patient has email
    if not patient.email:
        return None
    
    return send_email_notification(
        notification_type='APPOINTMENT_CONFIRMED',
        recipient_email=patient.email,
        recipient_name=patient_name,
        subject=f'Appointment Confirmed - {context["appointment_date"]}',
        template_name='notifications/appointment_confirmation.html',
        context=context,
        appointment=appointment,
        created_by=appointment.created_by,
    )


def send_lab_result_notification(lab_result):
    """Send lab result ready notification."""
    from django.utils import timezone
    visit = lab_result.lab_order.visit
    patient = visit.patient
    
    # Only send if patient has email
    if not patient.email:
        return None
    
    patient_name = patient.get_full_name()
    context = {
        'patient_name': patient_name,
        'visit_date': visit.created_at.strftime('%B %d, %Y'),
        'lab_order_id': lab_result.lab_order.id,
        'current_year': timezone.now().year,
    }
    
    return send_email_notification(
        notification_type='LAB_RESULT_READY',
        recipient_email=patient.email,
        recipient_name=patient_name,
        subject='Lab Results Ready',
        template_name='notifications/lab_result_ready.html',
        context=context,
        visit=visit,
    )


def send_radiology_result_notification(radiology_result):
    """Send radiology result ready notification."""
    from django.utils import timezone
    visit = radiology_result.radiology_order.visit
    patient = visit.patient
    
    # Only send if patient has email
    if not patient.email:
        return None
    
    patient_name = patient.get_full_name()
    context = {
        'patient_name': patient_name,
        'visit_date': visit.created_at.strftime('%B %d, %Y'),
        'radiology_order_id': radiology_result.radiology_order.id,
        'current_year': timezone.now().year,
    }
    
    return send_email_notification(
        notification_type='RADIOLOGY_RESULT_READY',
        recipient_email=patient.email,
        recipient_name=patient_name,
        subject='Radiology Results Ready',
        template_name='notifications/radiology_result_ready.html',
        context=context,
        visit=visit,
    )


def send_patient_verification_notification(patient, verified_by_user):
    """Send patient account verification notification."""
    from django.utils import timezone
    from django.conf import settings
    
    # Only send if patient has email
    if not patient.email:
        return None
    
    patient_name = patient.get_full_name()
    verified_by_name = f"{verified_by_user.first_name} {verified_by_user.last_name}"
    
    # Get portal URL from settings or use default
    portal_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    if not portal_url.endswith('/'):
        portal_url += '/'
    portal_url += 'patient-portal/dashboard'
    
    context = {
        'patient_name': patient_name,
        'patient_id': patient.patient_id,
        'verified_by_name': verified_by_name,
        'verified_date': patient.verified_at.strftime('%B %d, %Y at %I:%M %p') if patient.verified_at else timezone.now().strftime('%B %d, %Y at %I:%M %p'),
        'portal_url': portal_url,
        'current_year': timezone.now().year,
    }
    
    return send_email_notification(
        notification_type='PATIENT_VERIFIED',
        recipient_email=patient.email,
        recipient_name=patient_name,
        subject='Your Patient Portal Account Has Been Verified',
        template_name='notifications/patient_verified.html',
        context=context,
        created_by=verified_by_user,
    )
