/**
 * Read-only list of visit charges (catalog + misc) for clinical roles.
 * Mirrors receptionist Charges Breakdown data without add/payment controls.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { getVisitCharges, VisitCharge } from '../../api/billing';
import { formatCurrency } from '../../utils/currency';
import { useToast } from '../../hooks/useToast';
import { useBillingPermissions } from '../../hooks/useBillingPermissions';
import styles from './ChargesBreakdown.module.css';

const DEPARTMENT_LABELS: Record<string, string> = {
  CONSULTATION: 'Consultation',
  LAB: 'Laboratory',
  RADIOLOGY: 'Radiology',
  DRUG: 'Pharmacy',
  PROCEDURE: 'Procedures',
  MISC: 'Miscellaneous',
};

const DEPARTMENT_ICONS: Record<string, string> = {
  CONSULTATION: '🩺',
  LAB: '🧪',
  RADIOLOGY: '📷',
  DRUG: '💊',
  PROCEDURE: '⚕️',
  MISC: '📋',
};

export interface VisitChargesReadOnlyProps {
  visitId: number;
  /** When set, display these rows (e.g. Visit Details page already loaded charges). */
  charges?: VisitCharge[] | null;
  /** Increment to refetch when using internal fetch (Consultation workspace). */
  refreshTrigger?: number;
  /** Optional title override */
  title?: string;
  /** When true, show line-item amounts (default: receptionist only). */
  showAmounts?: boolean;
  /** When true, skip outer panel chrome (parent card e.g. consultation inlineComponent). */
  embedded?: boolean;
}

export default function VisitChargesReadOnly({
  visitId,
  charges: chargesFromParent,
  refreshTrigger = 0,
  title,
  showAmounts: showAmountsProp,
  embedded = false,
}: VisitChargesReadOnlyProps) {
  const { showError } = useToast();
  const { canViewChargeAmounts } = useBillingPermissions();
  const showAmounts = showAmountsProp ?? canViewChargeAmounts;
  const panelTitle = title ?? (showAmounts ? 'Ordered services & charges' : 'Ordered services');
  const [charges, setCharges] = useState<VisitCharge[]>(chargesFromParent ?? []);
  const [loading, setLoading] = useState(chargesFromParent === undefined || chargesFromParent === null);

  useEffect(() => {
    if (chargesFromParent !== undefined && chargesFromParent !== null) {
      setCharges(chargesFromParent);
      setLoading(false);
      return;
    }

    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await getVisitCharges(visitId);
        if (!cancelled) setCharges(data);
      } catch {
        if (!cancelled) showError('Failed to load ordered services for this visit');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [visitId, refreshTrigger, chargesFromParent, showError]);

  const groupedCharges = useMemo(() => {
    return charges.reduce((acc: Record<string, VisitCharge[]>, charge: VisitCharge) => {
      const dept = charge.category;
      if (!acc[dept]) acc[dept] = [];
      acc[dept].push(charge);
      return acc;
    }, {});
  }, [charges]);

  const totalCharges = useMemo(
    () => charges.reduce((sum, c) => sum + parseFloat(String(c.amount)), 0),
    [charges]
  );

  const panelClass = embedded
    ? `${styles.readOnlyPanel} ${styles.readOnlyPanelEmbedded}`
    : styles.readOnlyPanel;

  if (loading) {
    return (
      <div className={`${styles.container} ${panelClass}`}>
        <div className={styles.header}>
          <h3 className={styles.headerTitle}>{panelTitle}</h3>
          <p className={styles.headerSubtitle}>Loading…</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${styles.container} ${panelClass}`}>
      <div className={styles.header}>
        <div>
          <h3 className={styles.headerTitle}>{panelTitle}</h3>
          <p className={styles.headerSubtitle}>
            {showAmounts ? (
              <>
                Same line items as on the patient account / reception billing. Total:{' '}
                <span className={styles.headerSubtitleAmount}>
                  {formatCurrency(totalCharges.toString())}
                </span>
              </>
            ) : (
              'Services ordered for this visit (amounts visible to reception only).'
            )}
          </p>
        </div>
      </div>

      {Object.keys(groupedCharges).length === 0 ? (
        <div className={styles.emptyState}>
          <p className={styles.emptyStateText}>
            No catalog or misc charges yet for this visit. Use Search & Order Service above to add items.
          </p>
        </div>
      ) : (
        <div className={styles.chargesList}>
          {Object.entries(groupedCharges).map(([department, deptCharges]) => {
            const chargesArray = deptCharges as VisitCharge[];
            const deptTotal = chargesArray.reduce(
              (sum, c) => sum + parseFloat(String(c.amount)),
              0
            );
            return (
              <div key={department} className={styles.departmentGroup}>
                <div className={styles.departmentHeader}>
                  <div className={styles.departmentHeaderLeft}>
                    <span className={styles.departmentIcon}>{DEPARTMENT_ICONS[department] || '📋'}</span>
                    <h4 className={styles.departmentName}>
                      {DEPARTMENT_LABELS[department] || department}
                    </h4>
                    <span className={styles.departmentCount}>
                      ({chargesArray.length} {chargesArray.length === 1 ? 'item' : 'items'})
                    </span>
                  </div>
                  {showAmounts && (
                    <span className={styles.departmentTotal}>
                      {formatCurrency(deptTotal.toString())}
                    </span>
                  )}
                </div>
                <div className={styles.chargesItems}>
                  {chargesArray.map((charge) => (
                    <div key={String(charge.id)} className={styles.chargeItem}>
                      <div className={styles.chargeContent}>
                        <div className={styles.chargeLeft}>
                          <p className={styles.chargeDescription}>{charge.description}</p>
                          <div className={styles.chargeMeta}>
                            <span className={styles.chargeDate}>
                              {new Date(charge.created_at).toLocaleDateString('en-NG', {
                                year: 'numeric',
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </span>
                            {charge.created_by_system && (
                              <span className={styles.systemBadge}>System / catalog</span>
                            )}
                          </div>
                        </div>
                        {showAmounts && (
                          <div className={styles.chargeAmount}>{formatCurrency(charge.amount)}</div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showAmounts && charges.length > 0 && (
        <div className={styles.totalSummary}>
          <div className={styles.totalSummaryContent}>
            <span className={styles.totalSummaryLabel}>Total charges</span>
            <span className={styles.totalSummaryAmount}>{formatCurrency(totalCharges.toString())}</span>
          </div>
        </div>
      )}
    </div>
  );
}
