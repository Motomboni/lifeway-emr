"""Default payment channel bootstrap for wallet top-ups."""

from .models import PaymentChannel

ONLINE_TOP_UP_CHANNEL_TYPES = {"PAYSTACK", "CARD"}


def ensure_paystack_channel() -> PaymentChannel:
    """Ensure the Paystack channel exists for online wallet top-ups."""
    channel, _ = PaymentChannel.objects.get_or_create(
        name="Paystack",
        defaults={
            "channel_type": "PAYSTACK",
            "is_active": True,
            "config": {
                "description": "Pay with card, bank transfer, or USSD",
                "supported_currencies": ["NGN"],
            },
        },
    )
    if not channel.is_active or channel.channel_type != "PAYSTACK":
        channel.channel_type = "PAYSTACK"
        channel.is_active = True
        channel.save(update_fields=["channel_type", "is_active", "updated_at"])
    return channel
