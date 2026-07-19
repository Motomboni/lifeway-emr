"""Integration hub stub API."""



from django.utils import timezone

from rest_framework import status

from rest_framework.decorators import api_view, permission_classes

from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response



from core.permissions import IsPlatformAdmin



from .models import ExternalHealthHub





def _serialize(h: ExternalHealthHub) -> dict:

    return {

        "hub_type": h.hub_type,

        "base_url": h.base_url,

        "api_key_env": h.api_key_env,

        "is_enabled": h.is_enabled,

        "last_sync_at": h.last_sync_at,

        "config": h.config,

    }





@api_view(["GET"])

@permission_classes([IsAuthenticated, IsPlatformAdmin])

def external_hubs_list(request):

    hubs = ExternalHealthHub.objects.all()

    if not hubs.exists():

        for hub_type, _ in ExternalHealthHub.HUB_CHOICES:

            ExternalHealthHub.objects.get_or_create(hub_type=hub_type)

        hubs = ExternalHealthHub.objects.all()

    return Response([_serialize(h) for h in hubs])





@api_view(["PATCH"])

@permission_classes([IsAuthenticated, IsPlatformAdmin])

def external_hub_update(request, hub_type: str):

    hub = ExternalHealthHub.objects.filter(hub_type=hub_type.upper()).first()

    if not hub:

        return Response({"detail": "Hub not found."}, status=status.HTTP_404_NOT_FOUND)

    for field in ("base_url", "api_key_env", "is_enabled", "config"):

        if field in request.data:

            setattr(hub, field, request.data[field])

    if request.data.get("mark_synced"):

        hub.last_sync_at = timezone.now()

    hub.save()

    return Response(_serialize(h))


