/**
 * Billing Dashboard Component
 * 
 * Main container for visit-scoped billing operations.
 * Per EMR Rules: Receptionist-only access, visit-scoped, real-time totals.
 */
import React, { useState } from 'react';
import { useBillingPermissions } from '../../hooks/useBillingPermissions';
import BillingSummary from './BillingSummary';
import ChargesBreakdown from './ChargesBreakdown';
import PaymentOptions from './PaymentOptions';
import InsuranceDetails from './InsuranceDetails';
import WalletBalanceCard from './WalletBalanceCard';
import OutstandingBalance from './OutstandingBalance';
import BillingErrorBoundary from './BillingErrorBoundary';
import { BillingDashboardSkeleton } from './BillingSkeleton';
import { Visit } from '../../types/visit';
import { Patient } from '../../types/patient';
import { BillingSummary as BillingSummaryType } from '../../api/billing';
import styles from './BillingDashboard.module.css';

interface BillingDashboardProps {
  visitId: number;
  visit: Visit;
  patient: Patient | null;
  billingSummary: BillingSummaryType | null;
  onBillingUpdate: () => void;
}

type TabType = 'summary' | 'charges' | 'payments' | 'insurance' | 'wallet';

export default function BillingDashboard({
  visitId,
  visit,
  patient,
  billingSummary,
  onBillingUpdate,
}: BillingDashboardProps) {
  const permissions = useBillingPermissions();
  const [activeTab, setActiveTab] = useState<TabType>('summary');

  // Guard: Only Receptionist can view billing
  if (!permissions.canViewBilling) {
    return (
      <div className={styles.permissionMessage}>
        <p className={styles.permissionText}>Billing information is only available to Receptionist and Admin.</p>
      </div>
    );
  }

  // Show loading skeleton if no billing summary
  if (!billingSummary) {
    return <BillingDashboardSkeleton />;
  }

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: 'summary', label: 'Summary', icon: '📊' },
    { id: 'charges', label: 'Charges', icon: '💰' },
    { id: 'payments', label: 'Payments', icon: '💳' },
    { id: 'insurance', label: 'Insurance', icon: '🏥' },
    { id: 'wallet', label: 'Wallet', icon: '💼' },
  ];

  return (
    <div className={styles.dashboard}>
      {/* Header */}
      <div className={styles.header}>
        <div className={styles.headerContent}>
          <div>
            <h2 className={styles.headerTitle}>Billing & Payments</h2>
            <p className={styles.headerSubtitle}>
              Visit #{visitId} • {patient ? `${patient.first_name} ${patient.last_name}` : 'Loading...'}
            </p>
          </div>
          {visit.status === 'CLOSED' && (
            <span className={styles.visitClosedBadge}>
              Visit Closed
            </span>
          )}
        </div>
      </div>

      {/* Outstanding Balance Alert */}
      {billingSummary && parseFloat(billingSummary.outstanding_balance) > 0 && (
        <div className={styles.outstandingBalanceContainer}>
          <OutstandingBalance
            outstandingBalance={billingSummary.outstanding_balance}
            paymentStatus={billingSummary.payment_status}
            visitStatus={visit.status}
          />
        </div>
      )}

      {/* Tabs */}
      <div className={styles.tabsContainer}>
        <nav className={styles.tabs} aria-label="Billing tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ''}`}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              <span className={styles.tabIcon}>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className={styles.tabContent}>
        <BillingErrorBoundary>
          {activeTab === 'summary' && (
            <BillingSummary
              billingSummary={billingSummary}
              visit={visit}
              patient={patient}
            />
          )}

          {activeTab === 'charges' && (
            <ChargesBreakdown
              visitId={visitId}
              visit={visit}
              permissions={permissions}
              onUpdate={onBillingUpdate}
            />
          )}

          {activeTab === 'payments' && (
            <PaymentOptions
              visitId={visitId}
              visit={visit}
              billingSummary={billingSummary}
              permissions={permissions}
              onUpdate={onBillingUpdate}
            />
          )}

          {activeTab === 'insurance' && (
            <InsuranceDetails
              visitId={visitId}
              visit={visit}
              billingSummary={billingSummary}
              permissions={permissions}
              onUpdate={onBillingUpdate}
            />
          )}

          {activeTab === 'wallet' && (
            <WalletBalanceCard
              visitId={visitId}
              patient={patient}
              billingSummary={billingSummary}
              permissions={permissions}
              onUpdate={onBillingUpdate}
            />
          )}
        </BillingErrorBoundary>
      </div>
    </div>
  );
}

