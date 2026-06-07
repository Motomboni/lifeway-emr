"""
Per-organization branding for receipts, emails, and PDFs (SaaS multi-tenant).
"""

from django.conf import settings


def get_org_branding(organization=None) -> dict:
    """Return clinic branding dict; falls back to global settings."""
    if organization is not None:
        return {
            "clinic_name": organization.name or getattr(
                settings, "CLINIC_NAME", "Clinic"
            ),
            "clinic_address": organization.address
            or getattr(settings, "CLINIC_ADDRESS", ""),
            "clinic_phone": organization.phone
            or getattr(settings, "CLINIC_PHONE", ""),
            "clinic_email": organization.email
            or getattr(settings, "CLINIC_EMAIL", ""),
            "logo_url": organization.logo_url or "",
            "patient_id_prefix": organization.patient_id_prefix or "LMC",
            "organization_id": organization.id,
        }
    return {
        "clinic_name": getattr(settings, "CLINIC_NAME", "Clinic"),
        "clinic_address": getattr(settings, "CLINIC_ADDRESS", ""),
        "clinic_phone": getattr(settings, "CLINIC_PHONE", ""),
        "clinic_email": getattr(settings, "CLINIC_EMAIL", ""),
        "logo_url": "",
        "patient_id_prefix": "LMC",
        "organization_id": None,
    }


def get_org_branding_for_visit(visit) -> dict:
    org = getattr(visit, "organization", None)
    if org is None and hasattr(visit, "patient"):
        org = getattr(visit.patient, "organization", None)
    return get_org_branding(org)
