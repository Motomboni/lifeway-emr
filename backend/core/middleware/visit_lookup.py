"""
Middleware to extract visit_id from URL and attach Visit object to request.

This enables:
- Payment guard middleware to check payment status
- Permission classes to check visit status
- ViewSets to access visit without redundant lookups

Per EMR rules: All clinical endpoints are visit-scoped.
"""
import logging
from django.shortcuts import get_object_or_404
from django.conf import settings
from apps.visits.models import Visit

logger = logging.getLogger(__name__)


class VisitLookupMiddleware:
    """
    Middleware to extract visit_id from URL path and attach Visit to request.
    
    Assumes URL pattern: /api/v1/visits/{visit_id}/...
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        """
        Extract visit_id from URL if present and attach Visit to request.
        """
        # Check if URL contains visit_id pattern
        path_parts = request.path.split('/')
        
        try:
            # Look for 'visits' in path, next segment should be visit_id
            if 'visits' in path_parts:
                visits_index = path_parts.index('visits')
                if visits_index + 1 < len(path_parts):
                    visit_id_str = path_parts[visits_index + 1]
                    
                    # Try to parse as integer
                    try:
                        visit_id = int(visit_id_str)
                        # Fetch visit with bill relationship prefetched and attach to request
                        try:
                            visit = Visit.objects.select_related('bill').get(pk=visit_id)
                            request.visit = visit
                            request.visit_id = visit_id
                            if getattr(settings, 'DEBUG', False):
                                logger.debug("Middleware attached visit %s to request %s", visit_id, request.path)
                        except Visit.DoesNotExist:
                            if getattr(settings, 'DEBUG', False):
                                logger.debug("Middleware could not find visit %s for request %s", visit_id, request.path)
                            pass
                    except ValueError:
                        pass
        except (ValueError, IndexError):
            pass
        
        response = self.get_response(request)
        return response
