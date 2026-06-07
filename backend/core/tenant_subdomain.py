"""
Subdomain-based tenant resolution for multi-tenant SaaS.

Example: clinic1.emr.localhost → Organization slug "clinic1"
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

RESERVED_SUBDOMAINS = frozenset(
    {"www", "api", "app", "admin", "mail", "static", "cdn", "staging", "dev"}
)


def extract_subdomain_from_host(host: str) -> str | None:
    """
    Extract tenant slug from HTTP Host header.
    Returns None if subdomain routing is disabled or host is the base domain.
    """
    if not getattr(settings, "TENANT_SUBDOMAIN_ENABLED", False):
        return None

    if not host:
        return None

    host = host.split(":")[0].lower().strip()
    base_domain = getattr(settings, "TENANT_BASE_DOMAIN", "localhost").lower().strip()

    if host == base_domain:
        return None

    suffix = f".{base_domain}"
    if not host.endswith(suffix):
        return None

    subdomain = host[: -len(suffix)]
    if not subdomain or "." in subdomain:
        return None

    if subdomain in RESERVED_SUBDOMAINS:
        return None

    return subdomain


def resolve_organization_from_host(request):
    """Return Organization for the request host subdomain, if any."""
    host = request.get_host() if hasattr(request, "get_host") else ""
    slug = extract_subdomain_from_host(host)
    if not slug:
        return None

    try:
        from apps.organizations.models import Organization

        return Organization.objects.get(slug=slug, is_active=True)
    except Organization.DoesNotExist:
        logger.debug("No organization for subdomain slug: %s", slug)
        return None
