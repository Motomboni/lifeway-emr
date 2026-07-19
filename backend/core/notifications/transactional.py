"""
Transactional email for Lifeway EMR (portal, billing, notifications).
Uses Django EMAIL_BACKEND — configure SMTP in production.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_transactional_email(
    to: str,
    subject: str,
    body: str,
    *,
    html_message: str | None = None,
    fail_silently: bool = True,
) -> bool:
    if not to or not to.strip():
        logger.warning("Transactional email skipped: empty recipient")
        return False

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@emr.local")
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[to.strip()],
            html_message=html_message,
            fail_silently=fail_silently,
        )
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.exception("Failed to send email to %s: %s", to, e)
        return False
