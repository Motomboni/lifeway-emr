# Telemedicine Quick Test Guide

## Prerequisites
- Backend running: `python manage.py runserver`
- Frontend running: `npm start`
- Internet connection (for Twilio API)
- Twilio credentials configured in `.env`

## 5-Minute Manual Test

### Step 1: Access Telemedicine Page (30 seconds)

1. Open browser: `http://localhost:3000`
2. Login as doctor:
   - Username: `doctor` (or your test doctor)
   - Password: your password
3. Navigate to: **Telemedicine** (from sidebar)

### Step 2: Create a Session (1 minute)

1. Click **"Create New Session"** button
2. Fill in the form:
   - **Visit:** Select an open visit (with PAID status)
   - **Patient:** Auto-filled from visit
   - **Scheduled Start:** Pick a time (current or future)
   - **Recording:** Check if you want to record
3. Click **"Create Session"**
4. You should see the session in the list

### Step 3: Join the Session (2 minutes)

1. Find your session in the list
2. Click **"Join Session"** button
3. **Expected:**
   - Browser asks for camera/microphone permissions → **Allow**
   - Video call interface opens
   - Your video appears in the preview
   - Twilio room ID shows in the UI

4. **Open second browser** (incognito or different browser):
   - Login as different user
   - Join the same session
   - Both participants should see each other

### Step 4: End the Session (1 minute)

1. In the doctor's browser, click **"End Session"**
2. Dialog appears:
   - **Session Notes:** Enter "Test session completed"
   - **Add to Bill:** Check this box
3. Click **"End Session"**
4. **Expected:**
   - Session status changes to COMPLETED
   - If "Add to Bill" was checked:
     - Billing line item added to visit
     - Shows in visit charges

### Step 5: Test Transcription (30 seconds - Optional)

**Only if OPENAI_API_KEY is configured:**

1. Find the completed session with recording
2. Click **"Transcribe Recording"**
3. **Expected:**
   - Status changes to "PROCESSING" or "PENDING"
   - If recording available:
     - Transcription completes
     - Text appears in session details
   - If no recording:
     - Status stays "PENDING" (expected)

## Quick Troubleshooting

### Issue: "Network error" when creating session
**Solution:** Check Twilio credentials in backend `.env`:
```bash
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_API_KEY=SK...
TWILIO_API_SECRET=...
```

### Issue: Video not appearing
**Solutions:**
1. Allow camera/microphone permissions in browser
2. Check browser console for errors
3. Verify internet connection

### Issue: Cannot join session
**Solutions:**
1. Ensure visit payment status is PAID or SETTLED
2. Check user has appropriate role (DOCTOR, RECEPTIONIST, or ADMIN)
3. Verify session status is not CANCELLED or FAILED

### Issue: "Add to Bill" not working
**Solutions:**
1. Verify telemedicine service exists in Service Catalog:
   - Service Code: `TELEMED-001`
   - Status: Active
2. Visit must be OPEN (not CLOSED)
3. User must be DOCTOR role

### Issue: Transcription stuck on "PENDING"
**Expected behavior if:**
- No OPENAI_API_KEY configured → Stays PENDING
- No recording available → Stays PENDING
- Recording URL requires auth → May fail

**Solution:** Add OpenAI key to `.env`:
```bash
OPENAI_API_KEY=sk-...
```

## Success Criteria

✅ **System Working** if:
1. Session created successfully
2. Access token generated
3. Video call interface opens
4. Can join from multiple browsers
5. Session ends successfully
6. Billing line item added (if checked)

## Test with cURL (Backend Only)

If frontend isn't available, test the backend API directly:

### 1. Get Auth Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"doctor\",\"password\":\"yourpassword\"}"
```

### 2. List Sessions
```bash
curl http://localhost:8000/api/v1/telemedicine/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Create Session
```bash
curl -X POST http://localhost:8000/api/v1/telemedicine/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"visit\": 250,
    \"scheduled_start\": \"2026-02-06T18:00:00Z\",
    \"recording_enabled\": true
  }"
```

### 4. Generate Token
```bash
curl -X POST http://localhost:8000/api/v1/telemedicine/{SESSION_ID}/generate-token/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. End Session
```bash
curl -X POST http://localhost:8000/api/v1/telemedicine/{SESSION_ID}/end/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"notes\": \"Test completed\",
    \"add_to_bill\": true
  }"
```

## Browser Developer Tools

Check these if issues occur:

### Frontend Console (F12)
Look for:
- Twilio errors
- Network requests failing
- Permission errors

### Backend Terminal
Watch for:
- API request logs
- Twilio API responses
- Error traceback

### Network Tab
Verify:
- `/telemedicine/` API calls succeed (200)
- Twilio token generation works
- No CORS errors

## Next Steps After Testing

1. **If everything works:** System is production-ready for telemedicine
2. **If token errors:** Verify Twilio credentials and account status
3. **If network errors:** Check firewall/proxy settings
4. **If UI errors:** Check frontend console and backend logs

## Support Resources

- **Twilio Docs:** https://www.twilio.com/docs/video
- **Backend Logs:** Check Django terminal output
- **Frontend Logs:** Browser developer console (F12)
- **Test Script:** `backend/test_telemedicine_flow.py`
