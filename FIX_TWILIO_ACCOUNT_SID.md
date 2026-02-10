# Fix Twilio Account SID Error

## Current Problem

Your `.env` file has an **incorrect Account SID**:
```
TWILIO_ACCOUNT_SID=0c47e7ba1cba93e2949dc8a876cc26ec
```

**This is wrong** because:
- Twilio Account SIDs **must start with `AC`**
- Your current value doesn't start with `AC`

## How to Fix

### Step 1: Get Your Correct Account SID

1. **Go to Twilio Console**: https://console.twilio.com/
2. **Look at the Dashboard** (main page)
3. **Find "Account SID"** - it's usually displayed at the top of the page
4. **Copy the Account SID** - it should look like:
   ```
   ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   - Starts with `AC`
   - 34 characters total
  - Example: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Step 2: Get Your Auth Token

1. **In Twilio Console**, click your **account name** (top right)
2. Click **"Account Settings"**
3. Or go directly to: https://console.twilio.com/us1/account/settings/account
4. Find **"Auth Token"** section
5. Click **"Show"** button next to Auth Token
6. **Copy the Auth Token** - it's a long random string (~32 characters)
   - ⚠️ **Does NOT start with `AC` or `SK`**
   - Just a random string like: `04983eff...f289`

### Step 3: Update Your .env File

Edit `backend/.env` and update these lines:

```env
# Twilio Video Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret_here
TWILIO_RECORDING_ENABLED=False
```

**Replace**:
- `TWILIO_ACCOUNT_SID` with your Account SID (must start with `AC`)
- `TWILIO_AUTH_TOKEN` with your Auth Token (random string, no prefix)

### Step 4: Verify Your Other Credentials

While you're at it, make sure:
- `TWILIO_API_KEY` starts with `SK`
- `TWILIO_API_SECRET` is a random string (no prefix)

### Step 5: Restart Django Server

After updating `.env`:
```bash
# Stop the server (Ctrl+C)
# Then restart:
cd backend
python manage.py runserver
```

### Step 6: Test Again

```bash
cd backend
python manage.py test_twilio
```

Should see: `[SUCCESS] All Twilio tests passed!`

## Quick Reference

- **Account SID**: Starts with `AC`, 34 characters
- **Auth Token**: Random string, ~32 characters, NO prefix
- **API Key**: Starts with `SK`, 34 characters
- **API Secret**: Random string, ~32 characters, NO prefix

## Where to Find Credentials

- **Account SID**: Dashboard (top of page) or Account Settings
- **Auth Token**: Account Settings → Show Auth Token
- **API Key**: API Keys page → Create/View API Keys
- **API Secret**: Only shown when creating API Key (copy immediately!)

## Common Mistakes

❌ **Wrong**: `TWILIO_ACCOUNT_SID=0c47e7ba1cba93e2949dc8a876cc26ec` (no AC prefix)
✅ **Correct**: `TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` (starts with AC)

❌ **Wrong**: Using Auth Token that starts with `AC` or `SK`
✅ **Correct**: Auth Token is just a random string with no prefix
