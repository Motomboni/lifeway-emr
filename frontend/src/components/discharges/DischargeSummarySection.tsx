/**
 * Discharge Summary Section Component
 * 
 * Component for viewing and creating discharge summaries for closed visits.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import {
  fetchDischargeSummary,
  createDischargeSummary,
  exportDischargeSummaryAsText,
  exportDischargeSummaryAsHTML,
} from '../../api/discharges';
import {
  DischargeSummary,
  DischargeSummaryCreate,
  DischargeCondition,
  DischargeDisposition,
} from '../../types/discharges';
import { Consultation } from '../../types/consultation';
import { fetchAdmission, Admission } from '../../api/admissions';
import { logger } from '../../utils/logger';
import styles from '../../styles/VisitDetails.module.css';

interface DischargeSummarySectionProps {
  visitId: number;
  visitStatus: string;
  consultation: Consultation | null;
}

export default function DischargeSummarySection({
  visitId,
  visitStatus,
  consultation,
}: DischargeSummarySectionProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [dischargeSummary, setDischargeSummary] = useState<DischargeSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [admission, setAdmission] = useState<Admission | null>(null);
  
  const [formData, setFormData] = useState<DischargeSummaryCreate>({
    consultation: consultation?.id || 0,
    chief_complaint: '',
    admission_date: new Date().toISOString().slice(0, 16),
    discharge_date: new Date().toISOString().slice(0, 16),
    diagnosis: '',
    procedures_performed: '',
    treatment_summary: '',
    medications_on_discharge: '',
    follow_up_instructions: '',
    condition_at_discharge: 'STABLE',
    discharge_disposition: 'HOME',
  });

  useEffect(() => {
    if (visitStatus === 'CLOSED') {
      loadDischargeSummary();
      loadAdmission();
    }
  }, [visitId, visitStatus]);

  useEffect(() => {
    if (consultation) {
      setFormData(prev => ({ ...prev, consultation: consultation.id }));
    }
  }, [consultation]);

  useEffect(() => {
    // Auto-populate form fields from admission and consultation when form is opened
    if (showForm && (admission || consultation)) {
      const newFormData: Partial<DischargeSummaryCreate> = {};
      
      // Populate from admission if available
      if (admission) {
        if (admission.chief_complaint) {
          newFormData.chief_complaint = admission.chief_complaint;
        }
        if (admission.admission_date) {
          newFormData.admission_date = new Date(admission.admission_date).toISOString().slice(0, 16);
        }
        if (admission.discharge_date) {
          newFormData.discharge_date = new Date(admission.discharge_date).toISOString().slice(0, 16);
        }
      }
      
      // Populate from consultation if available
      if (consultation) {
        if (consultation.diagnosis) {
          newFormData.diagnosis = consultation.diagnosis;
        }
        if (consultation.clinical_notes) {
          newFormData.treatment_summary = consultation.clinical_notes;
        }
      }
      
      // Only update if we have data to populate
      if (Object.keys(newFormData).length > 0) {
        setFormData(prev => ({ ...prev, ...newFormData }));
      }
    }
  }, [showForm, admission, consultation]);

  const loadAdmission = async () => {
    try {
      const admissionData = await fetchAdmission(visitId);
      setAdmission(admissionData);
    } catch (error: any) {
      // 404 is expected if there's no admission
      if (error.status !== 404) {
        logger.error('Failed to load admission:', error);
      }
    }
  };

  const loadDischargeSummary = async () => {
    try {
      setLoading(true);
      const summary = await fetchDischargeSummary(visitId);
      setDischargeSummary(summary);
    } catch (error: any) {
      logger.error('Failed to load discharge summary:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!consultation) {
      showError('Consultation must exist before creating discharge summary');
      return;
    }
    
    try {
      setSaving(true);
      const summary = await createDischargeSummary(visitId, {
        ...formData,
        consultation: consultation.id,
      });
      setDischargeSummary(summary);
      showSuccess('Discharge summary created successfully');
      setShowForm(false);
    } catch (error: any) {
      showError(error.message || 'Failed to create discharge summary');
    } finally {
      setSaving(false);
    }
  };

  const handleExportText = async () => {
    if (!dischargeSummary) return;
    
    try {
      const blob = await exportDischargeSummaryAsText(visitId, dischargeSummary.id);
      const url = window.URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = `discharge_summary_${visitId}.txt`;
      window.document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(link);
      showSuccess('Discharge summary exported as text');
    } catch (error: any) {
      showError(error.message || 'Failed to export discharge summary');
    }
  };

  const handleExportHTML = async () => {
    if (!dischargeSummary) return;
    
    try {
      const blob = await exportDischargeSummaryAsHTML(visitId, dischargeSummary.id);
      const url = window.URL.createObjectURL(blob);
      const link = window.document.createElement('a');
      link.href = url;
      link.download = `discharge_summary_${visitId}.html`;
      window.document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(url);
      window.document.body.removeChild(link);
      showSuccess('Discharge summary exported as HTML');
    } catch (error: any) {
      showError(error.message || 'Failed to export discharge summary');
    }
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  if (visitStatus !== 'CLOSED') {
    return null; // Only show for closed visits
  }

  if (loading) {
    return (
      <section className={styles.section}>
        <h2>Discharge Summary</h2>
        <p>Loading...</p>
      </section>
    );
  }

  const isDoctor = user?.role === 'DOCTOR';
  const canCreate = isDoctor && consultation && !dischargeSummary;

  return (
    <section className={styles.section}>
      <div className={styles.sectionHeader}>
        <h2>Discharge Summary</h2>
        {canCreate && (
          <button
            className={styles.addButton}
            onClick={() => setShowForm(!showForm)}
          >
            {showForm ? 'Cancel' : '+ Create Discharge Summary'}
          </button>
        )}
        {dischargeSummary && (
          <div className={styles.exportButtons}>
            <button
              className={styles.exportButton}
              onClick={handleExportText}
              title="Export as text file"
            >
              📄 Text
            </button>
            <button
              className={styles.exportButton}
              onClick={handleExportHTML}
              title="Export as HTML file"
            >
              🌐 HTML
            </button>
          </div>
        )}
      </div>

      {showForm && canCreate && (
        <form onSubmit={handleSubmit} className={styles.dischargeForm}>
          <div className={styles.formRow}>
            <label>
              Chief Complaint <span className={styles.required}>*</span>
              <textarea
                value={formData.chief_complaint}
                onChange={(e) =>
                  setFormData({ ...formData, chief_complaint: e.target.value })
                }
                required
                rows={3}
                placeholder="Chief complaint at admission"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Admission Date <span className={styles.required}>*</span>
              <input
                type="datetime-local"
                value={formData.admission_date}
                onChange={(e) =>
                  setFormData({ ...formData, admission_date: e.target.value })
                }
                required
              />
            </label>
            <label>
              Discharge Date <span className={styles.required}>*</span>
              <input
                type="datetime-local"
                value={formData.discharge_date}
                onChange={(e) =>
                  setFormData({ ...formData, discharge_date: e.target.value })
                }
                required
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Diagnosis <span className={styles.required}>*</span>
              <textarea
                value={formData.diagnosis}
                onChange={(e) =>
                  setFormData({ ...formData, diagnosis: e.target.value })
                }
                required
                rows={4}
                placeholder="Primary and secondary diagnoses"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Procedures Performed
              <textarea
                value={formData.procedures_performed}
                onChange={(e) =>
                  setFormData({ ...formData, procedures_performed: e.target.value })
                }
                rows={3}
                placeholder="Procedures performed during visit"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Treatment Summary <span className={styles.required}>*</span>
              <textarea
                value={formData.treatment_summary}
                onChange={(e) =>
                  setFormData({ ...formData, treatment_summary: e.target.value })
                }
                required
                rows={5}
                placeholder="Summary of treatment provided"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Medications on Discharge
              <textarea
                value={formData.medications_on_discharge}
                onChange={(e) =>
                  setFormData({ ...formData, medications_on_discharge: e.target.value })
                }
                rows={3}
                placeholder="Medications prescribed at discharge"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Follow-up Instructions <span className={styles.required}>*</span>
              <textarea
                value={formData.follow_up_instructions}
                onChange={(e) =>
                  setFormData({ ...formData, follow_up_instructions: e.target.value })
                }
                required
                rows={4}
                placeholder="Follow-up care instructions"
              />
            </label>
          </div>

          <div className={styles.formRow}>
            <label>
              Condition at Discharge
              <select
                value={formData.condition_at_discharge}
                onChange={(e) =>
                  setFormData({ ...formData, condition_at_discharge: e.target.value as DischargeCondition })
                }
              >
                <option value="STABLE">Stable</option>
                <option value="IMPROVED">Improved</option>
                <option value="UNCHANGED">Unchanged</option>
                <option value="DETERIORATED">Deteriorated</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </label>
            <label>
              Discharge Disposition
              <select
                value={formData.discharge_disposition}
                onChange={(e) =>
                  setFormData({ ...formData, discharge_disposition: e.target.value as DischargeDisposition })
                }
              >
                <option value="HOME">Home</option>
                <option value="TRANSFER">Transfer to Another Facility</option>
                <option value="AMA">Against Medical Advice</option>
                <option value="EXPIRED">Expired</option>
                <option value="OTHER">Other</option>
              </select>
            </label>
          </div>

          <div className={styles.formActions}>
            <button
              type="submit"
              className={styles.primaryButton}
              disabled={saving}
            >
              {saving ? 'Creating...' : 'Create Discharge Summary'}
            </button>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => setShowForm(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {dischargeSummary ? (
        <div className={styles.dischargeCard}>
          <div className={styles.dischargeHeader}>
            <div>
              <strong>Discharge Summary</strong>
              <span className={styles.badge}>{dischargeSummary.condition_at_discharge}</span>
              <span className={styles.badge}>{dischargeSummary.discharge_disposition}</span>
            </div>
            <div className={styles.meta}>
              <span>Created by: {dischargeSummary.created_by_name}</span>
              <span>Date: {formatDateTime(dischargeSummary.created_at)}</span>
            </div>
          </div>
          
          <div className={styles.dischargeDetails}>
            <div className={styles.detailItem}>
              <label>Admission Date:</label>
              <p>{formatDateTime(dischargeSummary.admission_date)}</p>
            </div>
            <div className={styles.detailItem}>
              <label>Discharge Date:</label>
              <p>{formatDateTime(dischargeSummary.discharge_date)}</p>
            </div>
            <div className={styles.detailItem}>
              <label>Chief Complaint:</label>
              <p>{dischargeSummary.chief_complaint}</p>
            </div>
            <div className={styles.detailItem}>
              <label>Diagnosis:</label>
              <p>{dischargeSummary.diagnosis}</p>
            </div>
            {dischargeSummary.procedures_performed && (
              <div className={styles.detailItem}>
                <label>Procedures Performed:</label>
                <p>{dischargeSummary.procedures_performed}</p>
              </div>
            )}
            <div className={styles.detailItem}>
              <label>Treatment Summary:</label>
              <p>{dischargeSummary.treatment_summary}</p>
            </div>
            {dischargeSummary.medications_on_discharge && (
              <div className={styles.detailItem}>
                <label>Medications on Discharge:</label>
                <p>{dischargeSummary.medications_on_discharge}</p>
              </div>
            )}
            <div className={styles.detailItem}>
              <label>Follow-up Instructions:</label>
              <p>{dischargeSummary.follow_up_instructions}</p>
            </div>
          </div>
        </div>
      ) : !showForm && (
        <div className={styles.emptyText}>
          {isDoctor && consultation ? (
            <div>
              <p>No discharge summary created yet.</p>
              <p className={styles.helpText}>
                {admission 
                  ? 'Click "Create Discharge Summary" to create one. Form fields will be auto-populated from admission and consultation data.'
                  : 'Click "Create Discharge Summary" to create one. Form fields will be auto-populated from consultation data.'}
              </p>
            </div>
          ) : (
            <div>
              <p>No discharge summary available for this visit.</p>
              {!consultation && (
                <p className={styles.helpText}>
                  A consultation must exist before a discharge summary can be created.
                </p>
              )}
              {!isDoctor && (
                <p className={styles.helpText}>
                  Only doctors can create discharge summaries.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
