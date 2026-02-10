"""
Input Sanitization Utilities

Provides functions to sanitize user input to prevent XSS and injection attacks.
"""
import re
import html
from django.utils.html import strip_tags
from django.utils.text import Truncator


def sanitize_text(text, max_length=None, allow_html=False):
    """
    Sanitize text input.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum length (truncate if longer)
        allow_html: Whether to allow HTML tags (default: False)
    
    Returns:
        Sanitized text
    """
    if not text:
        return ''
    
    # Convert to string
    text = str(text)
    
    # Remove HTML tags if not allowed
    if not allow_html:
        text = strip_tags(text)
    
    # Escape HTML entities
    text = html.escape(text)
    
    # Truncate if max_length specified
    if max_length:
        text = Truncator(text).chars(max_length)
    
    return text.strip()


def sanitize_phone(phone):
    """
    Sanitize phone number input.
    
    Args:
        phone: Phone number string
    
    Returns:
        Sanitized phone number (digits and + only)
    """
    if not phone:
        return ''
    
    # Remove all characters except digits, +, -, spaces, and parentheses
    phone = re.sub(r'[^\d\+\-\(\)\s]', '', str(phone))
    
    return phone.strip()


def sanitize_email(email):
    """
    Sanitize email input.
    
    Args:
        email: Email address string
    
    Returns:
        Sanitized email (lowercase, trimmed)
    """
    if not email:
        return ''
    
    email = str(email).lower().strip()
    
    # Basic email validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return ''
    
    return email


def sanitize_numeric(value, min_value=None, max_value=None):
    """
    Sanitize numeric input.
    
    Args:
        value: Numeric value
        min_value: Minimum allowed value
        max_value: Maximum allowed value
    
    Returns:
        Sanitized number or None if invalid
    """
    try:
        num = float(value)
        
        if min_value is not None and num < min_value:
            return None
        
        if max_value is not None and num > max_value:
            return None
        
        return num
    except (ValueError, TypeError):
        return None


def sanitize_date(date_string):
    """
    Sanitize date input.
    
    Args:
        date_string: Date string in YYYY-MM-DD format
    
    Returns:
        Sanitized date string or None if invalid
    """
    if not date_string:
        return None
    
    # Validate date format
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(date_pattern, str(date_string)):
        return None
    
    return str(date_string).strip()
