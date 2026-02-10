/**
 * Insurance Details Component
 * 
 * Manages insurance/HMO information and claims.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import {
  getVisitInsurance,
  createInsurance,
  updateInsurance,
  getHMOProviders,
  InsuranceCreateData,
  BillingSummary,
} from '../../api/billing';
import { formatCurrency } from '../../utils/currency';
import { BillingPermissions } from '../../hooks/useBillingPermissions';
import { Visit } from '../../types/visit';
import LoadingSpinner from '../common/LoadingSpinner';

interface InsuranceDetailsProps {
  visitId: number;
  visit: Visit;
  billingSummary: BillingSummary | null;
  permissions: BillingPermissions;
  onUpdate: () => void;
}

export default function InsuranceDetails({
  visitId,
  visit,
  billingSummary,
  permissions,
  onUpdate,
}: InsuranceDetailsProps) {
  const { showSuccess, showError } = useToast();
  const [insurance, setInsurance] = useState<any>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState<InsuranceCreateData>({
    provider: 0,
    policy_number: '',
    coverage_type: 'FULL',
    coverage_percentage: 100,
    notes: '',
  });

  useEffect(() => {
    loadData();
  }, [visitId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [insuranceData, providersData] = await Promise.all([
        getVisitInsurance(visitId).catch(() => null),
        getHMOProviders().catch(() => []),
      ]);
      setInsurance(insuranceData);
      setProviders(providersData);
    } catch (error) {
      showError('Failed to load insurance information');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateInsurance = async () => {
    if (!formData.provider || !formData.policy_number) {
      showError('Please select provider and enter policy number');
      return;
    }

    if (formData.coverage_type === 'PARTIAL' && (!formData.coverage_percentage || formData.coverage_percentage <= 0 || formData.coverage_percentage > 100)) {
      showError('Please enter a valid coverage percentage (1-100)');
      return;
    }

    try {
      setSubmitting(true);
      await createInsurance(visitId, {
        ...formData,
        coverage_percentage: formData.coverage_type === 'FULL' ? 100 : formData.coverage_percentage,
      });
      showSuccess('Insurance record created successfully');
      setShowForm(false);
      setFormData({
        provider: 0,
        policy_number: '',
        coverage_type: 'FULL',
        coverage_percentage: 100,
        notes: '',
      });
      await loadData();
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to create insurance record');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveInsurance = async () => {
    if (!insurance || !insurance.id) return;

    const approvedAmount = billingSummary?.insurance_amount || '0';
    try {
      setSubmitting(true);
      await updateInsurance(visitId, insurance.id, {
        approval_status: 'APPROVED',
        approved_amount: approvedAmount,
      });
      showSuccess('Insurance approved successfully');
      await loadData();
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to approve insurance');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRejectInsurance = async () => {
    if (!insurance || !insurance.id) return;

    const reason = prompt('Enter rejection reason:');
    if (!reason) return;

    try {
      setSubmitting(true);
      await updateInsurance(visitId, insurance.id, {
        approval_status: 'REJECTED',
        rejection_reason: reason,
      });
      showSuccess('Insurance rejected');
      await loadData();
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to reject insurance');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading insurance information..." />;
  }

  const isVisitClosed = visit.status === 'CLOSED';
  const isInsuranceVisit = visit.payment_type === 'INSURANCE';

  return (
    <div className="space-y-6">
      {/* Insurance Status */}
      {insurance ? (
        <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-blue-900">Insurance Information</h3>
            {insurance.approval_status === 'PENDING' && permissions.canManageInsurance && !isVisitClosed && (
              <div className="flex space-x-2">
                <button
                  onClick={handleApproveInsurance}
                  disabled={submitting}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50"
                >
                  Approve
                </button>
                <button
                  onClick={handleRejectInsurance}
                  disabled={submitting}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium disabled:opacity-50"
                >
                  Reject
                </button>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-blue-700">Provider</p>
              <p className="font-semibold text-blue-900">{insurance.hmo_provider?.name || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-blue-700">Policy Number</p>
              <p className="font-semibold text-blue-900">{insurance.insurance_number || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm text-blue-700">Coverage Type</p>
              <p className="font-semibold text-blue-900">{insurance.coverage_type || 'FULL'}</p>
            </div>
            <div>
              <p className="text-sm text-blue-700">Coverage Percentage</p>
              <p className="font-semibold text-blue-900">{insurance.coverage_percentage || 100}%</p>
            </div>
            <div>
              <p className="text-sm text-blue-700">Status</p>
              <span
                className={`
                  inline-block px-3 py-1 rounded-full text-sm font-medium
                  ${
                    insurance.approval_status === 'APPROVED'
                      ? 'bg-green-100 text-green-800'
                      : insurance.approval_status === 'REJECTED'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }
                `}
              >
                {insurance.approval_status || 'PENDING'}
              </span>
            </div>
            {insurance.approved_amount && (
              <div>
                <p className="text-sm text-blue-700">Approved Amount</p>
                <p className="font-semibold text-blue-900">
                  {formatCurrency(insurance.approved_amount)}
                </p>
              </div>
            )}
          </div>

          {billingSummary?.has_insurance && (
            <div className="mt-4 pt-4 border-t border-blue-200">
              <div className="flex justify-between items-center">
                <span className="text-sm text-blue-700">Insurance Coverage</span>
                <span className="text-lg font-bold text-blue-900">
                  {formatCurrency(billingSummary.insurance_amount)}
                </span>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-gray-50 rounded-lg p-6 border border-gray-200 text-center">
          <p className="text-gray-600 mb-4">No insurance record found for this visit</p>
          {permissions.canManageInsurance && !isVisitClosed && (
            <button
              onClick={() => setShowForm(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Add Insurance Record
            </button>
          )}
        </div>
      )}

      {/* Add Insurance Form */}
      {showForm && permissions.canManageInsurance && !isVisitClosed && (
        <div className="bg-gray-50 rounded-lg p-6 border border-gray-200">
          <h4 className="font-semibold text-gray-900 mb-4">Add Insurance Record</h4>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                HMO Provider *
              </label>
              <select
                value={formData.provider}
                onChange={(e) => setFormData({ ...formData, provider: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                required
              >
                <option value={0}>Select Provider</option>
                {providers.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Policy Number *
              </label>
              <input
                type="text"
                value={formData.policy_number}
                onChange={(e) => setFormData({ ...formData, policy_number: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Enter policy number"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Coverage Type *
              </label>
              <select
                value={formData.coverage_type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    coverage_type: e.target.value as 'FULL' | 'PARTIAL',
                  })
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="FULL">Full Coverage</option>
                <option value="PARTIAL">Partial Coverage</option>
              </select>
            </div>

            {formData.coverage_type === 'PARTIAL' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Coverage Percentage (1-100) *
                </label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={formData.coverage_percentage}
                  onChange={(e) =>
                    setFormData({ ...formData, coverage_percentage: parseInt(e.target.value) })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  required
                />
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
              <textarea
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                rows={3}
                placeholder="Optional notes"
              />
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleCreateInsurance}
                disabled={submitting}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-50"
              >
                {submitting ? 'Creating...' : 'Create Insurance Record'}
              </button>
              <button
                onClick={() => {
                  setShowForm(false);
                  setFormData({
                    provider: 0,
                    policy_number: '',
                    coverage_type: 'FULL',
                    coverage_percentage: 100,
                    notes: '',
                  });
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

