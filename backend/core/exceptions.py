"""
Unified DRF exception handler for consistent API error responses.

Shape: { "detail": str, "code": str, "fields": {...}? }
Rate-limit responses also include "retry_after".
"""

from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def _stringify_detail(detail) -> str:
    if detail is None:
        return "An error occurred."
    if isinstance(detail, list):
        parts = []
        for item in detail:
            if isinstance(item, dict):
                parts.append(str(item.get("message") or item))
            else:
                parts.append(str(item))
        return "; ".join(parts) if parts else "An error occurred."
    if isinstance(detail, dict):
        parts = []
        for key, val in detail.items():
            if isinstance(val, list):
                parts.append(f"{key}: {', '.join(str(v) for v in val)}")
            else:
                parts.append(f"{key}: {val}")
        return "; ".join(parts) if parts else "An error occurred."
    return str(detail)


def emr_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return response

    data = response.data
    payload = {
        "detail": "An error occurred.",
        "code": getattr(exc, "default_code", "error"),
    }

    if isinstance(data, dict):
        if "detail" in data:
            payload["detail"] = _stringify_detail(data["detail"])
        elif "non_field_errors" in data:
            payload["detail"] = _stringify_detail(data["non_field_errors"])
        else:
            field_errors = {
                k: v if isinstance(v, list) else [str(v)]
                for k, v in data.items()
                if k not in ("detail", "message", "error", "retry_after")
            }
            if field_errors:
                payload["fields"] = field_errors
                payload["detail"] = _stringify_detail(field_errors)
            elif data.get("message"):
                payload["detail"] = str(data["message"])
            elif data.get("error"):
                payload["detail"] = str(data["error"])

        if "retry_after" in data:
            payload["retry_after"] = data["retry_after"]
    elif isinstance(data, list):
        payload["detail"] = _stringify_detail(data)

    if isinstance(exc, ValidationError):
        payload["code"] = "validation_error"
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        payload["code"] = "rate_limit_exceeded"

    response.data = payload
    return response
