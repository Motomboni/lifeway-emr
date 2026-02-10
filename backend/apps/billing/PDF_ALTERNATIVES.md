# PDF Generation Alternatives for Windows

## Problem

WeasyPrint requires GTK+ system libraries which are difficult to install on Windows. The system is designed to work without PDF generation, but if you need PDFs, here are alternatives:

## Option 1: Use JSON + Frontend PDF Generation (Recommended)

The API returns JSON data. Use a JavaScript library in the frontend to generate PDFs:

```bash
npm install jspdf html2canvas
# or
npm install react-pdf
```

**Advantages:**
- No backend dependencies
- Works on all platforms
- Client-side generation
- Easy to customize

## Option 2: Use ReportLab (Pure Python)

ReportLab is pure Python with no system dependencies:

```bash
pip install reportlab
```

Then modify `pdf_service.py` to use ReportLab instead of WeasyPrint.

## Option 3: Use xhtml2pdf

Easier Windows installation than WeasyPrint:

```bash
pip install xhtml2pdf
```

## Option 4: Install WeasyPrint on Windows (MSYS2 + GTK)

If you need WeasyPrint for backend PDF generation:

1. **Follow the step-by-step guide:** [WEASYPRINT_WINDOWS.md](./WEASYPRINT_WINDOWS.md)  
   It covers: installing MSYS2, installing GTK (Pango/Cairo), adding `C:\msys64\ucrt64\bin` to PATH, and `pip install weasyprint`.
2. Use **64-bit Python** and ensure PATH is set and the terminal is restarted before running your app.

## Current Implementation

The current system:
- ✅ Works without PDF generation (returns JSON)
- ✅ Gracefully handles missing WeasyPrint
- ✅ No errors if WeasyPrint not installed
- ✅ Can be extended with alternative PDF libraries

## Recommendation

For Windows development, use **Option 1** (frontend PDF generation) as it's the most reliable and doesn't require system dependencies.

