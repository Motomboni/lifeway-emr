# Twilio Telemedicine Setup Guide

## Step 1: Get Twilio Account Credentials

1. **Sign up for Twilio** (if you don't have an account):
   - Go to https://www.twilio.com/try-twilio
   - Create a free account (includes $15.50 free credit)

2. **Get Account SID and Auth Token**:
   - Log into Twilio Console: https://console.twilio.com/
   - Go to Account → Account Info
   - Copy your **Account SID** and **Auth Token**

3. **Create API Key for Video**:
   - Go to Account → API Keys & Tokens
   - Click "Create API Key"
   - Give it a name (e.g., "EMR Video Key")
   - Copy the **API Key SID** and **API Secret** (⚠️ Secret is only shown once!)

## Step 2: Install Required Packages

### Backend
```bash
cd backend
pip install twilio
```

### Frontend
```bash
cd frontend
npm install twilio-video
```

## Step 3: Configure Environment Variables

Create or update `.env` file in the `backend` directory:

```bash
# Twilio Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_API_KEY=your_api_key_sid_here
TWILIO_API_SECRET=your_api_secret_here
TWILIO_RECORDING_ENABLED=False
```

**Or** set them as environment variables:
```bash
# Windows PowerShell
$env:TWILIO_ACCOUNT_SID="your_account_sid_here"
$env:TWILIO_AUTH_TOKEN="your_auth_token_here"
$env:TWILIO_API_KEY="your_api_key_sid_here"
$env:TWILIO_API_SECRET="your_api_secret_here"
$env:TWILIO_RECORDING_ENABLED="False"

# Linux/Mac
export TWILIO_ACCOUNT_SID="your_account_sid_here"
export TWILIO_AUTH_TOKEN="your_auth_token_here"
export TWILIO_API_KEY="your_api_key_sid_here"
export TWILIO_API_SECRET="your_api_secret_here"
export TWILIO_RECORDING_ENABLED="False"
```

## Step 4: Verify Setup

Run the test script to verify your Twilio configuration:
```bash
cd backend
python manage.py shell < scripts/test_twilio_setup.py
```

Or use the Django management command:
```bash
python manage.py test_twilio
```

## Step 5: Test Telemedicine

1. **Start the backend server**:
   ```bash
   cd backend
   python manage.py runserver
   ```

2. **Start the frontend server**:
   ```bash
   cd frontend
   npm start
   ```

3. **Test the flow**:
   - Login as a Doctor
   - Navigate to a visit
   - Click "📹 Telemedicine"
   - Create a new session
   - Start the session
   - Join the call (grant camera/mic permissions)
   - Test video/audio controls

## Troubleshooting

### "Twilio package not installed"
```bash
pip install twilio
```

### "Twilio credentials not configured"
- Check your `.env` file or environment variables
- Ensure all 4 credentials are set: Account SID, Auth Token, API Key, API Secret

### "Video not working in browser"
- **HTTPS Required**: In production, HTTPS is required for camera/microphone access
- **Development**: Use `http://localhost` (works in development)
- **Browser Permissions**: Grant camera/microphone permissions when prompted
- **Browser Support**: Chrome, Firefox, Safari, Edge (modern versions)

### "Failed to create room"
- Check Twilio account has Video API enabled
- Verify credentials are correct
- Check Twilio account balance (free tier has limits)

## Production Notes

- **HTTPS Required**: Camera/microphone access requires HTTPS in production
- **Recording**: Enable recording by setting `TWILIO_RECORDING_ENABLED=True`
- **Costs**: Twilio Video charges per participant-minute
- **Free Tier**: Includes $15.50 credit (good for testing)

## Next Steps

After setup, you can:
1. Create telemedicine sessions from visit pages
2. Join video calls as doctor or patient
3. Record sessions (if enabled)
4. View session history and recordings
