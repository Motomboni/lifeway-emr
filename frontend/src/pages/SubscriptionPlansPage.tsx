import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  getPlans,
  getSubscriptionStatus,
  createCheckoutSession,
  cancelSubscriptionAutoRenew,
  getBillingInvoices,
  verifySubscriptionPayment,
  Plan,
  SubscriptionStatus,
  SaasBillingInvoice,
} from '../api/organizations';
import { useAuth } from '../contexts/AuthContext';
import { useRolePermissions } from '../hooks/useRolePermissions';
import { useToast } from '../hooks/useToast';
import ToastContainer from '../components/common/ToastContainer';
import styles from '../styles/SubscriptionPlans.module.css';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';

function formatPlanPrice(amount: string, currency: string): string {
    const code = (currency || 'NGN').toUpperCase();
    const num = parseFloat(amount);
    if (Number.isNaN(num)) return amount;
    try {
        return new Intl.NumberFormat('en-NG', { style: 'currency', currency: code }).format(num);
    } catch {
        return `${code} ${num.toLocaleString()}`;
    }
}

export default function SubscriptionPlansPage() {
    const { user } = useAuth();
    const { isAdmin } = useRolePermissions();
    const { toasts, showSuccess, showError, removeToast } = useToast();
    const [searchParams, setSearchParams] = useSearchParams();

    const [plans, setPlans] = useState<Plan[]>([]);
    const [status, setStatus] = useState<SubscriptionStatus | null>(null);
    const [invoices, setInvoices] = useState<SaasBillingInvoice[]>([]);
    const [loading, setLoading] = useState(true);
    const [checkoutLoading, setCheckoutLoading] = useState<number | null>(null);
    const [cancelLoading, setCancelLoading] = useState(false);

    const paymentProvider = (status?.payment_provider || 'paystack').toLowerCase();
    const providerLabel =
        paymentProvider === 'flutterwave' ? 'Flutterwave' : 'Paystack';

    useEffect(() => {
        const reference =
            searchParams.get('reference') ||
            searchParams.get('trxref');
        if (!reference || !isAdmin) return;

        const verify = async () => {
            const result = await verifySubscriptionPayment(reference);
            if (result?.subscription) {
                setStatus(result.subscription);
                showSuccess(result.detail || 'Subscription payment confirmed.');
            } else if (result?.detail) {
                showError(result.detail);
            }
            searchParams.delete('reference');
            searchParams.delete('trxref');
            searchParams.delete('success');
            setSearchParams(searchParams, { replace: true });
        };
        verify();
    }, [isAdmin, searchParams, setSearchParams, showSuccess, showError]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [plansData, statusData, invoiceData] = await Promise.all([
                    getPlans(),
                    getSubscriptionStatus(),
                    getBillingInvoices()
                ]);
                setPlans(plansData);
                setStatus(statusData);
                setInvoices(invoiceData);
            } catch (err: any) {
                showError(err.message || 'Failed to load subscription data');
            } finally {
                setLoading(false);
            }
        };

        if (isAdmin) {
            fetchData();
        } else {
            setLoading(false);
        }
    }, [isAdmin, showError]);

    const handleCancelAutoRenew = async () => {
        setCancelLoading(true);
        try {
            const res = await cancelSubscriptionAutoRenew();
            if (res?.subscription) {
                setStatus(res.subscription);
            }
            showSuccess(res?.detail || 'Auto-renew disabled.');
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to cancel auto-renew';
            showError(message);
        } finally {
            setCancelLoading(false);
        }
    };

    const handleUpgrade = async (plan: Plan) => {
        setCheckoutLoading(plan.id);
        try {
            const res = await createCheckoutSession({
                plan_slug: plan.slug,
                success_url: `${window.location.origin}/plans?success=true`,
                cancel_url: `${window.location.origin}/plans?canceled=true`
            });

            if (res?.checkout_url) {
                window.location.href = res.checkout_url;
            } else {
                showError(
                    `${providerLabel} is not configured. Add PAYSTACK_SECRET_KEY (or FLUTTERWAVE_SECRET_KEY) on the server.`
                );
            }
        } catch (err: any) {
            showError(err.message || 'Error initiating checkout.');
        } finally {
            setCheckoutLoading(null);
        }
    };

    if (!isAdmin) {
        return (
            <div className={styles.page}>
                <h1>Subscription Plans</h1>
                <p className={styles.accessDenied}>Access denied. Organization administrators only.</p>
            </div>
        );
    }

    return (
        <div className={styles.page}>
            <BackToDashboard />
            <header className={styles.header}>
                <div className={styles.headerContent}>
                    <div>
                        <h1>Subscription & Billing</h1>
                        <p className={styles.subtitle}>
                            Manage your clinic&apos;s SaaS plan. Payments are processed via {providerLabel} (Nigeria).
                        </p>
                    </div>
                </div>
            </header>

            {loading ? (
                <LoadingSkeleton count={4} />
            ) : (
                <div className={styles.content}>

                    {/* Current Usage Overview */}
                    {status && (
                        <section className={styles.usageSection}>
                            <div className={styles.usageCard}>
                                <div className={styles.usageHeader}>
                                    <h2>Current Plan: <span className={styles.highlight}>{status.plan?.name || 'Unknown'}</span></h2>
                                    <div className={`${styles.statusBadge} ${status.status === 'ACTIVE' ? styles.statusActive : ''}`}>
                                        {status.status}
                                    </div>
                                </div>

                                <div className={styles.metricsGrid}>
                                    <div className={styles.metricItem}>
                                        <p className={styles.metricLabel}>Users</p>
                                        <p className={styles.metricValue}>
                                            {status.limits.users.current} / {status.limits.users.max === null ? '∞' : status.limits.users.max}
                                        </p>
                                        {status.limits.users.max && (
                                            <div className={styles.progressBar}>
                                                <div
                                                    className={styles.progressFill}
                                                    style={{ width: `${Math.min(100, (status.limits.users.current / status.limits.users.max) * 100)}%` }}
                                                />
                                            </div>
                                        )}
                                    </div>

                                    <div className={styles.metricItem}>
                                        <p className={styles.metricLabel}>Patients</p>
                                        <p className={styles.metricValue}>
                                            {status.limits.patients.current} / {status.limits.patients.max === null ? '∞' : status.limits.patients.max}
                                        </p>
                                        {status.limits.patients.max && (
                                            <div className={styles.progressBar}>
                                                <div
                                                    className={styles.progressFill}
                                                    style={{ width: `${Math.min(100, (status.limits.patients.current / status.limits.patients.max) * 100)}%` }}
                                                />
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </section>
                    )}

                    <section className={styles.billingSection}>
                        <div className={styles.billingGrid}>
                            <div className={styles.billingCard}>
                                <div className={styles.billingHeader}>
                                    <h3 className={styles.billingTitle}>Payment provider</h3>
                                </div>
                                <div className={styles.paymentMethodInfo}>
                                    <div className={styles.cardIcon}>🇳🇬</div>
                                    <div className={styles.cardDetails}>
                                        <p className={styles.cardName}>
                                            <strong>{providerLabel}</strong> — cards, bank transfer, USSD
                                        </p>
                                        <p className={styles.cardExpiry}>
                                            Upgrade plans below; you will be redirected to {providerLabel} to pay in NGN.
                                        </p>
                                    </div>
                                </div>
                                <p className={styles.billingNotice}>
                                    Current period ends{' '}
                                    <strong>
                                        {status?.current_period_end
                                            ? new Date(status.current_period_end).toLocaleDateString()
                                            : '—'}
                                    </strong>
                                    {status?.auto_renew_enabled
                                        ? '. Paystack auto-renew is active — your card will be charged monthly.'
                                        : '. Renew by upgrading your plan when due.'}
                                </p>
                                {status?.auto_renew_enabled && (
                                    <button
                                        type="button"
                                        className={styles.upgradeBtn}
                                        disabled={cancelLoading}
                                        onClick={handleCancelAutoRenew}
                                        style={{ marginTop: '0.75rem' }}
                                    >
                                        {cancelLoading ? 'Processing...' : 'Cancel auto-renew'}
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className={styles.invoiceHistoryCard}>
                            <h3 className={styles.billingTitle}>Recent subscription payments</h3>
                            <table className={styles.invoiceTable}>
                                <thead>
                                    <tr>
                                        <th>Date</th>
                                        <th>Reference</th>
                                        <th>Plan</th>
                                        <th>Amount</th>
                                        <th>Status</th>
                                        <th>Provider</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {invoices.length > 0 ? invoices.map(inv => (
                                        <tr key={inv.id}>
                                            <td>{inv.created ? new Date(inv.created * 1000).toLocaleDateString() : '—'}</td>
                                            <td>{inv.number || inv.id}</td>
                                            <td>{inv.plan_name || '—'}</td>
                                            <td>{formatPlanPrice(String(inv.amount_paid), inv.currency || 'NGN')}</td>
                                            <td><span className={inv.status === 'paid' ? styles.badgePaid : styles.badgePending}>{inv.status}</span></td>
                                            <td>{inv.provider || providerLabel}</td>
                                        </tr>
                                    )) : (
                                        <tr>
                                            <td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>No subscription payments yet.</td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </section>

                    {/* Available Plans */}
                    <section className={styles.plansSection}>
                        <h2 className={styles.sectionTitle}>Upgrade Your Capabilities</h2>
                        <div className={styles.plansGrid}>
                            {plans.map((plan) => {
                                const isCurrentPlan = status?.plan?.slug === plan.slug;

                                return (
                                    <div key={plan.id} className={`${styles.planCard} ${isCurrentPlan ? styles.planCardCurrent : ''}`}>
                                        {isCurrentPlan && <div className={styles.currentIndicator}>Current Plan</div>}
                                        <div className={styles.planHeader}>
                                            <h3 className={styles.planName}>{plan.name}</h3>
                                            <div className={styles.planPriceWrapper}>
                                                <span className={styles.planPrice}>
                                                    {formatPlanPrice(plan.price_monthly, plan.currency || 'NGN')}
                                                </span>
                                                <span className={styles.planPeriod}>/mo</span>
                                            </div>
                                            <p className={styles.planDescription}>{plan.description}</p>
                                        </div>

                                        <div className={styles.planLimits}>
                                            <ul>
                                                <li><span className={styles.checkIcon}>✓</span> {plan.max_users === null ? 'Unlimited' : plan.max_users} Users</li>
                                                <li><span className={styles.checkIcon}>✓</span> {plan.max_patients === null ? 'Unlimited' : plan.max_patients.toLocaleString()} Patients</li>
                                                <li><span className={styles.checkIcon}>✓</span> {plan.max_storage_mb === null ? 'Unlimited' : `${Math.round(plan.max_storage_mb / 1024)}GB`} Storage</li>
                                            </ul>
                                        </div>

                                        {plan.features && Object.keys(plan.features).length > 0 && (
                                            <div className={styles.planFeatures}>
                                                <p className={styles.featuresHeading}>Includes:</p>
                                                <ul>
                                                    {Object.entries(plan.features).map(([key, val]) => (
                                                        <li key={key}>
                                                            <span className={styles.checkIcon}>✓</span>
                                                            {key.replace(/_/g, ' ')}: {val === true ? 'Yes' : String(val)}
                                                        </li>
                                                    ))}
                                                </ul>
                                            </div>
                                        )}

                                        <div className={styles.planAction}>
                                            <button
                                                className={`${styles.upgradeBtn} ${isCurrentPlan ? styles.disabledBtn : ''}`}
                                                disabled={isCurrentPlan || checkoutLoading === plan.id}
                                                onClick={() => handleUpgrade(plan)}
                                            >
                                                {isCurrentPlan
                                                    ? 'Current Plan'
                                                    : checkoutLoading === plan.id
                                                        ? 'Processing...'
                                                        : `Subscribe with ${providerLabel}`
                                                }
                                            </button>
                                        </div>
                                    </div>
                                );
                            })}

                            {plans.length === 0 && (
                                <div className={styles.noPlansMessage}>
                                    No subscription plans available at the moment.
                                </div>
                            )}
                        </div>
                    </section>
                </div>
            )}
            <ToastContainer toasts={toasts} onRemove={removeToast} />
        </div>
    );
}
