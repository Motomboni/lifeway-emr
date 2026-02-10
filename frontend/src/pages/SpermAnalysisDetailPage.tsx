/**
 * Sperm Analysis Detail Page
 * Displays a single sperm analysis record by ID.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchSpermAnalysis, SpermAnalysis } from '../api/ivf';
import styles from '../styles/SpermAnalyses.module.css';

const ASSESSMENT_LABELS: Record<string, string> = {
  NORMOZOOSPERMIA: 'Normozoospermia',
  OLIGOZOOSPERMIA: 'Oligozoospermia',
  ASTHENOZOOSPERMIA: 'Asthenozoospermia',
  TERATOZOOSPERMIA: 'Teratozoospermia',
  OLIGOASTHENOTERATOZOOSPERMIA: 'OAT Syndrome',
  OLIGOASTHENOZOOSPERMIA: 'Oligoasthenozoospermia',
  AZOOSPERMIA: 'Azoospermia',
  CRYPTOZOOSPERMIA: 'Cryptozoospermia',
  NECROZOOSPERMIA: 'Necrozoospermia',
};

const SAMPLE_SOURCE_LABELS: Record<string, string> = {
  FRESH: 'Fresh',
  FROZEN: 'Frozen',
  TESE: 'TESE',
  MESA: 'MESA',
  PESA: 'PESA',
  DONOR: 'Donor',
};

const APPEARANCE_LABELS: Record<string, string> = {
  NORMAL: 'Normal',
  YELLOW: 'Yellow',
  RED_BROWN: 'Red/Brown',
  CLEAR: 'Clear',
};

const VISCOSITY_LABELS: Record<string, string> = {
  NORMAL: 'Normal',
  INCREASED: 'Increased',
};

function formatDate(iso: string | undefined): string {
  if (!iso) return '-';
  try {
    return new Date(iso).toLocaleDateString();
  } catch {
    return iso;
  }
}

function formatPercent(n: number | undefined): string {
  if (n == null) return '-';
  return `${Number(n)}%`;
}

function formatNumber(n: number | undefined): string {
  if (n == null) return '-';
  return String(n);
}

export default function SpermAnalysisDetailPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<SpermAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const analysisId = id ? parseInt(id, 10) : NaN;
    if (!id || isNaN(analysisId)) {
      setError('Invalid analysis ID');
      setLoading(false);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchSpermAnalysis(analysisId);
        if (!cancelled) setAnalysis(data);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to load sperm analysis';
        if (!cancelled) setError(message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.loading}>Loading sperm analysis...</div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.headerContent}>
          <button className={styles.backButton} onClick={() => navigate('/ivf/sperm-analyses')}>
            Back to Sperm Analyses
          </button>
        </div>
        <div className={styles.errorBanner}>
          <span>{error || 'Sperm analysis not found.'}</span>
          <button onClick={() => navigate('/ivf/sperm-analyses')}>Back to list</button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <button
            className={styles.backButton}
            onClick={() => navigate('/ivf/sperm-analyses')}
          >
            Back to Sperm Analyses
          </button>
          <h1>Sperm Analysis #{analysis.id}</h1>
          {analysis.assessment && (
            <span
              className={styles.assessmentBadge}
              style={{ backgroundColor: '#1971c2', color: '#fff' }}
            >
              {ASSESSMENT_LABELS[analysis.assessment] || analysis.assessment}
            </span>
          )}
        </div>
      </header>

      <div className={styles.detailGrid}>
        <section className={styles.detailSection}>
          <h3>Patient and collection</h3>
          <dl className={styles.detailList}>
            <dt>Patient</dt>
            <dd>{analysis.patient_name} (ID {analysis.patient})</dd>
            {analysis.cycle != null && (
              <>
                <dt>Cycle</dt>
                <dd>{analysis.cycle}</dd>
              </>
            )}
            <dt>Collection date</dt>
            <dd>{formatDate(analysis.collection_date)}</dd>
            {analysis.collection_time != null && (
              <>
                <dt>Collection time</dt>
                <dd>{analysis.collection_time}</dd>
              </>
            )}
            {analysis.abstinence_days != null && (
              <>
                <dt>Abstinence (days)</dt>
                <dd>{analysis.abstinence_days}</dd>
              </>
            )}
            <dt>Sample source</dt>
            <dd>{SAMPLE_SOURCE_LABELS[analysis.sample_source] || analysis.sample_source}</dd>
          </dl>
        </section>

        <section className={styles.detailSection}>
          <h3>Macroscopic</h3>
          <dl className={styles.detailList}>
            <dt>Volume (mL)</dt>
            <dd>{formatNumber(analysis.volume)}</dd>
            <dt>Appearance</dt>
            <dd>{APPEARANCE_LABELS[analysis.appearance ?? ''] || analysis.appearance || '-'}</dd>
            {analysis.liquefaction_time != null && (
              <>
                <dt>Liquefaction time (min)</dt>
                <dd>{analysis.liquefaction_time}</dd>
              </>
            )}
            {analysis.ph != null && (
              <>
                <dt>pH</dt>
                <dd>{analysis.ph}</dd>
              </>
            )}
            <dt>Viscosity</dt>
            <dd>{VISCOSITY_LABELS[analysis.viscosity ?? ''] || analysis.viscosity || '-'}</dd>
          </dl>
        </section>

        <section className={styles.detailSection}>
          <h3>Concentration and count</h3>
          <dl className={styles.detailList}>
            <dt>Concentration (million/mL)</dt>
            <dd>{formatNumber(analysis.concentration)}</dd>
            <dt>Total sperm count (million)</dt>
            <dd>{formatNumber(analysis.total_sperm_count)}</dd>
          </dl>
        </section>

        <section className={styles.detailSection}>
          <h3>Motility</h3>
          <dl className={styles.detailList}>
            <dt>Progressive motility</dt>
            <dd>{formatPercent(analysis.progressive_motility)}</dd>
            <dt>Non-progressive motility</dt>
            <dd>{formatPercent(analysis.non_progressive_motility)}</dd>
            <dt>Immotile</dt>
            <dd>{formatPercent(analysis.immotile)}</dd>
            <dt>Total motility</dt>
            <dd>{formatPercent(analysis.total_motility)}</dd>
          </dl>
        </section>

        <section className={styles.detailSection}>
          <h3>Morphology and other</h3>
          <dl className={styles.detailList}>
            <dt>Normal forms (%)</dt>
            <dd>{formatNumber(analysis.normal_forms)}</dd>
            {analysis.head_defects != null && (
              <>
                <dt>Head defects (%)</dt>
                <dd>{analysis.head_defects}</dd>
              </>
            )}
            {analysis.midpiece_defects != null && (
              <>
                <dt>Midpiece defects (%)</dt>
                <dd>{analysis.midpiece_defects}</dd>
              </>
            )}
            {analysis.tail_defects != null && (
              <>
                <dt>Tail defects (%)</dt>
                <dd>{analysis.tail_defects}</dd>
              </>
            )}
            {analysis.vitality != null && (
              <>
                <dt>Vitality (%)</dt>
                <dd>{formatPercent(analysis.vitality)}</dd>
              </>
            )}
            {analysis.round_cells != null && (
              <>
                <dt>Round cells</dt>
                <dd>{analysis.round_cells}</dd>
              </>
            )}
            {analysis.wbc_count != null && (
              <>
                <dt>WBC count</dt>
                <dd>{analysis.wbc_count}</dd>
              </>
            )}
            {analysis.dna_fragmentation_index != null && (
              <>
                <dt>DNA fragmentation index (%)</dt>
                <dd>{formatPercent(analysis.dna_fragmentation_index)}</dd>
              </>
            )}
          </dl>
        </section>
      </div>

      {(analysis.recommendation || analysis.notes) && (
        <div className={styles.detailGrid}>
          {analysis.recommendation && (
            <section className={styles.detailSection}>
              <h3>Recommendation</h3>
              <p className={styles.detailText}>{analysis.recommendation}</p>
            </section>
          )}
          {analysis.notes && (
            <section className={styles.detailSection}>
              <h3>Notes</h3>
              <p className={styles.detailText}>{analysis.notes}</p>
            </section>
          )}
        </div>
      )}

      <div className={styles.detailMeta}>
        <span>Analyzed by {analysis.analyzed_by_name}</span>
        <span>Created {formatDate(analysis.created_at)}</span>
      </div>
    </div>
  );
}
