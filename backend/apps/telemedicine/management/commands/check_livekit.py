"""
Verify self-hosted LiveKit configuration and connectivity.

Usage:
    python manage.py check_livekit
"""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify LiveKit credentials and server connectivity"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n[LiveKit] Checking configuration...\n"))

        provider = getattr(settings, "TELEMEDICINE_VIDEO_PROVIDER", "twilio").lower()
        if provider != "livekit":
            self.stdout.write(
                self.style.WARNING(
                    f"TELEMEDICINE_VIDEO_PROVIDER={provider!r} (set to 'livekit' to use self-hosted LiveKit)"
                )
            )

        url = getattr(settings, "LIVEKIT_URL", "")
        api_key = getattr(settings, "LIVEKIT_API_KEY", "")
        api_secret = getattr(settings, "LIVEKIT_API_SECRET", "")

        missing = [
            name
            for name, val in (
                ("LIVEKIT_URL", url),
                ("LIVEKIT_API_KEY", api_key),
                ("LIVEKIT_API_SECRET", api_secret),
            )
            if not val
        ]
        if missing:
            self.stdout.write(
                self.style.ERROR(f"Missing env vars: {', '.join(missing)}")
            )
            return

        self.stdout.write(f"  LIVEKIT_URL: {url}")
        self.stdout.write(f"  LIVEKIT_API_KEY: {api_key[:4]}...")

        try:
            from livekit import api as livekit_api
        except ImportError:
            self.stdout.write(
                self.style.ERROR(
                    "livekit-api not installed. Run: pip install livekit-api"
                )
            )
            return

        self.stdout.write(self.style.SUCCESS("  livekit-api: installed"))

        try:
            from apps.telemedicine.livekit_utils import (
                _api_url,
                generate_livekit_access_token,
            )
            from django.contrib.auth import get_user_model

            User = get_user_model()
            user = User.objects.filter(is_active=True).first()
            if not user:
                self.stdout.write(
                    self.style.WARNING("  No active user — skipping token test")
                )
            else:
                jwt = generate_livekit_access_token(user, room_name="emr-healthcheck")
                self.stdout.write(
                    self.style.SUCCESS(f"  JWT token: OK ({len(jwt)} chars)")
                )

            import asyncio

            async def ping_server():
                lkapi = livekit_api.LiveKitAPI(
                    _api_url(), api_key, api_secret
                )
                try:
                    rooms = await lkapi.room.list_rooms(livekit_api.ListRoomsRequest())
                    return len(rooms.rooms)
                finally:
                    await lkapi.aclose()

            room_count = asyncio.run(ping_server())
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Server API: reachable ({room_count} active room(s))"
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "\nLiveKit is configured. Start the server with:\n"
                    "  docker compose -f docker-compose.livekit.yml up -d\n"
                )
            )
        except Exception as exc:
            err = str(exc)
            if "401" in err or "invalid API key" in err.lower():
                self.stdout.write(
                    self.style.ERROR(
                        "  LiveKit rejected the API key (401).\n"
                        "  Keys in .env must match infra/livekit/livekit.dev.yaml under `keys:`.\n"
                        f"  Django is using LIVEKIT_API_KEY={api_key!r}\n"
                        "  Restart LiveKit after editing the yaml:\n"
                        "    docker compose -f docker-compose.livekit.yml up -d --force-recreate"
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f"  LiveKit check failed: {exc}"))
            self.stdout.write(
                "\nEnsure LiveKit is running (docker compose -f docker-compose.livekit.yml up -d)\n"
                "and LIVEKIT_URL points at it (ws://localhost:7880 on host, ws://livekit:7880 in Docker).\n"
            )
