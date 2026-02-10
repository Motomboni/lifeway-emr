/**
 * PDF Generation Utility
 * 
 * Uses jsPDF and html2canvas to generate PDFs from HTML content.
 * This works on all platforms including Windows.
 */
let jsPDF: any = null;
let html2canvas: any = null;

// Lazy load to handle missing dependencies gracefully
async function loadPDFLibraries() {
  if (!jsPDF) {
    try {
      jsPDF = (await import('jspdf')).default;
    } catch (e) {
      throw new Error('jsPDF is not installed. Install it with: npm install jspdf');
    }
  }
  if (!html2canvas) {
    try {
      html2canvas = (await import('html2canvas')).default;
    } catch (e) {
      throw new Error('html2canvas is not installed. Install it with: npm install html2canvas');
    }
  }
  return { jsPDF, html2canvas };
}

export interface PDFOptions {
  filename?: string;
  format?: 'a4' | 'letter';
  orientation?: 'portrait' | 'landscape';
  quality?: number;
}

/**
 * Generate PDF from HTML element
 */
export async function generatePDFFromElement(
  element: HTMLElement,
  options: PDFOptions = {}
): Promise<void> {
  const {
    filename = `document-${new Date().toISOString().split('T')[0]}.pdf`,
    format = 'a4',
    orientation = 'portrait',
    quality = 1.0,
  } = options;

  try {
    // Load libraries
    const { jsPDF: jsPDFLib, html2canvas: html2canvasLib } = await loadPDFLibraries();

    // Convert HTML element to canvas
    const canvas = await html2canvasLib(element, {
      scale: quality,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff',
    });

    // Calculate PDF dimensions
    const imgWidth = format === 'a4' ? 210 : 216; // A4: 210mm, Letter: 216mm
    const pageHeight = format === 'a4' ? 297 : 279; // A4: 297mm, Letter: 279mm
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    let heightLeft = imgHeight;

    // Create PDF
    const pdf = new jsPDFLib({
      orientation,
      unit: 'mm',
      format,
    });

    let position = 0;

    // Add first page
    pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
    heightLeft -= pageHeight;

    // Add additional pages if needed
    while (heightLeft >= 0) {
      position = heightLeft - imgHeight;
      pdf.addPage();
      pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;
    }

    // Save PDF
    pdf.save(filename);
  } catch (error: any) {
    console.error('Error generating PDF:', error);
    throw new Error(error.message || 'Failed to generate PDF. Please install jspdf and html2canvas.');
  }
}

/**
 * Generate PDF from HTML string
 */
export async function generatePDFFromHTML(
  htmlContent: string,
  options: PDFOptions = {}
): Promise<void> {
  // Create temporary element
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = htmlContent;
  tempDiv.style.position = 'absolute';
  tempDiv.style.left = '-9999px';
  tempDiv.style.width = '210mm'; // A4 width
  document.body.appendChild(tempDiv);

  try {
    await generatePDFFromElement(tempDiv, options);
  } finally {
    document.body.removeChild(tempDiv);
  }
}

/**
 * Print HTML element with full styling
 */
