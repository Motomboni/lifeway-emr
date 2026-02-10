# PACS-lite Integration - Next Steps

## ✅ Completed

1. **PACS-lite Models Created**
   - `RadiologyStudy` - Groups images by study
   - `RadiologySeries` - Groups images by series
   - `RadiologyImage` - Individual images with PACS-lite storage

2. **Offline Image Sync Implemented**
   - Metadata-first upload strategy
   - Checksum validation
   - ACK-based deletion

3. **Viewer Integration**
   - OHIF Viewer support
   - Signed URL generation
   - Read-only access enforcement

4. **Migrations Created**
   - Migration `0008_radiologyseries_radiologystudy_and_more.py` created

## 🔄 Next Steps

### 1. Apply Migrations

```bash
cd backend
python manage.py migrate radiology
```

This will:
- Create `RadiologyStudy` and `RadiologySeries` tables
- Update `RadiologyImage` table with PACS-lite fields
- Remove old `image_file` and `radiology_order` fields

### 2. Configure Storage Backend

Choose one of the following storage options:

#### Option A: Filesystem (Default - Development)
```python
# settings.py - Already configured
MEDIA_ROOT = '/path/to/media/radiology/'
MEDIA_URL = '/media/radiology/'
```

#### Option B: S3 (Production)
```python
# settings.py
INSTALLED_APPS = [
    ...
    'storages',  # django-storages
]

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')

RADIOLOGY_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

#### Option C: MinIO (Self-Hosted S3-Compatible)
```python
# settings.py
AWS_ACCESS_KEY_ID = os.environ.get('MINIO_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = os.environ.get('MINIO_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = 'radiology'
AWS_S3_ENDPOINT_URL = os.environ.get('MINIO_ENDPOINT_URL', 'http://localhost:9000')
AWS_S3_USE_SSL = False

RADIOLOGY_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

### 3. Configure OHIF Viewer (Optional)

```python
# settings.py
OHIF_VIEWER_URL = os.environ.get('OHIF_VIEWER_URL', 'https://viewer.ohif.org/viewer/')
RADIOLOGY_SIGNED_URLS = True  # Enable signed URLs for access control
```

### 4. Test the Integration

#### Test Offline Image Upload

1. **Upload Metadata** (First Step):
```bash
POST /api/v1/radiology/offline-images/upload-metadata/
{
  "image_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "radiology_order_id": 123,
  "filename": "chest_xray.dcm",
  "file_size": 1048576,
  "mime_type": "application/dicom",
  "checksum": "a1b2c3d4...",
  "image_metadata": {
    "study_uid": "1.2.3.4",
    "series_uid": "1.2.3.4.1",
    "image_uid": "1.2.3.4.1.1"
  }
}
```

2. **Upload Binary** (Second Step):
```bash
POST /api/v1/radiology/offline-images/upload-binary/
Form Data:
  - image_uuid: 550e8400-e29b-41d4-a716-446655440000
  - file: <binary file>
```

3. **Request ACK** (Third Step):
```bash
POST /api/v1/radiology/offline-images/acknowledge/
{
  "image_uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

#### Test Viewer Access

1. **Get Study Viewer URL**:
```bash
GET /api/v1/radiology/studies/{id}/viewer-url/
```

2. **Get Study Images (Grouped by Series)**:
```bash
GET /api/v1/radiology/studies/{id}/images/
```

3. **Get Individual Image URL**:
```bash
GET /api/v1/radiology/images/{id}/url/
```

### 5. Frontend Integration

The frontend needs to be updated to:

1. **Implement Offline Image Upload Flow**:
   - Queue metadata locally
   - Upload metadata when online
   - Upload binary after metadata
   - Request ACK and delete local copy

2. **Integrate OHIF Viewer**:
   - Fetch viewer URL from API
   - Embed OHIF viewer in iframe
   - Handle signed URL expiration

3. **Display Study/Series Structure**:
   - Show studies grouped by radiology order
   - Show series within each study
   - Show images within each series

### 6. Data Migration (If Needed)

If you have existing `RadiologyImage` records, you may need to:

1. Create `RadiologyStudy` for each radiology order
2. Create `RadiologySeries` for each study
3. Migrate existing images to new structure
4. Generate `file_key` for existing images

### 7. Documentation

- ✅ `PACS_LITE_INTEGRATION.md` - Complete PACS-lite documentation
- ✅ `OFFLINE_IMAGE_SYNC.md` - Offline upload sync documentation
- ✅ `NEXT_STEPS.md` - This file

### 8. Testing Checklist

- [ ] Migrations applied successfully
- [ ] Storage backend configured
- [ ] OHIF Viewer configured (if using)
- [ ] Offline image upload flow tested
- [ ] Viewer URL generation tested
- [ ] Signed URL access tested
- [ ] Study/Series grouping verified
- [ ] Read-only access enforced
- [ ] Frontend integration completed

## 📝 Important Notes

1. **Existing Data**: The new PACS-lite fields are nullable to handle existing records. New images will be validated to ensure all required fields are present.

2. **Immutability**: Images are immutable once created. This is enforced at the model level.

3. **Storage**: Images are stored outside the database (S3/MinIO/filesystem). The database only stores references (`file_key`).

4. **Access Control**: All viewer endpoints are read-only and require authentication. Signed URLs expire after 1 hour by default.

5. **Offline Sync**: The offline upload sync automatically creates Study/Series/Image records when binary is uploaded.

## 🚀 Ready to Use

The PACS-lite integration is complete and ready for use. Follow the steps above to configure and test the system.

