"""
Clinic-grade password validators for EMR (HIPAA-aligned).

- Minimum length 12
- Complexity: upper, lower, digit, special character
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class MinimumLengthValidator:
    """Require at least min_length characters (default 12 for clinic-grade)."""

    def __init__(self, min_length=12, **kwargs):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("Password must be at least %(min_length)d characters."),
                code="password_too_short",
                params={"min_length": self.min_length},
            )

    def get_help_text(self):
        return _("At least %(min_length)d characters.") % {"min_length": self.min_length}


class ComplexityValidator:
    """Require uppercase, lowercase, digit, and special character."""

    def __init__(self, **kwargs):
        pass

    def validate(self, password, user=None):
        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code="password_no_upper",
            )
        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code="password_no_lower",
            )
        if not re.search(r"\d", password):
            raise ValidationError(
                _("Password must contain at least one digit."),
                code="password_no_digit",
            )
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
            raise ValidationError(
                _("Password must contain at least one special character (!@#$%^&* etc.)."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _(
            "Must contain at least one uppercase letter, one lowercase letter, "
            "one digit, and one special character."
        )
