# Offline Image Upload Sync - PACS-lite Implementation

## Overview

This document describes the offline imaging upload sync strategy for radiology images, designed for Nigerian clinics with unreliable internet connectivity.

**Per EMR Context Document v2 (LOCKED):**
- Images are stored locally first
- Metadata syncs before binaries
- No image is deleted locally until server ACK

## Architecture (Non-Negotiable)

### Flow Diagram

```
RadiologyOrder (online)
        ↓
Perform imaging (offline)
        ↓
Store locally:
  - image_uuid
  - radiology_order_id
  - checksum
        ↓
Queue metadata
        ↓
Background sync
        ↓
Server ACK
        ↓
Upload binaries
```

### Why This Works

1. **Survives power outages**: Metadata is uploaded first, so we have a record even if upload fails
2. **Prevents orphan images**: Metadata must exist before binary can be uploaded
3. **Enables resume-on-failure**: Client can retry uploads based on status
4. **Protects medico-legal chain**: Complete audit trail of upload process

## Sync Rules

1. **Images are immutable**: Once uploaded, images cannot be modified
2. **No overwrite allowed**: Duplicate checksums are rejected
3. **Checksums validated server-side**: SHA-256 checksum must match file content
4. **Local copy deleted ONLY after ACK**: Client must wait for server ACK before deleting local copy

## API Endpoints

### 1. Upload Metadata (FIRST STEP)

**Endpoint:** `POST /api/v1/radiology/offline-images/upload-metadata/`

**Purpose:** Upload metadata for an offline image (metadata syncs before binaries).

**Request Body:**
```json
{
  "image_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "radiology_order_id": 123,
  "filename": "chest_xray_001.dcm",
  "file_size": 1048576,
  "mime_type": "application/dicom",
  "checksum": "a1b2c3d4e5f6...",  // SHA-256 (64 hex characters)
  "image_metadata": {
    "modality": "CR",
    "patient_name": "John Doe",
    "study_date": "2026-01-15",
    // ... other DICOM tags or EXIF data
  }
}
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "image_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "radiology_order_id": 123,
  "filename": "chest_xray_001.dcm",
  "file_size": 1048576,
  "mime_type": "application/dicom",
  "checksum": "a1b2c3d4e5f6...",
  "status": "METADATA_UPLOADED",
  "created_at": "2026-01-15T10:00:00Z",
  "metadata_uploaded_at": "2026-01-15T10:00:05Z"
}
```

### 2. Upload Binary (SECOND STEP)

**Endpoint:** `POST /api/v1/radiology/offline-images/upload-binary/`

**Purpose:** Upload binary file after metadata is uploaded.

**Request:** `multipart/form-data`
```
image_uuid: 550e8400-e29b-41d4-a716-446655440000
file: <binary file>
```

**Response:** `201 Created`
```json
{
  "id": 1,
  "image_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "radiology_order_id": 123,
  "filename": "chest_xray_001.dcm",
  "image_file": "/media/radiology/images/2026/01/15/chest_xray_001.dcm",
  "checksum": "a1b2c3d4e5f6...",
  "uploaded_at": "2026-01-15T10:00:10Z",
  "validated_at": "2026-01-15T10:00:10Z"
}
```

**Validation:**
- Checksum is validated server-side
- File size must match metadata
- Duplicate checksums are rejected (immutability)

### 3. Acknowledge Upload (THIRD STEP)

**Endpoint:** `POST /api/v1/radiology/offline-images/acknowledge/`

**Purpose:** Acknowledge successful upload (safe to delete local copy).

**Request Body:**
```json
{
  "image_uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "image_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ACK_RECEIVED",
  "ack_received_at": "2026-01-15T10:00:15Z"
}
```

**Client Action:** After receiving ACK, client can safely delete local copy.

### 4. Get Pending Uploads

**Endpoint:** `GET /api/v1/radiology/offline-images/pending/`

**Purpose:** Get list of pending uploads (for client-side sync).

**Query Parameters:**
- `radiology_order_id` (optional): Filter by radiology order

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "image_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "status": "METADATA_UPLOADED",
    "created_at": "2026-01-15T10:00:00Z"
  }
]
```

### 5. Get Failed Uploads

**Endpoint:** `GET /api/v1/radiology/offline-images/failed/`

**Purpose:** Get list of failed uploads (for manual intervention).

**Query Parameters:**
- `radiology_order_id` (optional): Filter by radiology order

**Response:** `200 OK`
```json
[
  {
    "id": 2,
    "image_uuid": "660e8400-e29b-41d4-a716-446655440001",
    "status": "FAILED",
    "failure_reason": "Checksum mismatch",
    "retry_count": 3,
    "failed_at": "2026-01-15T10:05:00Z"
  }
]
```

## Status Flow

```
PENDING
  ↓ (metadata uploaded)
