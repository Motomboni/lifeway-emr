/**
 * Export and Print Utilities
 * 
 * Provides functions for exporting visit summaries and printing reports.
 */

export interface VisitSummaryData {
  visit: any;
  patient?: any; // Patient information
  consultation: any;
  labOrders?: any[]; // Deprecated - services now ordered via catalog
  labResults?: any[]; // Deprecated
  radiologyOrders?: any[]; // Deprecated - services now ordered via catalog
  radiologyResults?: any[]; // Deprecated
  prescriptions?: any[]; // Deprecated - services now ordered via catalog
  payments: any[];
}

/**
 * Generate HTML for visit summary
 */
export function generateVisitSummaryHTML(data: VisitSummaryData): string {
  const { visit, patient, consultation, labOrders = [], labResults = [], radiologyOrders = [], radiologyResults = [], prescriptions = [], payments } = data;
  
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getLabResultForOrder = (orderId: number) => {
    return labResults.find(r => r.lab_order_id === orderId);
  };

  const getRadiologyResultForOrder = (orderId: number) => {
    return radiologyResults.find(r => r.radiology_request_id === orderId);
  };

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Visit Summary - Visit #${visit.id}</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      margin: 20px;
      color: #333;
    }
    .header {
      border-bottom: 2px solid #333;
      padding-bottom: 10px;
      margin-bottom: 20px;
    }
    .header h1 {
      margin: 0;
      color: #2c3e50;
    }
    .section {
      margin-bottom: 30px;
      page-break-inside: avoid;
    }
    .section h2 {
      color: #2c3e50;
      border-bottom: 1px solid #ddd;
      padding-bottom: 5px;
      margin-bottom: 15px;
    }
    .info-grid {
      display: grid;
      grid-template-columns: 150px 1fr;
      gap: 10px;
      margin-bottom: 15px;
    }
    .info-label {
      font-weight: bold;
      color: #555;
    }
    .consultation-details {
      background: #f8f9fa;
      padding: 15px;
      border-radius: 4px;
      margin-bottom: 15px;
    }
    .order-card {
      border: 1px solid #ddd;
      padding: 15px;
      margin-bottom: 15px;
      border-radius: 4px;
    }
    .order-header {
      font-weight: bold;
      margin-bottom: 10px;
      color: #2c3e50;
    }
    .result-card {
      background: #e3f2fd;
      padding: 10px;
      margin-top: 10px;
      border-left: 4px solid #2196f3;
    }
    .badge {
      display: inline-block;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 0.85em;
      font-weight: bold;
    }
    .badge-open { background: #4caf50; color: white; }
    .badge-closed { background: #f44336; color: white; }
    .badge-cleared { background: #2196f3; color: white; }
    .badge-pending { background: #ff9800; color: white; }
    @media print {
      body { margin: 0; }
      .no-print { display: none; }
      .section { page-break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>Visit Summary - Visit #${visit.id}</h1>
    ${patient ? `
    <div style="margin-bottom: 20px; padding: 15px; background: #f0f7ff; border-radius: 4px;">
      <h2 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 1.2em;">Patient Information</h2>
      <div class="info-grid">
        <div class="info-label">Name:</div>
        <div>${patient.full_name || `${patient.first_name} ${patient.last_name}`}</div>
        <div class="info-label">Patient ID:</div>
        <div>${patient.patient_id || 'N/A'}</div>
        ${patient.date_of_birth ? `
        <div class="info-label">Date of Birth:</div>
        <div>${new Date(patient.date_of_birth).toLocaleDateString()}</div>
        ` : ''}
        ${patient.age ? `
        <div class="info-label">Age:</div>
        <div>${patient.age} years</div>
        ` : ''}
        ${patient.gender ? `
        <div class="info-label">Gender:</div>
        <div>${patient.gender}</div>
        ` : ''}
        ${patient.phone ? `
        <div class="info-label">Phone:</div>
        <div>${patient.phone}</div>
        ` : ''}
        ${patient.blood_group ? `
        <div class="info-label">Blood Group:</div>
        <div>${patient.blood_group}</div>
        ` : ''}
        ${patient.allergies ? `
        <div class="info-label">Allergies:</div>
        <div>${patient.allergies}</div>
        ` : ''}
      </div>
    </div>
    ` : ''}
    <div class="info-grid">
      <div class="info-label">Visit Date:</div>
      <div>${formatDate(visit.created_at)}</div>
      <div class="info-label">Status:</div>
      <div><span class="badge badge-${visit.status.toLowerCase()}">${visit.status}</span></div>
      <div class="info-label">Payment:</div>
      <div><span class="badge badge-${visit.payment_status.toLowerCase()}">${visit.payment_status}</span></div>
      ${visit.closed_at ? `
      <div class="info-label">Closed:</div>
      <div>${formatDate(visit.closed_at)}</div>
      ` : ''}
    </div>
  </div>

  ${consultation ? `
  <div class="section">
    <h2>Consultation</h2>
    <div class="consultation-details">
      ${consultation.history ? `<div><strong>History:</strong><br>${consultation.history.replace(/\n/g, '<br>')}</div><br>` : ''}
      ${consultation.examination ? `<div><strong>Examination:</strong><br>${consultation.examination.replace(/\n/g, '<br>')}</div><br>` : ''}
      ${consultation.diagnosis ? `<div><strong>Diagnosis:</strong><br>${consultation.diagnosis.replace(/\n/g, '<br>')}</div><br>` : ''}
      ${consultation.clinical_notes ? `<div><strong>Clinical Notes:</strong><br>${consultation.clinical_notes.replace(/\n/g, '<br>')}</div>` : ''}
      <div style="margin-top: 15px; font-size: 0.9em; color: #666;">
        Created: ${formatDate(consultation.created_at)}
      </div>
    </div>
  </div>
  ` : ''}

  ${labOrders.length > 0 ? `
  <div class="section">
    <h2>Lab Orders (${labOrders.length})</h2>
    ${labOrders.map(order => {
      const result = getLabResultForOrder(order.id);
      return `
      <div class="order-card">
        <div class="order-header">Lab Order #${order.id} - ${order.status}</div>
        <div><strong>Tests:</strong> ${Array.isArray(order.tests_requested) ? order.tests_requested.join(', ') : 'N/A'}</div>
        ${order.clinical_indication ? `<div><strong>Indication:</strong> ${order.clinical_indication}</div>` : ''}
        <div><strong>Ordered:</strong> ${formatDate(order.created_at)}</div>
        ${result ? `
        <div class="result-card">
          <div><strong>Result:</strong> ${result.result_data.replace(/\n/g, '<br>')}</div>
          <div><strong>Flag:</strong> <span class="badge">${result.abnormal_flag}</span></div>
          <div><strong>Recorded:</strong> ${formatDate(result.recorded_at)}</div>
        </div>
        ` : ''}
      </div>
      `;
    }).join('')}
  </div>
  ` : ''}

  ${radiologyOrders.length > 0 ? `
  <div class="section">
    <h2>Radiology Orders (${radiologyOrders.length})</h2>
    ${radiologyOrders.map(order => {
      const result = getRadiologyResultForOrder(order.id);
      return `
      <div class="order-card">
        <div class="order-header">Radiology Order #${order.id} - ${order.status}</div>
        <div><strong>Study Type:</strong> ${order.study_type}</div>
        ${order.study_code ? `<div><strong>Code:</strong> ${order.study_code}</div>` : ''}
        ${order.clinical_indication ? `<div><strong>Indication:</strong> ${order.clinical_indication}</div>` : ''}
        ${order.instructions ? `<div><strong>Instructions:</strong> ${order.instructions}</div>` : ''}
        <div><strong>Ordered:</strong> ${formatDate(order.created_at)}</div>
        ${result ? `
        <div class="result-card">
          <div><strong>Report:</strong> ${result.report.replace(/\n/g, '<br>')}</div>
          <div><strong>Finding:</strong> <span class="badge">${result.finding_flag}</span></div>
          ${result.image_count > 0 ? `<div><strong>Images:</strong> ${result.image_count}</div>` : ''}
          <div><strong>Reported:</strong> ${formatDate(result.reported_at)}</div>
        </div>
        ` : ''}
      </div>
      `;
    }).join('')}
  </div>
  ` : ''}

  ${prescriptions.length > 0 ? `
  <div class="section">
    <h2>Prescriptions (${prescriptions.length})</h2>
    ${prescriptions.map(prescription => `
    <div class="order-card">
      <div class="order-header">Prescription #${prescription.id} - ${prescription.status}</div>
      <div><strong>Drug:</strong> ${prescription.drug}</div>
      ${prescription.dosage ? `<div><strong>Dosage:</strong> ${prescription.dosage}</div>` : ''}
      ${prescription.frequency ? `<div><strong>Frequency:</strong> ${prescription.frequency}</div>` : ''}
      ${prescription.duration ? `<div><strong>Duration:</strong> ${prescription.duration}</div>` : ''}
      ${prescription.quantity ? `<div><strong>Quantity:</strong> ${prescription.quantity}</div>` : ''}
      ${prescription.instructions ? `<div><strong>Instructions:</strong> ${prescription.instructions}</div>` : ''}
      ${prescription.dispensing_notes ? `<div><strong>Dispensing Notes:</strong> ${prescription.dispensing_notes}</div>` : ''}
      <div><strong>Created:</strong> ${formatDate(prescription.created_at)}</div>
    </div>
    `).join('')}
  </div>
  ` : ''}

  ${payments.length > 0 ? `
  <div class="section">
    <h2>Payments (${payments.length})</h2>
    ${payments.map(payment => `
    <div class="order-card">
      <div class="order-header">Payment #${payment.id} - ${payment.status}</div>
      <div><strong>Amount:</strong> ${payment.amount}</div>
      <div><strong>Method:</strong> ${payment.payment_method}</div>
      ${payment.transaction_reference ? `<div><strong>Reference:</strong> ${payment.transaction_reference}</div>` : ''}
      ${payment.notes ? `<div><strong>Notes:</strong> ${payment.notes}</div>` : ''}
      ${payment.processed_by_name ? `<div><strong>Processed By:</strong> ${payment.processed_by_name}</div>` : ''}
      <div><strong>Created:</strong> ${formatDate(payment.created_at)}</div>
    </div>
    `).join('')}
  </div>
  ` : ''}

  <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.85em; color: #666; text-align: center;">
    Generated on ${new Date().toLocaleString()}
  </div>
</body>
</html>
  `;
}

/**
 * Print visit summary
 */
export function printVisitSummary(data: VisitSummaryData) {
  const html = generateVisitSummaryHTML(data);
  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.onload = () => {
      printWindow.print();
    };
  }
}

/**
 * Export visit summary as PDF (using browser print to PDF)
 */
export function exportVisitSummaryAsPDF(data: VisitSummaryData) {
  printVisitSummary(data); // Browser's print dialog can save as PDF
}

/**
 * Download visit summary as HTML file
 */
export function downloadVisitSummaryAsHTML(data: VisitSummaryData, filename?: string) {
  const html = generateVisitSummaryHTML(data);
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || `visit-${data.visit.id}-summary-${new Date().toISOString().split('T')[0]}.html`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export visit summary as text
 */
export function exportVisitSummaryAsText(data: VisitSummaryData): string {
  const { visit, patient, consultation, labOrders = [], labResults = [], radiologyOrders = [], radiologyResults = [], prescriptions = [], payments } = data;
  
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  let text = `VISIT SUMMARY - Visit #${visit.id}\n`;
  text += `${'='.repeat(50)}\n\n`;
  
  if (patient) {
    text += `PATIENT INFORMATION\n`;
    text += `${'-'.repeat(50)}\n`;
    text += `Name: ${patient.full_name || `${patient.first_name} ${patient.last_name}`}\n`;
    text += `Patient ID: ${patient.patient_id || 'N/A'}\n`;
    if (patient.date_of_birth) text += `Date of Birth: ${new Date(patient.date_of_birth).toLocaleDateString()}\n`;
    if (patient.age) text += `Age: ${patient.age} years\n`;
    if (patient.gender) text += `Gender: ${patient.gender}\n`;
    if (patient.phone) text += `Phone: ${patient.phone}\n`;
    if (patient.blood_group) text += `Blood Group: ${patient.blood_group}\n`;
    if (patient.allergies) text += `Allergies: ${patient.allergies}\n`;
    text += `\n${'='.repeat(50)}\n\n`;
  }
  
  text += `VISIT INFORMATION\n`;
  text += `${'-'.repeat(50)}\n`;
  text += `Date: ${formatDate(visit.created_at)}\n`;
  text += `Status: ${visit.status}\n`;
  text += `Payment: ${visit.payment_status}\n`;
  if (visit.closed_at) {
    text += `Closed: ${formatDate(visit.closed_at)}\n`;
  }
  text += `\n${'='.repeat(50)}\n\n`;

  if (consultation) {
    text += `CONSULTATION\n`;
    text += `${'-'.repeat(50)}\n`;
    if (consultation.history) text += `History: ${consultation.history}\n\n`;
    if (consultation.examination) text += `Examination: ${consultation.examination}\n\n`;
    if (consultation.diagnosis) text += `Diagnosis: ${consultation.diagnosis}\n\n`;
    if (consultation.clinical_notes) text += `Clinical Notes: ${consultation.clinical_notes}\n\n`;
    text += `Created: ${formatDate(consultation.created_at)}\n\n`;
  }

  if (labOrders.length > 0) {
    text += `LAB ORDERS (${labOrders.length})\n`;
    text += `${'-'.repeat(50)}\n`;
    labOrders.forEach(order => {
      text += `Order #${order.id} - ${order.status}\n`;
      text += `Tests: ${Array.isArray(order.tests_requested) ? order.tests_requested.join(', ') : 'N/A'}\n`;
      if (order.clinical_indication) text += `Indication: ${order.clinical_indication}\n`;
      text += `Ordered: ${formatDate(order.created_at)}\n`;
      const result = labResults.find(r => r.lab_order_id === order.id);
      if (result) {
        text += `Result: ${result.result_data}\n`;
        text += `Flag: ${result.abnormal_flag}\n`;
        text += `Recorded: ${formatDate(result.recorded_at)}\n`;
      }
      text += `\n`;
    });
  }

  if (radiologyOrders.length > 0) {
    text += `RADIOLOGY ORDERS (${radiologyOrders.length})\n`;
    text += `${'-'.repeat(50)}\n`;
    radiologyOrders.forEach(order => {
      text += `Order #${order.id} - ${order.status}\n`;
      text += `Study Type: ${order.study_type}\n`;
      if (order.study_code) text += `Code: ${order.study_code}\n`;
      if (order.clinical_indication) text += `Indication: ${order.clinical_indication}\n`;
      if (order.instructions) text += `Instructions: ${order.instructions}\n`;
      text += `Ordered: ${formatDate(order.created_at)}\n`;
      const result = radiologyResults.find(r => r.radiology_request_id === order.id);
      if (result) {
        text += `Report: ${result.report}\n`;
        text += `Finding: ${result.finding_flag}\n`;
        if (result.image_count > 0) text += `Images: ${result.image_count}\n`;
        text += `Reported: ${formatDate(result.reported_at)}\n`;
      }
      text += `\n`;
    });
  }

  if (prescriptions.length > 0) {
    text += `PRESCRIPTIONS (${prescriptions.length})\n`;
    text += `${'-'.repeat(50)}\n`;
    prescriptions.forEach(prescription => {
      text += `Prescription #${prescription.id} - ${prescription.status}\n`;
      text += `Drug: ${prescription.drug}\n`;
      if (prescription.dosage) text += `Dosage: ${prescription.dosage}\n`;
      if (prescription.frequency) text += `Frequency: ${prescription.frequency}\n`;
      if (prescription.duration) text += `Duration: ${prescription.duration}\n`;
      if (prescription.quantity) text += `Quantity: ${prescription.quantity}\n`;
      if (prescription.instructions) text += `Instructions: ${prescription.instructions}\n`;
      if (prescription.dispensing_notes) text += `Dispensing Notes: ${prescription.dispensing_notes}\n`;
      text += `Created: ${formatDate(prescription.created_at)}\n\n`;
    });
  }

  if (payments.length > 0) {
    text += `PAYMENTS (${payments.length})\n`;
    text += `${'-'.repeat(50)}\n`;
    payments.forEach(payment => {
      text += `Payment #${payment.id} - ${payment.status}\n`;
      text += `Amount: ${payment.amount}\n`;
      text += `Method: ${payment.payment_method}\n`;
      if (payment.transaction_reference) text += `Reference: ${payment.transaction_reference}\n`;
      if (payment.notes) text += `Notes: ${payment.notes}\n`;
      if (payment.processed_by_name) text += `Processed By: ${payment.processed_by_name}\n`;
      text += `Created: ${formatDate(payment.created_at)}\n\n`;
    });
  }

  text += `\n${'='.repeat(50)}\n`;
  text += `Generated on ${new Date().toLocaleString()}\n`;

  return text;
}

/**
 * Download visit summary as text file
 */
export function downloadVisitSummaryAsText(data: VisitSummaryData, filename?: string) {
  const text = exportVisitSummaryAsText(data);
  const blob = new Blob([text], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || `visit-${data.visit.id}-summary-${new Date().toISOString().split('T')[0]}.txt`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
