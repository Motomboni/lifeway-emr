"""
Caching utilities for API responses.

Provides decorators and utilities for caching expensive operations.
"""
from functools import wraps
from django.core.cache import cache
from django.conf import settings
import hashlib
import json


def cache_response(timeout=300, key_prefix='api'):
    """
    Decorator to cache API responses.
    
    Args:
        timeout: Cache timeout in seconds (default: 5 minutes)
        key_prefix: Prefix for cache keys
    
    Usage:
        @cache_response(timeout=600)
        def my_view(request):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            cache_key_parts = [key_prefix, func.__name__]
            
            # Add request-specific parts if available
            if args and hasattr(args[0], 'GET'):
                request = args[0]
                # Include query params in cache key
                query_string = request.GET.urlencode()
                if query_string:
                    cache_key_parts.append(hashlib.md5(query_string.encode()).hexdigest())
            
            cache_key = ':'.join(cache_key_parts)
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """
    Invalidate all cache keys matching a pattern.
    
    Args:
        pattern: Pattern to match cache keys (e.g., 'api:visits:*')
    """
    # Note: This is a simplified version. In production, use Redis with pattern matching
    # or maintain a list of cache keys
    pass


def get_or_set_cache(key, callable_func, timeout=300):
    """
    Get value from cache or set it if not present.
    
    Args:
        key: Cache key
        callable_func: Function to call if cache miss
        timeout: Cache timeout in seconds
    
    Returns:
        Cached or computed value
    """
    value = cache.get(key)
    if value is None:
        value = callable_func()
        cache.set(key, value, timeout)
    return value
