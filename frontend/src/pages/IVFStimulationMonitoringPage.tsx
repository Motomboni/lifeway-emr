/**
 * IVF Stimulation Monitoring Page
 * 
 * Nursing-focused page for recording daily ovarian stimulation monitoring data.
 * Includes:
 * - Hormone levels (E2, LH, Progesterone)
 * - Follicle measurements
 * - Endometrial assessment
 * - Medication administration
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  fetchIVFCycleFull,
  fetchStimulationRecords,
  createStimulationRecord,
  IVFCycleFull,
  OvarianStimulation,
  OvarianStimulationCreateData,
  CYCLE_STATUS_LABELS
} from '../api/ivf';
import styles from '../styles/StimulationMonitoring.module.css';

export default function IVFStimulationMonitoringPage() {
  const { cycleId } = useParams<{ cycleId: string }>();
  const navigate = useNavigate();
  
  const [cycle, setCycle] = useState<IVFCycleFull | null>(null);
  const [records, setRecords] = useState<OvarianStimulation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    day: 1,
    date: new Date().toISOString().split('T')[0],
    estradiol: '',
    lh: '',
    progesterone: '',
    endometrial_thickness: '',
    endometrial_pattern: '',
    right_ovary_follicles: '',
    left_ovary_follicles: '',
    notes: '',
    next_appointment: '',
  });

  useEffect(() => {
    if (cycleId) {
      loadData(parseInt(cycleId, 10));
    }
  }, [cycleId]);

  const loadData = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const [cycleData, recordsData] = await Promise.all([
        fetchIVFCycleFull(id),
        fetchStimulationRecords(id)
      ]);
      setCycle(cycleData);
      setRecords(recordsData);
      
      // Set the next day number
      if (recordsData.length > 0) {
        const maxDay = Math.max(...recordsData.map(r => r.day));
        setFormData(prev => ({ ...prev, day: maxDay + 1 }));
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!cycleId) return;

    try {
      setSubmitting(true);
      
      // Parse follicle measurements from comma-separated strings
      const rightFollicles = formData.right_ovary_follicles
        ? formData.right_ovary_follicles.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n))
        : [];
      const leftFollicles = formData.left_ovary_follicles
        ? formData.left_ovary_follicles.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n))
        : [];

      const data: OvarianStimulationCreateData = {
        day: formData.day,
        date: formData.date,
        estradiol: formData.estradiol ? parseFloat(formData.estradiol) : undefined,
        lh: formData.lh ? parseFloat(formData.lh) : undefined,
        progesterone: formData.progesterone ? parseFloat(formData.progesterone) : undefined,
        endometrial_thickness: formData.endometrial_thickness ? parseFloat(formData.endometrial_thickness) : undefined,
        endometrial_pattern: formData.endometrial_pattern || undefined,
        right_ovary_follicles: rightFollicles.length > 0 ? rightFollicles : undefined,
        left_ovary_follicles: leftFollicles.length > 0 ? leftFollicles : undefined,
        notes: formData.notes || undefined,
        next_appointment: formData.next_appointment || undefined,
      };

      await createStimulationRecord(parseInt(cycleId, 10), data);
      setShowNewForm(false);
      loadData(parseInt(cycleId, 10));
      
      // Reset form
      setFormData({
        day: formData.day + 1,
        date: new Date().toISOString().split('T')[0],
        estradiol: '',
        lh: '',
        progesterone: '',
        endometrial_thickness: '',
        endometrial_pattern: '',
        right_ovary_follicles: '',
        left_ovary_follicles: '',
        notes: '',
        next_appointment: '',
      });
    } catch (err: any) {
      alert(err.message || 'Failed to save record');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div className={styles.loading}>Loading...</div>;
  }

  if (error || !cycle) {
    return (
      <div className={styles.error}>
        <p>{error || 'Cycle not found'}</p>
        <button onClick={() => navigate('/ivf')}>Back to IVF Dashboard</button>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <button 
            className={styles.backButton}
            onClick={() => navigate(`/ivf/cycles/${cycleId}`)}
          >
            ← Back to Cycle
          </button>
          <div>
            <h1>Stimulation Monitoring</h1>
            <p className={styles.patientInfo}>
              <strong>{cycle.patient_name}</strong> - Cycle #{cycle.cycle_number}
              <span className={styles.statusBadge}>{CYCLE_STATUS_LABELS[cycle.status]}</span>
            </p>
          </div>
        </div>
        <button 
          className={styles.addButton}
          onClick={() => setShowNewForm(true)}
        >
          + Record Monitoring
        </button>
      </header>

      {/* Monitoring Records Table */}
      <div className={styles.section}>
        <h2>Monitoring History</h2>
        {records.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No monitoring records yet</p>
            <button onClick={() => setShowNewForm(true)}>Add First Record</button>
          </div>
        ) : (
          <div className={styles.tableContainer}>
            <table className={styles.monitoringTable}>
              <thead>
                <tr>
                  <th>Day</th>
                  <th>Date</th>
                  <th>E2 (pg/mL)</th>
                  <th>LH (mIU/mL)</th>
                  <th>P4 (ng/mL)</th>
                  <th>Endo (mm)</th>
                  <th>Right Follicles</th>
                  <th>Left Follicles</th>
                  <th>Total</th>
                  <th>Recorded By</th>
                </tr>
              </thead>
              <tbody>
                {records.map((record) => (
                  <tr key={record.id}>
                    <td><strong>Day {record.day}</strong></td>
                    <td>{record.date}</td>
                    <td>{record.estradiol || '-'}</td>
                    <td>{record.lh || '-'}</td>
                    <td>{record.progesterone || '-'}</td>
                    <td>
                      {record.endometrial_thickness ? (
                        <span>
                          {record.endometrial_thickness}
                          {record.endometrial_pattern && ` (${record.endometrial_pattern})`}
                        </span>
                      ) : '-'}
                    </td>
                    <td>
                      {record.right_ovary_follicles?.length > 0 
                        ? record.right_ovary_follicles.join(', ')
                        : '-'}
                    </td>
                    <td>
                      {record.left_ovary_follicles?.length > 0 
                        ? record.left_ovary_follicles.join(', ')
                        : '-'}
                    </td>
                    <td>
                      <strong>{record.total_follicle_count}</strong>
                      {record.leading_follicles > 0 && (
                        <small> ({record.leading_follicles} ≥14mm)</small>
                      )}
                    </td>
                    <td>{record.recorded_by_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Follicle Growth Chart Placeholder */}
      <div className={styles.section}>
        <h2>Follicle Growth Summary</h2>
        <div className={styles.summaryGrid}>
          <div className={styles.summaryCard}>
            <div className={styles.summaryValue}>
              {records.length > 0 ? records[records.length - 1].total_follicle_count : 0}
            </div>
            <div className={styles.summaryLabel}>Current Total Follicles</div>
          </div>
          <div className={styles.summaryCard}>
            <div className={styles.summaryValue}>
              {records.length > 0 ? records[records.length - 1].leading_follicles : 0}
            </div>
            <div className={styles.summaryLabel}>Leading Follicles (≥14mm)</div>
          </div>
          <div className={styles.summaryCard}>
            <div className={styles.summaryValue}>
              {records.length > 0 && records[records.length - 1].estradiol 
                ? records[records.length - 1].estradiol 
                : '-'}
            </div>
            <div className={styles.summaryLabel}>Latest E2 (pg/mL)</div>
          </div>
          <div className={styles.summaryCard}>
            <div className={styles.summaryValue}>
              {records.length > 0 && records[records.length - 1].endometrial_thickness 
                ? records[records.length - 1].endometrial_thickness 
                : '-'}
            </div>
            <div className={styles.summaryLabel}>Endometrial Thickness (mm)</div>
          </div>
        </div>
      </div>

      {/* New Record Form Modal */}
      {showNewForm && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h2>Record Stimulation Monitoring</h2>
              <button className={styles.closeButton} onClick={() => setShowNewForm(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit} className={styles.form}>
              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Day *</label>
                  <input
                    type="number"
                    value={formData.day}
                    onChange={(e) => setFormData({ ...formData, day: parseInt(e.target.value) })}
                    min="1"
                    required
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Date *</label>
                  <input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                  />
                </div>
              </div>

              <h3 className={styles.sectionTitle}>Hormone Levels</h3>
              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Estradiol (E2) pg/mL</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.estradiol}
                    onChange={(e) => setFormData({ ...formData, estradiol: e.target.value })}
                    placeholder="e.g., 250"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>LH mIU/mL</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.lh}
                    onChange={(e) => setFormData({ ...formData, lh: e.target.value })}
                    placeholder="e.g., 5.2"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Progesterone (P4) ng/mL</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.progesterone}
                    onChange={(e) => setFormData({ ...formData, progesterone: e.target.value })}
                    placeholder="e.g., 0.5"
                  />
                </div>
              </div>

              <h3 className={styles.sectionTitle}>Ultrasound Findings</h3>
              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Endometrial Thickness (mm)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={formData.endometrial_thickness}
                    onChange={(e) => setFormData({ ...formData, endometrial_thickness: e.target.value })}
                    placeholder="e.g., 8.5"
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Endometrial Pattern</label>
                  <select
                    value={formData.endometrial_pattern}
                    onChange={(e) => setFormData({ ...formData, endometrial_pattern: e.target.value })}
                  >
                    <option value="">Select pattern...</option>
                    <option value="TRILAMINAR">Trilaminar (Triple Line)</option>
                    <option value="HYPERECHOIC">Hyperechoic</option>
                    <option value="HYPOECHOIC">Hypoechoic</option>
                    <option value="HOMOGENEOUS">Homogeneous</option>
                  </select>
                </div>
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Right Ovary Follicles (mm)</label>
                  <input
                    type="text"
                    value={formData.right_ovary_follicles}
                    onChange={(e) => setFormData({ ...formData, right_ovary_follicles: e.target.value })}
                    placeholder="e.g., 12, 14, 16, 18"
                  />
                  <small>Enter sizes separated by commas</small>
                </div>
                <div className={styles.formGroup}>
                  <label>Left Ovary Follicles (mm)</label>
                  <input
                    type="text"
                    value={formData.left_ovary_follicles}
                    onChange={(e) => setFormData({ ...formData, left_ovary_follicles: e.target.value })}
                    placeholder="e.g., 10, 13, 15"
                  />
                  <small>Enter sizes separated by commas</small>
                </div>
              </div>

              <h3 className={styles.sectionTitle}>Notes & Follow-up</h3>
              <div className={styles.formGroup}>
                <label>Clinical Notes</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows={3}
                  placeholder="Any observations, patient symptoms, etc..."
                />
              </div>
              <div className={styles.formGroup}>
                <label>Next Appointment</label>
                <input
                  type="datetime-local"
                  value={formData.next_appointment}
                  onChange={(e) => setFormData({ ...formData, next_appointment: e.target.value })}
                />
              </div>

              <div className={styles.formActions}>
                <button type="button" onClick={() => setShowNewForm(false)} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" className={styles.submitButton} disabled={submitting}>
                  {submitting ? 'Saving...' : 'Save Record'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
