# Lifeway Medical Center Logo Setup Instructions

## Overview
The official Lifeway Medical Center logo has been integrated across the application, including receipts and invoices.

## Logo File Placement

### Frontend (Web Application)
1. **Save the logo image** as `logo.png` in the `frontend/public/` directory
   - Path: `frontend/public/logo.png`
   - Recommended format: PNG with transparent background
   - Recommended size: 200x200px to 400x400px for best quality

### Backend (PDF Generation)
The backend will automatically use the logo from `frontend/public/logo.png` if it exists.

Alternatively, you can set a custom path via environment variable:
```bash
CLINIC_LOGO_PATH=/absolute/path/to/logo.png
```

Or update `backend/core/settings.py`:
```python
CLINIC_LOGO_PATH = os.path.join(BASE_DIR, 'path', 'to', 'logo.png')
```

## Where the Logo Appears

### Frontend
- ✅ Landing Page (large logo with text)
- ✅ Dashboard Header (medium logo, no text)
- ✅ All pages using the Logo component

### Backend (PDF Documents)
- ✅ Receipts (A4 format) - Top center, above clinic name
- ✅ Receipts (POS format) - Top center, smaller size
- ✅ Invoices (A4 format) - Top center, above clinic name
- ✅ Invoices (POS format) - Top center, smaller size

## Logo Component Usage

The Logo component can be used anywhere in the frontend:

```tsx
import Logo from '../components/common/Logo';

// Large logo with text (for landing pages)
<Logo size="large" />

// Medium logo with text (default)
<Logo size="medium" />

// Small logo with text
<Logo size="small" />

// Logo only, no text
<Logo size="medium" showText={false} />
```

## Fallback Behavior

If the logo image file is not found:
- Frontend: Shows a hospital emoji (🏥) as fallback
- Backend PDFs: Logo section is omitted, clinic name still displays

## Testing

1. Place the logo file at `frontend/public/logo.png`
2. Restart the frontend development server
3. Check the landing page - logo should appear
4. Generate a receipt or invoice - logo should appear in PDF
5. Check the dashboard header - logo should appear

## Notes

- The logo is automatically embedded in PDFs as base64-encoded images
- Logo sizes are optimized for different contexts (A4 vs POS receipts)
- The logo supports PNG, JPG, and SVG formats
- For best results, use PNG with transparent background
