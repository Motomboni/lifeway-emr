"""
NHIA Claims Portal — local tracking only.

NHIA does not publish a public claims API. Facilities export claim packs
(CSV) and upload them through the official NHIA portal manually.

This module records submission status in the EMR (local reference only).
Optional HTTP submit exists for future use when hub.config.allow_http_submission
is true — do not enable until NHIA publishes an official integration.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import requests
from django.utils import timezone

from apps.integrations.models import ExternalHealthHub

logger = logging.getLogger(__name__)


@dataclass
class PortalSubmitResult:
    success: bool
    portal_reference: str
    message: str
    mode: str  # local | http


class NHIAPortalSubmitError(Exception):
    """Raised when portal submission fails in live (http) mode."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _get_nhia_hub() -> ExternalHealthHub | None:
    return ExternalHealthHub.objects.filter(hub_type="NHIA_PORTAL").first()


def _resolve_api_key(hub: ExternalHealthHub | None) -> str:
    env_name = (hub.api_key_env if hub else "") or "NHIA_PORTAL_API_KEY"
    return os.environ.get(env_name, "").strip()


def submit_claim_to_portal(submission) -> PortalSubmitResult:
    """
    Record manual NHIA portal submission locally (default).

    HTTP is only attempted when hub.config.allow_http_submission is explicitly true.
    """
    hub = _get_nhia_hub()
    claim_ref = submission.claim_reference or f"NHIA-{submission.visit_id}"
    ref = f"LOCAL-{claim_ref}"

    allow_http = bool(hub and hub.is_enabled and (hub.config or {}).get("allow_http_submission"))
    if not allow_http:
        logger.info(
            "NHIA manual workflow: visit=%s local ref=%s",
            submission.visit_id,
            ref,
        )
        return PortalSubmitResult(
            success=True,
            portal_reference=ref,
            message=(
                "Claim marked submitted locally. Upload the exported pack via the "
                "official NHIA portal and update paid/denied status when confirmed."
            ),
            mode="local",
        )

    base_url = (hub.base_url or "").strip().rstrip("/")
    if not base_url:
        return PortalSubmitResult(
            success=True,
            portal_reference=ref,
            message="Claim recorded locally (portal URL not configured).",
            mode="local",
        )

    pack = submission.claim_pack_snapshot or {}
    payload = {
        "claim_reference": claim_ref,
        "visit_id": submission.visit_id,
        "organization_id": submission.organization_id,
        "total_amount_ngn": str(submission.total_amount_ngn),
        "line_count": submission.line_count,
        "claim_pack": pack,
        "submitted_at": timezone.now().isoformat(),
    }

    api_key = _resolve_api_key(hub)
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    submit_path = (hub.config or {}).get("submit_path", "/api/v1/claims/submit")
    url = f"{base_url}{submit_path}"

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        logger.exception("NHIA portal HTTP submit failed: %s", exc)
        raise NHIAPortalSubmitError(
            "Unable to reach NHIA portal. Claim was not submitted."
        ) from exc

    if response.status_code >= 400:
        logger.warning(
            "NHIA portal rejected claim status=%s body=%s",
            response.status_code,
            response.text[:300],
        )
        raise NHIAPortalSubmitError(
            f"NHIA portal rejected the claim (HTTP {response.status_code})."
        )

    try:
        data = response.json()
    except ValueError:
        data = {}

    portal_ref = (
        data.get("portal_reference")
        or data.get("reference")
        or data.get("claim_id")
        or f"NHIA-{claim_ref}"
    )

    if hub:
        hub.last_sync_at = timezone.now()
        hub.save(update_fields=["last_sync_at", "updated_at"])

    return PortalSubmitResult(
        success=True,
        portal_reference=str(portal_ref),
        message=data.get("message") or "Claim submitted to NHIA portal.",
        mode="http",
    )
