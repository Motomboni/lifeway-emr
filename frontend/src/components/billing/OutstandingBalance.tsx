/**
 * Outstanding Balance Component
 * 
 * Displays outstanding balance with clear visual indicators.
 */
import React from 'react';
import { formatCurrency } from '../../utils/currency';
import styles from './OutstandingBalance.module.css';

interface OutstandingBalanceProps {
  outstandingBalance: string;
  paymentStatus: string;
  visitStatus: string;
}

export default function OutstandingBalance({
  outstandingBalance,
  paymentStatus,
  visitStatus,
}: OutstandingBalanceProps) {
  const balance = parseFloat(outstandingBalance);
  const isCleared = balance <= 0;
  const isVisitClosed = visitStatus === 'CLOSED';

  if (isCleared) {
    return (
      <div className={`${styles.container} ${styles.containerCleared}`}>
        <div className={styles.content}>
          <div>
            <p className={`${styles.label} ${styles.labelCleared}`}>Payment Status</p>
            <p className={`${styles.amount} ${styles.amountCleared}`} style={{ fontSize: '1.25rem', marginTop: '0.25rem' }}>
              Fully Paid
            </p>
          </div>
          <span className={styles.icon}>✅</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.container} ${styles.containerPending}`}>
      <div className={styles.content}>
        <div className={styles.left}>
          <p className={`${styles.label} ${styles.labelPending}`}>Outstanding Balance</p>
          <p className={`${styles.amount} ${styles.amountPending}`}>
            {formatCurrency(outstandingBalance)}
          </p>
          <p className={`${styles.statusText} ${styles.statusTextPending}`}>
            Status: <span className={styles.statusValue}>{paymentStatus}</span>
            {isVisitClosed && (
              <span className={styles.visitClosedBadge}>
                Visit Closed
              </span>
            )}
          </p>
        </div>
        <span className={styles.icon}>⚠️</span>
      </div>
      {!isVisitClosed && (
        <div className={`${styles.warningSection} ${styles.warningSectionPending}`}>
          <p className={styles.warningText}>
            Please process payment before closing this visit.
          </p>
        </div>
      )}
    </div>
  );
}

