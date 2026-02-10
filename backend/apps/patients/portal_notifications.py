"""
Patient Portal Notification Utility

Prepares notification messages for patient portal account creation.
Designed for easy integration with email/SMS services later.

Usage:
    from apps.patients.portal_notifications import notify_portal_account_created
    
    notify_portal_account_created(
        patient=patient,
        username='john@example.com',
        temporary_password='xK9mP2nQ7vR3'
    )
"""
import logging
from typing import Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


def prepare_portal_welcome_message(
    patient_name: str,
    username: str,
    temporary_password: str,
    login_url: str = '/patient-portal/login'
) -> Dict[str, str]:
    """
    Prepare welcome message for patient portal account.
    
    Args:
        patient_name: Full name of the patient
        username: Portal login username (usually email)
        temporary_password: Temporary password (12 characters)
        login_url: URL path for portal login
    
    Returns:
        Dictionary with 'subject', 'email_body', and 'sms_body'
    """
    # Get clinic name from settings (with fallback)
    clinic_name = getattr(settings, 'CLINIC_NAME', 'Our Clinic')
    
    # Build absolute login URL if BASE_URL is configured
    base_url = getattr(settings, 'BASE_URL', 'https://yoursite.com')
    full_login_url = f"{base_url}{login_url}"
    
    # Email subject
    subject = f"Welcome to {clinic_name} Patient Portal"
    
    # Email body (formatted for readability)
    email_body = f"""Dear {patient_name},

Your patient portal account has been created successfully.

LOGIN CREDENTIALS:
------------------
Username: {username}
Temporary Password: {temporary_password}
Portal URL: {full_login_url}

IMPORTANT: Please change your password after your first login for security.

What you can do in the Patient Portal:
• View your medical records
• Check lab results
• View prescriptions
• See upcoming appointments
• View bills and payment status
• Update your contact information

If you have any questions, please contact our reception desk.

Best regards,
{clinic_name}

---
This is an automated message. Please do not reply to this email.
"""
    
    # SMS body (shorter, character-limited)
    sms_body = f"""Your patient portal account has been created.

Login: {username}
Temporary Password: {temporary_password}
Please change it after login.

{clinic_name}"""
    
    return {
        'subject': subject,
        'email_body': email_body,
        'sms_body': sms_body,
        'login_url': full_login_url
    }


def notify_portal_account_created(
    patient,
    username: str,
    temporary_password: str,
    send_email: bool = True,
    send_sms: bool = False,
    phone_number: Optional[str] = None
) -> Dict[str, any]:
    """
    Notify patient that portal account has been created.
    
    This function prepares notification messages and logs them.
    Real email/SMS sending is not implemented - ready for integration.
    
    Args:
        patient: Patient model instance
        username: Portal login username (email)
        temporary_password: Generated temporary password
        send_email: Whether to prepare email notification (default: True)
        send_sms: Whether to prepare SMS notification (default: False)
        phone_number: Phone number for SMS (optional)
    
    Returns:
        Dictionary with notification details and status
    """
    result = {
        'success': True,
        'patient_id': patient.id,
        'patient_name': patient.get_full_name(),
        'username': username,
        'notifications_sent': []
    }
    
    # Prepare messages
    messages = prepare_portal_welcome_message(
        patient_name=patient.get_full_name(),
        username=username,
        temporary_password=temporary_password
    )
    
    # Email notification (prepared but not sent)
    if send_email:
        email_data = {
            'type': 'email',
            'to': username,
            'subject': messages['subject'],
            'body': messages['email_body'],
            'status': 'prepared'
        }
        
        # TODO: Integrate with real email service
        # Example: send_email_via_service(email_data)
        
        logger.info(
            f"Portal account email prepared for {patient.get_full_name()} "
            f"(Patient ID: {patient.id}, Email: {username})"
        )
        logger.debug(f"Email subject: {messages['subject']}")
        logger.debug(f"Email body preview: {messages['email_body'][:100]}...")
        
        result['notifications_sent'].append(email_data)
        result['email_prepared'] = True
    
    # SMS notification (prepared but not sent)
    if send_sms and phone_number:
        sms_data = {
            'type': 'sms',
            'to': phone_number,
            'body': messages['sms_body'],
            'status': 'prepared'
        }
        
        # TODO: Integrate with real SMS service (Twilio, AWS SNS, etc.)
        # Example: send_sms_via_service(sms_data)
        
        logger.info(
            f"Portal account SMS prepared for {patient.get_full_name()} "
            f"(Patient ID: {patient.id}, Phone: {phone_number})"
        )
        logger.debug(f"SMS body: {messages['sms_body']}")
        
        result['notifications_sent'].append(sms_data)
        result['sms_prepared'] = True
    
    # Log the credentials (WARNING: Only for development)
    if settings.DEBUG:
        logger.info(
            f"[DEV ONLY] Portal credentials for {patient.get_full_name()}: "
            f"Username={username}, Password={temporary_password}"
        )
    
    return result


