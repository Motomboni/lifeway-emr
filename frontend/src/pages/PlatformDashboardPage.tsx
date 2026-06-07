import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { isSuperuser } from '../utils/roleUtils';
import {
  getPlatformOverview,
  getPlatformOrganizations,
  PlatformOverview,
  PlatformOrganization,
} from '../api/platform';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import { useToast } from '../hooks/useToast';
import ToastContainer from '../components/common/ToastContainer';

function formatNgn(amount: string): string {
  const num = parseFloat(amount);
  if (Number.isNaN(num)) return amount;
  try {
    return new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN' }).format(num);
  } catch {
    return `NGN ${num.toLocaleString()}`;
  }
}

export default function PlatformDashboardPage() {
  const { user } = useAuth();
  const { toasts, showError, removeToast } = useToast();
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [organizations, setOrganizations] = useState<PlatformOrganization[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isSuperuser(user)) {
      setLoading(false);
      return;
    }

    const load = async () => {
      try {
        const [ov, orgs] = await Promise.all([
          getPlatformOverview(),
          getPlatformOrganizations(),
        ]);
        setOverview(ov);
        setOrganizations(orgs.organizations);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load platform data';
        showError(message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [user, showError]);

  if (!isSuperuser(user)) {
    return (
      <div style={{ padding: '2rem' }}>
        <h1>Platform Dashboard</h1>
        <p>Access denied. Django superuser account required.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '1.5rem 2rem', maxWidth: 1200, margin: '0 auto' }}>
      <BackToDashboard />
      <header style={{ marginBottom: '2rem' }}>
        <h1>Platform Dashboard</h1>
        <p style={{ color: 'var(--text-muted, #666)' }}>
          Cross-tenant SaaS metrics — all clinics on Damianix EMR
        </p>
      </header>

      {loading ? (
        <LoadingSkeleton count={4} />
      ) : overview ? (
        <>
          <section
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '1rem',
              marginBottom: '2rem',
            }}
          >
            {[
              { label: 'Organizations', value: overview.totals.organizations },
              { label: 'Active subs', value: overview.totals.active_subscriptions },
              { label: 'Trials', value: overview.totals.trial_subscriptions },
              { label: 'Patients (all)', value: overview.totals.patients },
              { label: 'Staff memberships', value: overview.totals.staff_memberships },
              { label: 'MRR (est.)', value: formatNgn(overview.totals.mrr_ngn) },
              { label: 'Revenue 30d', value: formatNgn(overview.totals.revenue_30d_ngn) },
            ].map((m) => (
              <div
                key={m.label}
                style={{
                  padding: '1rem',
                  borderRadius: 8,
                  border: '1px solid var(--border-color, #e0e0e0)',
                  background: 'var(--card-bg, #fff)',
                }}
              >
                <p style={{ margin: 0, fontSize: '0.85rem', opacity: 0.7 }}>{m.label}</p>
                <p style={{ margin: '0.25rem 0 0', fontSize: '1.5rem', fontWeight: 600 }}>
                  {m.value}
                </p>
              </div>
            ))}
          </section>

          {overview.expiring_soon.length > 0 && (
            <section style={{ marginBottom: '2rem' }}>
              <h2>Expiring within 7 days</h2>
              <ul>
                {overview.expiring_soon.map((e) => (
                  <li key={e.organization_id}>
                    {e.organization_name} — {e.plan}
                    {e.current_period_end
                      ? ` (ends ${new Date(e.current_period_end).toLocaleDateString()})`
                      : ''}
                    {e.auto_renew_enabled ? ' · auto-renew on' : ' · manual renew'}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2>All organizations</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #ddd', textAlign: 'left' }}>
                  <th style={{ padding: '0.5rem' }}>Clinic</th>
                  <th>Plan</th>
                  <th>Status</th>
                  <th>Patients</th>
                  <th>Users</th>
                  <th>Period end</th>
                </tr>
              </thead>
              <tbody>
                {organizations.map((org) => (
                  <tr key={org.id} style={{ borderBottom: '1px solid #eee' }}>
                    <td style={{ padding: '0.5rem' }}>
                      <strong>{org.name}</strong>
                      <br />
                      <small>{org.slug}</small>
                    </td>
                    <td>{org.plan_name || '—'}</td>
                    <td>{org.subscription_status}</td>
                    <td>{org.patients}</td>
                    <td>{org.users}</td>
                    <td>
                      {org.current_period_end
                        ? new Date(org.current_period_end).toLocaleDateString()
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      ) : null}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </div>
  );
}
