# Telemedicine: Transcription and Billing

## Automatic transcription (after session)

Completed telemedicine sessions that have **recording enabled** can be transcribed to text.

### Flow

1. Create a session with **Enable Recording** checked.
2. After the session, end it (recordings are fetched from Twilio when available).
3. On the Telemedicine page, for a completed session with a recording, click **Transcribe recording**.
4. Backend runs transcription when a provider is configured (see below). Result is stored on the session and shown in the session card.

### Enabling automatic transcription (optional)

Choose a provider via `TRANSCRIPTION_PROVIDER`:

#### Option A — OpenAI Whisper API (cloud)

1. Install: `pip install openai requests`
2. Set in your environment or Django settings:
   - `TRANSCRIPTION_PROVIDER=openai` (default)
   - `OPENAI_API_KEY=sk-...` (or `TRANSCRIPTION_API_KEY`)
3. Ensure the session has a `recording_url`. Twilio recording URLs may require authentication; the backend downloads recordings server-side with Twilio credentials.

#### Option B — faster-whisper (local, no API key)

1. Install: `pip install faster-whisper requests`
2. Install **ffmpeg** and ensure it is on your `PATH` (required for Twilio `.mp4` recordings).
3. Set in your environment:
   - `TRANSCRIPTION_PROVIDER=faster-whisper`
   - `FASTER_WHISPER_MODEL=base` (or `small`, `medium`, etc.)
   - `FASTER_WHISPER_DEVICE=cpu` (or `cuda` if GPU available)
   - Optional: `FASTER_WHISPER_COMPUTE_TYPE=int8`, `FASTER_WHISPER_LANGUAGE=en`

If no provider is configured, clicking "Transcribe recording" will set status to **PENDING**.

---

## Billing for telemedicine sessions

When **ending** a session, the doctor can check **Add telemedicine consultation to visit bill**. That adds a billing line item to the visit using a service from your **Service Catalog**.

### Setup

1. Add a service to **Service Catalog** (e.g. via Admin or import):
   - **Service code**: `TELEMED-001` (or set `TELEMEDICINE_BILLING_SERVICE_CODE` in settings to another code)
   - **Name**: e.g. "Telemedicine Consultation"
   - **Department**: CONSULTATION (or as you prefer)
   - **Workflow type**: OTHER (no consultation link required)
   - **Amount**: your telemedicine fee
   - **Active**: Yes

2. Optional: in `settings.py` or env:
   - `TELEMEDICINE_BILLING_SERVICE_CODE = 'TELEMED-001'` (default if not set)

3. When ending a session, check **Add telemedicine consultation to visit bill**. One line item per visit is created; the receptionist can collect payment as usual.

### Behaviour

- Only **doctors** can end sessions and add billing.
- The visit must be **OPEN**.
- If the service code is missing or inactive, ending the session still succeeds; billing is skipped and a log message is written.
