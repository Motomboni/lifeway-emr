# PACS-lite Integration - Complete Implementation

## Overview

This document describes the PACS-lite integration for radiology image storage and viewing, designed for Nigerian clinics.

**Per EMR Context Document v2 (LOCKED):**

### PACS-lite DOES:
- ✅ Store DICOM/JPEG
- ✅ Group by Study / Series
- ✅ Expose viewer URLs
- ✅ Enforce read-only access

### PACS-lite DOES NOT:
- ❌ Manage modality devices
- ❌ Do HL7 routing
- ❌ Own patient records

## Architecture

### Clean Integration Pattern

```
RadiologyOrder
   ↓
PACS-lite Storage (Study/Series)
   ↓
Viewer (OHIF or lightweight DICOM viewer)
   ↓
Doctor Review
```

### Storage Rule (Critical)

**EMR DB stores:**
- `study_uid` (DICOM StudyInstanceUID or generated UUID)
- `series_uid` (DICOM SeriesInstanceUID or generated UUID)
- `file_keys` (S3/MinIO/filesystem path)

**Images live in:**
- S3 / MinIO / filesystem (not in DB)

## Database Models

### RadiologyStudy

Groups images by study (one study per RadiologyOrder).

**Key Fields:**
- `study_uid`: DICOM StudyInstanceUID or generated UUID
- `radiology_order`: One-to-one link to RadiologyOrder
- `study_date`: Study date
- `study_description`: Study description
- `modality`: Modality (e.g., CR, CT, MR, US)
- `patient_name`, `patient_id`: Snapshot from visit

### RadiologySeries

Groups images by series within a study (multiple series per study).

**Key Fields:**
- `series_uid`: DICOM SeriesInstanceUID or generated UUID
- `study`: ForeignKey to RadiologyStudy
- `series_number`: Series number (from DICOM)
- `series_description`: Series description
- `modality`: Modality

### RadiologyImage

Individual image file with PACS-lite storage.

**Key Fields:**
- `series`: ForeignKey to RadiologySeries
- `image_uid`: DICOM SOPInstanceUID or generated UUID
- `file_key`: File key/path in storage (S3/MinIO/filesystem)
- `filename`: Original filename
- `file_size`: File size in bytes
- `mime_type`: MIME type
- `checksum`: SHA-256 checksum (validated server-side)
- `image_metadata`: DICOM tags or JPEG EXIF (JSON)

## Storage Configuration

### Filesystem Storage (Default)

```python
# settings.py
MEDIA_ROOT = '/path/to/media/radiology/'
MEDIA_URL = '/media/radiology/'
```

### S3 Storage (Recommended for Production)

