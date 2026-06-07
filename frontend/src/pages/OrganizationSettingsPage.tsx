/**
 * Clinic settings — branding, contact, patient ID prefix (SaaS).
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRolePermissions } from '../hooks/useRolePermissions';
import { useOrganization } from '../contexts/OrganizationContext';
import { useToast } from '../hooks/useToast';
import {
  getOrganizationMemberships,
  updateOrganizationSettings,
  Organization,
} from '../api/organizations';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/OrganizationSettings.module.css';

export default function OrganizationSettingsPage() {
  const { isAdmin } = useRolePermissions();
  const { organization, refresh } = useOrganization();
  const navigate = useNavigate();
  const { showSuccess, showError } = useToast();

  const [orgId, setOrgId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: '',
    logo_url: '',
    email: '',
    phone: '',
    address: '',
    patient_id_prefix: '',
  });
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAdmin) {
      navigate('/dashboard');
      return;
    }
    const load = async () => {
      try {
        const memberships = await getOrganizationMemberships();
        const current =
          memberships.find((m) => m.is_default) || memberships[0];
        if (current?.organization) {
          const o = current.organization;
          setOrgId(o.id);
          setForm({
            name: o.name || '',
            logo_url: o.logo_url || '',
            email: o.email || '',
            phone: o.phone || '',
            address: o.address || '',
            patient_id_prefix: o.patient_id_prefix || 'LMC',
          });
        }
      } catch (e: unknown) {
        showError(e instanceof Error ? e.message : 'Failed to load settings');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [isAdmin, navigate, showError]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgId) return;
    setSaving(true);
    try {
      await updateOrganizationSettings(orgId, form);
      await refresh();
      showSuccess('Clinic settings saved. Receipts and headers will use your branding.');
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <LoadingSkeleton count={4} />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Clinic Settings</h1>
        <p>Your branding appears on the dashboard, receipts, and patient communications.</p>
      </header>

      <form className={styles.form} onSubmit={handleSave}>
        <div className={styles.preview}>
          {form.logo_url ? (
            <img src={form.logo_url} alt="" className={styles.previewLogo} />
          ) : (
            <div className={styles.previewMark}>{(form.name || 'C').charAt(0)}</div>
          )}
          <div>
            <strong>{form.name || 'Your Clinic'}</strong>
            <p>{form.patient_id_prefix}000001 · Patient ID prefix</p>
          </div>
        </div>

        <label>
          Clinic name
          <input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
        </label>

        <label>
          Logo URL
          <input
            value={form.logo_url}
            onChange={(e) => setForm({ ...form, logo_url: e.target.value })}
            placeholder="https://your-cdn.com/logo.png"
          />
        </label>

        <label>
          Patient ID prefix
          <input
            value={form.patient_id_prefix}
            onChange={(e) =>
              setForm({ ...form, patient_id_prefix: e.target.value.toUpperCase().slice(0, 10) })
            }
            maxLength={10}
          />
        </label>

        <label>
          Billing email
          <input
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        </label>

        <label>
          Phone
          <input
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
        </label>

        <label>
          Address (on receipts)
          <textarea
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
            rows={3}
          />
        </label>

        <button type="submit" className={styles.saveBtn} disabled={saving}>
          {saving ? 'Saving…' : 'Save clinic settings'}
        </button>
      </form>
    </div>
  );
}
