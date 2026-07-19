"""Offline clinic queue sync API."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import CanManageOfflineQueue

from .clinic_queue_models import ClinicOfflineQueueEntry
from .clinic_queue_sync_service import execute_offline_queue_entry, mark_entry_failed


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, CanManageOfflineQueue])
def clinic_offline_queue(request):
    org = getattr(request, "organization", None)
    if request.method == "GET":
        device_id = request.query_params.get("device_id", "")
        qs = ClinicOfflineQueueEntry.objects.filter(status="PENDING")
        if org:
            qs = qs.filter(organization=org)
        if device_id:
            qs = qs.filter(device_id=device_id)
        return Response(
            [
                {
                    "id": e.id,
                    "device_id": e.device_id,
                    "action": e.action,
                    "payload": e.payload,
                    "status": e.status,
                    "error_message": e.error_message,
                    "created_at": e.created_at,
                }
                for e in qs[:100]
            ]
        )

    entry = ClinicOfflineQueueEntry.objects.create(
        organization=org,
        device_id=request.data.get("device_id", "unknown"),
        action=request.data.get("action", "QUEUE_NOTE"),
        payload=request.data.get("payload") or {},
        created_by=request.user,
    )
    return Response({"id": entry.id, "status": entry.status}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated, CanManageOfflineQueue])
def clinic_offline_sync(request, entry_id: int):
    org = getattr(request, "organization", None)
    qs = ClinicOfflineQueueEntry.objects.filter(id=entry_id)
    if org:
        qs = qs.filter(organization=org)
    entry = qs.first()
    if not entry:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if entry.status != "PENDING":
        return Response(
            {"detail": f"Entry already {entry.status}."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        result = execute_offline_queue_entry(
            entry, user=request.user, organization=org
        )
    except ValidationError as exc:
        mark_entry_failed(entry, str(exc.detail if hasattr(exc, "detail") else exc))
        return Response(
            {"detail": str(exc.detail if hasattr(exc, "detail") else exc), "status": "FAILED"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as exc:
        mark_entry_failed(entry, str(exc))
        return Response(
            {"detail": str(exc), "status": "FAILED"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "id": entry.id,
            "status": entry.status,
            "synced_at": entry.synced_at,
            "result": result,
        }
    )
