/**
 * Tenant Switcher - Multi-tenant organization selector
 *
 * Shows current organization and allows switching when user belongs to multiple orgs.
 */
import React, { useState, useEffect, useRef } from 'react';
import {
  getOrganizationMemberships,
  setDefaultOrganization,
  getSubscriptionStatus,
  createCheckoutSession,
  type OrganizationMembership,
  type SubscriptionStatus,
} from '../../api/organizations';
import { setOrganizationId, getOrganizationId } from '../../utils/apiClient';
import styles from '../../styles/TenantSwitcher.module.css';

interface TenantSwitcherProps {
  /** Compact mode for smaller headers */
  compact?: boolean;
  className?: string;
}

export default function TenantSwitcher({ compact = false, className = '' }: TenantSwitcherProps) {
  const [memberships, setMemberships] = useState<OrganizationMembership[]>([]);
  const [currentOrgId, setCurrentOrgId] = useState<number | null>(null);
  const [subscriptionStatus, setSubscriptionStatus] = useState<SubscriptionStatus | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [list, status] = await Promise.all([
          getOrganizationMemberships(),
          getSubscriptionStatus(),
        ]);
        setMemberships(list);
        setCurrentOrgId(getOrganizationId());
        setSubscriptionStatus(status);
      } catch {
        setMemberships([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleUpgrade = async () => {
    setCheckoutLoading(true);
    try {
      const base = window.location.origin;
      const res = await createCheckoutSession({
        plan_slug: 'professional',
        success_url: `${base}/dashboard?upgraded=1`,
        cancel_url: `${base}/dashboard`,
      });
      if (res?.checkout_url) {
        window.location.href = res.checkout_url;
      }
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleSwitch = async (membership: OrganizationMembership) => {
    const orgId = membership.organization.id;
    setOrganizationId(orgId);
    setCurrentOrgId(orgId);
    setIsOpen(false);
    try {
      await setDefaultOrganization(orgId);
    } catch {
      // Still switched locally; backend may sync on next login
    }
    window.location.reload();
  };

  const usageTooltip = subscriptionStatus?.plan
    ? `${subscriptionStatus.plan.name} • ${subscriptionStatus.usage.patients}/${subscriptionStatus.limits.patients.max ?? '∞'} patients • ${subscriptionStatus.usage.users}/${subscriptionStatus.limits.users.max ?? '∞'} users`
    : '';

  if (loading || memberships.length === 0) return null;
  if (memberships.length === 1) {
    const m = memberships[0];
    return (
      <span
        className={`${styles.badge} ${compact ? styles.compact : ''} ${className}`}
        title={usageTooltip || m.organization.name}
      >
        {m.organization.name}
      </span>
    );
  }

  const currentMembership = memberships.find((m) => m.organization.id === currentOrgId) || memberships[0];
  const currentName = currentMembership.organization.name;

  return (
    <div className={`${styles.wrapper} ${className}`} ref={dropdownRef}>
      <button
        type="button"
        className={`${styles.trigger} ${compact ? styles.compact : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title={`Current: ${currentName}. Click to switch.`}
      >
        <span className={styles.triggerIcon}>🏥</span>
        <span className={styles.triggerText}>{currentName}</span>
        <span className={styles.chevron}>{isOpen ? '▲' : '▼'}</span>
      </button>
      {isOpen && (
        <>
          {subscriptionStatus?.plan && (
            <div className={styles.usageBar}>
              <span>{subscriptionStatus.plan.name}</span>
              <span>
                {subscriptionStatus.usage.patients}/{subscriptionStatus.limits.patients.max ?? '∞'} patients
                {' • '}
                {subscriptionStatus.usage.users}/{subscriptionStatus.limits.users.max ?? '∞'} users
              </span>
              {(subscriptionStatus.limits.patients.at_limit || subscriptionStatus.limits.users.at_limit) && (
                <button
                  type="button"
                  className={styles.upgradeBtn}
                  onClick={handleUpgrade}
                  disabled={checkoutLoading}
                >
                  {checkoutLoading ? '...' : 'Upgrade'}
                </button>
              )}
            </div>
          )}
          <ul className={styles.dropdown}>
            {memberships.map((m) => (
            <li key={m.id}>
              <button
                type="button"
                className={currentOrgId === m.organization.id ? styles.active : ''}
                onClick={() => handleSwitch(m)}
              >
                {m.organization.name}
                {m.is_default && <span className={styles.defaultBadge}>default</span>}
              </button>
            </li>
          ))}
          </ul>
        </>
      )}
    </div>
  );
}
