/**
 * Collect Payment Modal Component
 * 
 * Modal for collecting payments with multiple payment methods.
 * Per EMR Rules: Receptionist-only, visit-scoped, real-time balance updates.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import {
  createPayment,
  createWalletDebit,
  initializePaystackPayment,
  PaymentCreateData,
  WalletDebitData,
  BillingSummary,
} from '../../api/billing';
import { formatCurrency, isValidAmount } from '../../utils/currency';
import { apiRequest } from '../../utils/apiClient';
import { Visit } from '../../types/visit';
import { Patient } from '../../types/patient';

interface CollectPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  visitId: number;
  visit: Visit;
  patient: Patient | null;
  billingSummary: BillingSummary | null;
  onPaymentSuccess: () => void;
}

type PaymentMethod = 'CASH' | 'POS' | 'TRANSFER' | 'WALLET' | 'PAYSTACK';

export default function CollectPaymentModal({
  isOpen,
  onClose,
  visitId,
  visit,
  patient,
  billingSummary,
  onPaymentSuccess,
}: CollectPaymentModalProps) {
  const { showSuccess, showError } = useToast();
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('CASH');
  const [amount, setAmount] = useState('');
  const [transactionReference, setTransactionReference] = useState('');
  const [notes, setNotes] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [patientWallet, setPatientWallet] = useState<any>(null);
  const [loadingWallet, setLoadingWallet] = useState(false);

  // Load patient wallet if needed
  useEffect(() => {
    if (isOpen && patient && paymentMethod === 'WALLET') {
      loadPatientWallet();
    }
  }, [isOpen, patient, paymentMethod]);

  // Reset form when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setAmount('');
      setTransactionReference('');
      setNotes('');
      setCustomerEmail('');
      setShowConfirmation(false);
      setPaymentMethod('CASH');
    }
  }, [isOpen]);

  const loadPatientWallet = async () => {
    if (!patient) return;

    try {
      setLoadingWallet(true);
      const wallets = await apiRequest<any>(`/wallet/wallets/`);
      const walletList = Array.isArray(wallets) ? wallets : wallets.results || [];
      const wallet = walletList.find(
        (w: any) => w.patient === patient.id || w.patient_id === patient.id
      );
      setPatientWallet(wallet || null);
    } catch (error) {
      console.error('Failed to load wallet:', error);
      setPatientWallet(null);
    } finally {
      setLoadingWallet(false);
    }
  };

  const outstandingBalance = billingSummary
    ? parseFloat(billingSummary.outstanding_balance)
    : 0;

  const amountNum = parseFloat(amount) || 0;
  const remainingBalance = outstandingBalance - amountNum;
  const isAmountValid = isValidAmount(amount) && amountNum > 0;
  const isAmountExceedsBalance = amountNum > outstandingBalance;
  const isAmountExceedsWallet = paymentMethod === 'WALLET' && patientWallet && amountNum > parseFloat(patientWallet.balance);
  const canProceed = isAmountValid && !isAmountExceedsBalance && !isAmountExceedsWallet;

  // Check if transfer reference is required
  const requiresReference = paymentMethod === 'TRANSFER';
  const canProceedToConfirmation = canProceed && (!requiresReference || transactionReference.trim() !== '');

  const handleProceedToConfirmation = () => {
    if (canProceedToConfirmation) {
      setShowConfirmation(true);
    }
  };

  const handleConfirmPayment = async () => {
    if (!canProceedToConfirmation) return;

    try {
      setSubmitting(true);

      switch (paymentMethod) {
        case 'CASH':
        case 'POS':
        case 'TRANSFER': {
          await createPayment(visitId, {
            amount: amount,
            payment_method: paymentMethod,
            transaction_reference: transactionReference || undefined,
            notes: notes || undefined,
            // status is handled by backend
          });
          showSuccess(`${paymentMethod === 'CASH' ? 'Cash' : paymentMethod === 'POS' ? 'POS' : 'Transfer'} payment recorded successfully`);
          break;
        }

        case 'WALLET': {
          if (!patientWallet) {
            showError('Patient wallet not found');
            return;
          }
          await createWalletDebit(visitId, {
            wallet_id: patientWallet.id,
            amount: amount,
            description: notes || `Payment for Visit ${visitId}`,
          });
          showSuccess('Wallet payment processed successfully');
          break;
        }

        case 'PAYSTACK': {
          const response = await initializePaystackPayment(visitId, {
            visit_id: visitId,
            amount: amount,
            callback_url: `${window.location.origin}/visits/${visitId}`,
            customer_email: customerEmail || undefined,
          });

          if (response.authorization_url) {
            // Open Paystack checkout in new window
            window.open(response.authorization_url, '_blank', 'width=800,height=600');
            showSuccess('Paystack payment initialized. Complete payment in the popup window.');
          } else {
            showError('Failed to initialize Paystack payment');
            return;
          }
          break;
        }
      }

      // Close modal and refresh
      onClose();
      onPaymentSuccess();
    } catch (error: any) {
      showError(error.message || `Failed to process ${paymentMethod} payment`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (showConfirmation) {
      setShowConfirmation(false);
    } else {
      onClose();
    }
  };

  if (!isOpen) return null;

  const isInsuranceVisit = visit.payment_type === 'INSURANCE';
  const isVisitClosed = visit.status === 'CLOSED';

  // Payment method restrictions
  const availableMethods: PaymentMethod[] = [];
  if (!isInsuranceVisit) {
    availableMethods.push('CASH');
  }
  availableMethods.push('POS', 'TRANSFER');
  if (!isInsuranceVisit) {
    availableMethods.push('PAYSTACK');
  }
  if (patientWallet && parseFloat(patientWallet.balance) > 0) {
    availableMethods.push('WALLET');
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleCancel}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 z-10">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Collect Payment</h2>
              <button
                onClick={handleCancel}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Close modal"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <p className="text-sm text-gray-600 mt-1">
              Visit #{visitId} • {patient ? `${patient.first_name} ${patient.last_name}` : 'Loading...'}
            </p>
          </div>

          {/* Content */}
          <div className="px-6 py-4">
            {showConfirmation ? (
              /* Confirmation View */
              <div className="space-y-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <h3 className="text-lg font-semibold text-blue-900 mb-3">Confirm Payment</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-blue-700">Payment Method:</span>
                      <span className="font-medium text-blue-900">{paymentMethod}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-blue-700">Amount:</span>
                      <span className="font-semibold text-blue-900">{formatCurrency(amount)}</span>
                    </div>
                    {transactionReference && (
                      <div className="flex justify-between">
                        <span className="text-blue-700">Transaction Reference:</span>
                        <span className="font-medium text-blue-900">{transactionReference}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-blue-700">Outstanding Balance:</span>
                      <span className="font-medium text-blue-900">{formatCurrency(outstandingBalance.toString())}</span>
                    </div>
                    <div className="flex justify-between border-t border-blue-200 pt-2 mt-2">
                      <span className="font-semibold text-blue-900">Remaining Balance:</span>
                      <span className={`font-bold text-lg ${remainingBalance > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                        {formatCurrency(remainingBalance.toString())}
                      </span>
                    </div>
                  </div>
                </div>

                {notes && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-700">
                      <span className="font-medium">Notes:</span> {notes}
                    </p>
                  </div>
                )}

                {paymentMethod === 'PAYSTACK' && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-sm text-yellow-800">
                      ⚠️ You will be redirected to Paystack checkout to complete the payment.
                    </p>
                  </div>
                )}

                <div className="flex space-x-3 pt-4">
                  <button
                    onClick={handleConfirmPayment}
                    disabled={submitting}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitting ? 'Processing...' : 'Confirm & Process Payment'}
                  </button>
                  <button
                    onClick={() => setShowConfirmation(false)}
                    disabled={submitting}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium disabled:opacity-50"
                  >
                    Back
                  </button>
                </div>
              </div>
            ) : (
              /* Payment Form View */
              <div className="space-y-6">
                {/* Outstanding Balance */}
                {outstandingBalance > 0 && (
                  <div className="bg-red-50 border-2 border-red-200 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-red-900">Outstanding Balance</p>
                        <p className="text-2xl font-bold text-red-600 mt-1">
                          {formatCurrency(outstandingBalance.toString())}
                        </p>
                      </div>
                      <span className="text-4xl">⚠️</span>
                    </div>
                  </div>
                )}

                {/* Payment Method Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Payment Method *
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {availableMethods.map((method) => {
                      const icons: Record<PaymentMethod, string> = {
                        CASH: '💵',
                        POS: '💳',
                        TRANSFER: '🏦',
                        WALLET: '💼',
                        PAYSTACK: '🌐',
                      };
                      const labels: Record<PaymentMethod, string> = {
                        CASH: 'Cash',
                        POS: 'POS',
                        TRANSFER: 'Transfer',
                        WALLET: 'Wallet',
                        PAYSTACK: 'Paystack',
                      };

                      return (
                        <button
                          key={method}
                          type="button"
                          onClick={() => {
                            setPaymentMethod(method);
                            if (method === 'WALLET' && !patientWallet) {
                              loadPatientWallet();
                            }
                          }}
                          className={`
                            p-4 rounded-lg border-2 transition-all text-left
                            ${
                              paymentMethod === method
                                ? 'border-blue-500 bg-blue-50'
                                : 'border-gray-200 bg-white hover:border-gray-300'
                            }
                            ${isVisitClosed ? 'opacity-50 cursor-not-allowed' : ''}
                          `}
                          disabled={isVisitClosed}
                        >
                          <div className="text-2xl mb-1">{icons[method]}</div>
                          <div className="font-semibold text-gray-900">{labels[method]}</div>
                          {method === 'WALLET' && patientWallet && (
                            <div className="text-xs text-gray-600 mt-1">
                              Balance: {formatCurrency(patientWallet.balance)}
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Amount Input */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Payment Amount (₦) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max={outstandingBalance}
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className={`
                      w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                      ${
                        isAmountExceedsBalance || isAmountExceedsWallet
                          ? 'border-red-300 bg-red-50'
                          : 'border-gray-300'
                      }
                    `}
                    placeholder="0.00"
                    disabled={isVisitClosed}
                  />
                  <div className="mt-2 space-y-1">
                    {isAmountExceedsBalance && (
                      <p className="text-sm text-red-600">
                        ⚠️ Amount exceeds outstanding balance
                      </p>
                    )}
                    {isAmountExceedsWallet && (
                      <p className="text-sm text-red-600">
                        ⚠️ Amount exceeds wallet balance ({formatCurrency(patientWallet?.balance || '0')})
                      </p>
                    )}
                    {isAmountValid && !isAmountExceedsBalance && !isAmountExceedsWallet && (
                      <p className="text-sm text-gray-600">
                        Remaining balance: <span className="font-semibold">{formatCurrency(remainingBalance.toString())}</span>
                      </p>
                    )}
                  </div>
                </div>

                {/* Transaction Reference (for Transfer) */}
                {paymentMethod === 'TRANSFER' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Transaction Reference *
                    </label>
                    <input
                      type="text"
                      value={transactionReference}
                      onChange={(e) => setTransactionReference(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Enter bank transaction reference"
                      disabled={isVisitClosed}
                      required
                    />
                  </div>
                )}

                {/* Transaction Reference (for POS - optional) */}
                {paymentMethod === 'POS' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Transaction Reference (Optional)
                    </label>
                    <input
                      type="text"
                      value={transactionReference}
                      onChange={(e) => setTransactionReference(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Enter POS transaction reference"
                      disabled={isVisitClosed}
                    />
                  </div>
                )}

                {/* Customer Email (for Paystack) */}
                {paymentMethod === 'PAYSTACK' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Customer Email (Optional)
                    </label>
                    <input
                      type="email"
                      value={customerEmail}
                      onChange={(e) => setCustomerEmail(e.target.value)}
                      className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="customer@example.com"
                      disabled={isVisitClosed}
                    />
                  </div>
                )}

                {/* Wallet Balance Info */}
                {paymentMethod === 'WALLET' && (
                  <div>
                    {loadingWallet ? (
                      <div className="bg-gray-50 rounded-lg p-4 text-center">
                        <p className="text-sm text-gray-600">Loading wallet...</p>
                      </div>
                    ) : patientWallet ? (
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-blue-900">Available Balance:</span>
                          <span className="text-lg font-bold text-blue-600">
                            {formatCurrency(patientWallet.balance)}
                          </span>
                        </div>
                        {parseFloat(patientWallet.balance) < outstandingBalance && (
                          <p className="text-xs text-blue-700 mt-2">
                            ⚠️ Wallet balance is less than outstanding balance
                          </p>
                        )}
                      </div>
                    ) : (
                      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                        <p className="text-sm text-red-800">Patient wallet not found</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Notes */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Notes (Optional)
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={3}
                    placeholder="Additional notes about this payment"
                    disabled={isVisitClosed}
                  />
                </div>

                {/* Visit Status Warning */}
                {isVisitClosed && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <p className="text-sm text-yellow-800">
                      ⚠️ This visit is CLOSED. Payments cannot be processed.
                    </p>
                  </div>
                )}

                {/* Insurance Visit Warning */}
                {isInsuranceVisit && (paymentMethod === 'CASH' || paymentMethod === 'PAYSTACK') && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                    <p className="text-sm text-red-800">
                      ⚠️ Insurance visits cannot accept {paymentMethod === 'CASH' ? 'Cash' : 'Paystack'} payments.
                    </p>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex space-x-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={handleProceedToConfirmation}
                    disabled={!canProceedToConfirmation || isVisitClosed || submitting}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Continue to Confirmation
                  </button>
                  <button
                    onClick={handleCancel}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

