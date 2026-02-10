# Radiology Upload & Sync Status Page Setup

## Route Addition Required

Add the following to `frontend/src/App.tsx`:

### Import Statement
Add to the imports section (around line 27):
```typescript
import RadiologyUploadStatusPage from './pages/RadiologyUploadStatusPage';
```

### Route Definition
Add to the routes section (after Radiology Orders route, around line 220):
```typescript
{/* Radiology Upload Status - Radiology Tech and Admin */}
<Route
  path="/radiology-upload-status"
  element={
    <ProtectedRoute>
      <RadiologyUploadStatusPage />
    </ProtectedRoute>
  }
/>
```

## Features Implemented

✅ **List of imaging sessions** with:
- Patient name (from metadata)
- Study type (from metadata)
- Upload status (Queued, Uploading, Synced, Failed)
- Progress bar for active uploads
- File name and size

✅ **Retry button** for failed uploads
- Only shown for failed sessions
- Disabled when offline
- Shows retry count

✅ **Offline indicator banner**
- Detects network status
- Shows when offline
- Explains that uploads will resume automatically

✅ **Success messages**
- Clear completion indicator
- Shows when upload is acknowledged

✅ **Auto-refresh**
- Refreshes every 5 seconds when enabled
- Can be toggled on/off
- Manual refresh button available

✅ **Network loss handling**
- Gracefully handles network errors
- Doesn't show error toasts for network issues
- Maintains existing data when offline

✅ **No image previews**
- Only shows metadata until upload complete
- No preview functionality for incomplete uploads

## Access Control

The page automatically checks for Radiology Tech or Admin roles and redirects unauthorized users.

## Status Types

- **QUEUED**: Orange - Waiting to start
- **METADATA_UPLOADING**: Blue - Uploading metadata
- **METADATA_UPLOADED**: Blue - Metadata uploaded, ready for binary
- **BINARY_UPLOADING**: Blue - Uploading image data
- **SYNCED**: Green - Uploaded to server
- **ACK_RECEIVED**: Green - Server acknowledged (complete)
- **FAILED**: Red - Upload failed
- **CANCELLED**: Grey - Cancelled

## Filters

- **All**: Shows all sessions
- **Pending**: Shows queued/uploading sessions
- **Failed**: Shows failed sessions
- **Completed**: Shows acknowledged sessions

## Summary Cards

- Pending/Uploading count
- Failed count
- Completed count
- Total sessions

## UX Features

- **Color-coded status badges** for quick visual identification
- **Progress bars** for active uploads
- **Expandable details** (can be added if needed)
- **Responsive design** for mobile and desktop
- **Auto-refresh toggle** for control
- **Offline mode** clearly indicated

## API Endpoints Used

- `GET /api/v1/visits/0/radiology/upload-sessions/pending/` - Get pending uploads
- `GET /api/v1/visits/0/radiology/upload-sessions/failed/` - Get failed uploads
- `POST /api/v1/visits/0/radiology/upload-sessions/{session_id}/retry/` - Retry failed upload

## Note on API Endpoints

The upload sessions API is visit-scoped, but we need a global view. The current implementation:
- Uses placeholder visit ID (0) for global endpoints
- Combines pending and failed endpoints
- May need backend enhancement for true global list

Consider adding a backend endpoint like:
- `GET /api/v1/radiology/upload-sessions/` (global, not visit-scoped)

