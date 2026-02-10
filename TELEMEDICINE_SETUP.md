# Telemedicine Setup Guide

## Overview

Telemedicine functionality has been implemented using Twilio Video API, allowing doctors to conduct video consultations with patients.

## Features

✅ **Backend Implementation:**
- Telemedicine session models (TelemedicineSession, TelemedicineParticipant)
- Twilio Video integration (room creation, token generation)
- RESTful API endpoints for session management
- Visit-scoped architecture (all sessions linked to visits)
- Audit logging for all telemedicine actions
- Recording support (optional)

✅ **Frontend Implementation:**
- Video call component with Twilio Video SDK
- Session management UI
- Join/leave functionality
- Camera and microphone controls
- Responsive design

## Setup Instructions

### 1. Install Twilio Package

```bash
cd backend
pip install twilio
```

### 2. Get Twilio Credentials

1. Sign up for a Twilio account: https://www.twilio.com/
2. Get your Account SID and Auth Token from the Twilio Console
3. Create an API Key and API Secret for Video:
   - Go to Twilio Console → Account → API Keys & Tokens
   - Create a new API Key
   - Save the API Key SID and API Secret

### 3. Configure Settings

Update `backend/core/settings.py` or set environment variables:

```python
# Twilio Video Configuration
TWILIO_ACCOUNT_SID = 'your-account-sid'
TWILIO_AUTH_TOKEN = 'your-auth-token'
TWILIO_API_KEY = 'your-api-key-sid'
TWILIO_API_SECRET = 'your-api-secret'
TWILIO_RECORDING_ENABLED = False  # Set to True to enable recording
```

Or via environment variables:
```bash
export TWILIO_ACCOUNT_SID="your-account-sid"
export TWILIO_AUTH_TOKEN="your-auth-token"
export TWILIO_API_KEY="your-api-key-sid"
export TWILIO_API_SECRET="your-api-secret"
export TWILIO_RECORDING_ENABLED="False"
```

### 4. Install Frontend Dependencies

```bash
cd frontend
npm install twilio-video
```

### 5. Apply Database Migrations

```bash
cd backend
python manage.py migrate telemedicine
```

## Usage

### Creating a Telemedicine Session

1. Navigate to a visit (must be OPEN status)
2. Click "📹 Telemedicine" button (Doctor only)
3. Create a new session with:
   - Scheduled start time
   - Optional recording
   - Optional notes

### Joining a Video Call

1. From the telemedicine page, click "Join Call" on an active session
2. Grant camera/microphone permissions when prompted
3. Use controls to:
   - Toggle camera on/off
   - Mute/unmute microphone
   - Leave the call

### Ending a Session

- Doctor can end the session from the telemedicine page
- Session duration is automatically calculated
- Recordings (if enabled) are linked to the session

## API Endpoints

### Sessions
- `GET /api/v1/telemedicine/` - List sessions
- `POST /api/v1/telemedicine/` - Create session
- `GET /api/v1/telemedicine/{id}/` - Get session details
- `POST /api/v1/telemedicine/{id}/start/` - Start session
- `POST /api/v1/telemedicine/{id}/end/` - End session

### Access
- `POST /api/v1/telemedicine/token/` - Get access token for joining
- `POST /api/v1/telemedicine/{id}/leave/` - Leave session

## Permissions

- **Doctor**: Can create, start, end, and join sessions
- **Patient**: Can join sessions (via visit context)
- All actions are audit logged

## EMR Compliance

✅ Visit-scoped: All sessions linked to visits  
✅ Audit logging: All actions logged  
✅ PHI protection: Secure token generation  
✅ Role-based access: Doctor-only creation  
✅ Immutability: Completed sessions cannot be modified  

## Troubleshooting

### "Twilio package not installed"
- Install: `pip install twilio`

### "Twilio credentials not configured"
- Set all required environment variables or update settings.py

### Video not working in browser
- Ensure HTTPS in production (required for camera/microphone)
- Check browser permissions for camera/microphone
- Verify Twilio Video SDK is installed: `npm install twilio-video`

### Cannot join session
- Verify session status is IN_PROGRESS
- Check that access token was generated successfully
- Ensure user has permission to join (doctor or patient)

## Next Steps

1. ✅ Install Twilio package
2. ✅ Configure Twilio credentials
3. ✅ Install frontend dependencies (`twilio-video`)
4. ✅ Test video call functionality
5. ✅ Configure recording (optional)
6. ✅ Set up HTTPS for production (required for camera access)

## Notes

- Twilio Video requires HTTPS in production for camera/microphone access
- Recording feature requires additional Twilio configuration
- Sessions are automatically linked to visits for EMR compliance
- All telemedicine actions are audit logged
