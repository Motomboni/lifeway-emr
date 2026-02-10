# PACS-lite Storage Configuration Guide

## Current Configuration

### Filesystem Storage (Default - Active)

**Status:** ✅ **CONFIGURED AND TESTED**

**Configuration:**
```python
# settings.py
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
```

**Storage Location:**
- Files stored in: `backend/media/radiology/{study_uid}/{series_uid}/{image_uid}/{filename}`
- Example: `backend/media/radiology/8f06e605-e810-4418-85cb-6304772f152e/d98553c6-4595-45ff-8adf-666daf4ad91a/f23b2e7a-f916-4865-95ab-290eb39a296f/chest_pa_test.dcm`

**Test Results:**
- ✅ Files successfully stored
- ✅ File keys generated correctly
- ✅ Media URLs accessible
- ✅ File structure maintained

## Alternative Storage Options

### Option 1: AWS S3 (Production)

**Installation:**
```bash
pip install django-storages boto3
```

**Configuration:**
```python
# settings.py
INSTALLED_APPS = [
    ...
    'storages',
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

**Environment Variables:**
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=us-east-1
```

### Option 2: MinIO (Self-Hosted S3-Compatible)

**Installation:**
```bash
pip install django-storages boto3
```

**Configuration:**
```python
# settings.py
INSTALLED_APPS = [
    ...
    'storages',
]

# MinIO Configuration (S3-Compatible)
AWS_ACCESS_KEY_ID = os.environ.get('MINIO_ACCESS_KEY')
AWS_SECRET_ACCESS_KEY = os.environ.get('MINIO_SECRET_KEY')
AWS_STORAGE_BUCKET_NAME = 'radiology'
AWS_S3_ENDPOINT_URL = os.environ.get('MINIO_ENDPOINT_URL', 'http://localhost:9000')
AWS_S3_USE_SSL = False  # Set to True if using HTTPS
AWS_S3_FILE_OVERWRITE = False

# Custom storage for radiology images
RADIOLOGY_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

**Environment Variables:**
```bash
MINIO_ACCESS_KEY=your_minio_access_key
MINIO_SECRET_KEY=your_minio_secret_key
MINIO_ENDPOINT_URL=http://localhost:9000
```

**MinIO Setup:**
```bash
# Download MinIO from https://min.io/download
# Start MinIO server
minio server /path/to/data --console-address ":9001"

# Create bucket via MinIO console or API
```

## Storage Backend Selection

The system automatically selects the storage backend based on `RADIOLOGY_STORAGE` setting:

1. **If `RADIOLOGY_STORAGE` is set:** Uses the specified storage class
2. **If `RADIOLOGY_STORAGE` is not set:** Uses Django's default storage (filesystem)

## File Key Structure

All storage backends use the same file key structure:

```
radiology/
  {study_uid}/
    {series_uid}/
      {image_uid}/
        {filename}
```

**Example:**
```
radiology/
  8f06e605-e810-4418-85cb-6304772f152e/
    d98553c6-4595-45ff-8adf-666daf4ad91a/
      f23b2e7a-f916-4865-95ab-290eb39a296f/
        chest_pa_test.dcm
```

## URL Generation

### Filesystem Storage
- **URL Format:** `/media/{file_key}`
- **Example:** `/media/radiology/8f06e605-e810-4418-85cb-6304772f152e/.../chest_pa_test.dcm`

### S3/MinIO Storage
- **URL Format:** Signed URL (expires after configured time)
- **Example:** `https://bucket.s3.amazonaws.com/radiology/.../chest_pa_test.dcm?signature=...&expires=...`

## Testing Storage

Run the test command to verify storage configuration:

```bash
python manage.py test_pacs_lite
```

This will:
1. Create test data
2. Upload metadata
3. Upload binary file
4. Verify file storage
5. Generate URLs
6. Test retrieval

## Migration from Filesystem to S3/MinIO

If you need to migrate existing files:

1. **Configure new storage backend** in settings
2. **Run migration script** to copy files:
   ```python
   # Migration script (create as needed)
   from apps.radiology.pacs_lite_models import RadiologyImage
   from apps.radiology.pacs_lite_service import PACSLiteService
   
   for image in RadiologyImage.objects.all():
       # Read from old storage
       old_storage = default_storage
       file_content = old_storage.open(image.file_key).read()
       
       # Write to new storage
       new_storage = PACSLiteService.get_storage_backend()
       new_storage.save(image.file_key, ContentFile(file_content))
   ```

## Best Practices

1. **Development:** Use filesystem storage
2. **Staging:** Use MinIO (self-hosted)
3. **Production:** Use AWS S3 or MinIO (depending on infrastructure)

## Security Considerations

1. **Access Control:** Signed URLs expire after 1 hour (configurable)
2. **File Permissions:** Storage backend handles file permissions
3. **Encryption:** S3/MinIO support encryption at rest
4. **Backup:** Regular backups recommended for production

## Troubleshooting

### Files Not Storing
- Check `MEDIA_ROOT` directory exists and is writable
- Check storage backend configuration
- Check file permissions

### URLs Not Working
- Verify `MEDIA_URL` is correctly configured
- Check Django's `STATIC_URL` and `MEDIA_URL` don't conflict
- For S3/MinIO, verify bucket permissions

### Storage Backend Not Found
- Verify `RADIOLOGY_STORAGE` setting is correct
- Check if required packages are installed (`django-storages`, `boto3`)
- Verify storage class path is correct

