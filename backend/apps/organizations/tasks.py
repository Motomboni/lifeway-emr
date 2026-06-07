import io
import logging
from decimal import Decimal

from celery import shared_task
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from .models import Organization, Subscription

logger = logging.getLogger(__name__)

@shared_task
def generate_and_send_invoice_pdf(organization_id, invoice_id, amount, date, status="PAID"):
    """
    Generate a styled PDF invoice for SaaS subscriptions using reportlab,
    and optionally send it via email to the organization.
    """
    try:
        org = Organization.objects.get(pk=organization_id)
    except Organization.DoesNotExist:
        logger.warning(f"Organization {organization_id} not found for invoice {invoice_id}")
        return

    logger.info(f"Generating SaaS Invoice PDF for Org {org.name}, Invoice {invoice_id}")

    # Generate PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=24, spaceAfter=20, textColor=colors.HexColor('#1f2937'))
    normal_style = styles['Normal']
    
    # Header
    elements.append(Paragraph("<b>Billing Invoice</b>", title_style))
    elements.append(Paragraph(f"<b>Invoice ID:</b> {invoice_id}", normal_style))
    elements.append(Paragraph(f"<b>Date:</b> {date}", normal_style))
    elements.append(Paragraph(f"<b>Status:</b> {status}", normal_style))
    elements.append(Spacer(1, 0.5 * inch))
    
    # Org Info
    elements.append(Paragraph("<b>Billed To:</b>", styles['Heading3']))
    elements.append(Paragraph(org.name, normal_style))
    if org.email:
        elements.append(Paragraph(org.email, normal_style))
    if org.address:
        elements.append(Paragraph(org.address, normal_style))
    elements.append(Spacer(1, 0.5 * inch))
    
    # Line Items Table
    plan_name = "Subscription Plan"
    try:
        plan_name = org.subscription.plan.name
    except Exception:
        pass

    currency = "NGN"
    try:
        currency = org.subscription.plan.currency or "NGN"
    except Exception:
        pass

    data = [
        ['Description', 'Amount'],
        [f'{plan_name} - SaaS Subscription', f'{currency} {amount}'],
        ['', ''],
        ['Total', f'{currency} {amount}']
    ]
    
    table = Table(data, colWidths=[4.5 * inch, 1.5 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#111827')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#4b5563')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#d1d5db')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#d1d5db')),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 1 * inch))
    
    # Footer
    elements.append(Paragraph("Thank you for choosing Lifeway EMR SaaS.", styles['Italic']))
    
    # Build PDF
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    logger.info(f"Successfully generated PDF for invoice {invoice_id} ({len(pdf_bytes)} bytes)")
    
    if org.email:
        from core.notifications import send_transactional_email
        from django.core.mail import EmailMessage

        try:
            email = EmailMessage(
                subject=f"SaaS Invoice {invoice_id} — {org.name}",
                body=(
                    f"Dear {org.name},\n\n"
                    f"Attached is your subscription invoice ({invoice_id}).\n"
                    f"Amount: {currency} {amount}\n\n"
                    f"Thank you,\nDamianix EMR"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@emr.local"),
                to=[org.email],
            )
            email.attach(f"invoice_{invoice_id}.pdf", pdf_bytes, "application/pdf")
            email.send(fail_silently=True)
        except Exception as e:
            logger.warning("Invoice email failed: %s", e)
            send_transactional_email(
                org.email,
                f"Payment received — {org.name}",
                f"Your subscription payment ({invoice_id}) of {currency} {amount} was received.",
            )

    return True


@shared_task
def send_subscription_renewal_reminders():
    """Email clinic admins when subscription period ends within 7 days."""
    from datetime import timedelta

    from core.notifications import send_transactional_email

    from django.utils import timezone

    threshold = timezone.now() + timedelta(days=7)
    subs = Subscription.objects.filter(
        status="ACTIVE",
        current_period_end__isnull=False,
        current_period_end__lte=threshold,
        current_period_end__gte=timezone.now(),
    ).select_related("organization", "plan")

    base = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    for sub in subs:
        org = sub.organization
        if not org.email:
            continue
        end = sub.current_period_end.strftime("%d %b %Y")
        send_transactional_email(
            org.email,
            f"Subscription renewal due — {org.name}",
            (
                f"Your {sub.plan.name} plan for {org.name} renews on {end}.\n\n"
                f"Upgrade or renew at {base}/plans to avoid interruption.\n\n"
                f"— Damianix EMR"
            ),
        )

@shared_task
def check_subscription_limits():
    """
    Check all active subscriptions and optionally send reminder emails
    if they are nearing their limits (e.g., users, patients).
    """
    from .billing_service import get_subscription_status
    logger.info("Running scheduled task: check_subscription_limits")
    
    orgs = Organization.objects.filter(is_active=True, subscription__status="ACTIVE")
    for org in orgs:
        try:
            status_data = get_subscription_status(org)
            users_limit = status_data["limits"]["users"]
            patients_limit = status_data["limits"]["patients"]
            
            # Simple threshold logic: if current >= 90% of max
            if users_limit.get("max"):
                if users_limit["current"] >= users_limit["max"] * 0.9:
                    logger.warning(f"Org {org.name} is nearing user limit: {users_limit['current']}/{users_limit['max']}")
                    
            if patients_limit.get("max"):
                if patients_limit["current"] >= patients_limit["max"] * 0.9:
                    logger.warning(f"Org {org.name} is nearing patient limit: {patients_limit['current']}/{patients_limit['max']}")
        except Exception as e:
            logger.error(f"Error checking limits for org {org.id}: {str(e)}")


@shared_task
def prune_audit_logs():
    """
    Periodic task to prune audit logs older than a specific timeframe (e.g. 1 year)
    to save DB storage space for SAAS architecture.
    """
    from core.audit import AuditLog
    from django.utils import timezone
    from datetime import timedelta
    logger.info("Running scheduled task: prune_audit_logs")
    
    # Prune logs older than 365 days
    threshold_date = timezone.now() - timedelta(days=365)
    
    deleted_count, _ = AuditLog.objects.filter(timestamp__lt=threshold_date).delete()
    if deleted_count > 0:
        logger.info(f"Pruned {deleted_count} old audit logs.")
