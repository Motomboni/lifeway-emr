/**
 * Invoice/Receipt Viewer Component
 * 
 * Modern, professional viewer for invoices and receipts with:
 * - Print functionality
 * - PDF download
 * - Email sending
 * - QR code display
 */
import React, { useRef, useState } from 'react';
import { useToast } from '../../hooks/useToast';
import { generatePDFFromElement, printElement, formatCurrency, formatDate } from '../../utils/pdfGenerator';
import { sendReceiptEmail, sendInvoiceEmail } from '../../api/billing';
import Logo from '../common/Logo';
import styles from '../../styles/InvoiceReceipt.module.css';

export interface ReceiptData {
  receipt_number: string;
  receipt_type: 'RECEIPT';
  visit_id: number;
  patient_name: string;
  patient_id: string;
  date: string;
  charges: Array<{
    category: string;
    description: string;
    amount: string;
    created_at: string;
  }>;
  payments: Array<{
    id: number;
    amount: string;
    payment_method: string;
    transaction_reference: string;
    notes?: string;
    processed_by: string;
    created_at: string;
  }>;
  total_charges: string;
  total_paid: string;
  outstanding_balance: string;
  payment_status: string;
  clinic_name: string;
  clinic_address: string;
  clinic_phone: string;
}

export interface InvoiceData {
  invoice_number: string;
  invoice_type: 'INVOICE';
  visit_id: number;
  patient_name: string;
  patient_id: string;
  insurance_provider: string;
  insurance_number: string;
  approval_status: string;
  approved_amount?: string;
  coverage_type: string;
  coverage_percentage: number;
  date: string;
  charges: Array<{
    category: string;
    description: string;
    amount: string;
    created_at: string;
  }>;
  total_charges: string;
  insurance_amount: string;
  patient_payable: string;
  outstanding_balance: string;
  payment_status: string;
  clinic_name: string;
  clinic_address: string;
  clinic_phone: string;
}

interface InvoiceReceiptViewerProps {
  document: ReceiptData | InvoiceData;
  visitId: number;
  onClose?: () => void;
}

