/**
 * Invoice/Receipt Panel Component
 * 
 * Enhanced version of BillingDocumentsPanel with modern viewer integration.
 */
import React, { useState } from 'react';
import { useToast } from '../../hooks/useToast';
import { getReceipt, getInvoice, ReceiptData, InvoiceData } from '../../api/billing';
import InvoiceReceiptViewer from './InvoiceReceiptViewer';
import { Visit } from '../../types/visit';
import styles from '../../styles/BillingDocuments.module.css';

interface InvoiceReceiptPanelProps {
  visitId: number;
  visit: Visit;
  className?: string;
}

export default function InvoiceReceiptPanel({
  visitId,
  visit,
  className = '',
}: InvoiceReceiptPanelProps) {
  const { showSuccess, showError } = useToast();
  const [loading, setLoading] = useState(false);
  const [document, setDocument] = useState<ReceiptData | InvoiceData | null>(null);
  const [showViewer, setShowViewer] = useState(false);

  const isCashVisit = visit.payment_type === 'CASH';
  const isInsuranceVisit = visit.payment_type === 'INSURANCE';
  const isPaid = visit.payment_status === 'PAID' || visit.payment_status === 'SETTLED';
  const canGenerateReceipt = isCashVisit && isPaid;
  const canGenerateInvoice = isInsuranceVisit;

  const handleViewReceipt = async () => {
    if (!canGenerateReceipt) {
      showError('Receipt can only be generated for CASH visits with PAID status.');
      return;
    }

    try {
      setLoading(true);
      const receiptData = await getReceipt(visitId);
      setDocument(receiptData);
      setShowViewer(true);
    } catch (error: any) {
      console.error('Failed to load receipt:', error);
      showError(error.message || 'Failed to load receipt');
    } finally {
      setLoading(false);
    }
  };

  const handleViewInvoice = async () => {
    if (!canGenerateInvoice) {
      showError('Invoice can only be generated for INSURANCE visits.');
      return;
    }

    try {
      setLoading(true);
      const invoiceData = await getInvoice(visitId);
      setDocument(invoiceData);
      setShowViewer(true);
    } catch (error: any) {
      console.error('Failed to load invoice:', error);
      showError(error.message || 'Failed to load invoice');
    } finally {
      setLoading(false);
    }
  };

  if (showViewer && document) {
    return (
      <InvoiceReceiptViewer
        document={document}
        visitId={visitId}
        onClose={() => {
          setShowViewer(false);
          setDocument(null);
        }}
      />
    );
  }

  return (
    <div className={`${styles.panel} ${className}`}>
      <div className={styles.header}>
        <h3 className={styles.title}>Billing Documents</h3>
      </div>

      <div className={styles.actionsGrid}>
        {/* Receipt Card */}
        <div className={styles.documentCard}>
          <div className={styles.cardHeader}>
            <div className={styles.cardIcon}>🧾</div>
            <div>
              <h4 className={styles.cardTitle}>Receipt</h4>
              {canGenerateReceipt && (
                <span className={styles.badgeAvailable}>Available</span>
              )}
            </div>
          </div>
          <p className={styles.cardDescription}>
            View and download payment receipt for cash payments.
          </p>
          <button
            onClick={handleViewReceipt}
            disabled={!canGenerateReceipt || loading}
            className={`${styles.actionButton} ${
              canGenerateReceipt && !loading ? styles.buttonPrimary : styles.buttonDisabled
            }`}
            title={
              !canGenerateReceipt
                ? isCashVisit
                  ? 'Payment must be PAID to view receipt'
                  : 'Only available for CASH visits'
                : 'View receipt'
            }
          >
            {loading ? (
              <>
                <span className={styles.spinner}></span>
                Loading...
              </>
            ) : (
              <>
                <span>👁️</span>
                View Receipt
              </>
            )}
          </button>
          {!canGenerateReceipt && (
            <p className={styles.helpText}>
              {isCashVisit
                ? 'Payment must be PAID to view receipt'
                : 'Only available for CASH visits'}
            </p>
          )}
        </div>

        {/* Invoice Card */}
        <div className={styles.documentCard}>
          <div className={styles.cardHeader}>
            <div className={styles.cardIcon}>📄</div>
            <div>
              <h4 className={styles.cardTitle}>Invoice</h4>
              {canGenerateInvoice && (
                <span className={styles.badgeAvailable}>Available</span>
              )}
            </div>
          </div>
          <p className={styles.cardDescription}>
            View and download invoice for insurance claims.
          </p>
          <button
            onClick={handleViewInvoice}
            disabled={!canGenerateInvoice || loading}
            className={`${styles.actionButton} ${
              canGenerateInvoice && !loading ? styles.buttonPrimary : styles.buttonDisabled
            }`}
            title={
              !canGenerateInvoice
                ? 'Invoices are only available for INSURANCE visits'
                : 'View invoice'
            }
          >
            {loading ? (
              <>
                <span className={styles.spinner}></span>
                Loading...
              </>
            ) : (
              <>
                <span>👁️</span>
                View Invoice
              </>
            )}
          </button>
          {!canGenerateInvoice && (
            <p className={styles.helpText}>
              Only available for INSURANCE visits
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