def send_portal_password_reset(
    patient,
    username: str,
    reset_token: str,
    reset_url: str
) -> Dict[str, any]:
    """
    Prepare password reset notification for patient portal.
    
    Args:
        patient: Patient model instance
        username: Portal username
        reset_token: Password reset token
        reset_url: URL for password reset
    
    Returns:
        Dictionary with notification details
    """
    clinic_name = getattr(settings, 'CLINIC_NAME', 'Our Clinic')
    
    subject = f"{clinic_name} - Password Reset Request"
    
    email_body = f"""Dear {patient.get_full_name()},

We received a request to reset your patient portal password.

Click the link below to reset your password:
{reset_url}

This link will expire in 24 hours.

If you did not request this reset, please ignore this email.
Your password will remain unchanged.

Best regards,
{clinic_name}
"""
    
    sms_body = f"""Password reset requested for {clinic_name} portal.
Link: {reset_url}
Expires in 24 hours."""
    
    result = {
        'success': True,
        'patient_id': patient.id,
        'username': username,
        'reset_url': reset_url,
        'email_prepared': True
    }
    
    logger.info(
        f"Password reset notification prepared for {patient.get_full_name()} "
        f"(Patient ID: {patient.id})"
    )
    
    # TODO: Send actual email/SMS here
    
    return result


def send_portal_appointment_reminder(
    patient,
    appointment_datetime: str,
    doctor_name: str,
    clinic_location: str = ''
) -> Dict[str, any]:
    """
    Prepare appointment reminder notification.
    
    Args:
        patient: Patient model instance
        appointment_datetime: Formatted date/time of appointment
        doctor_name: Name of the doctor
        clinic_location: Location/room (optional)
    
    Returns:
        Dictionary with notification details
    """
    clinic_name = getattr(settings, 'CLINIC_NAME', 'Our Clinic')
    
    subject = f"Appointment Reminder - {clinic_name}"
    
    location_text = f"\nLocation: {clinic_location}" if clinic_location else ""
    
    email_body = f"""Dear {patient.get_full_name()},

This is a reminder of your upcoming appointment:

Date & Time: {appointment_datetime}
Doctor: {doctor_name}{location_text}

Please arrive 15 minutes early for registration.

View your appointment details in your patient portal:
{getattr(settings, 'BASE_URL', 'https://yoursite.com')}/patient-portal/appointments

If you need to reschedule, please contact us as soon as possible.

Best regards,
{clinic_name}
"""
    
    sms_body = f"""Appointment reminder: {appointment_datetime} with Dr. {doctor_name} at {clinic_name}.
Please arrive 15 min early."""
    
    logger.info(
        f"Appointment reminder prepared for {patient.get_full_name()} "
        f"(Appointment: {appointment_datetime})"
    )
    
    # TODO: Send actual email/SMS here
    
    return {
        'success': True,
        'patient_id': patient.id,
        'appointment_datetime': appointment_datetime,
        'notifications_prepared': ['email', 'sms']
    }


