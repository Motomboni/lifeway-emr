/**
 * Wallet Payment Panel Component
 * 
 * Panel for processing wallet payments with balance display and validation.
 * Per EMR Rules: Receptionist-only, visit-scoped, balance validation.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { createWalletDebit, WalletDebitData, BillingSummary } from '../../api/billing';
import { formatCurrency, isValidAmount } from '../../utils/currency';
import { apiRequest } from '../../utils/apiClient';
import { Patient } from '../../types/patient';
import LoadingSpinner from '../common/LoadingSpinner';

interface WalletPaymentPanelProps {
  visitId: number;
  patient: Patient | null;
  billingSummary: BillingSummary | null;
  onPaymentSuccess: () => void;
}

export default function WalletPaymentPanel({
  visitId,
  patient,
  billingSummary,
  onPaymentSuccess,
}: WalletPaymentPanelProps) {
  const { showSuccess, showError } = useToast();
  const [wallet, setWallet] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [amount, setAmount] = useState('');
  const [description, setDescription] = useState('');

  useEffect(() => {
    if (patient) {
      loadWallet();
    }
  }, [patient]);

  const loadWallet = async () => {
    if (!patient) return;

    try {
      setLoading(true);
      const wallets = await apiRequest<any>(`/wallet/wallets/`);
      const walletList = Array.isArray(wallets) ? wallets : wallets.results || [];
      const patientWallet = walletList.find(
        (w: any) => w.patient === patient.id || w.patient_id === patient.id
      );
      setWallet(patientWallet || null);
    } catch (error) {
      console.error('Failed to load wallet:', error);
      setWallet(null);
    } finally {
      setLoading(false);
    }
  };

  const handleFullPayment = () => {
    if (!billingSummary) return;
    const outstandingBalance = parseFloat(billingSummary.outstanding_balance);
    if (outstandingBalance > 0) {
      setAmount(outstandingBalance.toString());
      setDescription(`Full payment for Visit ${visitId}`);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!wallet) {
      showError('Patient wallet not found');
      return;
    }

    if (!isValidAmount(amount)) {
      showError('Please enter a valid payment amount');
      return;
    }

    const amountNum = parseFloat(amount);
    const walletBalance = parseFloat(wallet.balance);

    if (amountNum > walletBalance) {
      showError('Payment amount exceeds wallet balance');
      return;
    }

    const outstandingBalance = billingSummary
      ? parseFloat(billingSummary.outstanding_balance)
      : 0;

    if (amountNum > outstandingBalance) {
      showError('Payment amount exceeds outstanding balance');
      return;
    }

    try {
      setSubmitting(true);
      await createWalletDebit(visitId, {
        wallet_id: wallet.id,
        amount: amount,
        description: description || `Payment for Visit ${visitId}`,
      });
      showSuccess('Wallet payment processed successfully');
      setAmount('');
      setDescription('');
      await loadWallet();
      onPaymentSuccess();
    } catch (error: any) {
      showError(error.message || 'Failed to process wallet payment');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <LoadingSpinner message="Loading wallet information..." />
      </div>
    );
  }

  if (!wallet) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="text-center py-8">
          <div className="text-4xl mb-4">💼</div>
          <p className="text-gray-600 font-medium">No wallet found for this patient</p>
          <p className="text-sm text-gray-500 mt-2">
            The patient needs to create a wallet account before making wallet payments.
          </p>
        </div>
      </div>
    );
  }

  const walletBalance = parseFloat(wallet.balance);
  const outstandingBalance = billingSummary
    ? parseFloat(billingSummary.outstanding_balance)
    : 0;
  const amountNum = parseFloat(amount) || 0;

  const canPayFull = walletBalance >= outstandingBalance && outstandingBalance > 0;
  const isAmountValid = isValidAmount(amount) && amountNum > 0;
  const isAmountExceedsBalance = amountNum > walletBalance;
  const isAmountExceedsOutstanding = amountNum > outstandingBalance;
  const canSubmit = isAmountValid && !isAmountExceedsBalance && !isAmountExceedsOutstanding;

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Wallet Balance Card */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-5 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-blue-900 mb-1">Patient Wallet Balance</p>
            <p className="text-3xl font-bold text-blue-600">{formatCurrency(wallet.balance)}</p>
            <p className="text-xs text-blue-700 mt-2">Currency: {wallet.currency || 'NGN'}</p>
          </div>
          <div className="text-5xl">💼</div>
        </div>
      </div>

      {/* Outstanding Balance Info */}
      {outstandingBalance > 0 && (
        <div className="px-6 py-4 bg-yellow-50 border-b border-yellow-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-yellow-900">Outstanding Balance</p>
              <p className="text-xl font-bold text-yellow-600 mt-1">
                {formatCurrency(outstandingBalance.toString())}
              </p>
            </div>
            {canPayFull && (
              <button
                onClick={handleFullPayment}
                className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors font-medium text-sm"
              >
                Pay Full Amount
              </button>
            )}
          </div>
        </div>
      )}

      {/* Insufficient Balance Warning */}
      {walletBalance < outstandingBalance && outstandingBalance > 0 && (
        <div className="px-6 py-4 bg-red-50 border-b border-red-200">
          <div className="flex items-start space-x-2">
            <span className="text-xl">⚠️</span>
            <div className="flex-1">
              <p className="text-sm font-medium text-red-900">Insufficient Wallet Balance</p>
              <p className="text-xs text-red-700 mt-1">
                Wallet balance ({formatCurrency(wallet.balance)}) is less than outstanding balance (
                {formatCurrency(outstandingBalance.toString())}). Patient can make a partial payment
                or top up their wallet.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Payment Form */}
      <form onSubmit={handleSubmit} className="p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Payment Amount (₦) *
          </label>
          <input
            type="number"
            step="0.01"
            min="0"
            max={Math.min(walletBalance, outstandingBalance)}
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className={`
              w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500
              ${
                isAmountExceedsBalance || isAmountExceedsOutstanding
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }
            `}
            placeholder="0.00"
            required
          />
          <div className="mt-2 space-y-1">
            {isAmountExceedsBalance && (
              <p className="text-sm text-red-600 flex items-center space-x-1">
                <span>⚠️</span>
                <span>Amount exceeds wallet balance</span>
              </p>
            )}
            {isAmountExceedsOutstanding && !isAmountExceedsBalance && (
              <p className="text-sm text-red-600 flex items-center space-x-1">
                <span>⚠️</span>
                <span>Amount exceeds outstanding balance</span>
              </p>
            )}
            {isAmountValid && !isAmountExceedsBalance && !isAmountExceedsOutstanding && (
              <p className="text-sm text-gray-600">
                Remaining balance after payment:{' '}
                <span className="font-semibold">
                  {formatCurrency((outstandingBalance - amountNum).toString())}
                </span>
              </p>
            )}
            <p className="text-xs text-gray-500">
              Maximum: {formatCurrency(Math.min(walletBalance, outstandingBalance).toString())}
            </p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description (Optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            rows={3}
            placeholder={`Payment for Visit ${visitId}`}
          />
        </div>

        {/* Payment Summary */}
        {isAmountValid && !isAmountExceedsBalance && !isAmountExceedsOutstanding && (
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <h4 className="text-sm font-semibold text-gray-900 mb-3">Payment Summary</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Outstanding Balance:</span>
                <span className="font-medium text-gray-900">
                  {formatCurrency(outstandingBalance.toString())}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Payment Amount:</span>
                <span className="font-medium text-gray-900">{formatCurrency(amount)}</span>
              </div>
              <div className="flex justify-between border-t border-gray-300 pt-2 mt-2">
                <span className="font-semibold text-gray-900">Remaining Balance:</span>
                <span
                  className={`font-bold ${
                    outstandingBalance - amountNum > 0 ? 'text-yellow-600' : 'text-green-600'
                  }`}
                >
                  {formatCurrency((outstandingBalance - amountNum).toString())}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex space-x-3 pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={!canSubmit || submitting}
            className="flex-1 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {submitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Processing...</span>
              </>
            ) : (
              <>
                <span>💳</span>
                <span>Process Wallet Payment</span>
              </>
            )}
          </button>
          <button
            type="button"
            onClick={() => {
              setAmount('');
              setDescription('');
            }}
            disabled={submitting}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium disabled:opacity-50"
          >
            Clear
          </button>
        </div>
      </form>

      {/* Balance Info Footer */}
      <div className="px-6 py-3 bg-gray-50 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Available Balance: {formatCurrency(wallet.balance)}</span>
          {outstandingBalance > 0 && (
            <span>
              Outstanding: {formatCurrency(outstandingBalance.toString())}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

