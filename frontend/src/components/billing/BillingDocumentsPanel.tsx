/**
 * Billing Documents Panel Component
 * 
 * Provides access to receipts (Cash visits) and invoices (Insurance visits).
 * Per EMR Rules: Receipt only if PAID, Invoice only if INSURANCE.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { getAuthToken } from '../../utils/apiClient';
import { Visit } from '../../types/visit';

interface BillingDocumentsPanelProps {
  visitId: number;
  visit: Visit;
  className?: string;
}

interface DocumentHistoryItem {
  id: number;
  document_type: 'RECEIPT' | 'INVOICE';
  generated_at: string;
  generated_by?: string;
  download_url?: string;
}

export default function BillingDocumentsPanel({
  visitId,
  visit,
  className = '',
}: BillingDocumentsPanelProps) {
  const { showSuccess, showError } = useToast();
  const [loading, setLoading] = useState(false);
  const [documentHistory, setDocumentHistory] = useState<DocumentHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const isCashVisit = visit.payment_type === 'CASH';
  const isInsuranceVisit = visit.payment_type === 'INSURANCE';
  const isPaid = visit.payment_status === 'PAID' || visit.payment_status === 'SETTLED';
  const canGenerateReceipt = isCashVisit && isPaid;
  const canGenerateInvoice = isInsuranceVisit;

  // Load document history
  useEffect(() => {
    loadDocumentHistory();
  }, [visitId]);

  const loadDocumentHistory = async () => {
    try {
      setLoadingHistory(true);
      // TODO: Replace with actual document history endpoint when available
      // For now, we'll track locally or fetch from a future endpoint
      // const history = await apiRequest(`/billing/visit/${visitId}/documents/`);
      // setDocumentHistory(history);
    } catch (error) {
      console.error('Failed to load document history:', error);
    } finally {
      setLoadingHistory(false);
    }
  };

  const handleDownloadReceipt = async () => {
    if (!canGenerateReceipt) {
      showError('Receipt can only be generated for CASH visits with PAID status.');
      return;
    }

    try {
      setLoading(true);
      
      // GET receipt endpoint - use fetch directly for blob response
      const API_BASE_URL = process.env.REACT_APP_API_URL || '';
      const token = localStorage.getItem('auth_token') || localStorage.getItem('auth_tokens');
      const authToken = token ? (token.startsWith('{') ? JSON.parse(token).access : token) : '';
      
      const response = await fetch(
        `${API_BASE_URL}/api/v1/visits/${visitId}/billing/receipt/?format=pdf`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${authToken}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to generate receipt' }));
        throw new Error(errorData.detail || 'Failed to generate receipt');
      }

      // Get the blob and open in new window
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      // Open PDF in new tab/window
      const newWindow = window.open(url, '_blank');
      
      if (!newWindow) {
        // If popup was blocked, fall back to download
        const link = document.createElement('a');
        link.href = url;
        link.download = `receipt-visit-${visitId}-${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showSuccess('Receipt downloaded (popup was blocked)');
      } else {
        showSuccess('Receipt opened in new tab');
      }
      
      // Clean up the blob URL after a delay (to allow the new tab to load)
      setTimeout(() => window.URL.revokeObjectURL(url), 5000);
      
      // Add to document history
      setDocumentHistory(prev => [
        {
          id: Date.now(),
          document_type: 'RECEIPT',
          generated_at: new Date().toISOString(),
          generated_by: 'Current User', // TODO: Get from auth context
        },
        ...prev,
      ]);
    } catch (error: any) {
      console.error('Failed to download receipt:', error);
      showError(error.message || 'Failed to download receipt');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadInvoice = async () => {
    if (!canGenerateInvoice) {
      showError('Invoice can only be generated for INSURANCE visits.');
      return;
    }

    try {
      setLoading(true);
      
      // GET invoice endpoint - use fetch directly for blob response
      const API_BASE_URL = process.env.REACT_APP_API_URL || '';
      const token = localStorage.getItem('auth_token') || localStorage.getItem('auth_tokens');
      const authToken = token ? (token.startsWith('{') ? JSON.parse(token).access : token) : '';
      
      const response = await fetch(
        `${API_BASE_URL}/api/v1/visits/${visitId}/billing/invoice/?format=pdf`,
        {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${authToken}`,
          },
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to generate invoice' }));
        throw new Error(errorData.detail || 'Failed to generate invoice');
      }

      // Get the blob and open in new window
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      
      // Open PDF in new tab/window
      const newWindow = window.open(url, '_blank');
      
      if (!newWindow) {
        // If popup was blocked, fall back to download
        const link = document.createElement('a');
        link.href = url;
        link.download = `invoice-visit-${visitId}-${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showSuccess('Invoice downloaded (popup was blocked)');
      } else {
        showSuccess('Invoice opened in new tab');
      }
      
      // Clean up the blob URL after a delay (to allow the new tab to load)
      setTimeout(() => window.URL.revokeObjectURL(url), 5000);
      
      // Add to document history
      setDocumentHistory(prev => [
        {
          id: Date.now(),
          document_type: 'INVOICE',
          generated_at: new Date().toISOString(),
          generated_by: 'Current User', // TODO: Get from auth context
        },
        ...prev,
      ]);
    } catch (error: any) {
      console.error('Failed to download invoice:', error);
      showError(error.message || 'Failed to download invoice');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Billing Documents</h3>
        <button
          onClick={loadDocumentHistory}
          disabled={loadingHistory}
          className="text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
        >
          {loadingHistory ? 'Loading...' : '🔄 Refresh'}
        </button>
      </div>

      {/* Download Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {/* Receipt Download */}
        <div className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">🧾</span>
              <h4 className="font-medium text-gray-900">Receipt</h4>
            </div>
            {canGenerateReceipt && (
              <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded-full">
                Available
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 mb-3">
            Download payment receipt for cash payments.
          </p>
          <button
            onClick={handleDownloadReceipt}
            disabled={!canGenerateReceipt || loading}
            className={`
              w-full px-4 py-2 rounded-lg font-medium transition-colors
              ${
                canGenerateReceipt && !loading
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-gray-200 text-gray-500 cursor-not-allowed'
              }
            `}
            title={
              !canGenerateReceipt
                ? isCashVisit
                  ? 'Receipt can only be generated when payment status is PAID'
                  : 'Receipts are only available for CASH visits'
                : 'Download receipt'
            }
          >
            {loading ? (
              <>
                <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                Generating...
              </>
            ) : (
              <>
                <span className="mr-2">📥</span>
                Download Receipt
              </>
            )}
          </button>
          {!canGenerateReceipt && (
            <p className="text-xs text-gray-500 mt-2">
              {isCashVisit
                ? 'Payment must be PAID to generate receipt'
                : 'Only available for CASH visits'}
            </p>
          )}
        </div>

        {/* Invoice Download */}
        <div className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">📄</span>
              <h4 className="font-medium text-gray-900">Invoice</h4>
            </div>
            {canGenerateInvoice && (
              <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                Available
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 mb-3">
            Download invoice for insurance claims.
          </p>
          <button
            onClick={handleDownloadInvoice}
            disabled={!canGenerateInvoice || loading}
            className={`
              w-full px-4 py-2 rounded-lg font-medium transition-colors
              ${
                canGenerateInvoice && !loading
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-200 text-gray-500 cursor-not-allowed'
              }
            `}
            title={
              !canGenerateInvoice
                ? 'Invoices are only available for INSURANCE visits'
                : 'Download invoice'
            }
          >
            {loading ? (
              <>
                <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
                Generating...
              </>
            ) : (
              <>
                <span className="mr-2">📥</span>
                Download Invoice
              </>
            )}
          </button>
          {!canGenerateInvoice && (
            <p className="text-xs text-gray-500 mt-2">
              Only available for INSURANCE visits
            </p>
          )}
        </div>
      </div>

      {/* Document History */}
      <div className="border-t border-gray-200 pt-4">
        <h4 className="font-medium text-gray-900 mb-3">Document History</h4>
        {loadingHistory ? (
          <div className="text-center py-4">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
            <p className="text-sm text-gray-500 mt-2">Loading history...</p>
          </div>
        ) : documentHistory.length > 0 ? (
          <div className="space-y-2">
            {documentHistory.map((doc) => (
              <div
                key={doc.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <span className="text-xl">
                    {doc.document_type === 'RECEIPT' ? '🧾' : '📄'}
                  </span>
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {doc.document_type === 'RECEIPT' ? 'Receipt' : 'Invoice'}
                    </p>
                    <p className="text-xs text-gray-500">
                      Generated {new Date(doc.generated_at).toLocaleString()}
                      {doc.generated_by && ` by ${doc.generated_by}`}
                    </p>
                  </div>
                </div>
                {doc.download_url && (
                  <a
                    href={doc.download_url}
                    download
                    className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                  >
                    Download
                  </a>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-4 text-gray-500">
            <p className="text-sm">No documents generated yet</p>
            <p className="text-xs mt-1">
              Documents will appear here after they are generated
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