METADATA_UPLOADED
  ↓ (binary uploaded)
BINARY_UPLOADED
  ↓ (server ACK)
ACK_RECEIVED (terminal state)

Any state → FAILED (on error)
FAILED → PENDING (on retry)
```

## Client Implementation Guide

### 1. Queue Metadata Locally

```javascript
// Generate UUID client-side
const imageUuid = generateUUID();

// Calculate SHA-256 checksum
const fileContent = await readFileAsArrayBuffer(file);
const checksum = await calculateSHA256(fileContent);

// Store locally
const metadata = {
  image_uuid: imageUuid,
  radiology_order_id: orderId,
  filename: file.name,
  file_size: file.size,
  mime_type: file.type,
  checksum: checksum,
  image_metadata: extractMetadata(file), // DICOM tags, EXIF, etc.
  status: 'PENDING',
  created_at: new Date().toISOString(),
};

await localDB.save('offline_images', metadata);
```

### 2. Upload Metadata (Background Sync)

```javascript
// When online, upload metadata
const metadata = await localDB.get('offline_images', { status: 'PENDING' });

for (const item of metadata) {
  try {
    const response = await fetch('/api/v1/radiology/offline-images/upload-metadata/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item),
    });
    
    if (response.ok) {
      // Update local status
      await localDB.update('offline_images', item.id, { status: 'METADATA_UPLOADED' });
    }
  } catch (error) {
    // Retry later
    console.error('Metadata upload failed:', error);
  }
}
```

### 3. Upload Binary (After Metadata)

```javascript
// Upload binary for metadata that's been uploaded
const metadata = await localDB.get('offline_images', { status: 'METADATA_UPLOADED' });

for (const item of metadata) {
  try {
    const file = await getLocalFile(item.image_uuid);
    const formData = new FormData();
    formData.append('image_uuid', item.image_uuid);
    formData.append('file', file);
    
    const response = await fetch('/api/v1/radiology/offline-images/upload-binary/', {
      method: 'POST',
      body: formData,
    });
    
    if (response.ok) {
      // Update local status
      await localDB.update('offline_images', item.id, { status: 'BINARY_UPLOADED' });
    }
  } catch (error) {
    // Retry later
    console.error('Binary upload failed:', error);
  }
}
```

### 4. Request ACK and Delete Local Copy

```javascript
// Request ACK for uploaded binaries
const metadata = await localDB.get('offline_images', { status: 'BINARY_UPLOADED' });

for (const item of metadata) {
  try {
    const response = await fetch('/api/v1/radiology/offline-images/acknowledge/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_uuid: item.image_uuid }),
    });
    
    if (response.ok) {
      // ACK received - safe to delete local copy
      await deleteLocalFile(item.image_uuid);
      await localDB.delete('offline_images', item.id);
    }
  } catch (error) {
    // Retry later
    console.error('ACK request failed:', error);
  }
}
```

## Error Handling

### Checksum Mismatch

If checksum validation fails:
- Status is set to `FAILED`
- `failure_reason` is set to "Checksum mismatch"
- Client should retry upload (recalculate checksum)

### File Size Mismatch

If file size doesn't match metadata:
- Status is set to `FAILED`
- `failure_reason` is set to "File size mismatch"
- Client should retry upload

### Network Errors

If network error occurs:
- Client should retry upload
- `retry_count` is incremented
- Status remains in current state (not set to FAILED unless server explicitly fails)

## Security Considerations

1. **Authentication**: All endpoints require authentication (Radiology Tech role)
2. **Checksum Validation**: Server validates checksum to prevent tampering
3. **File Size Limits**: Maximum 100MB per file
4. **MIME Type Validation**: Only allowed types (JPEG, PNG, DICOM)
5. **Immutability**: Images cannot be modified once uploaded

## Database Models

### OfflineImageMetadata

Tracks metadata for offline images waiting to be synced.

**Key Fields:**
- `image_uuid`: Unique identifier (UUID)
- `radiology_order`: Link to radiology order
- `checksum`: SHA-256 checksum
- `status`: Current sync status
- `retry_count`: Number of retries

### RadiologyImage

Server-side image record (after successful upload).

**Key Fields:**
- `offline_metadata`: One-to-one link to metadata
- `image_file`: FileField (stored outside DB)
- `checksum`: Validated checksum
- `uploaded_by`: User who uploaded
- `uploaded_at`: Upload timestamp

## Compliance

This implementation complies with:
- EMR Context Document v2 (LOCKED)
- PACS-lite requirements
- Medico-legal audit requirements
- Nigerian clinic operational realities

