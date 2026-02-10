"""
Rate limiting middleware and utilities.

Per EMR Rules: Protect against abuse while allowing legitimate use.
"""
from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from functools import wraps
import time


class RateLimiter:
    """
    Simple rate limiter using cache.
    
    Tracks requests per IP/user and enforces limits.
    """
    
    def __init__(self, requests_per_minute=60, requests_per_hour=1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
    
    def is_allowed(self, identifier):
        """
        Check if request is allowed for given identifier (IP or user ID).
        
        Args:
            identifier: Unique identifier (IP address or user ID)
        
        Returns:
            tuple: (is_allowed: bool, remaining: int, reset_time: int)
        """
        now = timezone.now()
        minute_key = f'rate_limit:minute:{identifier}:{now.minute}'
        hour_key = f'rate_limit:hour:{identifier}:{now.hour}'
        
        # Get current counts
        minute_count = cache.get(minute_key, 0)
        hour_count = cache.get(hour_key, 0)
        
        # Check limits
        if minute_count >= self.requests_per_minute:
            return False, 0, 60 - now.second
        
        if hour_count >= self.requests_per_hour:
            return False, 0, 3600 - (now.minute * 60 + now.second)
        
        # Increment counters
        cache.set(minute_key, minute_count + 1, 60)
        cache.set(hour_key, hour_count + 1, 3600)
        
        remaining = min(
            self.requests_per_minute - minute_count - 1,
            self.requests_per_hour - hour_count - 1
        )
        
        return True, remaining, 0


def get_client_identifier(request):
    """Get rate-limit identifier: real client IP (proxy-aware) or user id if authenticated."""
    if getattr(request, 'user', None) and request.user.is_authenticated:
        return f"user:{request.user.id}"
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def rate_limit(requests_per_minute=60, requests_per_hour=1000):
    """
    Decorator to rate limit a view.
    
    Args:
        requests_per_minute: Max requests per minute
        requests_per_hour: Max requests per hour
    
    Usage:
        @rate_limit(requests_per_minute=30)
        def my_view(request):
            ...
    """
    limiter = RateLimiter(requests_per_minute, requests_per_hour)
    
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            identifier = get_client_identifier(request)
            
            is_allowed, remaining, reset_time = limiter.is_allowed(identifier)
            
            if not is_allowed:
                response = JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.',
                    'retry_after': reset_time
                }, status=429)
                response['Retry-After'] = str(reset_time)
                return response
            
            # Add rate limit headers (DRF Response and HttpResponse both support [] assignment)
            response = func(request, *args, **kwargs)
            response['X-RateLimit-Remaining'] = str(remaining)
            response['X-RateLimit-Reset'] = str(int(time.time()) + reset_time)
            return response
        return wrapper
    return decorator