def send_lab_result_notification(
    patient,
    test_name: str,
    result_url: str
) -> Dict[str, any]:
    """
    Prepare lab result availability notification.
    
    Args:
        patient: Patient model instance
        test_name: Name of the lab test
        result_url: URL to view results in portal
    
    Returns:
        Dictionary with notification details
    """
    clinic_name = getattr(settings, 'CLINIC_NAME', 'Our Clinic')
    
    subject = f"Lab Results Available - {clinic_name}"
    
    email_body = f"""Dear {patient.get_full_name()},

Your lab results are now available.

Test: {test_name}

View your results in the patient portal:
{result_url}

If you have any questions about your results, please contact your doctor.

Best regards,
{clinic_name}
"""
    
    sms_body = f"""Your lab results for {test_name} are now available.
Login to patient portal to view."""
    
    logger.info(
        f"Lab result notification prepared for {patient.get_full_name()} "
        f"(Test: {test_name})"
    )
    
    # TODO: Send actual email/SMS here
    
    return {
        'success': True,
        'patient_id': patient.id,
        'test_name': test_name,
        'notifications_prepared': ['email', 'sms']
    }


# Helper function to integrate with email service (future)
def _send_email(to: str, subject: str, body: str) -> bool:
    """
    Send email using configured email service.
    
    This is a placeholder for real email integration.
    
    Integration options:
    - Django built-in: send_mail()
    - SendGrid: sendgrid.SendGridAPIClient()
    - AWS SES: boto3.client('ses')
    - Mailgun: requests.post()
    - Postmark: postmarkclient.emails.send()
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # TODO: Replace with actual email service
        # Example using Django's send_mail:
        """
        from django.core.mail import send_mail
        
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to],
            fail_silently=False,
        )
        """
        
        logger.info(f"[EMAIL PREPARED] To: {to}, Subject: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {str(e)}")
        return False


# Helper function to integrate with SMS service (future)
def _send_sms(to: str, body: str) -> bool:
    """
    Send SMS using configured SMS service.
    
    This is a placeholder for real SMS integration.
    
    Integration options:
    - Twilio: client.messages.create()
    - AWS SNS: boto3.client('sns').publish()
    - Africa's Talking: africastalking.SMS.send()
    - Nexmo/Vonage: nexmo.Client().send_message()
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # TODO: Replace with actual SMS service
        # Example using Twilio:
        """
        from twilio.rest import Client
        
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to
        )
        """
        
        logger.info(f"[SMS PREPARED] To: {to}, Body length: {len(body)} chars")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send SMS to {to}: {str(e)}")
        return False


# Integration helper for serializer
def notify_new_portal_account(
    patient,
    username: str,
    temporary_password: str,
    email: Optional[str] = None,
    phone: Optional[str] = None
) -> Dict[str, any]:
    """
    Convenience function to notify patient of new portal account.
    
    Call this from PatientCreateSerializer after portal account creation.
    
    Args:
        patient: Patient instance
        username: Portal username (email)
        temporary_password: Generated temporary password
        email: Email address (defaults to username)
        phone: Phone number for SMS (optional)
    
    Returns:
        Notification result with prepared messages
    
    Example:
        # In PatientCreateSerializer.create()
        if portal_created:
            from apps.patients.portal_notifications import notify_new_portal_account
            
            notify_new_portal_account(
                patient=patient,
                username=portal_email,
                temporary_password=temporary_password,
                phone=portal_phone
            )
    """
    email_address = email or username
    
    return notify_portal_account_created(
        patient=patient,
        username=username,
        temporary_password=temporary_password,
        send_email=bool(email_address),
        send_sms=bool(phone),
        phone_number=phone
    )
