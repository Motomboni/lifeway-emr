"""
Middleware to extract visit_id from URL and attach Visit object to request.

This enables:
- Payment guard middleware to check payment status
- Permission classes to check visit status
- ViewSets to access visit without redundant lookups

Per EMR rules: All clinical endpoints are visit-scoped.
"""

import logging

from django.conf import settings
from django.http import Http404

from apps.visits.models import Visit
from core.tenant import (
    get_organization_from_request_headers,
    get_request_organization,
    is_platform_superuser,
)

logger = logging.getLogger(__name__)


class VisitLookupMiddleware:
    """
    Middleware to extract visit_id from URL path and attach Visit to request.

    Assumes URL pattern: /api/v1/visits/{visit_id}/...
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Extract visit_id from URL if present and attach org-scoped Visit to request."""
        path_parts = request.path.split("/")

        try:
            if "visits" in path_parts:
                visits_index = path_parts.index("visits")
                if visits_index + 1 < len(path_parts):
                    visit_id_str = path_parts[visits_index + 1]

                    try:
                        visit_id = int(visit_id_str)
                        filters = {"pk": visit_id}
                        # Headers work before JWT auth; fall back after DRF authenticates
                        org = get_organization_from_request_headers(request)
                        if not org:
                            org = get_request_organization(request)
                        if org and not is_platform_superuser(request):
                            filters["organization"] = org

                        visit = Visit.objects.select_related("bill").get(**filters)
                        request.visit = visit
                        request.visit_id = visit_id
                        if getattr(settings, "DEBUG", False):
                            logger.debug(
                                "Middleware attached visit %s to request %s",
                                visit_id,
                                request.path,
                            )
                    except (ValueError, Visit.DoesNotExist, Http404):
                        pass
        except (ValueError, IndexError):
            pass

        return self.get_response(request)
