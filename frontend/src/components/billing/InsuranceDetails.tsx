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
import styles from './InsuranceDetails.module.css';

interface InsuranceDetailsProps {
  visitId: number;
  visit: Visit;
  billingSummary: BillingSummary | null;
  permissions: BillingPermissions;
  onUpdate: () => void;
}

const EMPTY_FORM: InsuranceCreateData = {
  provider: 0,
  policy_number: '',
  coverage_type: 'FULL',
  coverage_percentage: 100,
  notes: '',
  billing_scheme: 'FEE_FOR_SERVICE',
  employer_name: '',
  pre_auth_status: 'NOT_REQUIRED',
};

function statusBadgeClass(status?: string) {
  if (status === 'APPROVED') return styles.statusApproved;
  if (status === 'REJECTED') return styles.statusRejected;
  return styles.statusPending;
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
  const [formData, setFormData] = useState<InsuranceCreateData>(EMPTY_FORM);

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
    } catch {
      showError('Failed to load insurance information');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData(EMPTY_FORM);
    setShowForm(false);
  };

  const handleCreateInsurance = async () => {
    if (!formData.provider || !formData.policy_number) {
      showError('Please select provider and enter policy number');
      return;
    }

    if (
      formData.coverage_type === 'PARTIAL' &&
      (!formData.coverage_percentage ||
        formData.coverage_percentage <= 0 ||
        formData.coverage_percentage > 100)
    ) {
      showError('Please enter a valid coverage percentage (1-100)');
      return;
    }

    try {
      setSubmitting(true);
      await createInsurance(visitId, {
        ...formData,
        coverage_percentage:
          formData.coverage_type === 'FULL' ? 100 : formData.coverage_percentage,
      });
      showSuccess('Insurance record created successfully');
      resetForm();
      await loadData();
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to create insurance record');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveInsurance = async () => {
    if (!insurance?.id) return;

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
    if (!insurance?.id) return;

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

  const handlePreAuthAction = async (
    status: 'NOT_REQUIRED' | 'PENDING' | 'APPROVED' | 'REJECTED',
    extra?: { pre_auth_number?: string; pre_auth_notes?: string },
  ) => {
    if (!insurance?.id) return;
    try {
      setSubmitting(true);
      await updateInsurance(visitId, insurance.id, {
        pre_auth_status: status,
        ...extra,
      });
      showSuccess('Pre-authorization updated');
      await loadData();
      onUpdate();
    } catch (error: any) {
      showError(error.message || 'Failed to update pre-authorization');
    } finally {
      setSubmitting(false);
    }
  };

  const handleRequestPreAuth = () => handlePreAuthAction('PENDING');

  const handleApprovePreAuth = () => {
    const ref = prompt('Enter pre-authorization reference number:');
    if (!ref?.trim()) return;
    handlePreAuthAction('APPROVED', { pre_auth_number: ref.trim() });
  };

  const handleDenyPreAuth = () => {
    const notes = prompt('Enter denial reason:');
    if (!notes?.trim()) return;
    handlePreAuthAction('REJECTED', { pre_auth_notes: notes.trim() });
  };

  if (loading) {
    return <LoadingSpinner message="Loading insurance information..." />;
  }

  const isVisitClosed = visit.status === 'CLOSED';
  const canManage = permissions.canManageInsurance && !isVisitClosed;

  return (
    <div className={styles.container}>
      {insurance ? (
        <div className={styles.infoPanel}>
          <div className={styles.infoHeader}>
            <h3 className={styles.infoTitle}>Insurance Information</h3>
            {insurance.approval_status === 'PENDING' && canManage && (
              <div className={styles.infoActions}>
                <button
                  type="button"
                  onClick={handleApproveInsurance}
                  disabled={submitting}
                  className={styles.approveButton}
                >
                  Approve
                </button>
                <button
                  type="button"
                  onClick={handleRejectInsurance}
                  disabled={submitting}
                  className={styles.rejectButton}
                >
                  Reject
                </button>
              </div>
            )}
          </div>

          <div className={styles.infoGrid}>
            <div>
              <p className={styles.infoFieldLabel}>Provider</p>
              <p className={styles.infoFieldValue}>{insurance.hmo_provider?.name || 'N/A'}</p>
            </div>
            <div>
              <p className={styles.infoFieldLabel}>Policy Number</p>
              <p className={styles.infoFieldValue}>{insurance.insurance_number || 'N/A'}</p>
            </div>
            <div>
              <p className={styles.infoFieldLabel}>Coverage Type</p>
              <p className={styles.infoFieldValue}>{insurance.coverage_type || 'FULL'}</p>
            </div>
            <div>
              <p className={styles.infoFieldLabel}>Coverage Percentage</p>
              <p className={styles.infoFieldValue}>{insurance.coverage_percentage || 100}%</p>
            </div>
            <div>
              <p className={styles.infoFieldLabel}>Status</p>
              <span className={`${styles.statusBadge} ${statusBadgeClass(insurance.approval_status)}`}>
                {insurance.approval_status || 'PENDING'}
              </span>
            </div>
            {insurance.approved_amount && (
              <div>
                <p className={styles.infoFieldLabel}>Approved Amount</p>
                <p className={styles.infoFieldValue}>{formatCurrency(insurance.approved_amount)}</p>
              </div>
            )}
          </div>

          {billingSummary?.has_insurance && (
            <div className={styles.infoDivider}>
              <div className={styles.infoCoverageRow}>
                <span className={styles.infoFieldLabel}>Insurance Coverage</span>
                <span className={styles.infoCoverageAmount}>
                  {formatCurrency(billingSummary.insurance_amount)}
                </span>
              </div>
            </div>
          )}

          <div className={styles.infoDivider}>
            <h4 className={styles.sectionTitle}>HMO Pre-Authorization</h4>
            <div className={styles.infoGrid}>
              <div>
                <p className={styles.infoFieldLabel}>Billing Scheme</p>
                <p className={styles.infoFieldValue}>
                  {(insurance.billing_scheme || 'FEE_FOR_SERVICE').replace(/_/g, ' ')}
                </p>
              </div>
              {insurance.employer_name && (
                <div>
                  <p className={styles.infoFieldLabel}>Employer / Retainer</p>
                  <p className={styles.infoFieldValue}>{insurance.employer_name}</p>
                </div>
              )}
              <div>
                <p className={styles.infoFieldLabel}>Pre-Auth Status</p>
                <span className={`${styles.statusBadge} ${styles.statusPending}`}>
                  {insurance.pre_auth_status || 'NOT_REQUIRED'}
                </span>
              </div>
              {insurance.pre_auth_number && (
                <div>
                  <p className={styles.infoFieldLabel}>Pre-Auth Reference</p>
                  <p className={styles.infoFieldValue}>{insurance.pre_auth_number}</p>
                </div>
              )}
            </div>
            {canManage && (
              <div className={styles.preAuthActions}>
                {['NOT_REQUIRED', 'PENDING'].includes(insurance.pre_auth_status || 'NOT_REQUIRED') && (
                  <button
                    type="button"
                    onClick={handleRequestPreAuth}
                    disabled={submitting}
                    className={styles.preAuthButton}
                  >
                    Request Pre-Auth
                  </button>
                )}
                {insurance.pre_auth_status === 'PENDING' && (
                  <>
                    <button
                      type="button"
                      onClick={handleApprovePreAuth}
                      disabled={submitting}
                      className={styles.approveButton}
                    >
                      Approve Pre-Auth
                    </button>
                    <button
                      type="button"
                      onClick={handleDenyPreAuth}
                      disabled={submitting}
                      className={styles.rejectButton}
                    >
                      Deny Pre-Auth
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      ) : showForm && canManage ? (
        <InsuranceForm
          formData={formData}
          setFormData={setFormData}
          providers={providers}
          submitting={submitting}
          onSubmit={handleCreateInsurance}
          onCancel={resetForm}
        />
      ) : (
        <div className={styles.emptyState}>
          <p className={styles.emptyText}>No insurance record found for this visit</p>
          {canManage && (
            <button
              type="button"
              onClick={() => setShowForm(true)}
              className={styles.primaryButton}
            >
              Add Insurance Record
            </button>
          )}
        </div>
      )}
    </div>
  );
}

interface InsuranceFormProps {
  formData: InsuranceCreateData;
  setFormData: React.Dispatch<React.SetStateAction<InsuranceCreateData>>;
  providers: any[];
  submitting: boolean;
  onSubmit: () => void;
  onCancel: () => void;
}

function InsuranceForm({
  formData,
  setFormData,
  providers,
  submitting,
  onSubmit,
  onCancel,
}: InsuranceFormProps) {
  return (
    <div className={styles.formPanel}>
      <h4 className={styles.formTitle}>Add Insurance Record</h4>
      <div className={styles.formFields}>
        <div className={styles.formGroup}>
          <label className={styles.formLabel} htmlFor="insurance-provider">
            HMO Provider *
          </label>
          <select
            id="insurance-provider"
            value={formData.provider}
            onChange={(e) => setFormData({ ...formData, provider: parseInt(e.target.value, 10) })}
            className={styles.formSelect}
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

        <div className={styles.formGroup}>
          <label className={styles.formLabel} htmlFor="insurance-policy">
            Policy Number *
          </label>
          <input
            id="insurance-policy"
            type="text"
            value={formData.policy_number}
            onChange={(e) => setFormData({ ...formData, policy_number: e.target.value })}
            className={styles.formInput}
            placeholder="Enter policy number"
            required
          />
        </div>

        <div className={styles.formGroup}>
          <label className={styles.formLabel} htmlFor="insurance-coverage-type">
            Coverage Type *
          </label>
          <select
            id="insurance-coverage-type"
            value={formData.coverage_type}
            onChange={(e) =>
              setFormData({
                ...formData,
                coverage_type: e.target.value as 'FULL' | 'PARTIAL',
              })
            }
            className={styles.formSelect}
          >
            <option value="FULL">Full Coverage</option>
            <option value="PARTIAL">Partial Coverage</option>
          </select>
        </div>

        {formData.coverage_type === 'PARTIAL' && (
          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="insurance-coverage-pct">
              Coverage Percentage (1-100) *
            </label>
            <input
              id="insurance-coverage-pct"
              type="number"
              min={1}
              max={100}
              value={formData.coverage_percentage}
              onChange={(e) =>
                setFormData({ ...formData, coverage_percentage: parseInt(e.target.value, 10) })
              }
              className={styles.formInput}
              required
            />
          </div>
        )}

        <div className={styles.formGroup}>
          <label className={styles.formLabel} htmlFor="insurance-notes">
            Notes
          </label>
          <textarea
            id="insurance-notes"
            value={formData.notes}
            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
            className={styles.formTextarea}
            rows={3}
            placeholder="Optional notes"
          />
        </div>

        <div className={styles.formGroup}>
          <label className={styles.formLabel} htmlFor="insurance-billing-scheme">
            Billing Scheme
          </label>
          <select
            id="insurance-billing-scheme"
            value={formData.billing_scheme || 'FEE_FOR_SERVICE'}
            onChange={(e) =>
              setFormData({
                ...formData,
                billing_scheme: e.target.value as InsuranceCreateData['billing_scheme'],
              })
            }
            className={styles.formSelect}
          >
            <option value="FEE_FOR_SERVICE">Fee for Service</option>
            <option value="CAPITATION">Capitation</option>
            <option value="RETAINER">Corporate Retainer</option>
          </select>
        </div>

        {(formData.billing_scheme === 'RETAINER' || formData.billing_scheme === 'CAPITATION') && (
          <div className={styles.formGroup}>
            <label className={styles.formLabel} htmlFor="insurance-employer">
              Employer / Organization
            </label>
            <input
              id="insurance-employer"
              type="text"
              value={formData.employer_name || ''}
              onChange={(e) => setFormData({ ...formData, employer_name: e.target.value })}
              className={styles.formInput}
              placeholder="Employer or retainer organization"
            />
          </div>
        )}

        <div className={styles.formGroup}>
          <label className={styles.formLabel} htmlFor="insurance-pre-auth">
            Pre-Auth Required?
          </label>
          <select
            id="insurance-pre-auth"
            value={formData.pre_auth_status || 'NOT_REQUIRED'}
            onChange={(e) =>
              setFormData({
                ...formData,
                pre_auth_status: e.target.value as InsuranceCreateData['pre_auth_status'],
              })
            }
            className={styles.formSelect}
          >
            <option value="NOT_REQUIRED">Not Required</option>
            <option value="PENDING">Required — Pending</option>
          </select>
        </div>

        <div className={styles.formActions}>
          <button
            type="button"
            onClick={onSubmit}
            disabled={submitting}
            className={styles.primaryButton}
          >
            {submitting ? 'Creating...' : 'Create Insurance Record'}
          </button>
          <button type="button" onClick={onCancel} className={styles.secondaryButton}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
