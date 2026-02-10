# Twilio Setup - Quick Action Required ⚠️

## Current Issue

The error you're seeing:
```
Authentication Error - invalid username
GET /Accounts/your-twilio-account-sid.json
```

This means your `.env` file has **placeholder values** instead of real Twilio credentials.

## Quick Fix (3 Steps)

### Step 1: Get Twilio Credentials

1. **Sign up** (if needed): https://www.twilio.com/try-twilio
2. **Log in**: https://console.twilio.com/
3. **Get credentials**:
   - **Account SID**: On dashboard (starts with `AC`)
   - **Auth Token**: Account Settings → Show Auth Token
   - **API Key**: Create at API Keys page → Copy SID and Secret

### Step 2: Create .env File

Create file: `backend/.env`

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_actual_auth_token
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_actual_api_secret
TWILIO_RECORDING_ENABLED=False
```

**Replace the `x` and `your_actual_*` with your real values!**

### Step 3: Test

```bash
cd backend
python manage.py test_twilio
```

Should show: `[SUCCESS] All Twilio tests passed!`

## Detailed Guide

See `GET_TWILIO_CREDENTIALS.md` for step-by-step instructions with screenshots locations.

## File Location

**Put `.env` in**: `backend/.env` (same folder as `manage.py`)

The system will automatically load it from there.

## Need Help?

- Twilio Console: https://console.twilio.com/
- Twilio Docs: https://www.twilio.com/docs/video
- Test command: `python manage.py test_twilio`
