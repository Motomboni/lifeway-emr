# How to Get the Correct Twilio Credentials

## ⚠️ Important: OAuth Client ≠ API Key

The **OAuth Client ID/Secret** you provided are for user authentication flows, not for server-side video token generation.

For Twilio Video, you need **4 separate credentials**:

## Required Credentials

1. **Account SID** (starts with `AC`)
2. **Auth Token** (long random string, ~32 characters)
3. **API Key SID** (starts with `SK`)
4. **API Secret** (long random string, ~32 characters)

## Step-by-Step: Get All 4 Credentials

### Step 1: Get Account SID and Auth Token

1. **Go to Twilio Console**: https://console.twilio.com/
2. **Account SID** is on the dashboard (top of page)
   - Should start with `AC`
   - Example: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
3. **Get Auth Token**:
   - Click your account name (top right) → **Account Settings**
   - Or go to: https://console.twilio.com/us1/account/settings/account
   - Click **"Show"** next to **Auth Token**
   - Copy the Auth Token (it's a long random string, ~32 characters)
   - ⚠️ **Note**: Auth Token does NOT start with `AC` or `SK` - it's just a random string

### Step 2: Create API Key (for Video Token Generation)

1. **Go to API Keys page**: https://console.twilio.com/us1/develop/api-keys/keys
2. Click **"Create API Key"** button
3. Fill in:
   - **Friendly Name**: `EMR Video Key` (or any name)
   - Click **"Create"**
4. **CRITICAL**: Copy BOTH values immediately:
   - **API Key SID** (starts with `SK`, e.g., `SKxxxxxxxxxxxxx`)
   - **API Secret** (long random string, shown ONLY ONCE!)
   
   ⚠️ **If you lose the secret, you must create a new API Key**

### Step 3: Update Your .env File

Edit `backend/.env` and make sure you have:

```env
# Twilio Video Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret_here
TWILIO_RECORDING_ENABLED=False
```

**Important**:
- Account SID must start with `AC`
- Auth Token is a random string (no prefix)
- API Key must start with `SK`
- API Secret is a random string (no prefix)

## Current Issue

Your current `.env` has:
- ✅ Account SID: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (correct format)
- ❌ Auth Token: `SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (wrong - starts with SK)
- ✅ API Key: `SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (correct format)
- ✅ API Secret: `your_api_secret_here` (looks correct)

**Action**: Get the correct Auth Token from Twilio Console (Account Settings → Show Auth Token)

## Quick Links

- **Dashboard**: https://console.twilio.com/
- **Account Settings**: https://console.twilio.com/us1/account/settings/account
- **API Keys**: https://console.twilio.com/us1/develop/api-keys/keys

## After Updating

Run the test:
```bash
cd backend
python manage.py test_twilio
```

Should see: `[SUCCESS] All Twilio tests passed!`

## About OAuth Client

The OAuth Client ID/Secret you provided (`OQxxxx...` and `secret...`) are for:
- User authentication flows
- OAuth token generation
- Different use case than video token generation

**Keep them for other purposes**, but for Twilio Video, you need the API Key approach.
