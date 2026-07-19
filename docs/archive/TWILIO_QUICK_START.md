# Twilio Telemedicine Quick Start Guide

## ✅ Current Status

- ✅ Twilio package installed (v9.3.0)
- ✅ twilio-video package installed (v2.33.0)
- ⚠️ Twilio credentials need to be configured

## Step 1: Get Your Twilio Credentials

### Option A: Use Twilio Trial Account (Free - $15.50 credit)

1. **Sign up**: Go to https://www.twilio.com/try-twilio
2. **Verify your phone number** (required for trial)
3. **Get Account SID and Auth Token**:
   - Go to https://console.twilio.com/
   - Click on your account name (top right)
   - Copy **Account SID** and **Auth Token**

4. **Create API Key for Video**:
   - Go to: https://console.twilio.com/us1/develop/api-keys/keys
   - Click "Create API Key"
   - Name it: "EMR Video Key"
   - Copy **API Key SID** and **API Secret** (⚠️ Secret shown only once!)

### Option B: Use Existing Twilio Account

If you already have a Twilio account, just get:
- Account SID
- Auth Token  
- API Key SID (create new if needed)
- API Secret

## Step 2: Update Your .env File

Edit `backend/.env` file (or create it if it doesn't exist):

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret_here
TWILIO_RECORDING_ENABLED=False
```

**Important**: 
- Replace the placeholder values with your actual credentials
- Keep the `.env` file secure (don't commit it to git)
- Account SID starts with `AC`
- API Key SID starts with `SK`

## Step 3: Test Your Configuration

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

## Step 4: Test Telemedicine in the App

1. **Start Backend**:
   ```bash
   cd backend
   python manage.py runserver
   ```

2. **Start Frontend** (in a new terminal):
   ```bash
   cd frontend
   npm start
   ```

3. **Test Flow**:
   - Login as a **Doctor**
   - Navigate to a visit (or create one)
   - Click "📹 Telemedicine" button
   - Create a new telemedicine session
   - Click "Start Session"
   - Click "Join Call"
   - Grant camera/microphone permissions
   - Test video and audio controls

4. **Test as Patient**:
   - Login as a **Patient** (in another browser/incognito)
   - Go to `/patient-portal/telemedicine`
   - Find the session and click "Join Session"
   - Both doctor and patient should see each other

## Troubleshooting

### "Authentication Error - invalid username"
- Check your Account SID and Auth Token are correct
- Make sure there are no extra spaces in `.env` file
- Restart the Django server after updating `.env`

### "API Key test failed"
- Verify API Key SID and API Secret are correct
- Make sure you copied the API Secret correctly (it's only shown once)
- Create a new API Key if needed

### "Video not working"
- **Development**: Works on `http://localhost` (no HTTPS needed)
- **Production**: Requires HTTPS for camera/microphone
- Check browser permissions for camera/microphone
- Try a different browser (Chrome, Firefox, Edge)

### "Failed to create room"
- Check Twilio account has Video API enabled
- Verify account has sufficient balance (trial account has $15.50)
- Check Twilio console for any errors

## Next Steps After Setup

Once configured, you can:
- ✅ Create telemedicine sessions from visit pages
- ✅ Join video calls as doctor or patient
- ✅ Record sessions (if enabled)
- ✅ View session history
- ✅ Access recordings (if enabled)

## Need Help?

- Twilio Console: https://console.twilio.com/
- Twilio Video Docs: https://www.twilio.com/docs/video
- Test your setup: `python manage.py test_twilio`
