# Twilio Token Authorization Error - Troubleshooting

## Error Message

```
Failed to connect to video room: TwilioError: The authorization with Token failed
```

## Status

✅ **Room Creation Works**: Room is created successfully  
✅ **Token Generation Works**: Test command passes  
❌ **Token Authorization Fails**: When connecting to room, token is rejected

## Possible Causes

### 1. Room Name vs Room SID Mismatch

The token might be generated with a room name that doesn't match the actual room.

**Fix Applied**: Updated code to use **room SID** instead of room name (more reliable)

### 2. API Key/Secret Issue

Even though the test passes, the API Key/Secret might not be correct for the actual account.

**Check**:
- Verify API Key SID and Secret in Twilio Console
- Make sure they match what's in `.env`
- Try creating a new API Key if unsure

### 3. Room Not Fully Created

There might be a timing issue where the token is generated before the room is ready.

**Fix**: The code now uses room SID which is immediately available

## Changes Made

### 1. Updated Token Generation (`backend/apps/telemedicine/utils.py`)

- Changed to accept both `room_sid` and `room_name`
- Prefers `room_sid` over `room_name` (more reliable)
- Added better logging for debugging

### 2. Updated Token Request (`backend/apps/telemedicine/views.py`)

- Now passes both `room_sid` and `room_name` to token generation
- Uses room SID as primary identifier

## Next Steps

### Step 1: Restart Django Server

The code changes require a server restart:

```bash
# Stop the server (Ctrl+C)
# Then restart:
cd backend
python manage.py runserver
```

### Step 2: Try Creating Session Again

1. Create a new telemedicine session
2. Try to join the call
3. Check Django server logs for detailed error messages

### Step 3: Check Django Server Logs

When you try to join, check the Django server console for:
- `Generating token for room: ...` (shows which room identifier is used)
- `Token generated successfully` (confirms token was created)
- Any error messages

## Debugging

The updated code now logs:
- Which room identifier is being used (SID or name)
- Account SID and API Key (masked for security)
- Token generation success/failure

## If Still Failing

1. **Verify API Key/Secret**:
   - Go to: https://console.twilio.com/us1/develop/api-keys/keys
   - Check if your API Key shows "Secret not available"
   - If yes, create a new API Key and update `.env`

2. **Check Room Status**:
   - In Twilio Console, go to Video → Rooms
   - Verify the room was created
   - Check the room's unique name matches what's in the database

3. **Try Using Room SID Directly**:
   - The code now uses room SID which should be more reliable
   - Room SID always exists and is unique

## Expected Behavior After Fix

1. Room created with `unique_name`
2. Room SID returned immediately
3. Token generated using room SID
4. Client connects using token and room name
5. Twilio matches token's room (SID) with actual room

The fix ensures we use the room SID in the token, which is more reliable than the room name.
