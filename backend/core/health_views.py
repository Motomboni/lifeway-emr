"""
Health Check Views

Provides endpoints for monitoring application health and status.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import os


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Basic health check endpoint.
    
    Returns 200 if the application is running.
    """
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_detailed(request):
    """
    Detailed health check endpoint.
    
    Checks:
    - Database connectivity
    - Cache connectivity
    - Application status
    
    Returns 200 if all checks pass, 503 if any check fails.
    """
    checks = {
        'database': False,
        'cache': False,
        'application': True,
    }
    
    errors = []
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        checks['database'] = True
    except Exception as e:
        errors.append(f'Database check failed: {str(e)}')
    
    # Check cache
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            checks['cache'] = True
        else:
            errors.append('Cache check failed: Unable to read/write')
    except Exception as e:
        errors.append(f'Cache check failed: {str(e)}')
    
    # Determine overall status
    all_healthy = all(checks.values())
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    
    response_data = {
        'status': 'healthy' if all_healthy else 'unhealthy',
        'timestamp': timezone.now().isoformat(),
        'checks': checks,
    }
    
    if errors:
        response_data['errors'] = errors
    
    return Response(response_data, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_info(request):
    """
    Application information endpoint.
    
    Returns version, environment, and basic system info.
    """
    from django.conf import settings
    
    info = {
        'application': 'Modern EMR System',
        'version': os.environ.get('APP_VERSION', '1.0.0'),
        'environment': 'development' if settings.DEBUG else 'production',
        'timestamp': timezone.now().isoformat(),
        'database': settings.DATABASES['default']['ENGINE'].split('.')[-1],
        'debug': settings.DEBUG,
    }
    
    # Don't expose sensitive info in production
    if settings.DEBUG:
        info['allowed_hosts'] = settings.ALLOWED_HOSTS
        info['cors_origins'] = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
    
    return Response(info, status=status.HTTP_200_OK)
