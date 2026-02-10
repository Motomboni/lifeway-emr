# How to Get Your Twilio Credentials

## Step-by-Step Guide

### Step 1: Create Twilio Account (if you don't have one)

1. Go to: https://www.twilio.com/try-twilio
2. Click "Start Free Trial"
3. Fill in your information:
   - Email address
   - Password
   - Phone number (for verification)
4. Verify your phone number (they'll send a code)
5. Complete the signup process

**Note**: Free trial includes **$15.50 credit** - perfect for testing!

### Step 2: Get Account SID and Auth Token

1. **Log into Twilio Console**: https://console.twilio.com/
2. **You'll see your Account SID** on the dashboard (starts with `AC`)
3. **Get Auth Token**:
   - Click on your account name (top right)
   - Or go to: https://console.twilio.com/us1/account/settings/account
   - Click "Show" next to Auth Token
   - Copy the Auth Token (⚠️ This is sensitive - keep it secret!)

### Step 3: Create API Key for Video

1. Go to: https://console.twilio.com/us1/develop/api-keys/keys
2. Click **"Create API Key"** button
3. Fill in:
   - **Friendly Name**: `EMR Video Key` (or any name you like)
   - Click **"Create"**
4. **IMPORTANT**: Copy both values immediately:
   - **API Key SID** (starts with `SK`)
   - **API Secret** (⚠️ This is shown ONLY ONCE - copy it now!)
   
   If you lose the secret, you'll need to create a new API Key.

### Step 4: Update Your .env File

Create or edit `backend/.env` file:

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_actual_auth_token_here
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_actual_api_secret_here
TWILIO_RECORDING_ENABLED=False
```

**Replace the placeholder values with your actual credentials!**

### Step 5: Verify Setup

Run the test command:

```bash
cd backend
python manage.py test_twilio
```

You should see:
```
[OK] Twilio package is installed
[OK] Twilio Video SDK is available
[OK] Account SID: ACxxxxx...
[OK] Auth Token: xxxxx...
[OK] API Key SID: SKxxxxx...
[OK] API Secret: xxxxx...
[OK] Successfully connected to Twilio
[OK] API Key is valid
[SUCCESS] All Twilio tests passed!
```

## Quick Reference

### Where to Find Each Credential:

| Credential | Where to Find |
|------------|---------------|
| **Account SID** | Twilio Console Dashboard (starts with `AC`) |
| **Auth Token** | Console → Account Settings → Auth Token (click "Show") |
| **API Key SID** | Console → API Keys → Create New (starts with `SK`) |
| **API Secret** | Shown once when creating API Key - copy immediately! |

### Twilio Console Links:

- **Dashboard**: https://console.twilio.com/
- **Account Settings**: https://console.twilio.com/us1/account/settings/account
- **API Keys**: https://console.twilio.com/us1/develop/api-keys/keys

## Troubleshooting

### "Authentication Error - invalid username"
- ✅ **Cause**: Using placeholder values instead of real credentials
- ✅ **Fix**: Replace `your-twilio-account-sid` with your actual Account SID (starts with `AC`)

### "API Key test failed"
- Check that you copied the API Secret correctly (it's long and random)
- Make sure there are no extra spaces in your `.env` file
- Try creating a new API Key if you lost the secret

### "Failed to create room"
- Verify your Twilio account has Video API enabled
- Check account balance (trial has $15.50)
- Ensure all 4 credentials are set correctly

## Security Notes

⚠️ **Important**:
- Never commit `.env` file to git
- Keep credentials secret
- Don't share credentials publicly
- Rotate credentials if exposed

## Next Steps After Setup

Once credentials are configured:
1. ✅ Run `python manage.py test_twilio` - should pass
2. ✅ Start backend: `python manage.py runserver`
3. ✅ Start frontend: `npm start`
4. ✅ Test telemedicine in the app!
