/**
 * NHIA compliance dashboard — claim readiness, missing NHID, revenue at risk.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useRolePermissions } from '../hooks/useRolePermissions';
import {
  downloadBatchClaimPackCsv,
  getNHIAComplianceSummary,
  getNHIAClaimSubmissions,
  nhiaClaimAction,
  NHIAComplianceSummary,
  NHIAClaimSubmission,
} from '../api/billing';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/RevenueLeakDashboard.module.css';

export default function NHIAComplianceDashboardPage() {
  const { user } = useAuth();
  const { isAdmin } = useRolePermissions();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();

  const [summary, setSummary] = useState<NHIAComplianceSummary | null>(null);
  const [claims, setClaims] = useState<NHIAClaimSubmission[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [startDate, setStartDate] = useState(
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
  );
  const [endDate, setEndDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    if (!user) navigate('/login');
  }, [user, navigate]);

  useEffect(() => {
    if (!user || !isAdmin) return;
    loadSummary();
  }, [user, isAdmin, startDate, endDate]);

  const loadSummary = async () => {
    try {
      setLoading(true);
      const data = await getNHIAComplianceSummary({ start_date: startDate, end_date: endDate });
      setSummary(data);
      const lifecycle = await getNHIAClaimSubmissions({ start_date: startDate, end_date: endDate });
      setClaims(lifecycle);
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to load NHIA compliance data');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    try {
      setExporting(true);
      await downloadBatchClaimPackCsv({ start_date: startDate, end_date: endDate });
      showSuccess('Claim pack CSV downloaded');
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  if (loading && !summary) {
    return (
      <div className={styles.page}>
        <LoadingSkeleton lines={8} />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>NHIA Compliance Dashboard</h1>
        <p className={styles.subtitle}>
          Claim readiness, verified NHID coverage, and scribe-billed NHIA items
        </p>
      </header>

      <div className={styles.filters}>
        <label>
          From
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        </label>
        <button type="button" onClick={loadSummary} disabled={loading}>
          Refresh
        </button>
        <button type="button" onClick={handleExport} disabled={exporting}>
          {exporting ? 'Exporting…' : 'Export claim pack CSV'}
        </button>
      </div>

      {summary && (
        <>
          <div className={styles.summaryCards}>
            <div className={styles.summaryCard}>
              <div>
                <div className={styles.summaryValue}>{summary.claim_ready_count}</div>
                <div className={styles.summaryLabel}>Claim-ready visits</div>
              </div>
            </div>
            <div className={styles.summaryCard}>
              <div>
                <div className={styles.summaryValue}>{summary.claim_ready_pct}%</div>
                <div className={styles.summaryLabel}>Claim-ready rate</div>
              </div>
            </div>
            <div className={styles.summaryCard}>
              <div>
                <div className={styles.summaryValue}>₦{summary.total_nhia_billable_ngn}</div>
                <div className={styles.summaryLabel}>NHIA billable (ready)</div>
              </div>
            </div>
            <div className={styles.summaryCard}>
              <div>
                <div className={styles.summaryValue}>{summary.missing_nhid_count}</div>
                <div className={styles.summaryLabel}>Missing NHID</div>
              </div>
            </div>
            <div className={styles.summaryCard}>
              <div>
                <div className={styles.summaryValue}>{summary.scribe_billed_items}</div>
                <div className={styles.summaryLabel}>Scribe NHIA charges</div>
              </div>
            </div>
            <div className={styles.summaryCard}>
              <div>
                <div className={styles.summaryValue}>{summary.open_revenue_leaks}</div>
                <div className={styles.summaryLabel}>Open revenue leaks</div>
              </div>
            </div>
          </div>

          {claims.length > 0 && (
            <div className={styles.tableContainer} style={{ marginTop: '1.5rem' }}>
              <h2>Claim lifecycle</h2>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Visit</th>
                    <th>Patient</th>
                    <th>Status</th>
                    <th>Reference</th>
                    <th>Amount</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {claims.map((claim) => (
                    <tr key={claim.id}>
                      <td>#{claim.visit_id}</td>
                      <td>{claim.patient_name}</td>
                      <td>{claim.status}</td>
                      <td>{claim.claim_reference}</td>
                      <td>₦{claim.total_amount_ngn}</td>
                      <td>
                        {claim.status === 'DRAFT' && (
                          <button type="button" onClick={() => nhiaClaimAction(claim.visit_id, 'validate').then(loadSummary)}>
                            Validate
                          </button>
                        )}
                        {claim.status === 'VALIDATED' && (
                          <button type="button" onClick={() => nhiaClaimAction(claim.visit_id, 'export').then(loadSummary)}>
                            Export
                          </button>
                        )}
                        {['EXPORTED', 'RESUBMITTED'].includes(claim.status) && (
                          <button type="button" onClick={() => nhiaClaimAction(claim.visit_id, 'submit').then(loadSummary)}>
                            Submit
                          </button>
                        )}
                        {claim.status === 'SUBMITTED' && (
                          <>
                            <button type="button" onClick={() => nhiaClaimAction(claim.visit_id, 'paid').then(loadSummary)}>
                              Mark paid
                            </button>
                            <button type="button" onClick={() => nhiaClaimAction(claim.visit_id, 'deny', { reason: 'NHIA denial' }).then(loadSummary)}>
                              Deny
                            </button>
                          </>
                        )}
                        {claim.status === 'DENIED' && (
                          <button type="button" onClick={() => nhiaClaimAction(claim.visit_id, 'resubmit').then(loadSummary)}>
                            Resubmit
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className={styles.tableContainer}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Visit</th>
                  <th>Date</th>
                  <th>Patient</th>
                  <th>NHID</th>
                  <th>NHIA lines</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Issues</th>
                  <th>Claim</th>
                </tr>
              </thead>
              <tbody>
                {summary.visits.map((row) => {
                  const hasClaim = claims.some((c) => c.visit_id === row.visit_id);
                  return (
                  <tr key={row.visit_id}>
                    <td>
                      <button
                        type="button"
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--primary)',
                          cursor: 'pointer',
                          textDecoration: 'underline',
                        }}
                        onClick={() => navigate(`/visits/${row.visit_id}`)}
                      >
                        #{row.visit_id}
                      </button>
                    </td>
                    <td>{row.visit_date}</td>
                    <td>{row.patient_name}</td>
                    <td>{row.national_health_id || '—'}</td>
                    <td>{row.line_count}</td>
                    <td>₦{row.total_amount_ngn}</td>
                    <td>{row.claim_ready ? 'Ready' : 'Incomplete'}</td>
                    <td>{row.issues.join(', ') || '—'}</td>
                    <td>
                      {row.claim_ready && !hasClaim && (
                        <button
                          type="button"
                          onClick={() =>
                            nhiaClaimAction(row.visit_id, 'draft')
                              .then(loadSummary)
                              .then(() => showSuccess('Claim draft created'))
                              .catch((e: unknown) =>
                                showError(e instanceof Error ? e.message : 'Failed to create claim'),
                              )
                          }
                        >
                          Start claim
                        </button>
                      )}
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
