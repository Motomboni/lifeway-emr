/**
 * Wallet Balance Card Component
 * 
 * Displays patient wallet balance and allows wallet payments.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { createWalletDebit, WalletDebitData, BillingSummary } from '../../api/billing';
import { formatCurrency, isValidAmount } from '../../utils/currency';
import { BillingPermissions } from '../../hooks/useBillingPermissions';
import { Patient } from '../../types/patient';
import { apiRequest } from '../../utils/apiClient';
import LoadingSpinner from '../common/LoadingSpinner';

interface WalletBalanceCardProps {
  visitId: number;
  patient: Patient | null;
  billingSummary: BillingSummary | null;
  permissions: BillingPermissions;
  onUpdate: () => void;
}

export default function WalletBalanceCard({
  visitId,
  patient,
  billingSummary,
  permissions,
  onUpdate,
}: WalletBalanceCardProps) {
  const { showSuccess, showError } = useToast();
  const [wallet, setWallet] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<WalletDebitData>({
    wallet_id: 0,
    amount: '',
    description: '',
  });

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
      if (patientWallet) {
        setFormData({ ...formData, wallet_id: patientWallet.id });
      }
    } catch (error) {
      console.error('Failed to load wallet:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleWalletPayment = async () => {
    if (!wallet) {
      showError('Patient wallet not found');
      return;
    }

    if (!isValidAmount(formData.amount)) {
      showError('Please enter a valid amount');
      return;
    }

    const amount = parseFloat(formData.amount);
    if (amount > parseFloat(wallet.balance)) {
      showError('Insufficient wallet balance');
      return;
    }

    try {
      setSubmitting(true);
      await createWalletDebit(visitId, {
        wallet_id: wallet.id,
        amount: formData.amount,
        description: formData.description || `Payment for Visit ${visitId}`,
      });
      showSuccess('Wallet payment processed successfully');
      setFormData({ wallet_id: wallet.id, amount: '', description: '' });
      setShowForm(false);
      await loadWallet();
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to process wallet payment');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading wallet information..." />;
  }

  if (!wallet) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 border border-gray-200 text-center">
        <p className="text-gray-600">No wallet found for this patient</p>
      </div>
    );
  }

  const balance = parseFloat(wallet.balance);
  const outstandingBalance = billingSummary
    ? parseFloat(billingSummary.outstanding_balance)
    : 0;
  const canPayFull = balance >= outstandingBalance && outstandingBalance > 0;

  return (
    <div className="space-y-6">
      {/* Wallet Balance Card */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6 border-2 border-blue-200">
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
        <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-yellow-900">Outstanding Balance</p>
              <p className="text-xl font-bold text-yellow-600 mt-1">
                {formatCurrency(outstandingBalance.toString())}
              </p>
            </div>
            {canPayFull && (
              <button
                onClick={() => {
                  setFormData({
                    wallet_id: wallet.id,
                    amount: outstandingBalance.toString(),
                    description: `Full payment for Visit ${visitId}`,
                  });
                  setShowForm(true);
                }}
                className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition-colors font-medium text-sm"
              >
                Pay Full Amount
              </button>
            )}
          </div>
        </div>
      )}

      {/* Wallet Payment Form */}
      {permissions.canProcessPayments && (
        <>
          {!showForm ? (
            <button
              onClick={() => setShowForm(true)}
              disabled={balance <= 0 || outstandingBalance <= 0}
              className="w-full px-4 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Pay from Wallet
            </button>
          ) : (
            <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
              <h4 className="font-semibold text-gray-900 mb-4">Wallet Payment</h4>
              <div className="space-y-4">
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm text-gray-700">
                    Available Balance: <span className="font-semibold">{formatCurrency(wallet.balance)}</span>
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Amount (₦) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max={wallet.balance}
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter amount"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Maximum: {formatCurrency(wallet.balance)}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={2}
                    placeholder="Optional description"
                  />
                </div>

                <div className="flex space-x-3">
                  <button
                    onClick={handleWalletPayment}
                    disabled={
                      submitting ||
                      !isValidAmount(formData.amount) ||
                      parseFloat(formData.amount) > balance
                    }
                    className="flex-1 px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {submitting ? 'Processing...' : 'Process Payment'}
                  </button>
                  <button
                    onClick={() => {
                      setShowForm(false);
                      setFormData({ wallet_id: wallet.id, amount: '', description: '' });
                    }}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Insufficient Balance Warning */}
      {outstandingBalance > 0 && balance < outstandingBalance && (
        <div className="bg-red-50 rounded-lg p-4 border border-red-200">
          <p className="text-sm text-red-800">
            ⚠️ Insufficient wallet balance. Wallet balance ({formatCurrency(wallet.balance)}) is less
            than outstanding balance ({formatCurrency(outstandingBalance.toString())}).
          </p>
        </div>
      )}
    </div>
  );
}