```python
# settings.py
INSTALLED_APPS = [
    ...
    'storages',  # django-storages
]

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'

# Custom storage for radiology images
RADIOLOGY_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

### MinIO Storage (Self-Hosted S3-Compatible)

```python
# settings.py
AWS_ACCESS_KEY_ID = os.environ.get('MINIO_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = os.environ.get('MINIO_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = 'radiology'
AWS_S3_ENDPOINT_URL = os.environ.get('MINIO_ENDPOINT_URL', 'http://localhost:9000')
AWS_S3_USE_SSL = False  # Set to True if using HTTPS

RADIOLOGY_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

## Viewer Configuration

### OHIF Viewer (Recommended)

```python
# settings.py
OHIF_VIEWER_URL = os.environ.get('OHIF_VIEWER_URL', 'https://viewer.ohif.org/viewer/')
RADIOLOGY_SIGNED_URLS = True  # Enable signed URLs for access control
```

### Lightweight DICOM Viewer (Alternative)

```python
# settings.py
OHIF_VIEWER_URL = None  # Disable OHIF
RADIOLOGY_SIGNED_URLS = True
```

## API Endpoints

### 1. Get Study Viewer URL

**Endpoint:** `GET /api/v1/radiology/studies/{id}/viewer-url/`

**Purpose:** Generate signed viewer URL for OHIF Viewer.

**Response:**
```json
{
  "viewer_url": "https://viewer.ohif.org/viewer/?studyInstanceUIDs=1.2.3.4&token=...&expires=3600",
  "study_uid": "1.2.3.4",
  "expires_in": 3600
}
```

### 2. Get Study Images (Grouped by Series)

**Endpoint:** `GET /api/v1/radiology/studies/{id}/images/`

**Purpose:** Get all images for a study, grouped by series.

**Response:**
```json
{
  "study_uid": "1.2.3.4",
  "study_description": "Chest X-Ray",
  "series": [
    {
      "series_uid": "1.2.3.4.1",
      "series_description": "PA View",
      "series_number": 1,
      "modality": "CR",
      "images": [
        {
          "image_uid": "1.2.3.4.1.1",
          "filename": "chest_pa.dcm",
          "file_size": 1048576,
          "mime_type": "application/dicom",
          "instance_number": 1,
          "image_url": "https://storage.example.com/radiology/...?token=...&expires=3600"
        }
      ]
    }
  ]
}
```

### 3. Get Image URL

**Endpoint:** `GET /api/v1/radiology/images/{id}/url/`

**Purpose:** Generate signed URL for individual image access.

**Response:**
```json
{
  "image_url": "https://storage.example.com/radiology/...?token=...&expires=3600",
  "image_uid": "1.2.3.4.1.1",
  "filename": "chest_pa.dcm",
  "expires_in": 3600
}
```

### 4. List Studies

**Endpoint:** `GET /api/v1/radiology/studies/?radiology_order_id=123`

**Purpose:** List all studies (optionally filtered by radiology order).

**Response:**
```json
[
  {
    "id": 1,
    "study_uid": "1.2.3.4",
    "radiology_order": 123,
    "study_description": "Chest X-Ray",
    "modality": "CR",
    "study_date": "2026-01-15",
    "patient_name": "John Doe",
    "created_at": "2026-01-15T10:00:00Z"
  }
]
```

## Usage Examples

### 1. Create Study for Radiology Order

```python
from apps.radiology.pacs_lite_service import PACSLiteService
from apps.radiology.models import RadiologyOrder

# Get radiology order
order = RadiologyOrder.objects.get(pk=123)

# Create study
study = PACSLiteService.create_study_for_order(
    radiology_order=order,
    study_uid="1.2.3.4",  # DICOM StudyInstanceUID (optional)
    study_description="Chest X-Ray",
    modality="CR",
)
```

### 2. Create Series and Upload Image

```python
# Create series
series = PACSLiteService.create_series_for_study(
    study=study,
    series_uid="1.2.3.4.1",  # DICOM SeriesInstanceUID (optional)
    series_number=1,
    series_description="PA View",
    modality="CR",
)

# Generate file key
file_key = PACSLiteService.generate_file_key(
    study_uid=study.study_uid,
    series_uid=series.series_uid,
    image_uid="1.2.3.4.1.1",  # DICOM SOPInstanceUID
    filename="chest_pa.dcm",
)

# Store image
stored_file_key = PACSLiteService.store_image(
    file_content=file_content,
    file_key=file_key,
    content_type="application/dicom",
)

# Create image record
image = RadiologyImage.objects.create(
    series=series,
    image_uid="1.2.3.4.1.1",
    file_key=stored_file_key,
    filename="chest_pa.dcm",
    file_size=1048576,
    mime_type="application/dicom",
    checksum=calculated_checksum,
    uploaded_by=user,
)
```

### 3. Generate Viewer URL

```python
# Generate OHIF viewer URL
viewer_url = PACSLiteService.generate_viewer_url(
    study_uid=study.study_uid,
    user=user,
    expires_in=3600,  # 1 hour
)
```

### 4. Generate Image URL

```python
# Generate signed image URL
image_url = PACSLiteService.generate_image_url(
    image=image,
    user=user,
    expires_in=3600,  # 1 hour
)
```

## Integration with Offline Upload

The PACS-lite integration works seamlessly with the offline image upload sync:

1. **Metadata Upload**: Client uploads metadata (includes study_uid, series_uid, image_uid)
2. **Binary Upload**: Client uploads binary → Service creates Study/Series/Image automatically
3. **Storage**: Image stored in S3/MinIO/filesystem with proper file_key
4. **Viewer Access**: Doctor can access via OHIF viewer URL

## Access Control

### Read-Only Enforcement

- All viewer endpoints are read-only (GET only)
- Images are immutable once created
- Signed URLs expire after configured time (default: 1 hour)
- Access controlled via Django permissions (CanViewRadiologyRequest)

### Permission Classes

- `IsAuthenticated`: User must be authenticated
- `CanViewRadiologyRequest`: User must be Doctor or Radiology Tech

## File Key Structure

Files are stored with the following structure:

```
radiology/
  {study_uid}/
    {series_uid}/
      {image_uid}/
        {filename}
```

Example:
```
radiology/
  1.2.3.4/
    1.2.3.4.1/
      1.2.3.4.1.1/
        chest_pa.dcm
```

## Compliance

This implementation complies with:
- EMR Context Document v2 (LOCKED)
- PACS-lite requirements (no modality worklist, no HL7 routing)
- Read-only access enforcement
- Study/Series grouping
- Signed URL access control

## Next Steps

1. **Configure Storage**: Set up S3/MinIO/filesystem storage
2. **Configure Viewer**: Set up OHIF Viewer or lightweight DICOM viewer
3. **Create Migrations**: `python manage.py makemigrations radiology`
4. **Run Migrations**: `python manage.py migrate`
5. **Test Integration**: Upload images and test viewer access