export default function InvoiceReceiptViewer({
  document,
  visitId,
  onClose,
}: InvoiceReceiptViewerProps) {
  const { showSuccess, showError } = useToast();
  const printRef = useRef<HTMLDivElement>(null);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [emailAddress, setEmailAddress] = useState('');

  const isReceipt = 'receipt_type' in document;
  const documentNumber = isReceipt ? document.receipt_number : document.invoice_number;

  const handlePrint = () => {
    if (printRef.current) {
      printElement(printRef.current);
    }
  };

  const handleDownloadPDF = async () => {
    if (!printRef.current) return;

    try {
      const filename = `${isReceipt ? 'receipt' : 'invoice'}-${documentNumber}.pdf`;
      await generatePDFFromElement(printRef.current, {
        filename,
        format: 'a4',
        orientation: 'portrait',
        quality: 2,
      });
      showSuccess('PDF downloaded successfully');
    } catch (error: any) {
      console.error('Error generating PDF:', error);
      showError(error.message || 'Failed to generate PDF');
    }
  };

  const handleSendEmail = async () => {
    if (!emailAddress || !emailAddress.includes('@')) {
      showError('Please enter a valid email address');
      return;
    }

    try {
      setSendingEmail(true);
      if (isReceipt) {
        await sendReceiptEmail(visitId, emailAddress);
      } else {
        await sendInvoiceEmail(visitId, emailAddress);
      }
      showSuccess(`Document sent to ${emailAddress} successfully`);
      setShowEmailModal(false);
      setEmailAddress('');
    } catch (error: any) {
      console.error('Error sending email:', error);
      showError(error.message || 'Failed to send email');
    } finally {
      setSendingEmail(false);
    }
  };

  return (
    <div className={styles.viewerContainer}>
      {/* Action Bar */}
      <div className={styles.actionBar}>
        <div className={styles.actionGroup}>
          <button onClick={handlePrint} className={styles.actionButton}>
            🖨️ Print
          </button>
          <button onClick={handleDownloadPDF} className={styles.actionButton}>
            📥 Download PDF
          </button>
          <button
            onClick={() => setShowEmailModal(true)}
            className={styles.actionButton}
          >
            📧 Send Email
          </button>
        </div>
        {onClose && (
          <button onClick={onClose} className={styles.closeButton}>
            ✕ Close
          </button>
        )}
      </div>

      {/* Document Content */}
      <div ref={printRef} className={styles.document}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.clinicInfo}>
            <div className={styles.logoWrap}>
              <Logo size="small" showText={false} />
            </div>
            <div className={styles.clinicName}>{document.clinic_name}</div>
            <div className={styles.clinicDetails}>
              <div>{document.clinic_address}</div>
              <div>Phone: {document.clinic_phone}</div>
            </div>
          </div>
          <div className={styles.documentTitle}>
            {isReceipt ? 'PAYMENT RECEIPT' : 'INVOICE'}
          </div>
          <div className={styles.documentNumber}>
            {isReceipt ? 'Receipt No:' : 'Invoice No:'} {documentNumber}
          </div>
        </div>

        {/* Patient Information */}
        <div className={styles.infoSection}>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Patient Name:</span>
            <span>{document.patient_name}</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Patient ID:</span>
            <span>{document.patient_id}</span>
          </div>
          {!isReceipt && (
            <>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Insurance Provider:</span>
                <span>{document.insurance_provider}</span>
              </div>
              <div className={styles.infoRow}>
                <span className={styles.infoLabel}>Insurance Number:</span>
                <span>{document.insurance_number}</span>
              </div>
            </>
          )}
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Visit ID:</span>
            <span>#{document.visit_id}</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Date:</span>
            <span>{formatDate(document.date)}</span>
          </div>
        </div>

        {/* Charges Table */}
        <div className={styles.section}>
          <h3 className={styles.sectionTitle}>Services</h3>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Category</th>
                <th>Description</th>
                <th className={styles.textRight}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {document.charges.map((charge, index) => (
                <tr key={index}>
                  <td>{charge.category}</td>
                  <td>{charge.description}</td>
                  <td className={styles.textRight}>{formatCurrency(charge.amount)}</td>
                </tr>
              ))}
              <tr className={styles.totalRow}>
                <td colSpan={2}>Total Charges</td>
                <td className={styles.textRight}>{formatCurrency(document.total_charges)}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Payments (Receipt only) */}
        {isReceipt && (
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Payments</h3>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Method</th>
                  <th>Reference</th>
                  <th className={styles.textRight}>Amount</th>
                </tr>
              </thead>
              <tbody>
                {document.payments.map((payment) => (
                  <tr key={payment.id}>
                    <td>{formatDate(payment.created_at)}</td>
                    <td>{payment.payment_method}</td>
                    <td>{payment.transaction_reference || 'N/A'}</td>
                    <td className={styles.textRight}>{formatCurrency(payment.amount)}</td>
                  </tr>
                ))}
                <tr className={styles.totalRow}>
                  <td colSpan={3}>Total Paid</td>
                  <td className={styles.textRight}>{formatCurrency(document.total_paid)}</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {/* Insurance Info (Invoice only) */}
        {!isReceipt && (
          <div className={styles.section}>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Insurance Coverage:</span>
              <span>{formatCurrency(document.insurance_amount)}</span>
            </div>
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Patient Payable:</span>
              <span className={styles.highlight}>{formatCurrency(document.patient_payable)}</span>
            </div>
          </div>
        )}

        {/* Summary */}
        <div className={styles.summary}>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>Outstanding Balance:</span>
            <span
              className={
                parseFloat(document.outstanding_balance) > 0
                  ? styles.balanceNegative
                  : styles.balancePositive
              }
            >
              {formatCurrency(document.outstanding_balance)}
            </span>
          </div>
        </div>

        {/* Footer */}
        <div className={styles.footer}>
          <div className={styles.footerNote}>
            {isReceipt
              ? 'Thank you for your payment!'
              : 'Please submit this invoice to your insurance provider.'}
          </div>
          <div className={styles.footerSignature}>
            <div className={styles.signatureLine}>Authorized Signature</div>
          </div>
        </div>
      </div>

      {/* Email Modal */}
      {showEmailModal && (
        <div className={styles.modalOverlay} onClick={() => setShowEmailModal(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <h3>Send {isReceipt ? 'Receipt' : 'Invoice'} via Email</h3>
            <div className={styles.modalContent}>
              <label>
                Email Address:
                <input
                  type="email"
                  value={emailAddress}
                  onChange={(e) => setEmailAddress(e.target.value)}
                  placeholder="patient@example.com"
                  className={styles.emailInput}
                />
              </label>
            </div>
            <div className={styles.modalActions}>
              <button
                onClick={() => setShowEmailModal(false)}
                className={styles.modalButton}
                disabled={sendingEmail}
              >
                Cancel
              </button>
              <button
                onClick={handleSendEmail}
                className={`${styles.modalButton} ${styles.modalButtonPrimary}`}
                disabled={sendingEmail || !emailAddress}
              >
                {sendingEmail ? 'Sending...' : 'Send Email'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

