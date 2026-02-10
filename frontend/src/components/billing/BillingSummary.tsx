/**
 * Billing Summary Component
 * 
 * Displays comprehensive billing summary with real-time totals.
 */
import React from 'react';
import { formatCurrency } from '../../utils/currency';
import { BillingSummary as BillingSummaryType } from '../../api/billing';
import { Visit } from '../../types/visit';
import { Patient } from '../../types/patient';
import { BillingSummarySkeleton } from './BillingSkeleton';
import styles from './BillingSummary.module.css';

interface BillingSummaryProps {
  billingSummary: BillingSummaryType | null;
  visit: Visit;
  patient: Patient | null;
}

export default function BillingSummary({ billingSummary, visit, patient }: BillingSummaryProps) {
  if (!billingSummary) {
    return <BillingSummarySkeleton />;
  }

  // NEVER calculate totals on frontend - use backend totals only
  // Backend provides: total_payments, total_wallet_debits, outstanding_balance
  // We can safely add payments + wallet debits for display, but outstanding_balance comes from backend
  const totalPaid = parseFloat(billingSummary.total_payments) + parseFloat(billingSummary.total_wallet_debits);
  const outstandingBalance = parseFloat(billingSummary.outstanding_balance);
  const isCleared = outstandingBalance <= 0;
  const isInsuranceVisit = visit.payment_type === 'INSURANCE';
  // When SETTLED or fully covered by insurance, treat registration/consultation as paid for display
  const gatesOverride =
    billingSummary.payment_status === 'SETTLED' || billingSummary.is_fully_covered_by_insurance;
  const gates = billingSummary.payment_gates
    ? {
        ...billingSummary.payment_gates,
        ...(gatesOverride
          ? {
              registration_paid: true,
              consultation_paid: true,
              can_access_consultation: true,
              can_doctor_start_encounter: true,
            }
          : {}),
      }
    : undefined;

  return (
    <div className={styles.container} data-testid="billing-summary">
      {/* Payment gates (pre-service: Registration & Consultation must be paid before access) */}
      {gates && (
        <div className={styles.paymentGates} style={{ marginBottom: '1rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <span title="Registration must be paid before access to consultation" style={{ padding: '0.25rem 0.5rem', borderRadius: 6, fontSize: '0.875rem', background: gates.registration_paid ? '#dcfce7' : '#fef3c7', color: gates.registration_paid ? '#166534' : '#92400e' }}>
            {gates.registration_paid ? '✓ Registration paid' : '⚠ Registration unpaid'}
          </span>
          <span title="Consultation must be paid before doctor can start encounter" style={{ padding: '0.25rem 0.5rem', borderRadius: 6, fontSize: '0.875rem', background: gates.consultation_paid ? '#dcfce7' : '#fef3c7', color: gates.consultation_paid ? '#166534' : '#92400e' }}>
            {gates.consultation_paid ? '✓ Consultation paid' : '⚠ Consultation unpaid'}
          </span>
        </div>
      )}
      {/* Key Metrics Grid */}
      <div className={styles.metricsGrid}>
        {/* Total Charges */}
        <div className={`${styles.metricCard} ${styles.metricCardBlue}`}>
          <div className={styles.metricContent}>
            <p className={`${styles.metricLabel} ${styles.metricLabelBlue}`}>Total Charges</p>
            <p className={`${styles.metricValue} ${styles.metricValueBlue}`} data-testid="total-charges">
              {formatCurrency(billingSummary.total_charges)}
            </p>
          </div>
          <div className={styles.metricIcon}>💰</div>
        </div>

        {/* Retainership Discount */}
        {billingSummary.has_retainership && parseFloat(billingSummary.retainership_discount) > 0 && (
          <div className={`${styles.metricCard} ${styles.metricCardOrange}`}>
            <div className={styles.metricContent}>
              <p className={`${styles.metricLabel} ${styles.metricLabelOrange}`}>Retainership Discount</p>
              <p className={`${styles.metricValue} ${styles.metricValueOrange}`}>
                -{formatCurrency(billingSummary.retainership_discount)}
              </p>
              <p className={`${styles.metricSubtext} ${styles.metricSubtextOrange}`}>
                {parseFloat(billingSummary.retainership_discount_percentage).toFixed(1)}% off
              </p>
            </div>
            <div className={styles.metricIcon}>🎫</div>
          </div>
        )}

        {/* Insurance Coverage */}
        {billingSummary.has_insurance && (
          <div className={`${styles.metricCard} ${styles.metricCardGreen}`}>
            <div className={styles.metricContent}>
              <p className={`${styles.metricLabel} ${styles.metricLabelGreen}`}>Insurance Coverage</p>
              <p className={`${styles.metricValue} ${styles.metricValueGreen}`}>
                {formatCurrency(billingSummary.insurance_amount)}
              </p>
              {billingSummary.is_fully_covered_by_insurance && (
                <p className={`${styles.metricSubtext} ${styles.metricSubtextGreen}`}>Fully Covered</p>
              )}
            </div>
            <div className={styles.metricIcon}>🏥</div>
          </div>
        )}

        {/* Patient Payable */}
        <div className={`${styles.metricCard} ${styles.metricCardPurple}`}>
          <div className={styles.metricContent}>
            <p className={`${styles.metricLabel} ${styles.metricLabelPurple}`}>Patient Payable</p>
            <p className={`${styles.metricValue} ${styles.metricValuePurple}`}>
              {formatCurrency(billingSummary.patient_payable)}
            </p>
          </div>
          <div className={styles.metricIcon}>👤</div>
        </div>

        {/* Total Paid */}
        <div className={`${styles.metricCard} ${styles.metricCardEmerald}`}>
          <div className={styles.metricContent}>
            <p className={`${styles.metricLabel} ${styles.metricLabelEmerald}`}>Total Paid</p>
            <p className={`${styles.metricValue} ${styles.metricValueEmerald}`}>
              {formatCurrency(totalPaid.toString())}
            </p>
          </div>
          <div className={styles.metricIcon}>✅</div>
        </div>
      </div>

      {/* Outstanding Balance Card */}
      <div
        className={`
          ${styles.outstandingCard}
          ${
            isCleared
              ? styles.outstandingCardCleared
              : outstandingBalance > 0
              ? styles.outstandingCardPending
              : isInsuranceVisit
              ? styles.outstandingCardInsurance
              : styles.outstandingCardPending
          }
        `}
      >
        <div className={styles.outstandingHeader}>
          <div>
            <p
              className={`
                ${styles.outstandingTitle}
                ${
                  isCleared
                    ? styles.outstandingTitleCleared
                    : outstandingBalance > 0
                    ? styles.outstandingTitlePending
                    : styles.outstandingTitleInsurance
                }
              `}
            >
              Outstanding Balance
            </p>
            <p
              className={`
                ${styles.outstandingAmount}
                ${
                  isCleared
                    ? styles.outstandingAmountCleared
                    : outstandingBalance > 0
                    ? styles.outstandingAmountPending
                    : styles.outstandingAmountInsurance
                }
              `}
              data-testid="outstanding-balance"
            >
              {formatCurrency(billingSummary.outstanding_balance)}
            </p>
            <p
              className={`
                ${styles.statusInfoText}
                ${
                  isCleared
                    ? styles.statusInfoTextCleared
                    : outstandingBalance > 0
                    ? styles.statusInfoTextPending
                    : styles.statusInfoTextInsurance
                }
              `}
              style={{ marginTop: '0.5rem' }}
            >
              Status: <span style={{ fontWeight: 500 }} data-testid="payment-status">{billingSummary.payment_status}</span>
            </p>
          </div>
          <div className={styles.outstandingIcon}>
            {isCleared ? '✅' : outstandingBalance > 0 ? '⚠️' : 'ℹ️'}
          </div>
        </div>
      </div>

      {/* Payment Breakdown */}
      <div style={{ background: '#f9fafb', borderRadius: '8px', padding: '1.5rem' }}>
        <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#111827', marginBottom: '1rem', margin: '0 0 1rem 0' }}>
          Payment Breakdown
        </h3>
        <div className={styles.paymentStatusGrid}>
          <div className={styles.paymentStatusItem}>
            <span className={styles.paymentStatusLabel}>Cash/Card/Transfer:</span>
            <span className={styles.paymentStatusValue}>
              {formatCurrency(billingSummary.total_payments)}
            </span>
          </div>
          <div className={styles.paymentStatusItem}>
            <span className={styles.paymentStatusLabel}>Wallet Payments:</span>
            <span className={styles.paymentStatusValue}>
              {formatCurrency(billingSummary.total_wallet_debits)}
            </span>
          </div>
        </div>
        <div style={{ borderTop: '1px solid #d1d5db', paddingTop: '0.75rem', marginTop: '0.75rem' }}>
          <div className={styles.paymentStatusItem}>
            <span style={{ fontWeight: 600, color: '#111827' }}>Total Paid:</span>
            <span style={{ fontWeight: 700, fontSize: '1.125rem', color: '#111827' }}>
              {formatCurrency(totalPaid.toString())}
            </span>
          </div>
        </div>
      </div>

      {/* Insurance Information */}
      {billingSummary.has_insurance && (
        <div style={{ background: '#eff6ff', borderRadius: '8px', padding: '1.5rem', border: '1px solid #dbeafe' }}>
          <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#1e3a8a', marginBottom: '1rem', margin: '0 0 1rem 0' }}>
            Insurance Information
          </h3>
          <div className={styles.paymentStatusGrid}>
            <div className={styles.paymentStatusItem}>
              <span style={{ color: '#1e40af' }}>Status:</span>
              <span style={{ fontWeight: 500, color: '#1e3a8a' }}>{billingSummary.insurance_status || 'Pending'}</span>
            </div>
            <div className={styles.paymentStatusItem}>
              <span style={{ color: '#1e40af' }}>Coverage Type:</span>
              <span style={{ fontWeight: 500, color: '#1e3a8a' }}>
                {billingSummary.insurance_coverage_type || 'Full'}
              </span>
            </div>
            <div className={styles.paymentStatusItem}>
              <span style={{ color: '#1e40af' }}>Covered Amount:</span>
              <span style={{ fontWeight: 500, color: '#1e3a8a' }}>
                {formatCurrency(billingSummary.insurance_amount)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Visit Information */}
      <div style={{ background: '#f9fafb', borderRadius: '8px', padding: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', fontSize: '0.875rem' }}>
          <div>
            <span style={{ color: '#6b7280' }}>Visit Type:</span>
            <span style={{ marginLeft: '0.5rem', fontWeight: 500, color: '#111827' }}>
              {isInsuranceVisit ? 'Insurance/HMO' : 'Cash Payment'}
            </span>
          </div>
          <div>
            <span style={{ color: '#6b7280' }}>Visit Status:</span>
            <span style={{ marginLeft: '0.5rem', fontWeight: 500, color: '#111827' }}>{visit.status}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

