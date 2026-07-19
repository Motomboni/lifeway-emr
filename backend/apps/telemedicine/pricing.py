"""
Telemedicine billing price — backed by ServiceCatalog (TELEMED-001 by default).
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings

from apps.billing.service_catalog_models import ServiceCatalog

DEFAULT_TELEMEDICINE_SERVICE_CODE = "TELEMED-001"
DEFAULT_TELEMEDICINE_AMOUNT = Decimal("5000.00")


def get_telemedicine_service_code() -> str:
    return (
        getattr(settings, "TELEMEDICINE_BILLING_SERVICE_CODE", None)
        or DEFAULT_TELEMEDICINE_SERVICE_CODE
    )


def get_telemedicine_billing_service(organization=None) -> ServiceCatalog | None:
    """Resolve the active telemedicine billable service (org-specific preferred)."""
    code = get_telemedicine_service_code()
    qs = ServiceCatalog.objects.filter(service_code=code)
    if organization is not None:
        org_svc = qs.filter(organization=organization).first()
        if org_svc:
            return org_svc
    return qs.first()


def get_or_create_telemedicine_billing_service(organization=None) -> tuple[ServiceCatalog, bool]:
    """
    Return the telemedicine ServiceCatalog row, creating a sensible default if missing.
    Created=True when a new row was inserted.
    """
    existing = get_telemedicine_billing_service(organization)
    if existing:
        return existing, False

    code = get_telemedicine_service_code()
    # Unique service_code — only one row can exist; attach org when creating
    service = ServiceCatalog.objects.create(
        organization=organization,
        service_code=code,
        name="Telemedicine Consultation",
        department="CONSULTATION",
        category="CONSULTATION",
        workflow_type="OTHER",
        amount=DEFAULT_TELEMEDICINE_AMOUNT,
        description="Virtual clinic / telemedicine consultation fee charged when ending a session with billing.",
        requires_visit=True,
        requires_consultation=False,
        auto_bill=False,
        bill_timing="AFTER",
        is_active=True,
        allowed_roles=["DOCTOR", "ADMIN", "RECEPTIONIST"],
    )
    return service, True


def serialize_telemedicine_pricing(service: ServiceCatalog) -> dict:
    return {
        "service_id": service.id,
        "service_code": service.service_code,
        "name": service.name,
        "amount": str(service.amount),
        "currency": "NGN",
        "is_active": service.is_active,
        "description": service.description or "",
        "updated_at": service.updated_at.isoformat() if service.updated_at else None,
    }
