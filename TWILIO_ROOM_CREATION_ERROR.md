# Twilio Room Creation Error - Troubleshooting

## Error Message

```
Failed to create telemedicine session: 
HTTP Error Your request was: POST /Rooms
Twilio returned the following information:
Unable to create record: Authentication Error - invalid username
```

## Status

✅ **Test Command Passes**: `python manage.py test_twilio` shows all credentials are correct  
❌ **Room Creation Fails**: When actually creating a room, authentication fails

## Possible Causes

### 1. Django Server Not Restarted (Most Likely)

The Django server caches environment variables when it starts. If you updated the `.env` file, you need to **restart the Django server**.

**Fix**:
1. Stop the Django server (Ctrl+C)
2. Restart it: `python manage.py runserver`
3. Try creating a session again

### 2. Environment Variables Not Loaded

The `.env` file might not be in the correct location or not being loaded.

**Check**:
- File location: `backend/.env` (same folder as `manage.py`)
- File exists and has all Twilio credentials
- No syntax errors in `.env` file

### 3. Credentials Still Incorrect

Even though the test passes, double-check the credentials match exactly.

**Verify**:
1. Run: `python manage.py test_twilio`
2. Check the masked values match what's in your `.env`
3. Verify in Twilio Console that credentials are correct

## Quick Fix Steps

### Step 1: Restart Django Server

```bash
# Stop the server (Ctrl+C in the terminal running it)
# Then restart:
cd backend
python manage.py runserver
```

### Step 2: Verify Credentials

```bash
cd backend
python manage.py test_twilio
```

Should show: `[SUCCESS] All Twilio tests passed!`

### Step 3: Check .env File

Make sure `backend/.env` has:
```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_correct_auth_token_here
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret_here
TWILIO_RECORDING_ENABLED=False
```

**Important**: The Auth Token should NOT start with `AC` or `SK` - it's a random string.

### Step 4: Try Creating Session Again

After restarting the server, try creating a telemedicine session again.

## Why Test Passes But Room Creation Fails

The `test_twilio` command:
- Tests basic API connection ✅
- Tests token generation ✅
- Uses the same credentials from settings ✅

But when creating a room:
- Uses the same credentials
- But if the server wasn't restarted, it might be using old cached values
- Or there's a different code path that reads credentials differently

## Debugging

I've added better error logging to the `create_twilio_room` function. Check the Django server logs when you try to create a session - it will show:
- Which Account SID is being used (masked)
- Whether credentials are configured
- The exact error message

## Next Steps

1. **Restart Django server** (most important!)
2. Try creating a session again
3. If still fails, check Django server logs for the detailed error
4. Verify credentials one more time in Twilio Console

