# Twilio "Invalid Access Token issuer/subject" Error - Troubleshooting

## Error Message

```
TwilioError: Invalid Access Token issuer/subject
```

## What This Means

This error indicates that the **Account SID** used to generate the token doesn't match the account that owns the **API Key**.

## Root Cause

When creating a Twilio Access Token, you need:
1. **Account SID** - Must be the account that owns the API Key
2. **API Key SID** - The API Key identifier
3. **API Secret** - The secret for that API Key

If the Account SID doesn't match the API Key's account, you get this error.

## Common Causes

### 1. API Key from Different Account

You might have:
- Account SID from Account A
- API Key from Account B

**Solution**: Use the Account SID that matches your API Key, or create a new API Key for your Account SID.

### 2. API Key from Different Region

Twilio has different regions (US1, EU1, etc.). API Keys are region-specific.

**Solution**: Ensure your API Key is from the same region as your Account SID.

### 3. API Key Deleted or Revoked

If the API Key was deleted or revoked, tokens won't work.

**Solution**: Create a new API Key in the Twilio Console.

## How to Fix

### Step 1: Verify API Key Account

I've updated the `test_twilio` command to check if the API Key belongs to the correct account.

Run:
```bash
cd backend
python manage.py test_twilio
```

The command will now show:
- ✅ `[OK] API Key belongs to the correct account` - Everything is good
- ❌ `[ERROR] API Key Account SID mismatch!` - The Account SID doesn't match

### Step 2: Check Your Credentials

1. **Go to Twilio Console**: https://console.twilio.com/
2. **Check Account SID**: 
   - Go to Account → Account Info
   - Copy the Account SID (starts with `AC...`)
3. **Check API Key**:
   - Go to Account → API Keys & Tokens → API Keys
   - Find your API Key
   - Click on it to see which account it belongs to
   - Verify the Account SID matches

### Step 3: Update .env File

Make sure your `backend/.env` file has:

```env
# These MUST belong to the same Twilio account
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret_here
```

**Important**: 
- `TWILIO_ACCOUNT_SID` must be the account that owns `TWILIO_API_KEY`
- If they don't match, either:
  - Update `TWILIO_ACCOUNT_SID` to match the API Key's account, OR
  - Create a new API Key for your Account SID

### Step 4: Create New API Key (If Needed)

If your API Key belongs to a different account:

1. Go to: https://console.twilio.com/us1/develop/api-keys/keys
2. Click "Create new API Key"
3. Give it a friendly name (e.g., "EMR Telemedicine")
4. Click "Create"
5. **IMPORTANT**: Copy the **API Secret** immediately (you can only see it once!)
6. Update your `.env` file with the new API Key SID and Secret

### Step 5: Restart Django Server

After updating credentials:

```bash
# Stop the server (Ctrl+C)
# Then restart:
cd backend
python manage.py runserver
```

### Step 6: Test Again

Run the test command:
```bash
python manage.py test_twilio
```

Should show: `[SUCCESS] All Twilio tests passed!`

## Verification Checklist

- [ ] Account SID starts with `AC` (not `SK` or `OQ`)
- [ ] API Key SID starts with `SK`
- [ ] API Key belongs to the same account as Account SID
- [ ] API Secret is correct (copied when API Key was created)
- [ ] All credentials are in `backend/.env`
- [ ] Django server restarted after updating `.env`

## Expected Behavior After Fix

1. `test_twilio` command shows: `[OK] API Key belongs to the correct account`
2. Token generation succeeds
3. Video call connection works

## Still Having Issues?

If the test command passes but you still get the error:

1. **Check Django server logs** when generating a token
2. **Verify the Account SID** in the logs matches your `.env`
3. **Double-check API Key** hasn't been deleted or regenerated
4. **Try creating a fresh API Key** to rule out any corruption

The enhanced `test_twilio` command will now catch this issue before you try to use telemedicine!
