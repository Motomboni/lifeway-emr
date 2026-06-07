"""
Flutterwave webhook for SaaS subscription payments.
POST /api/v1/subscriptions/flutterwave/webhook/
"""

import hashlib
import json
import logging

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


def _verify_flutterwave_signature(payload: bytes, signature: str) -> bool:
    secret = getattr(settings, "FLUTTERWAVE_SECRET_KEY", "") or ""
    if not secret or not signature:
        return False
    expected = hashlib.sha256((secret + payload.decode("utf-8")).encode()).hexdigest()
    return expected == signature


@csrf_exempt
def flutterwave_webhook(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    signature = request.headers.get("verif-hash", "")
    payload = request.body

    if not _verify_flutterwave_signature(payload, signature):
        logger.warning("Flutterwave webhook signature invalid")
        return JsonResponse({"error": "Invalid signature"}, status=401)

    try:
        data = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    event = data.get("event")
    if event != "charge.completed":
        return JsonResponse({"message": f"Event {event} ignored"}, status=200)

    payment_data = data.get("data", {})
    status = payment_data.get("status")
    reference = payment_data.get("tx_ref")

    if status != "successful" or not reference:
        return JsonResponse({"message": "Not a successful charge"}, status=200)

    if not str(reference).startswith("SAAS-FW-"):
        return JsonResponse({"message": "Not a SaaS payment"}, status=200)

    try:
        from .saas_payment_handlers import verify_and_activate_subscription

        verify_and_activate_subscription(reference)
    except Exception as e:
        logger.exception("Flutterwave SaaS webhook failed: %s", e)
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"message": "SaaS subscription updated"}, status=200)
