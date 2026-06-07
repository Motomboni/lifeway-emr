/**
 * Plan limits and subscription renewal alerts (SaaS).
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRolePermissions } from '../../hooks/useRolePermissions';
import { getSubscriptionStatus, SubscriptionStatus } from '../../api/organizations';
import styles from '../../styles/SaaSAlertsBanner.module.css';

export default function SaaSAlertsBanner() {
  const { isAdmin } = useRolePermissions();
  const navigate = useNavigate();
  const [status, setStatus] = useState<SubscriptionStatus | null>(null);

  useEffect(() => {
    if (!isAdmin) return;
    getSubscriptionStatus().then(setStatus);
  }, [isAdmin]);

  if (!isAdmin || !status?.plan) return null;

  const alerts: { type: 'warn' | 'danger' | 'info'; message: string; action?: string }[] = [];

  if (status.limits.users.at_limit) {
    alerts.push({
      type: 'danger',
      message: `Staff limit reached (${status.limits.users.current}/${status.limits.users.max}). Upgrade to add more users.`,
      action: 'Upgrade plan',
    });
  } else if (
    status.limits.users.max &&
    status.limits.users.current >= status.limits.users.max * 0.85
  ) {
    alerts.push({
      type: 'warn',
      message: `Approaching staff limit: ${status.limits.users.current}/${status.limits.users.max} users.`,
      action: 'View plans',
    });
  }

  if (status.limits.patients.at_limit) {
    alerts.push({
      type: 'danger',
      message: `Patient limit reached (${status.limits.patients.current}/${status.limits.patients.max}).`,
      action: 'Upgrade plan',
    });
  } else if (
    status.limits.patients.max &&
    status.limits.patients.current >= status.limits.patients.max * 0.85
  ) {
    alerts.push({
      type: 'warn',
      message: `Approaching patient limit: ${status.limits.patients.current}/${status.limits.patients.max}.`,
      action: 'View plans',
    });
  }

  if (
    status.days_until_renewal !== undefined &&
    status.days_until_renewal !== null &&
    status.days_until_renewal <= 7
  ) {
    alerts.push({
      type: 'info',
      message: `Subscription renews in ${status.days_until_renewal} day(s). Pay with Paystack to stay active.`,
      action: 'Renew now',
    });
  }

  if (alerts.length === 0) return null;

  return (
    <div className={styles.wrapper}>
      {alerts.map((a, i) => (
        <div key={i} className={`${styles.alert} ${styles[a.type]}`}>
          <span>{a.message}</span>
          {a.action && (
            <button
              type="button"
              className={styles.actionBtn}
              onClick={() => navigate('/plans')}
            >
              {a.action}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
