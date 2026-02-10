/**
 * Antenatal Record Detail Page
 * 
 * Page for viewing and editing individual antenatal records.
 * Shows record details, visits, ultrasounds, labs, medications, and outcomes.
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import {
  fetchAntenatalRecord,
  updateAntenatalRecord,
  getAntenatalRecordSummary,
  getAntenatalRecordVisits,
  AntenatalRecord,
  AntenatalRecordUpdateData,
  AntenatalRecordSummary,
  AntenatalVisit,
  PregnancyOutcome,
} from '../api/antenatal';
import BackToDashboard from '../components/common/BackToDashboard';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import styles from '../styles/AntenatalRecordForm.module.css';

const OUTCOME_OPTIONS: { value: PregnancyOutcome; label: string }[] = [
  { value: 'ONGOING', label: 'Ongoing Pregnancy' },
  { value: 'DELIVERED', label: 'Delivered' },
  { value: 'MISCARRIAGE', label: 'Miscarriage' },
  { value: 'STILLBIRTH', label: 'Stillbirth' },
  { value: 'TERMINATION', label: 'Termination' },
  { value: 'ECTOPIC', label: 'Ectopic Pregnancy' },
  { value: 'MOLAR', label: 'Molar Pregnancy' },
];

export default function AntenatalRecordDetailPage() {
  const { recordId } = useParams<{ recordId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();

  const [record, setRecord] = useState<AntenatalRecord | null>(null);
  const [summary, setSummary] = useState<AntenatalRecordSummary | null>(null);
  const [visits, setVisits] = useState<AntenatalVisit[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [showEditForm, setShowEditForm] = useState(false);

  // Edit form fields
  const [outcome, setOutcome] = useState<PregnancyOutcome>('ONGOING');
  const [deliveryDate, setDeliveryDate] = useState<string>('');
  const [deliveryGestationalAgeWeeks, setDeliveryGestationalAgeWeeks] = useState<number>(0);
  const [deliveryGestationalAgeDays, setDeliveryGestationalAgeDays] = useState<number>(0);
  const [highRisk, setHighRisk] = useState<boolean>(false);
  const [riskFactors, setRiskFactors] = useState<string>('');
  const [clinicalNotes, setClinicalNotes] = useState<string>('');

  useEffect(() => {
    if (recordId) {
      loadRecord();
    }
  }, [recordId]);

  const loadRecord = async () => {
    if (!recordId) return;

    try {
      setLoading(true);
      const [recordData, summaryData, visitsData] = await Promise.all([
        fetchAntenatalRecord(parseInt(recordId)),
        getAntenatalRecordSummary(parseInt(recordId)),
        getAntenatalRecordVisits(parseInt(recordId)),
      ]);

      setRecord(recordData);
      setSummary(summaryData);
      setVisits(visitsData);

      // Initialize edit form with current values
      setOutcome(recordData.outcome);
      setDeliveryDate(recordData.delivery_date || '');
      setDeliveryGestationalAgeWeeks(recordData.delivery_gestational_age_weeks || 0);
      setDeliveryGestationalAgeDays(recordData.delivery_gestational_age_days || 0);
      setHighRisk(recordData.high_risk);
      setRiskFactors(recordData.risk_factors?.join(', ') || '');
      setClinicalNotes(recordData.clinical_notes || '');
    } catch (error: any) {
      showError(error?.message || 'Failed to load antenatal record');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!recordId) return;

    try {
      setIsUpdating(true);

      const riskFactorsArray = riskFactors
        ? riskFactors.split(',').map(f => f.trim()).filter(f => f)
        : [];

      const data: AntenatalRecordUpdateData = {
        outcome: outcome,
        delivery_date: deliveryDate || undefined,
        delivery_gestational_age_weeks: deliveryGestationalAgeWeeks || undefined,
        delivery_gestational_age_days: deliveryGestationalAgeDays || undefined,
        high_risk: highRisk,
        risk_factors: riskFactorsArray.length > 0 ? riskFactorsArray : undefined,
        clinical_notes: clinicalNotes || undefined,
      };

      await updateAntenatalRecord(parseInt(recordId), data);
      showSuccess('Antenatal record updated successfully');
      setShowEditForm(false);
      await loadRecord();
    } catch (error: any) {
      const errorMessage = error?.responseData?.detail || error?.message || 'Failed to update antenatal record';
      showError(errorMessage);
    } finally {
      setIsUpdating(false);
    }
  };

  const formatGestationalAge = (weeks?: number, days?: number): string => {
    if (weeks === undefined || weeks === null) return 'N/A';
    if (days && days > 0) {
      return `${weeks}w ${days}d`;
    }
    return `${weeks}w`;
  };

  const getOutcomeColor = (outcome: PregnancyOutcome): string => {
    const colors: Record<PregnancyOutcome, string> = {
      ONGOING: '#007bff',
      DELIVERED: '#28a745',
      MISCARRIAGE: '#dc3545',
      STILLBIRTH: '#6c757d',
      TERMINATION: '#ffc107',
      ECTOPIC: '#fd7e14',
      MOLAR: '#e83e8c',
    };
    return colors[outcome] || '#6c757d';
  };

  if (loading) {
    return (
      <div className={styles.pageContainer}>
        <BackToDashboard />
        <LoadingSkeleton count={10} />
      </div>
    );
  }

  if (!record) {
    return (
      <div className={styles.pageContainer}>
        <BackToDashboard />
        <div className={styles.errorContainer}>
          <p>Antenatal record not found</p>
        </div>
      </div>
    );
  }

  const canEdit = user?.role === 'DOCTOR' || user?.role === 'ADMIN';

  return (
    <div className={styles.pageContainer}>
      <BackToDashboard />
      <header className={styles.header}>
        <div>
          <h1>Antenatal Record #{record.id}</h1>
          <p>Patient: {record.patient_name || `Patient ID ${record.patient}`}</p>
        </div>
        <div className={styles.headerActions}>
          {canEdit && !showEditForm && (
            <button
              className={styles.editButton}
              onClick={() => setShowEditForm(true)}
            >
              Edit Record
            </button>
          )}
          <button
            className={styles.secondaryButton}
            onClick={() => navigate('/antenatal')}
          >
            Back to Dashboard
          </button>
        </div>
      </header>

      {/* Summary Cards */}
      {summary && (
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{summary.visits_count}</div>
            <div className={styles.statLabel}>Visits</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{summary.ultrasounds_count}</div>
            <div className={styles.statLabel}>Ultrasounds</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{summary.labs_count}</div>
            <div className={styles.statLabel}>Lab Tests</div>
          </div>
          <div className={styles.statCard} style={{ borderColor: getOutcomeColor(record.outcome) }}>
            <div className={styles.statValue} style={{ color: getOutcomeColor(record.outcome) }}>
              {OUTCOME_OPTIONS.find(o => o.value === record.outcome)?.label || record.outcome}
            </div>
            <div className={styles.statLabel}>Outcome</div>
          </div>
        </div>
      )}

      {/* Edit Form */}
      {showEditForm && canEdit && (
        <div className={styles.editSection}>
          <h2>Edit Antenatal Record</h2>
          <form onSubmit={handleUpdate} className={styles.form}>
            <div className={styles.formGrid}>
              <div className={styles.formGroup}>
                <label>Outcome</label>
                <select
                  value={outcome}
                  onChange={(e) => setOutcome(e.target.value as PregnancyOutcome)}
                >
                  {OUTCOME_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              {outcome === 'DELIVERED' && (
                <>
                  <div className={styles.formGroup}>
                    <label>Delivery Date</label>
                    <input
                      type="date"
                      value={deliveryDate}
                      onChange={(e) => setDeliveryDate(e.target.value)}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>Gestational Age at Delivery (Weeks)</label>
                    <input
                      type="number"
                      min="0"
                      max="45"
                      value={deliveryGestationalAgeWeeks}
                      onChange={(e) => setDeliveryGestationalAgeWeeks(parseInt(e.target.value) || 0)}
                    />
                  </div>
                  <div className={styles.formGroup}>
                    <label>Gestational Age at Delivery (Days)</label>
                    <input
                      type="number"
                      min="0"
                      max="6"
                      value={deliveryGestationalAgeDays}
                      onChange={(e) => setDeliveryGestationalAgeDays(parseInt(e.target.value) || 0)}
                    />
                  </div>
                </>
              )}
              <div className={styles.formGroup}>
                <label>
                  <input
                    type="checkbox"
                    checked={highRisk}
                    onChange={(e) => setHighRisk(e.target.checked)}
                  />
                  High Risk Pregnancy
                </label>
              </div>
              <div className={styles.formGroup}>
                <label>Risk Factors (comma-separated)</label>
                <input
                  type="text"
                  value={riskFactors}
                  onChange={(e) => setRiskFactors(e.target.value)}
                  placeholder="e.g., Advanced maternal age, Hypertension"
                />
              </div>
              <div className={styles.formGroup}>
                <label>Clinical Notes</label>
                <textarea
                  value={clinicalNotes}
                  onChange={(e) => setClinicalNotes(e.target.value)}
                  rows={4}
                />
              </div>
            </div>
            <div className={styles.formActions}>
              <button
                type="button"
                onClick={() => setShowEditForm(false)}
                className={styles.cancelButton}
                disabled={isUpdating}
              >
                Cancel
              </button>
              <button
                type="submit"
                className={styles.submitButton}
                disabled={isUpdating}
              >
                {isUpdating ? 'Updating...' : 'Update Record'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Record Details */}
      <div className={styles.detailsSection}>
        <h2>Record Details</h2>
        <div className={styles.detailsGrid}>
          <div className={styles.detailItem}>
            <label>Pregnancy Number:</label>
            <span>{record.pregnancy_number}</span>
          </div>
          <div className={styles.detailItem}>
            <label>Booking Date:</label>
            <span>{new Date(record.booking_date).toLocaleDateString()}</span>
          </div>
          <div className={styles.detailItem}>
            <label>LMP:</label>
            <span>{new Date(record.lmp).toLocaleDateString()}</span>
          </div>
          <div className={styles.detailItem}>
            <label>EDD:</label>
            <span>{new Date(record.edd).toLocaleDateString()}</span>
          </div>
          <div className={styles.detailItem}>
            <label>Current Gestational Age:</label>
            <span>{formatGestationalAge(record.current_gestational_age_weeks, record.current_gestational_age_days)}</span>
          </div>
          <div className={styles.detailItem}>
            <label>Parity:</label>
            <span>{record.parity}</span>
          </div>
          <div className={styles.detailItem}>
            <label>Gravida:</label>
            <span>{record.gravida}</span>
          </div>
          <div className={styles.detailItem}>
            <label>Para:</label>
            <span>{record.para}</span>
          </div>
          <div className={styles.detailItem}>
            <label>Pregnancy Type:</label>
            <span>{record.pregnancy_type}</span>
          </div>
          <div className={styles.detailItem}>
            <label>Outcome:</label>
            <span
              className={styles.outcomeBadge}
              style={{ backgroundColor: getOutcomeColor(record.outcome) }}
            >
              {OUTCOME_OPTIONS.find(o => o.value === record.outcome)?.label || record.outcome}
            </span>
          </div>
          {record.high_risk && (
            <div className={styles.detailItem}>
              <label>Risk Status:</label>
              <span className={styles.riskBadge}>High Risk</span>
            </div>
          )}
        </div>

        {record.past_medical_history && (
          <div className={styles.detailSection}>
            <h3>Past Medical History</h3>
            <p>{record.past_medical_history}</p>
          </div>
        )}

        {record.clinical_notes && (
          <div className={styles.detailSection}>
            <h3>Clinical Notes</h3>
            <p>{record.clinical_notes}</p>
          </div>
        )}
      </div>

      {/* Visits */}
      <div className={styles.visitsSection}>
        <h2>Antenatal Visits ({visits.length})</h2>
        {visits.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No visits recorded yet</p>
          </div>
        ) : (
          <div className={styles.visitsList}>
            {visits.map((visit) => (
              <div key={visit.id} className={styles.visitCard}>
                <div className={styles.visitHeader}>
                  <h3>Visit #{visit.id}</h3>
                  <span className={styles.visitType}>{visit.visit_type}</span>
                </div>
                <div className={styles.visitDetails}>
                  <p><strong>Date:</strong> {new Date(visit.visit_date).toLocaleDateString()}</p>
                  <p><strong>Gestational Age:</strong> {formatGestationalAge(visit.gestational_age_weeks, visit.gestational_age_days)}</p>
                  {visit.chief_complaint && (
                    <p><strong>Chief Complaint:</strong> {visit.chief_complaint}</p>
                  )}
                  {visit.clinical_notes && (
                    <p><strong>Notes:</strong> {visit.clinical_notes}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
