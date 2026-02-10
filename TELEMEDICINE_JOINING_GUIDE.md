# How to Join a Telemedicine Session - Step-by-Step Guide

## Overview

Telemedicine sessions allow doctors and patients to conduct video consultations. This guide covers the complete flow for both roles.

## Prerequisites

✅ **Twilio credentials configured** (Account SID, Auth Token, API Key, API Secret)  
✅ **Backend server running** (`python manage.py runserver`)  
✅ **Frontend server running** (`npm start`)  
✅ **User logged in** (Doctor or Patient role)  
✅ **Visit exists** (for Doctor - must be OPEN status)

---

## For Doctors

### Step 1: Create a Telemedicine Session

1. **Navigate to a Visit**:
   - Go to the Visits page
   - Click on an **OPEN** visit
   - Or navigate to: `/visits/:visitId/telemedicine`

2. **Create Session**:
   - Click **"+ Create Session"** button
   - Fill in the form:
     - **Scheduled Start Time**: Select date and time
     - **Enable Recording**: Check if you want to record (optional)
     - **Notes**: Add any notes (optional)
   - Click **"Create Session"**

3. **Session Created**:
   - Session status will be **"SCHEDULED"**
   - You'll see the session in the list

### Step 2: Start the Session

1. **Find Your Session**:
   - Look for the session with status **"SCHEDULED"**
   - Click **"Start Session"** button

2. **Session Started**:
   - Status changes to **"IN_PROGRESS"**
   - The **"Join Call"** button becomes available

### Step 3: Join the Video Call

1. **Click "Join Call"**:
   - Button appears when session status is **"IN_PROGRESS"**
   - Click the **"Join Call"** button

2. **Browser Permissions**:
   - Browser will ask for **camera permission** - Click **"Allow"**
   - Browser will ask for **microphone permission** - Click **"Allow"**

3. **Video Call Interface**:
   - Your local video (yourself) appears in a small window
   - Remote video (patient) appears in the main window when they join
   - Connection status shows "Connected" when ready

### Step 4: During the Call

