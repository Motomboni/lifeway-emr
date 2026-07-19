/**
 * NHIA claim lifecycle panel for a single visit.
 *
 * NHIA does not publish a public claims API — staff export the claim pack and
 * upload via the official NHIA portal manually, then record status here.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  downloadVisitClaimPackCsv,
  getVisitNHIAClaim,
  nhiaClaimAction,
  NHIAClaimSubmission,
} from '../../api/billing';
import { useToast } from '../../hooks/useToast';
import styles from '../../styles/VisitDetails.module.css';

interface NHIAVisitClaimPanelProps {
  visitId: number;
}

export default function NHIAVisitClaimPanel({ visitId }: NHIAVisitClaimPanelProps) {
  const { showError, showSuccess } = useToast();
  const navigate = useNavigate();
  const [claim, setClaim] = useState<NHIAClaimSubmission | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const loadClaim = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getVisitNHIAClaim(visitId);
      setClaim(data);
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Failed to load NHIA claim');
      setClaim(null);
    } finally {
      setLoading(false);
    }
  }, [visitId, showError]);

  useEffect(() => {
    loadClaim();
  }, [loadClaim]);

  const runAction = async (
    action: 'validate' | 'export' | 'submit' | 'paid' | 'deny' | 'resubmit' | 'draft',
    extra?: { reason?: string },
  ) => {
    setBusy(action);
    try {
      const updated = await nhiaClaimAction(visitId, action, extra);
      setClaim(updated);
      if (action === 'submit') {
        showSuccess(
          updated.nhia_portal_reference
            ? `Recorded as submitted locally (portal ref ${updated.nhia_portal_reference})`
            : 'Recorded as submitted locally — enter portal ref on NHIA site if needed',
        );
      } else {
        showSuccess(`Claim ${action} completed`);
      }
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : `Claim ${action} failed`);
    } finally {
      setBusy(null);
    }
  };

  if (loading) {
    return <p>Loading NHIA claim status…</p>;
  }

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <h2>NHIA Claim</h2>
        <button type="button" onClick={() => navigate('/billing/nhia-compliance')}>
          Open compliance dashboard
        </button>
      </div>

      {claim ? (
        <>
          <p className={styles.nhiaManualWorkflowNote} role="note">
            NHIA has no public claims API. Export the claim pack CSV, upload it through the
            official NHIA portal, then use the buttons below to track status in this EMR.
          </p>
          <p>
            <strong>Status:</strong> {claim.status}
            {claim.claim_reference ? ` · Ref ${claim.claim_reference}` : ''}
          </p>
          <p>
            <strong>Lines:</strong> {claim.line_count} · <strong>Total:</strong> ₦
            {claim.total_amount_ngn}
          </p>
          {claim.national_health_id && (
            <p>
              <strong>NHID:</strong> {claim.national_health_id}
              {claim.id_verified ? ' (verified)' : ' (not verified)'}
            </p>
          )}
          {claim.validation_errors?.length > 0 && (
            <ul>
              {claim.validation_errors.map((err) => (
                <li key={err}>{err}</li>
              ))}
            </ul>
          )}
          {claim.denial_reason && (
            <p>
              <strong>Denial:</strong> {claim.denial_reason}
            </p>
          )}

          {claim.nhia_portal_reference && (
            <p>
              <strong>Portal ref (from NHIA site):</strong> {claim.nhia_portal_reference}
            </p>
          )}

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.75rem' }}>
            <button
              type="button"
              disabled={!!busy}
              onClick={async () => {
                try {
                  setBusy('csv');
                  await downloadVisitClaimPackCsv(visitId);
                  showSuccess('Claim pack CSV downloaded — upload via NHIA portal');
                } catch (e: unknown) {
                  showError(e instanceof Error ? e.message : 'Export failed');
                } finally {
                  setBusy(null);
                }
              }}
            >
              {busy === 'csv' ? 'Downloading…' : 'Download claim pack (for NHIA portal)'}
            </button>
            <button type="button" disabled={!!busy} onClick={() => runAction('validate')}>
              {busy === 'validate' ? 'Validating…' : 'Validate'}
            </button>
            <button type="button" disabled={!!busy} onClick={() => runAction('export')}>
              {busy === 'export' ? 'Updating…' : 'Mark pack exported'}
            </button>
            <button
              type="button"
              disabled={!!busy || claim.status !== 'EXPORTED'}
              title={
                claim.status !== 'EXPORTED'
                  ? 'Mark the claim pack exported before recording manual portal submission'
                  : 'Record that this claim was uploaded via the NHIA portal (manual step)'
              }
              onClick={() => runAction('submit')}
            >
              {busy === 'submit' ? 'Recording…' : 'Record manual portal submission'}
            </button>
            <button
              type="button"
              disabled={!!busy}
              onClick={() => runAction('paid')}
              title="After checking the NHIA portal, record that payment was received"
            >
              {busy === 'paid' ? 'Updating…' : 'Mark paid (manual reconciliation)'}
            </button>
            <button
              type="button"
              disabled={!!busy}
              onClick={async () => {
                const reason = window.prompt('Denial reason from NHIA portal:');
                if (!reason?.trim()) return;
                setBusy('deny');
                try {
                  const updated = await nhiaClaimAction(visitId, 'deny', { reason: reason.trim() });
                  setClaim(updated);
                  showSuccess('Claim marked denied');
                } catch (e: unknown) {
                  showError(e instanceof Error ? e.message : 'Failed to record denial');
                } finally {
                  setBusy(null);
                }
              }}
              title="Record denial after checking the NHIA portal"
            >
              {busy === 'deny' ? 'Updating…' : 'Mark denied'}
            </button>
          </div>
        </>
      ) : (
        <p>No NHIA claim draft yet.</p>
      )}
    </section>
  );
}
