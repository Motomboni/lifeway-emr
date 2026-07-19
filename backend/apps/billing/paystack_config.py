"""Paystack configuration helpers."""

from django.conf import settings

_PLACEHOLDER_FRAGMENTS = (
    "your-paystack",
    "your_paystack",
    "changeme",
    "placeholder",
    "example",
)


def get_paystack_secret_key() -> str:
    return (getattr(settings, "PAYSTACK_SECRET_KEY", "") or "").strip()


def get_paystack_public_key() -> str:
    return (getattr(settings, "PAYSTACK_PUBLIC_KEY", "") or "").strip()


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    if not value:
        return True
    if any(fragment in lowered for fragment in _PLACEHOLDER_FRAGMENTS):
        return True
    # Real Paystack keys start with sk_test_ / sk_live_ / pk_test_ / pk_live_
    if value.startswith(("sk_", "pk_")):
        return len(value) < 20
    return True


def is_paystack_configured() -> bool:
    secret = get_paystack_secret_key()
    public = get_paystack_public_key()
    if _looks_like_placeholder(secret) or _looks_like_placeholder(public):
        return False
    return secret.startswith(("sk_test_", "sk_live_")) and public.startswith(
        ("pk_test_", "pk_live_")
    )


def is_paystack_mock_enabled() -> bool:
    """
    Local/dev mock payments when real Paystack keys are not configured.

    Enabled when:
    - PAYSTACK_MOCK=true, or
    - DEBUG=True and Paystack keys are missing/placeholder
    """
    explicit = (getattr(settings, "PAYSTACK_MOCK", "") or "").strip().lower()
    if explicit in ("true", "1", "yes"):
        return True
    if explicit in ("false", "0", "no"):
        return False
    return bool(getattr(settings, "DEBUG", False)) and not is_paystack_configured()


def require_paystack_configured() -> None:
    if is_paystack_configured():
        return
    raise ValueError(
        "Paystack is not configured. Set real PAYSTACK_SECRET_KEY (sk_test_… / sk_live_…) "
        "and PAYSTACK_PUBLIC_KEY (pk_test_… / pk_live_…) in backend/.env, "
        "or enable PAYSTACK_MOCK=true for local development."
    )
