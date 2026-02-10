# Debug "The authorization with Token failed" Error

## Current Error

```
TwilioError: The authorization with Token failed
```

This error means the token being generated is invalid or doesn't match the room.

## Critical Steps

### Step 1: Verify Django Server Was Restarted

**MOST IMPORTANT**: After updating `.env`, you MUST restart the Django server!

```bash
# Stop the server (Ctrl+C)
# Then restart:
cd backend
python manage.py runserver
```

The server caches environment variables when it starts. If you updated `.env` but didn't restart, it's still using old credentials.

### Step 2: Check Django Server Logs

When you try to join a telemedicine session, check the **Django server console** (not the browser console). You should see logs like:

```
INFO: Generating token for room: visit-123-abc12345 (type: name), user: 1
INFO: Using Account SID: ACd8feec...3cc4, API Key: SK5f03d9...c864
INFO: Token generated successfully (length: 500)
```

**If you see errors here**, that's the real issue.

### Step 3: Verify Credentials Match

Run the test command again:

```bash
cd backend
python manage.py test_twilio
```

Should show:
- ✅ `[OK] Successfully connected to Twilio`
- ✅ `[OK] API Key is valid`
- ✅ `[SUCCESS] All Twilio tests passed!`

### Step 4: Check Token Generation Details

The token generation logs will show:
- Which Account SID is being used
- Which API Key is being used
- Which room identifier is being used

**Look for**:
- Account SID starts with `AC` (not `0c...`)
- API Key starts with `SK`
- Room name matches what's in the database

## Common Causes

### 1. Server Not Restarted (Most Common)

**Symptom**: Test command passes, but token fails in app

**Fix**: Restart Django server after updating `.env`

### 2. Account SID and API Key Mismatch

**Symptom**: Token generation works, but authorization fails

**Fix**: Ensure API Key belongs to the same account as Account SID

### 3. Room Name Mismatch

**Symptom**: Token generated but can't connect to room

**Fix**: Token uses room name, frontend connects with room name - should match

### 4. Cached Credentials

**Symptom**: Updated `.env` but still using old values

**Fix**: Restart server, clear any Python cache files

## Debugging Steps

### 1. Check What Account SID is Being Used

In Django server logs, look for:
```
INFO: Using Account SID: ACd8feec...3cc4
```

If it shows `0c47e7ba...` (no AC prefix), the server wasn't restarted.

### 2. Verify Room Creation

Check Django logs when creating a session:
```
INFO: Creating Twilio room with Account SID: ACd8feec...3cc4
INFO: Room created - SID: RM..., Unique Name: visit-123-abc12345, Status: in-progress
```

### 3. Verify Token Generation

Check Django logs when joining:
```
INFO: Generating token for room: visit-123-abc12345 (type: name), user: 1
INFO: Token generated successfully (length: 500)
```

## Next Steps

1. **Restart Django server** (if you haven't already)
2. **Check Django server console** when joining a session
3. **Share the Django server logs** - they'll show what's actually happening
4. **Run test command** to verify credentials are correct

The browser console error doesn't tell us much - we need the Django server logs to see what's happening during token generation.