**Available Controls**:
- **📹 Camera Toggle**: Turn camera on/off
- **🎤 Microphone Toggle**: Mute/unmute microphone
- **📞 Leave Call**: Exit the video call (doesn't end session)

**What You See**:
- **Local Video**: Your own video feed (bottom corner)
- **Remote Video**: Patient's video feed (main area)
- **Status Indicator**: Shows connection status

### Step 5: End the Session

1. **Click "End Session"**:
   - Available only to Doctors
   - Appears when session is **"IN_PROGRESS"**
   - Click **"End Session"** button

2. **Session Completed**:
   - Status changes to **"COMPLETED"**
   - Duration is automatically calculated
   - Recording (if enabled) is linked to the session

---

## For Patients

### Step 1: Access Telemedicine Page

1. **Navigate to Patient Portal**:
   - Login as a Patient
   - Go to Dashboard: `/patient-portal/dashboard`
   - Click on **"Telemedicine"** or navigate to: `/patient-portal/telemedicine`

2. **View Sessions**:
   - You'll see all sessions where you are the patient
   - Sessions show status: **SCHEDULED**, **IN_PROGRESS**, or **COMPLETED**

### Step 2: Join an Active Session

1. **Find Active Session**:
   - Look for session with status **"IN_PROGRESS"** or **"SCHEDULED"**
   - Click **"Join Session"** button

2. **Browser Permissions**:
   - Browser will ask for **camera permission** - Click **"Allow"**
   - Browser will ask for **microphone permission** - Click **"Allow"**

3. **Video Call Interface**:
   - Your local video (yourself) appears in a small window
   - Remote video (doctor) appears in the main window
   - Connection status shows "Connected" when ready

### Step 3: During the Call

**Available Controls**:
- **📹 Camera Toggle**: Turn camera on/off
- **🎤 Microphone Toggle**: Mute/unmute microphone
- **📞 Leave Session**: Exit the video call

**What You See**:
- **Local Video**: Your own video feed (bottom corner)
- **Remote Video**: Doctor's video feed (main area)
- **Status Indicator**: Shows connection status

### Step 4: Leave the Session

1. **Click "Leave Session"**:
   - Available at any time during the call
   - Click **"Leave Session"** button

2. **Return to Sessions List**:
   - You'll be returned to the telemedicine sessions page
   - Session remains active until Doctor ends it

---

## Complete Flow Diagram

```
DOCTOR FLOW:
┌─────────────────┐
│ Create Session  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Start Session   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Join Call       │───► Video Call Interface
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ End Session     │
└─────────────────┘

PATIENT FLOW:
┌─────────────────┐
│ View Sessions   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Join Session    │───► Video Call Interface
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Leave Session   │
└─────────────────┘
```

---

## Session Statuses

| Status | Description | Who Can Join |
|--------|-------------|--------------|
| **SCHEDULED** | Session created but not started | Doctor can start, Patient can join |
| **IN_PROGRESS** | Session is active | Both Doctor and Patient can join |
| **COMPLETED** | Session ended | No one can join (view only) |
| **CANCELLED** | Session was cancelled | View only |
| **FAILED** | Session failed to start | View only |

---

## Troubleshooting

### "Failed to join session"
- ✅ Check that session status is **IN_PROGRESS** or **SCHEDULED**
- ✅ Verify you have permission to join (Doctor assigned to session, or Patient matches session)
- ✅ Check Twilio credentials are configured correctly
- ✅ Run `python manage.py test_twilio` to verify setup

### Camera/Microphone Not Working
- ✅ Check browser permissions (Settings → Privacy → Camera/Microphone)
- ✅ Ensure you clicked "Allow" when prompted
- ✅ Try refreshing the page and joining again
- ✅ Check if another application is using camera/microphone

### "Unable to fetch record: Authenticate"
- ✅ Verify Twilio Auth Token is correct (not Account SID)
- ✅ Check all Twilio credentials in `backend/.env`
- ✅ Run `python manage.py test_twilio` to test connection

### Video Not Showing
- ✅ Wait a few seconds for connection to establish
- ✅ Check internet connection
- ✅ Verify Twilio Video SDK is installed: `npm install twilio-video`
- ✅ Check browser console for errors

### Can't See Remote Participant
- ✅ Wait for the other participant to join
- ✅ Check that both participants have granted camera permissions
- ✅ Verify both are connected (status shows "Connected")
- ✅ Try refreshing the page

---

## Quick Reference

### Doctor Actions
- ✅ Create session (from Visit page)
- ✅ Start session (change SCHEDULED → IN_PROGRESS)
- ✅ Join call (enter video interface)
- ✅ End session (change IN_PROGRESS → COMPLETED)

### Patient Actions
- ✅ View sessions (from Patient Portal)
- ✅ Join session (enter video interface)
- ✅ Leave session (exit video call)

### Both Can
- ✅ Toggle camera on/off
- ✅ Mute/unmute microphone
- ✅ See connection status
- ✅ View session details

---

## API Endpoints Used

- `GET /api/v1/telemedicine/` - List sessions
- `POST /api/v1/telemedicine/` - Create session (Doctor only)
- `POST /api/v1/telemedicine/{id}/start/` - Start session (Doctor only)
- `POST /api/v1/telemedicine/token/` - Get access token for joining
- `POST /api/v1/telemedicine/{id}/end/` - End session (Doctor only)
- `POST /api/v1/telemedicine/{id}/leave/` - Leave session (both)

---

## Security & Permissions

✅ **Role-Based Access**:
- Only Doctors can create and start sessions
- Both Doctor and Patient can join their own sessions
- Patients can only see sessions where they are the patient

✅ **Visit-Scoped**:
- All sessions are linked to a specific visit
- Visit must be OPEN to create session
- Session context is preserved throughout

✅ **Audit Logging**:
- All actions (create, start, join, end, leave) are logged
- Session history is maintained

---

## Next Steps After Setup

1. ✅ Configure Twilio credentials (see `GET_CORRECT_TWILIO_CREDENTIALS.md`)
2. ✅ Test connection: `python manage.py test_twilio`
3. ✅ Create a test session as Doctor
4. ✅ Join from both Doctor and Patient accounts
5. ✅ Test camera/microphone controls
6. ✅ Test ending session

---

## Support

If you encounter issues:
1. Check browser console for errors
2. Verify Twilio credentials are correct
3. Run `python manage.py test_twilio`
4. Check network connectivity
5. Review session status and permissions
