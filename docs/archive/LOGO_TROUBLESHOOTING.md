# Logo Troubleshooting Guide

## Issue: Logo Not Appearing in Receipts and Invoices

If the logo is not appearing in PDF receipts and invoices, follow these steps:

### Step 1: Verify Logo File Location

1. **Check if the logo file exists:**
   - File should be at: `frontend/public/logo.png`
   - Verify the file exists and is not empty

2. **Check file permissions:**
   - The file should be readable by the Django process
   - On Windows, ensure the file is not locked

### Step 2: Test Logo Loading

**Option A: Use the Test Endpoint (Recommended)**

1. Start your Django backend server
2. Make sure you're logged in
3. Visit: `http://localhost:3004/api/v1/visits/{any_visit_id}/billing/test-logo/`
4. Check the response to see:
   - If logo was loaded
   - Which paths were tried
   - Which paths exist

**Option B: Use Django Shell**

```bash
cd backend
python manage.py shell
```

Then run:
```python
from apps.billing.pdf_service import PDFService
import os
from pathlib import Path
from django.conf import settings

# Check BASE_DIR
print("BASE_DIR:", settings.BASE_DIR)

# Check CLINIC_LOGO_PATH
print("CLINIC_LOGO_PATH:", getattr(settings, 'CLINIC_LOGO_PATH', None))

# Test logo loading
logo = PDFService._get_logo_base64()
print("Logo loaded:", logo is not None)
if logo:
    print("Logo length:", len(logo))
    print("Logo preview:", logo[:100])
else:
    # Try manual path check
    logo_path = Path(settings.BASE_DIR) / 'frontend' / 'public' / 'logo.png'
    print("Checking path:", logo_path)
    print("Path exists:", os.path.exists(logo_path))
    if os.path.exists(logo_path):
        print("File size:", os.path.getsize(logo_path), "bytes")
```

### Step 3: Check Backend Logs

When generating a receipt/invoice, check the Django console/logs for:
- `Logo loaded successfully from: ...` (success message)
- `Logo not found. Tried paths: ...` (failure message)

### Step 4: Common Issues and Solutions

#### Issue: "Logo not found" in logs

**Solution 1: Verify BASE_DIR**
- BASE_DIR should point to the project root (where `frontend/` and `backend/` folders are)
- From `backend/core/settings.py`, BASE_DIR goes up 3 levels: `backend/core/` → `backend/` → project root

**Solution 2: Set CLINIC_LOGO_PATH explicitly**

In `backend/core/settings.py` or via environment variable:
```python
CLINIC_LOGO_PATH = '/absolute/path/to/frontend/public/logo.png'
```

Or using BASE_DIR:
```python
CLINIC_LOGO_PATH = str(BASE_DIR / 'frontend' / 'public' / 'logo.png')
```

**Solution 3: Check file path on Windows**
- Windows paths use backslashes, but Path objects handle this automatically
- If using environment variable, use forward slashes or double backslashes:
  ```
  CLINIC_LOGO_PATH=C:\\Users\\...\\Modern EMR\\frontend\\public\\logo.png
  ```

#### Issue: Logo loads but doesn't appear in PDF

**Possible causes:**
1. WeasyPrint might not support base64 images (unlikely)
2. Image data might be corrupted
3. HTML might have syntax errors

**Solution:**
- Check if logo_base64 is not None
- Verify the base64 string starts with `data:image/png;base64,`
- Check WeasyPrint version and compatibility

### Step 5: Manual Path Testing

If automatic path detection fails, you can manually set the path:

1. **Find the absolute path to your logo:**
   ```python
   import os
   from pathlib import Path
   # From project root
   logo_path = Path(__file__).resolve().parent / 'frontend' / 'public' / 'logo.png'
   print("Logo path:", logo_path)
   print("Exists:", os.path.exists(logo_path))
   ```

2. **Set it in settings.py:**
   ```python
   CLINIC_LOGO_PATH = r'C:\Users\Damian Motomboni\Desktop\Modern EMR\frontend\public\logo.png'
   ```

### Step 6: Verify Logo File

1. **Check file format:**
   - Should be PNG, JPG, or SVG
   - PNG with transparent background is recommended

2. **Check file size:**
   - Should not be 0 bytes
   - Should not be too large (> 5MB might cause issues)

3. **Test file can be opened:**
   - Try opening the file in an image viewer
   - Verify it's a valid image file

## Quick Fix Checklist

- [ ] Logo file exists at `frontend/public/logo.png`
- [ ] File is not empty (check file size)
- [ ] File permissions allow reading
- [ ] BASE_DIR is correctly set in settings.py
- [ ] CLINIC_LOGO_PATH is set correctly (or uses default)
- [ ] Backend server has been restarted after changes
- [ ] Check Django logs for logo loading messages
- [ ] Test using the `/api/v1/visits/{visit_id}/billing/test-logo/` endpoint

## Still Not Working?

1. Check the Django console output when generating a PDF
2. Look for warning/error messages about logo loading
3. Verify the exact path being tried matches your file location
4. Try setting CLINIC_LOGO_PATH to an absolute path
5. Ensure the logo file is not corrupted (try opening it in an image editor)
