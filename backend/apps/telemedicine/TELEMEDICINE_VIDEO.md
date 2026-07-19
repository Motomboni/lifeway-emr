# Telemedicine Video Providers



Telemedicine supports two WebRTC backends via `TELEMEDICINE_VIDEO_PROVIDER`:



| Provider | Env value | Best for |

|----------|-----------|----------|

| **Twilio Video** | `twilio` | Managed Twilio rooms + built-in recording |

| **LiveKit (self-hosted)** | `livekit` | Single-clinic control, on-prem / Docker |



## Self-hosted LiveKit (recommended for Lifeway)



### 1. Start the LiveKit server



**Windows (PowerShell):**

```powershell

.\scripts\start-livekit.ps1

```



**Docker Compose:**

```bash

docker compose -f docker-compose.livekit.yml up -d

# or with main stack:

docker compose --profile livekit up livekit -d

```



Config files:

- **Dev:** `infra/livekit/livekit.dev.yaml` (keys `devkey` / `secret`)

- **Prod:** `infra/livekit/livekit.yaml` (generate keys, enable Redis)



Generate production keys:

```bash

docker run --rm livekit/livekit-server:latest generate-keys

```

Put the key pair in `infra/livekit/livekit.yaml` under `keys:` and in `.env`.



### 2. Install app dependencies



**Backend (venv):**

```bash

pip install livekit-api

```



**Frontend:**

```bash

cd frontend && npm install

```

(`livekit-client` is already listed in `package.json`.)



**Database migration (once):**

```bash

python manage.py migrate telemedicine

```



### 3. Configure `.env`



**Backend on your machine (local dev):**

```env

TELEMEDICINE_VIDEO_PROVIDER=livekit

LIVEKIT_URL=ws://localhost:7880

LIVEKIT_API_KEY=devkey

LIVEKIT_API_SECRET=secret

```



**Backend in Docker** (same compose network as LiveKit):

```env

LIVEKIT_URL=ws://livekit:7880

```



**Production** (HTTPS site): use `wss://livekit.yourclinic.com` and TLS-terminated reverse proxy on port 7880.



### 4. Verify



```bash

python manage.py check_livekit

```



Restart Django + Vite, create a telemedicine session, and join the call.



### Ports (default dev)



| Port | Purpose |

|------|---------|

| 7880 | WebSocket + HTTP API |

| 7881 | WebRTC TCP |

| 7882 | TURN/UDP (optional dev) |

| 50100–50120 | ICE media (UDP) |



Open these on your firewall for production if clients are outside the LAN.



## Twilio setup (alternative)



```env

TELEMEDICINE_VIDEO_PROVIDER=twilio

TWILIO_ACCOUNT_SID=...

TWILIO_AUTH_TOKEN=...

TWILIO_API_KEY=...

TWILIO_API_SECRET=...

TWILIO_RECORDING_ENABLED=True

```



## Notes



- Sessions store `video_provider` so Twilio sessions still work after switching.

- **Recording:** Twilio uses `recording_enabled`. Self-hosted LiveKit needs [Room Egress](https://docs.livekit.io/home/egress/overview/) for server-side archives; doctor **live browser transcript** works on both.

- **Transcription:** Post-call STT from recordings works with Twilio today; wire LiveKit egress URLs when recording is enabled.



See also: [TELEMEDICINE_TRANSCRIPTION_AND_BILLING.md](./TELEMEDICINE_TRANSCRIPTION_AND_BILLING.md)


