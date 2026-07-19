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
  const gates = billingSummary.payment_gates;

  return (
    <div className={styles.container} data-testid="billing-summary">
      {/* Payment gates: registration required before encounter; consultation fee tracked separately */}
      {gates && (
        <div className={styles.paymentGates}>
          <span
            title="Registration must be paid before access to consultation"
            className={`${styles.gateBadge} ${gates.registration_paid ? styles.gateBadgePaid : styles.gateBadgeUnpaid}`}
          >
            {gates.registration_paid ? '✓ Registration paid' : '⚠ Registration unpaid'}
          </span>
          <span
            title="Consultation service fee (may be collected during or after the visit)"
            className={`${styles.gateBadge} ${gates.consultation_paid ? styles.gateBadgePaid : styles.gateBadgeUnpaid}`}
          >
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
              Status: <span className={styles.statusInfoValue} data-testid="payment-status">{billingSummary.payment_status}</span>
            </p>
          </div>
          <div className={styles.outstandingIcon}>
            {isCleared ? '✅' : outstandingBalance > 0 ? '⚠️' : 'ℹ️'}
          </div>
        </div>
      </div>

      {/* Payment Breakdown */}
      <div className={styles.breakdownPanel}>
        <h3 className={styles.breakdownTitle}>Payment Breakdown</h3>
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
        <div className={styles.breakdownTotalRow}>
          <div className={styles.paymentStatusItem}>
            <span className={styles.breakdownTotalLabel}>Total Paid:</span>
            <span className={styles.breakdownTotalValue}>
              {formatCurrency(totalPaid.toString())}
            </span>
          </div>
        </div>
      </div>

      {/* Insurance Information */}
      {billingSummary.has_insurance && (
        <div className={styles.insurancePanel}>
          <h3 className={styles.insurancePanelTitle}>Insurance Information</h3>
          <div className={styles.paymentStatusGrid}>
            <div className={styles.paymentStatusItem}>
              <span className={styles.insurancePanelLabel}>Status:</span>
              <span className={styles.insurancePanelValue}>{billingSummary.insurance_status || 'Pending'}</span>
            </div>
            <div className={styles.paymentStatusItem}>
              <span className={styles.insurancePanelLabel}>Coverage Type:</span>
              <span className={styles.insurancePanelValue}>
                {billingSummary.insurance_coverage_type || 'Full'}
              </span>
            </div>
            <div className={styles.paymentStatusItem}>
              <span className={styles.insurancePanelLabel}>Covered Amount:</span>
              <span className={styles.insurancePanelValue}>
                {formatCurrency(billingSummary.insurance_amount)}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Visit Information */}
      <div className={styles.visitInfoPanel}>
        <div className={styles.visitInfoGrid}>
          <div>
            <span className={styles.visitInfoLabel}>Visit Type:</span>
            <span className={styles.visitInfoValue}>
              {isInsuranceVisit ? 'Insurance/HMO' : 'Cash Payment'}
            </span>
          </div>
          <div>
            <span className={styles.visitInfoLabel}>Visit Status:</span>
            <span className={styles.visitInfoValue}>{visit.status}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

