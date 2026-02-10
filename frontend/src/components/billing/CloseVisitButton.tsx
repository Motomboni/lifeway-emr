/**
 * Close Visit Button Component
 * 
 * Allows doctors to close visits with billing validation.
 * Per EMR Rules: Doctor-only, no amount visibility, payment status badge only.
 */
import React, { useState } from 'react';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../contexts/AuthContext';
import { closeVisit } from '../../api/visits';
import { Visit } from '../../types/visit';

interface CloseVisitButtonProps {
  visitId: number;
  visit: Visit;
  onVisitClosed?: () => void;
  className?: string;
}

const PAYMENT_STATUS_CONFIG = {
  UNPAID: {
    label: 'Unpaid',
    color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    icon: '⏳',
    canClose: false,
  },
  PARTIALLY_PAID: {
    label: 'Partially Paid',
    color: 'bg-orange-100 text-orange-800 border-orange-200',
    icon: '⚠️',
    canClose: false,
  },
  PAID: {
    label: 'Paid',
    color: 'bg-green-100 text-green-800 border-green-200',
    icon: '✅',
    canClose: true,
  },
  INSURANCE_PENDING: {
    label: 'Insurance Pending',
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    icon: '🏥',
    canClose: true,
  },
  INSURANCE_CLAIMED: {
    label: 'Insurance Claimed',
    color: 'bg-indigo-100 text-indigo-800 border-indigo-200',
    icon: '📤',
    canClose: true,
  },
  SETTLED: {
    label: 'Settled',
    color: 'bg-green-100 text-green-800 border-green-200',
    icon: '✅',
    canClose: true,
  },
  CLEARED: {
    label: 'Cleared',
    color: 'bg-green-100 text-green-800 border-green-200',
    icon: '✅',
    canClose: true,
  },
};

export default function CloseVisitButton({
  visitId,
  visit,
  onVisitClosed,
  className = '',
}: CloseVisitButtonProps) {
  const { showSuccess, showError } = useToast();
  const { user } = useAuth();
  const [closing, setClosing] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  // Only show to doctors
  if (user?.role !== 'DOCTOR') {
    return null;
  }

  // Check if visit is closed (define early for type narrowing and reuse)
  const isVisitClosed = visit.status === 'CLOSED';

  // Don't show if visit is already closed
  if (isVisitClosed) {
    return (
      <div className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg border bg-gray-100 text-gray-600 border-gray-200 ${className}`}>
        <span>✅</span>
        <span>Visit Closed</span>
      </div>
    );
  }

  const paymentStatus = visit.payment_status || 'UNPAID';
  const statusConfig = PAYMENT_STATUS_CONFIG[paymentStatus as keyof typeof PAYMENT_STATUS_CONFIG] || PAYMENT_STATUS_CONFIG.UNPAID;
  const isInsuranceVisit = visit.payment_type === 'INSURANCE';

  const handleCloseVisit = async () => {
    try {
      setClosing(true);

      // Close visit using API function
      await closeVisit(visitId);

      showSuccess('Visit closed successfully');
      setShowConfirmModal(false);
      
      if (onVisitClosed) {
        onVisitClosed();
      }
    } catch (error: any) {
      console.error('Failed to close visit:', error);
      
      // Extract error message from response
      let errorMessage = 'Failed to close visit';
      
      if (error.responseData) {
        if (typeof error.responseData === 'string') {
          errorMessage = error.responseData;
        } else if (error.responseData.detail) {
          errorMessage = error.responseData.detail;
        } else if (error.responseData.message) {
          errorMessage = error.responseData.message;
        }
      } else if (error.message) {
        errorMessage = error.message;
      }

      showError(errorMessage);
    } finally {
      setClosing(false);
    }
  };

  const canClose = statusConfig.canClose || 
    (isInsuranceVisit && ['INSURANCE_PENDING', 'INSURANCE_CLAIMED', 'SETTLED'].includes(paymentStatus)) ||
    (!isInsuranceVisit && ['PAID'].includes(paymentStatus));

  return (
    <>
      <div className={`flex items-center space-x-4 ${className}`}>
        {/* Payment Status Badge (No Amounts) */}
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">Payment Status:</span>
          <span
            className={`
              inline-flex items-center space-x-1 px-3 py-1 rounded-full text-sm font-medium border
              ${statusConfig.color}
            `}
          >
            <span>{statusConfig.icon}</span>
            <span>{statusConfig.label}</span>
          </span>
        </div>

        {/* Close Visit Button */}
        <button
          onClick={() => setShowConfirmModal(true)}
          disabled={!canClose || closing || isVisitClosed}
          className={`
            px-4 py-2 rounded-lg font-medium transition-colors
            ${
              canClose && !isVisitClosed
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-300 text-gray-600 cursor-not-allowed'
            }
            ${closing ? 'opacity-50' : ''}
          `}
          title={
            !canClose
              ? `Cannot close visit. Payment status must be ${isInsuranceVisit ? 'INSURANCE_PENDING, INSURANCE_CLAIMED, or SETTLED' : 'PAID'} to close.`
              : isVisitClosed
              ? 'Visit is already closed'
              : 'Close this visit'
          }
        >
          {closing ? (
            <>
              <span className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></span>
              Closing...
            </>
          ) : (
            'Close Visit'
          )}
        </button>
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
            onClick={() => setShowConfirmModal(false)}
          />

          {/* Modal */}
          <div className="flex min-h-full items-center justify-center p-4">
            <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full">
              {/* Header */}
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Close Visit</h3>
              </div>

              {/* Content */}
              <div className="px-6 py-4">
                <p className="text-gray-700 mb-4">
                  Are you sure you want to close this visit? This action cannot be undone.
                </p>
                
                <div className="bg-gray-50 rounded-lg p-3 mb-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Visit ID:</span>
                    <span className="font-medium text-gray-900">#{visitId}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm mt-2">
                    <span className="text-gray-600">Payment Status:</span>
                    <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-medium ${statusConfig.color}`}>
                      <span>{statusConfig.icon}</span>
                      <span>{statusConfig.label}</span>
                    </span>
                  </div>
                </div>

                {!canClose && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                    <p className="text-sm text-red-800">
                      ⚠️ Cannot close visit. {isInsuranceVisit 
                        ? 'Insurance claim must be in PENDING, CLAIMED, or SETTLED status.'
                        : 'All payments must be cleared before closing the visit.'}
                    </p>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="px-6 py-4 border-t border-gray-200 flex space-x-3">
                <button
                  onClick={handleCloseVisit}
                  disabled={!canClose || closing}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {closing ? 'Closing...' : 'Confirm Close'}
                </button>
                <button
                  onClick={() => setShowConfirmModal(false)}
                  disabled={closing}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium disabled:opacity-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

