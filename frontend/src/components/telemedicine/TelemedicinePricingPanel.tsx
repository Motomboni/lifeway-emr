/**
 * Admin UI to set telemedicine consultation price (ServiceCatalog TELEMED-001).
 */
import React, { useEffect, useState } from 'react';
import {
  fetchTelemedicinePricing,
  updateTelemedicinePricing,
  type TelemedicinePricing,
} from '../../api/telemedicine';
import { useToast } from '../../hooks/useToast';
import styles from '../../styles/VirtualClinic.module.css';

export default function TelemedicinePricingPanel() {
  const { showSuccess, showError } = useToast();
  const [pricing, setPricing] = useState<TelemedicinePricing | null>(null);
  const [amount, setAmount] = useState('');
  const [name, setName] = useState('Telemedicine Consultation');
  const [active, setActive] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      const data = await fetchTelemedicinePricing();
      setPricing(data);
      if (data.configured && data.amount != null) {
        setAmount(String(data.amount));
        setName(data.name || 'Telemedicine Consultation');
        setActive(data.is_active !== false);
      }
    } catch (err: unknown) {
      showError(err instanceof Error ? err.message : 'Failed to load telemedicine pricing');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = Number(amount);
    if (Number.isNaN(parsed) || parsed < 0) {
      showError('Enter a valid non-negative amount');
      return;
    }
    try {
      setSaving(true);
      const updated = await updateTelemedicinePricing({
        amount: parsed.toFixed(2),
        name: name.trim() || 'Telemedicine Consultation',
        is_active: active,
      });
      setPricing(updated);
      setAmount(String(updated.amount));
      showSuccess(`Telemedicine price set to ₦${Number(updated.amount).toLocaleString()}`);
    } catch (err: unknown) {
      showError(err instanceof Error ? err.message : 'Failed to save price');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.pricingPanel}>
        <p className={styles.muted}>Loading telemedicine pricing…</p>
      </div>
    );
  }

  if (pricing && pricing.can_edit === false) {
    return (
      <div className={styles.pricingPanel}>
        <h3>Telemedicine price</h3>
        <p>
          {pricing.configured
            ? `Current fee: ₦${Number(pricing.amount).toLocaleString()} (${pricing.service_code})`
            : 'Pricing not configured yet. Ask an administrator to set it.'}
        </p>
      </div>
    );
  }

  return (
    <div className={styles.pricingPanel}>
      <div className={styles.inviteHeader}>
        <h3>Telemedicine pricing</h3>
        <p>
          Set the fee charged when a doctor ends a virtual clinic session with billing enabled.
          Uses service code {pricing?.service_code || 'TELEMED-001'}.
        </p>
      </div>
      <form className={styles.pricingForm} onSubmit={handleSave}>
        <label>
          Display name
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={255}
            required
          />
        </label>
        <label>
          Amount (NGN)
          <input
            type="number"
            min="0"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
            inputMode="decimal"
          />
        </label>
        <label className={styles.pricingActive}>
          <input
            type="checkbox"
            checked={active}
            onChange={(e) => setActive(e.target.checked)}
          />
          Active (available for billing)
        </label>
        <button type="submit" className={styles.inviteBtn} disabled={saving}>
          {saving ? 'Saving…' : 'Save telemedicine price'}
        </button>
      </form>
      {pricing?.configured && (
        <p className={styles.muted}>
          Last updated:{' '}
          {pricing.updated_at ? new Date(pricing.updated_at).toLocaleString() : '—'}
        </p>
      )}
    </div>
  );
}
