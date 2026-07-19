/**

 * Clinic settings — name, contact, patient ID prefix, Guide modules (admin only).

 */

import React, { useEffect, useState } from 'react';

import { useNavigate } from 'react-router-dom';

import { fetchGuideAnalytics } from '../api/guide';

import { useRolePermissions } from '../hooks/useRolePermissions';

import { useOrganization } from '../contexts/OrganizationContext';

import { useToast } from '../hooks/useToast';

import {

  getOrganizationMemberships,

  updateOrganizationSettings,

} from '../api/organizations';

import {

  GUIDE_MODULE_LABELS,

  GUIDE_MODULE_TOGGLES,

  normalizeGuideModules,

  type GuideModules,

} from '../data/guideModules';

import BackToDashboard from '../components/common/BackToDashboard';

import LoadingSkeleton from '../components/common/LoadingSkeleton';

import type { GuideAnalyticsSummary } from '../types/guide';

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

  const [guideModules, setGuideModules] = useState<GuideModules>(normalizeGuideModules());

  const [analytics, setAnalytics] = useState<GuideAnalyticsSummary | null>(null);

  const [analyticsLoading, setAnalyticsLoading] = useState(false);

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

          setGuideModules(normalizeGuideModules(o.guide_modules));

        }

      } catch (e: unknown) {

        showError(e instanceof Error ? e.message : 'Failed to load settings');

      } finally {

        setLoading(false);

      }

    };

    load();

  }, [isAdmin, navigate, showError]);



  useEffect(() => {

    if (!isAdmin || !orgId) return;

    setAnalyticsLoading(true);

    fetchGuideAnalytics(30)

      .then(setAnalytics)

      .catch(() => setAnalytics(null))

      .finally(() => setAnalyticsLoading(false));

  }, [isAdmin, orgId]);



  const handleSave = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!orgId) return;

    setSaving(true);

    try {

      await updateOrganizationSettings(orgId, {

        ...form,

        guide_modules: guideModules,

      });

      await refresh();

      showSuccess('Clinic settings saved.');

    } catch (e: unknown) {

      showError(e instanceof Error ? e.message : 'Failed to save');

    } finally {

      setSaving(false);

    }

  };



  const toggleModule = (key: keyof GuideModules) => {

    setGuideModules((prev) => ({ ...prev, [key]: !prev[key] }));

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



        <fieldset className={styles.guideModulesFieldset}>

          <legend>Guide modules</legend>

          <p className={styles.guideModulesHint}>

            Disable modules your clinic does not use — Role Launch tours and Ask Guide articles

            will hide related topics.

          </p>

          {GUIDE_MODULE_TOGGLES.map((key) => (

            <label key={key} className={styles.toggleRow}>

              <input

                type="checkbox"

                checked={guideModules[key]}

                onChange={() => toggleModule(key)}

              />

              <span>{GUIDE_MODULE_LABELS[key]}</span>

            </label>

          ))}

        </fieldset>



        <button type="submit" className={styles.saveBtn} disabled={saving}>

          {saving ? 'Saving…' : 'Save clinic settings'}

        </button>

      </form>



      <section className={styles.analyticsSection}>

        <h2>Guide analytics (30 days)</h2>

        <p className={styles.guideModulesHint}>

          Aggregated adoption metrics — no patient data or Ask Guide query text is stored.

        </p>

        {analyticsLoading ? (

          <LoadingSkeleton count={2} />

        ) : analytics ? (

          <div className={styles.analyticsGrid}>

            <div className={styles.analyticsCard}>

              <strong>{analytics.total_events}</strong>

              <span>Total interactions</span>

            </div>

            <div className={styles.analyticsCard}>

              <strong>{analytics.unique_users}</strong>

              <span>Staff using Guide</span>

            </div>

            {analytics.top_articles.length > 0 && (

              <div className={styles.analyticsList}>

                <h3>Top articles</h3>

                <ul>

                  {analytics.top_articles.map((row) => (

                    <li key={row.article_id}>

                      {row.article_id} <span>({row.count})</span>

                    </li>

                  ))}

                </ul>

              </div>

            )}

          </div>

        ) : (

          <p className={styles.guideModulesHint}>No guide analytics yet.</p>

        )}

      </section>

    </div>

  );

}

