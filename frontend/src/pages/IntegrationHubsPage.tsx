/**
 * External health hub integration settings (NHIA portal, e-Rx, lab exchange stubs).
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useRolePermissions } from '../hooks/useRolePermissions';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import { fetchIntegrationHubs, updateIntegrationHub, ExternalHealthHub } from '../api/integrations';
import styles from '../styles/RevenueLeakDashboard.module.css';

export default function IntegrationHubsPage() {
  const { user } = useAuth();
  const { isAdmin } = useRolePermissions();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();
  const [hubs, setHubs] = useState<ExternalHealthHub[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) navigate('/login');
    if (user && !isAdmin) navigate('/dashboard');
  }, [user, isAdmin, navigate]);

  const load = async () => {
    try {
      setLoading(true);
      setHubs(await fetchIntegrationHubs());
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to load hubs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && isAdmin) load();
  }, [user, isAdmin]);

  const toggleHub = async (hub: ExternalHealthHub) => {
    try {
      await updateIntegrationHub(hub.hub_type, { is_enabled: !hub.is_enabled });
      showSuccess(`${hub.hub_type} updated`);
      load();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Update failed');
    }
  };

  const saveUrl = async (hub: ExternalHealthHub, base_url: string) => {
    try {
      await updateIntegrationHub(hub.hub_type, { base_url });
      showSuccess('Base URL saved');
      load();
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Save failed');
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <LoadingSkeleton lines={4} />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Integration Hubs</h1>
        <p className={styles.subtitle}>
          Future national integrations. NHIA has no public API — use claim pack export and
          manual status tracking in Billing until official APIs exist.
        </p>
      </header>

      {hubs.map((hub) => (
        <div key={hub.hub_type} className={styles.summaryCard} style={{ marginBottom: '1rem', padding: '1rem' }}>
          <h3>{hub.hub_type.replace(/_/g, ' ')}</h3>
          {hub.hub_type === 'NHIA_PORTAL' && (
            <p style={{ marginBottom: '0.5rem', color: '#5d4037' }}>
              Manual workflow only: export CSV from visit billing, upload via NHIA portal,
              then record submitted/paid/denied in the EMR.
            </p>
          )}
          <p>Status: {hub.is_enabled ? 'Enabled' : 'Disabled'}</p>
          <p>Last sync: {hub.last_sync_at ? new Date(hub.last_sync_at).toLocaleString() : 'Never'}</p>
          <label>
            Base URL
            <input
              defaultValue={hub.base_url}
              onBlur={(e) => {
                if (e.target.value !== hub.base_url) saveUrl(hub, e.target.value);
              }}
              style={{ width: '100%', marginTop: '0.25rem' }}
            />
          </label>
          <button type="button" style={{ marginTop: '0.5rem' }} onClick={() => toggleHub(hub)}>
            {hub.is_enabled ? 'Disable' : 'Enable'}
          </button>
        </div>
      ))}
    </div>
  );
}
