# Install PDF Generation Dependencies

To enable PDF generation in the frontend, install the following packages:

```bash
cd frontend
npm install jspdf html2canvas
npm install --save-dev @types/jspdf
```

## Usage

After installation, the PDF generation will work automatically. The system uses:
- **jsPDF**: For creating PDF documents
- **html2canvas**: For converting HTML elements to images

## Features

- ✅ Print functionality (works without dependencies)
- ✅ PDF download (requires jspdf and html2canvas)
- ✅ Email sending with PDF attachment
- ✅ Modern, professional document viewer

## Note

If the packages are not installed, the system will:
- Still work for viewing documents
- Still work for printing (browser print)
- Show an error when trying to download PDF
- Email sending will work but without PDF attachment