export function printElement(element: HTMLElement): void {
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    throw new Error('Failed to open print window. Please allow popups.');
  }

  // Clone the element to preserve structure
  const clonedElement = element.cloneNode(true) as HTMLElement;
  
  // Apply computed styles as inline styles to preserve formatting
  const applyComputedStyles = (el: HTMLElement) => {
    const computed = window.getComputedStyle(el);
    const importantStyles = [
      'font-family', 'font-size', 'font-weight', 'color', 'background-color',
      'padding', 'margin', 'border', 'text-align', 'line-height',
      'display', 'flex-direction', 'justify-content', 'align-items',
      'width', 'max-width', 'border-collapse', 'border-spacing'
    ];
    
    let inlineStyles = '';
    importantStyles.forEach(prop => {
      const value = computed.getPropertyValue(prop);
      if (value) {
        inlineStyles += `${prop}: ${value}; `;
      }
    });
    
    if (inlineStyles) {
      el.setAttribute('style', inlineStyles + (el.getAttribute('style') || ''));
    }
    
    // Recursively apply to children
    Array.from(el.children).forEach(child => {
      applyComputedStyles(child as HTMLElement);
    });
  };
  
  applyComputedStyles(clonedElement);

  // Comprehensive print styles for invoice/receipt documents
  const printStyles = `
    <style>
      * {
        box-sizing: border-box;
      }

      body {
        font-family: 'Arial', 'Helvetica', sans-serif;
        font-size: 12pt;
        line-height: 1.6;
        color: #1f2937;
        background: white;
        padding: 20px;
        margin: 0;
      }

      /* Target the document container (works with CSS modules) */
      body > div {
        max-width: 800px;
        margin: 0 auto;
        background: white;
        padding: 40px;
      }

      /* Header styles */
      body > div > div:first-child {
        border-bottom: 3px solid #2563eb;
        padding-bottom: 24px;
        margin-bottom: 32px;
      }

      /* Clinic info - center aligned div */
      body > div > div:first-child > div:first-child {
        text-align: center;
        margin-bottom: 24px;
      }

      /* Clinic name - large bold text */
      body > div > div:first-child > div:first-child > div:first-child {
        font-size: 28px;
        font-weight: bold;
        color: #2563eb;
        margin-bottom: 12px;
      }

      /* Clinic details */
      body > div > div:first-child > div:first-child > div:last-child {
        font-size: 14px;
        color: #6b7280;
        line-height: 1.6;
      }

      body > div > div:first-child > div:first-child > div:last-child > div {
        margin: 4px 0;
      }

      /* Document title */
      body > div > div:first-child > div:nth-child(2) {
        font-size: 24px;
        font-weight: bold;
        text-align: center;
        margin: 24px 0;
        color: #1e40af;
      }

      /* Document number */
      body > div > div:first-child > div:last-child {
        text-align: right;
        font-size: 16px;
        color: #6b7280;
        font-weight: 500;
      }

      /* Universal table styles */
      table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 16px;
        border: 1px solid #e5e7eb;
      }

      table thead {
        background: #2563eb;
        color: white;
      }

      table thead th {
        padding: 12px;
        text-align: left;
        font-weight: 600;
        border: 1px solid #1e40af;
      }

      table tbody td {
        padding: 12px;
        border-bottom: 1px solid #e5e7eb;
        border-left: 1px solid #e5e7eb;
        border-right: 1px solid #e5e7eb;
      }

      table tbody tr:last-child td {
        border-bottom: none;
      }

      /* Total row styling */
      table tbody tr[class*="total"] {
        font-weight: 600;
        background: #f3f4f6;
      }

      table tbody tr[class*="total"] td {
        padding: 16px 12px;
        border-top: 2px solid #2563eb;
        border-bottom: 2px solid #2563eb;
      }

      /* Right-aligned text */
      [class*="textRight"],
      td[class*="textRight"],
      th[class*="textRight"] {
        text-align: right;
      }

      /* Section titles */
      h3 {
        font-size: 18px;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e5e7eb;
      }

      /* Info rows */
      [class*="infoRow"] {
        display: flex;
        justify-content: space-between;
        padding: 12px 0;
        border-bottom: 1px solid #e5e7eb;
      }

      [class*="infoLabel"] {
        font-weight: 600;
        color: #374151;
      }

      /* Summary section */
      [class*="summary"] {
        margin: 32px 0;
        padding: 24px;
        background: #f9fafb;
        border-radius: 8px;
        border: 2px solid #e5e7eb;
      }

      [class*="summaryRow"] {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 18px;
      }

      [class*="summaryLabel"] {
        font-weight: 600;
        color: #374151;
      }

      [class*="balancePositive"] {
        color: #16a34a;
        font-weight: 700;
        font-size: 20px;
      }

      [class*="balanceNegative"] {
        color: #dc2626;
        font-weight: 700;
        font-size: 20px;
      }

      [class*="highlight"] {
        font-weight: 600;
        color: #2563eb;
        font-size: 16px;
      }

      /* Footer */
      [class*="footer"] {
        margin-top: 48px;
        padding-top: 24px;
        border-top: 2px solid #e5e7eb;
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
      }

      [class*="footerNote"] {
        font-size: 14px;
        color: #2563eb;
        font-style: italic;
      }

      [class*="signatureLine"] {
        border-top: 1px solid #1f2937;
        width: 200px;
        padding-top: 8px;
        margin-top: 60px;
        font-size: 12px;
        color: #6b7280;
      }

      @media print {
        @page {
          size: A4;
          margin: 1cm;
        }

        body {
          padding: 0;
        }

        body > div {
          padding: 20px;
        }

        table {
          page-break-inside: avoid;
        }

        [class*="section"] {
          page-break-inside: avoid;
        }
      }
    </style>
  `;

  printWindow.document.write(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>Print Document</title>
        <meta charset="utf-8">
        ${printStyles}
      </head>
      <body>
        ${clonedElement.innerHTML}
      </body>
    </html>
  `);
  
  printWindow.document.close();
  
  // Wait for content to load, then print
  setTimeout(() => {
    printWindow.print();
  }, 250);
}

/**
 * Format currency for display
 */
export function formatCurrency(amount: string | number): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount;
  return new Intl.NumberFormat('en-NG', {
    style: 'currency',
    currency: 'NGN',
  }).format(num);
}

/**
 * Format date for display
 */
export function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-NG', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
}

