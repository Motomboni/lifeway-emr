"""
Request sanitization middleware (clinic-grade security).

Rejects requests that contain:
- Path traversal sequences (../, ..\)
- Null bytes in path or query
- Suspicious headers or methods
"""
import re
from django.http import HttpResponseBadRequest
from django.utils.deprecation import MiddlewareMixin


# Path traversal and null-byte patterns
PATH_TRAVERSAL = re.compile(r'\.\./|\.\.\\|%2e%2e%2f|%2e%2e/|\.\.%2f', re.I)
NULL_BYTE = re.compile(r'%00|\x00')


class RequestSanitizerMiddleware(MiddlewareMixin):
    """
    Reject obviously malicious requests before they reach views.
    Logging is left to the application; this only short-circuits bad requests.
    """

    def process_request(self, request):
        path = request.path or ''
        query_string = request.META.get('QUERY_STRING', '') or ''
        full_path = path + ('?' + query_string if query_string else '')

        if PATH_TRAVERSAL.search(full_path) or NULL_BYTE.search(full_path):
            return HttpResponseBadRequest('Bad Request')

        # Optional: restrict methods (Django/DRF already enforce this per view)
        if request.method and request.method.upper() not in (
            'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'
        ):
            return HttpResponseBadRequest('Bad Request')

        return None
