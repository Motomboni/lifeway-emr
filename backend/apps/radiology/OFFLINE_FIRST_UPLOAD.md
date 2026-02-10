# Offline-First Imaging Upload System

## Overview

The Offline-First Imaging Upload system enables reliable image uploads even when internet connectivity is unavailable. Images are stored locally first, then synced to the server when connectivity is restored.

## Key Features

- **Offline-First**: Images stored locally with UUIDs before upload
- **Metadata-First**: Metadata queued separately from binary data
- **Checksum Verification**: SHA-256 checksums ensure data integrity
- **Retry-Safe**: Resumable uploads with automatic retry logic
- **Server ACK Required**: Local files only deleted after server acknowledgment
- **No Orphan Images**: Deduplication prevents duplicate uploads
- **Full Audit Trail**: Complete history of all upload attempts

## Architecture

### Upload Flow

1. **Create Session**: Client creates upload session with local file
2. **Upload Metadata**: Metadata uploaded first (lightweight)
3. **Upload Binary**: Binary data uploaded (resumable, chunked)
4. **Server ACK**: Server acknowledges successful upload
5. **Local Cleanup**: Client can safely delete local file

### Status Flow

```
QUEUED → METADATA_UPLOADING → METADATA_UPLOADED → 
BINARY_UPLOADING → SYNCED → ACK_RECEIVED
```

Failed uploads can retry from any point in the flow.

## Models

### ImageUploadSession

Tracks a single image upload attempt with:
- Session UUID for idempotency
- Local file path and UUID
- File metadata (name, size, content type)
- SHA-256 checksum
- Upload progress tracking
- Retry count and error tracking
- Server acknowledgment status

## API Endpoints

### Create Upload Session
```
POST /api/v1/visits/{visit_id}/radiology/upload-sessions/create_session/
```

Request:
```json
{
  "radiology_order_id": 123,
  "local_file_path": "/path/to/local/image.dcm",
  "file_name": "image.dcm",
  "content_type": "application/dicom",
  "metadata": {}
}
```

### Upload Metadata
```
POST /api/v1/visits/{visit_id}/radiology/upload-sessions/{session_id}/upload_metadata/
```

### Upload Binary (Resumable)
```
POST /api/v1/visits/{visit_id}/radiology/upload-sessions/{session_id}/upload_binary/
```

Request:
```json
{
  "resume_from": 0,
  "chunk_size": 1048576
}
```

### Acknowledge Upload
```
POST /api/v1/visits/{visit_id}/radiology/upload-sessions/{session_id}/acknowledge/
```

Request:
```json
{
  "server_image_id": 456
}
```

### List Pending Uploads
```
GET /api/v1/visits/{visit_id}/radiology/upload-sessions/pending/?radiology_order_id=123
```

### List Failed Uploads
```
GET /api/v1/visits/{visit_id}/radiology/upload-sessions/failed/?radiology_order_id=123
```

### Retry Failed Upload
```
POST /api/v1/visits/{visit_id}/radiology/upload-sessions/{session_id}/retry/
```

## Service Layer

### ImageUploadService

Provides high-level methods for:
- `create_upload_session()`: Create new upload session
- `upload_metadata()`: Upload metadata to server
- `upload_binary()`: Upload binary data (resumable)
- `acknowledge_upload()`: Acknowledge successful upload
- `get_pending_uploads()`: Get pending upload sessions
- `get_failed_uploads()`: Get failed uploads that can be retried
- `cleanup_completed_sessions()`: Clean up old completed sessions

## Deduplication

Uploads are deduplicated using:
- **Session ID**: Unique UUID per upload attempt
- **Checksum**: SHA-256 hash of file content
- **Radiology Order**: Same file for same order = duplicate

If a duplicate is detected, the existing session is returned instead of creating a new one.

## Retry Logic

- Maximum retries: 5 (configurable per session)
- Retry only for FAILED status
- Retry resets session to QUEUED status
- Progress is preserved (can resume from last position)

## Data Integrity

- **Checksum Verification**: SHA-256 checksum calculated on creation
- **Checksum Validation**: Verified before each upload step
- **File Existence Check**: Verifies local file exists before upload
- **Server Validation**: Server validates checksum on receipt

## Local File Management

- Files stored locally with UUID-based naming
- Local path tracked in session
- File only deleted after ACK_RECEIVED status
- `is_safe_to_delete_local()` method checks safety

## Error Handling

Errors are tracked with:
- `error_message`: Human-readable error description
- `error_code`: Programmatic error code
- `status`: Set to FAILED on error
- `retry_count`: Incremented on retry

## Audit Trail

Complete audit trail includes:
- Session creation timestamp
- Metadata upload timestamp
- Binary upload timestamp
- Server acknowledgment timestamp
- All status transitions
- Retry attempts
- Error messages

## Constraints

- **No Manual Edits**: Sessions are immutable (except status transitions)
- **No Deletion**: Sessions cannot be deleted (maintains audit trail)
- **Status Validation**: Only valid status transitions allowed
- **Checksum Required**: All sessions must have valid SHA-256 checksum

## Integration with PACS-lite

Uploaded images are automatically:
- Stored in PACS-lite (Study/Series/Image structure)
- Linked to radiology order
- Available via viewer URLs
- Grouped by study and series

## Usage Example

```python
from apps.radiology.image_upload_service import ImageUploadService

# 1. Create session
session = ImageUploadService.create_upload_session(
    radiology_order_id=123,
    local_file_path="/local/path/image.dcm",
    file_name="image.dcm",
    content_type="application/dicom",
    created_by_id=user.id
)

# 2. Upload metadata
ImageUploadService.upload_metadata(str(session.session_id))

# 3. Upload binary
ImageUploadService.upload_binary(str(session.session_id))

# 4. Acknowledge (after server processes)
ImageUploadService.acknowledge_upload(
    str(session.session_id),
    server_image_id=456
)

# 5. Safe to delete local file
if session.is_safe_to_delete_local():
    os.remove(session.local_file_path)
```

## Migration

To apply the offline-first upload system:

```bash
python manage.py makemigrations radiology
python manage.py migrate radiology
```

## Future Enhancements

Potential enhancements:
- Background sync service
- Automatic retry on connectivity restore
- Chunked upload with progress callbacks
- Compression before upload
- Encryption for sensitive images
- Bandwidth-aware upload throttling

