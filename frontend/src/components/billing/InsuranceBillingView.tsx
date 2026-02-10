/**
 * Insurance Billing View Component
 * 
 * Read-only billing view for insurance/HMO visits.
 * Per EMR Rules: No payment actions, invoice generation only.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { useBillingPermissions } from '../../hooks/useBillingPermissions';
import {
  getVisitInsurance,
  getBillingSummary,
  BillingSummary,
} from '../../api/billing';
import { formatCurrency } from '../../utils/currency';
import { Visit } from '../../types/visit';
import { Patient } from '../../types/patient';
import { apiRequest } from '../../utils/apiClient';
import LoadingSpinner from '../common/LoadingSpinner';

interface InsuranceBillingViewProps {
  visitId: number;
  visit: Visit;
  patient: Patient | null;
  billingSummary: BillingSummary | null;
  onUpdate: () => void;
}

interface InsuranceRecord {
  id: number;
  visit_id: number;
  hmo_provider?: {
    id: number;
    name: string;
    code?: string;
  };
  provider_name?: string;
  insurance_number?: string;
  policy_number?: string;
  coverage_type: 'FULL' | 'PARTIAL';
  coverage_percentage: number;
  approval_status?: 'PENDING' | 'APPROVED' | 'REJECTED';
  approved_amount?: string;
  rejection_reason?: string;
  notes?: string;
}

export default function InsuranceBillingView({
  visitId,
  visit,
  patient,
  billingSummary,
  onUpdate,
}: InsuranceBillingViewProps) {
  const { showSuccess, showError } = useToast();
  const permissions = useBillingPermissions();
  const [insurance, setInsurance] = useState<InsuranceRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingInvoice, setGeneratingInvoice] = useState(false);
  const [submittingClaim, setSubmittingClaim] = useState(false);

  useEffect(() => {
    loadInsuranceData();
  }, [visitId]);

  const loadInsuranceData = async () => {
    try {
      setLoading(true);
      const [insuranceData, summary] = await Promise.all([
        getVisitInsurance(visitId).catch(() => null),
        billingSummary ? Promise.resolve(billingSummary) : getBillingSummary(visitId).catch(() => null),
      ]);
      setInsurance(insuranceData);
    } catch (error) {
      console.error('Failed to load insurance data:', error);
      showError('Failed to load insurance information');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateInvoice = async () => {
    try {
      setGeneratingInvoice(true);
      // Call invoice generation endpoint
      const response = await apiRequest(`/visits/${visitId}/billing/invoice/`, {
        method: 'GET',
      });

      // If response is HTML, open in new window
      const responseData = response as any;
      if (typeof response === 'string' || responseData.html) {
        const invoiceWindow = window.open('', '_blank');
        if (invoiceWindow) {
          invoiceWindow.document.write(responseData.html || response);
          invoiceWindow.document.close();
        }
        showSuccess('Invoice generated successfully');
      } else if (responseData.url) {
        // If response has URL, open it
        window.open(responseData.url, '_blank');
        showSuccess('Invoice generated successfully');
      } else {
        // Download as PDF or show in new window
        const blob = new Blob([JSON.stringify(response)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        window.open(url, '_blank');
        showSuccess('Invoice generated successfully');
      }
    } catch (error: any) {
      console.error('Invoice generation failed:', error);
      showError(error.message || 'Failed to generate invoice');
    } finally {
      setGeneratingInvoice(false);
    }
  };

  const handleSubmitClaim = async () => {
    if (!insurance || !billingSummary) {
      showError('Insurance information or billing summary not available');
      return;
    }

    // Get bill_id from billing dashboard API which includes bill information
    let billId: number | null = null;
    try {
      // Use the billing dashboard endpoint which returns bill.id
      const dashboardData = await apiRequest(`/billing/visit/${visitId}/summary/`) as any;
      if (dashboardData.bill && typeof dashboardData.bill === 'object' && dashboardData.bill.id) {
        billId = dashboardData.bill.id;
      } else if (dashboardData.bill_id) {
        billId = dashboardData.bill_id;
      }
    } catch (error) {
      console.error('Failed to get bill ID from dashboard:', error);
      showError('Could not retrieve bill information. Please try again.');
      return;
    }

    if (!billId) {
      showError('Could not find bill for this visit. Please ensure the visit has a bill.');
      return;
    }

    const providerName = insurance.hmo_provider?.name || insurance.provider_name;
    const policyNumber = insurance.policy_number || insurance.insurance_number;

    if (!providerName || !policyNumber) {
      showError('Insurance provider name and policy number are required to submit claim');
      return;
    }

    try {
      setSubmittingClaim(true);
      // Call insurance claim submission endpoint
      const response = await apiRequest(`/billing/insurance/submit-claim/`, {
        method: 'POST',
        body: JSON.stringify({
          bill_id: billId,
          insurance_provider: providerName,
          policy_number: policyNumber,
        }),
      });

      showSuccess('Insurance claim submitted successfully');
      await loadInsuranceData();
      onUpdate();
    } catch (error: any) {
      console.error('Claim submission failed:', error);
      showError(error.message || 'Failed to submit insurance claim');
    } finally {
      setSubmittingClaim(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <LoadingSpinner message="Loading insurance billing information..." />
      </div>
    );
  }

  const isInsuranceVisit = visit.payment_type === 'INSURANCE';
  const billTotal = billingSummary ? parseFloat(billingSummary.total_charges) : 0;
  const insuranceAmount = billingSummary ? parseFloat(billingSummary.insurance_amount) : 0;
  const claimStatus = insurance?.approval_status || 'PENDING';

  return (
    <div className="space-y-6">
      {/* Insurance Visit Banner */}
      <div className="bg-blue-50 border-2 border-blue-200 rounded-lg p-4">
        <div className="flex items-center space-x-3">
          <div className="text-3xl">🏥</div>
          <div className="flex-1">
            <h3 className="font-semibold text-blue-900">Insurance/HMO Visit</h3>
            <p className="text-sm text-blue-700 mt-1">
              This visit is covered by insurance. Payment actions are disabled.
            </p>
          </div>
        </div>
      </div>

      {/* Insurance Information Card */}
      {insurance ? (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <div className="bg-blue-50 px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">Insurance Information</h3>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-600 mb-1">Insurance Provider</p>
                <p className="font-semibold text-gray-900">
                  {insurance.hmo_provider?.name || insurance.provider_name || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Policy Number</p>
                <p className="font-semibold text-gray-900">
                  {insurance.policy_number || insurance.insurance_number || 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Coverage Type</p>
                <p className="font-semibold text-gray-900">
                  {insurance.coverage_type === 'FULL' ? 'Full Coverage' : 'Partial Coverage'}
                  {insurance.coverage_type === 'PARTIAL' && (
                    <span className="text-gray-600 ml-2">({insurance.coverage_percentage}%)</span>
                  )}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Claim Status</p>
                <span
                  className={`
                    inline-flex items-center px-3 py-1 rounded-full text-sm font-medium
                    ${
                      claimStatus === 'APPROVED'
                        ? 'bg-green-100 text-green-800'
                        : claimStatus === 'REJECTED'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }
                  `}
                >
                  {claimStatus}
                </span>
              </div>
              {insurance.approved_amount && (
                <div>
                  <p className="text-sm text-gray-600 mb-1">Approved Amount</p>
                  <p className="font-semibold text-gray-900">
                    {formatCurrency(insurance.approved_amount)}
                  </p>
                </div>
              )}
              {insurance.rejection_reason && (
                <div className="md:col-span-2">
                  <p className="text-sm text-gray-600 mb-1">Rejection Reason</p>
                  <p className="text-sm text-red-700 bg-red-50 p-2 rounded">
                    {insurance.rejection_reason}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <p className="text-yellow-800">No insurance record found for this visit</p>
        </div>
      )}

      {/* Billing Summary Card */}
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Billing Summary</h3>
          <p className="text-sm text-gray-600 mt-1">Read-only view for insurance visits</p>
        </div>
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Bill Total */}
            <div className="bg-blue-50 rounded-lg p-4 border border-blue-100">
              <p className="text-sm font-medium text-blue-900 mb-1">Total Bill Amount</p>
              <p className="text-2xl font-bold text-blue-600">
                {formatCurrency(billTotal.toString())}
              </p>
            </div>

            {/* Insurance Coverage */}
            <div className="bg-green-50 rounded-lg p-4 border border-green-100">
              <p className="text-sm font-medium text-green-900 mb-1">Insurance Coverage</p>
              <p className="text-2xl font-bold text-green-600">
                {formatCurrency(insuranceAmount.toString())}
              </p>
              {billingSummary?.is_fully_covered_by_insurance && (
                <p className="text-xs text-green-700 mt-1">Fully Covered</p>
              )}
            </div>
          </div>

          {/* Payment Status */}
          {billingSummary && (
            <div className="mt-6 pt-6 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Payment Status</p>
                  <p className="text-lg font-semibold text-gray-900 mt-1">
                    {billingSummary.payment_status}
                  </p>
                </div>
                <span
                  className={`
                    text-4xl
                    ${
                      billingSummary.payment_status === 'CLEARED' || claimStatus === 'APPROVED'
                        ? 'text-green-500'
                        : claimStatus === 'REJECTED'
                        ? 'text-red-500'
                        : 'text-yellow-500'
                    }
                  `}
                >
                  {billingSummary.payment_status === 'CLEARED' || claimStatus === 'APPROVED'
                    ? '✅'
                    : claimStatus === 'REJECTED'
                    ? '❌'
                    : '⏳'}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Generate Invoice Button */}
          <button
            onClick={handleGenerateInvoice}
            disabled={generatingInvoice || !billingSummary}
            className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {generatingInvoice ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Generating...</span>
              </>
            ) : (
              <>
                <span>📄</span>
                <span>Generate Invoice</span>
              </>
            )}
          </button>

          {/* Submit Insurance Claim Button */}
          {permissions.canManageInsurance && (
            <button
              onClick={handleSubmitClaim}
              disabled={submittingClaim || !insurance || claimStatus === 'APPROVED'}
              className="flex-1 px-4 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            >
              {submittingClaim ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <span>📤</span>
                  <span>Submit Insurance Claim</span>
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Disabled Payment Actions Notice */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div className="flex items-start space-x-2">
          <span className="text-xl">ℹ️</span>
          <div>
            <p className="text-sm font-medium text-gray-900">Payment Actions Disabled</p>
            <p className="text-xs text-gray-600 mt-1">
              Insurance visits cannot accept Cash, POS, Transfer, Paystack, or Wallet payments.
              All payments are processed through the insurance provider.
            </p>
          </div>
        </div>
      </div>

      {/* Claim Status Information */}
      {insurance && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h4 className="font-semibold text-gray-900 mb-4">Claim Status Details</h4>
          <div className="space-y-3">
            {claimStatus === 'PENDING' && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <p className="text-sm text-yellow-800">
                  ⏳ Insurance claim is pending approval. The claim will be processed by the
                  insurance provider.
                </p>
              </div>
            )}
            {claimStatus === 'APPROVED' && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <p className="text-sm text-green-800">
                  ✅ Insurance claim has been approved. Amount: {insurance.approved_amount ? formatCurrency(insurance.approved_amount) : 'N/A'}
                </p>
              </div>
            )}
            {claimStatus === 'REJECTED' && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-sm text-red-800">
                  ❌ Insurance claim has been rejected.
                  {insurance.rejection_reason && (
                    <span className="block mt-2">Reason: {insurance.rejection_reason}</span>
                  )}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

