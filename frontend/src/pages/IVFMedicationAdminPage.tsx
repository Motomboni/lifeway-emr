/**
 * IVF Medication Administration Page
 * 
 * Nursing-focused page for viewing prescribed medications and recording administration.
 * Includes:
 * - List of prescribed medications for the cycle
 * - Administration recording
 * - Patient instructions
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  fetchIVFCycleFull,
  fetchIVFMedications,
  createIVFMedication,
  IVFCycleFull,
  IVFMedication,
  IVFMedicationCreateData,
  CYCLE_STATUS_LABELS
} from '../api/ivf';
import styles from '../styles/MedicationAdmin.module.css';

const MEDICATION_CATEGORIES = [
  { value: 'GNRH_AGONIST', label: 'GnRH Agonist' },
  { value: 'GNRH_ANTAGONIST', label: 'GnRH Antagonist' },
  { value: 'GONADOTROPIN', label: 'Gonadotropin' },
  { value: 'HCG', label: 'hCG (Trigger)' },
  { value: 'PROGESTERONE', label: 'Progesterone' },
  { value: 'ESTROGEN', label: 'Estrogen' },
  { value: 'ANTIBIOTIC', label: 'Antibiotic' },
  { value: 'OTHER', label: 'Other' },
];

const ROUTES = [
  { value: 'SUBCUTANEOUS', label: 'Subcutaneous (SC)' },
  { value: 'INTRAMUSCULAR', label: 'Intramuscular (IM)' },
  { value: 'ORAL', label: 'Oral (PO)' },
  { value: 'VAGINAL', label: 'Vaginal' },
  { value: 'TRANSDERMAL', label: 'Transdermal' },
];

export default function IVFMedicationAdminPage() {
  const { cycleId } = useParams<{ cycleId: string }>();
  const navigate = useNavigate();
  
  const [cycle, setCycle] = useState<IVFCycleFull | null>(null);
  const [medications, setMedications] = useState<IVFMedication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [administrationNotes, setAdministrationNotes] = useState<Record<number, string>>({});
  
  // Form state for new medication
  const [formData, setFormData] = useState({
    medication_name: '',
    category: 'GONADOTROPIN',
    dose: '',
    unit: 'IU',
    route: 'SUBCUTANEOUS',
    frequency: '',
    start_date: new Date().toISOString().split('T')[0],
    end_date: '',
    instructions: '',
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
      const [cycleData, medsData] = await Promise.all([
        fetchIVFCycleFull(id),
        fetchIVFMedications(id)
      ]);
      setCycle(cycleData);
      setMedications(medsData);
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

      const data: IVFMedicationCreateData = {
        medication_name: formData.medication_name,
        category: formData.category as any,
        dose: parseFloat(formData.dose),
        unit: formData.unit,
        route: formData.route,
        frequency: formData.frequency,
        start_date: formData.start_date,
        end_date: formData.end_date || undefined,
        instructions: formData.instructions || undefined,
      };

      await createIVFMedication(parseInt(cycleId, 10), data);
      setShowNewForm(false);
      loadData(parseInt(cycleId, 10));
      
      // Reset form
      setFormData({
        medication_name: '',
        category: 'GONADOTROPIN',
        dose: '',
        unit: 'IU',
        route: 'SUBCUTANEOUS',
        frequency: '',
        start_date: new Date().toISOString().split('T')[0],
        end_date: '',
        instructions: '',
      });
    } catch (err: any) {
      alert(err.message || 'Failed to add medication');
    } finally {
      setSubmitting(false);
    }
  };

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      GNRH_AGONIST: '#6f42c1',
      GNRH_ANTAGONIST: '#e83e8c',
      GONADOTROPIN: '#007bff',
      HCG: '#fd7e14',
      PROGESTERONE: '#20c997',
      ESTROGEN: '#17a2b8',
      ANTIBIOTIC: '#ffc107',
      OTHER: '#6c757d',
    };
    return colors[category] || '#6c757d';
  };

  const isActiveMedication = (med: IVFMedication): boolean => {
    const today = new Date().toISOString().split('T')[0];
    if (med.end_date && med.end_date < today) return false;
    if (med.start_date > today) return false;
    return true;
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

  const activeMeds = medications.filter(isActiveMedication);
  const pastMeds = medications.filter(m => !isActiveMedication(m));

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
            <h1>Medication Administration</h1>
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
          + Add Medication
        </button>
      </header>

      {/* Active Medications */}
      <div className={styles.section}>
        <h2>Active Medications ({activeMeds.length})</h2>
        {activeMeds.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No active medications</p>
          </div>
        ) : (
          <div className={styles.medicationGrid}>
            {activeMeds.map((med) => (
              <div key={med.id} className={styles.medicationCard}>
                <div className={styles.cardHeader}>
                  <span 
                    className={styles.categoryBadge}
                    style={{ backgroundColor: getCategoryColor(med.category) }}
                  >
                    {MEDICATION_CATEGORIES.find(c => c.value === med.category)?.label || med.category}
                  </span>
                  <span className={styles.activeBadge}>Active</span>
                </div>
                <div className={styles.cardBody}>
                  <h3>{med.medication_name}</h3>
                  <div className={styles.doseInfo}>
                    <span className={styles.dose}>{med.dose} {med.unit}</span>
                    <span className={styles.route}>
                      {ROUTES.find(r => r.value === med.route)?.label || med.route}
                    </span>
                  </div>
                  <div className={styles.frequency}>
                    <strong>Frequency:</strong> {med.frequency}
                  </div>
                  <div className={styles.dates}>
                    <span>Start: {med.start_date}</span>
                    {med.end_date && <span>End: {med.end_date}</span>}
                  </div>
                  {med.instructions && (
                    <div className={styles.instructions}>
                      <strong>Instructions:</strong>
                      <p>{med.instructions}</p>
                    </div>
                  )}
                  <div className={styles.prescribedBy}>
                    Prescribed by: {med.prescribed_by_name}
                  </div>
                </div>
                <div className={styles.cardActions}>
                  <div className={styles.adminNote}>
                    <input
                      type="text"
                      placeholder="Administration note..."
                      value={administrationNotes[med.id] || ''}
                      onChange={(e) => setAdministrationNotes({
                        ...administrationNotes,
                        [med.id]: e.target.value
                      })}
                    />
                    <button 
                      className={styles.adminButton}
                      onClick={() => {
                        alert(`Recorded administration of ${med.medication_name}`);
                        setAdministrationNotes({ ...administrationNotes, [med.id]: '' });
                      }}
                    >
                      Record Given
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Medication Schedule Summary */}
      <div className={styles.section}>
        <h2>Today's Schedule</h2>
        <div className={styles.scheduleTable}>
          <table>
            <thead>
              <tr>
                <th>Medication</th>
                <th>Dose</th>
                <th>Route</th>
                <th>Frequency</th>
                <th>Special Instructions</th>
              </tr>
            </thead>
            <tbody>
              {activeMeds.map((med) => (
                <tr key={med.id}>
                  <td>
                    <strong>{med.medication_name}</strong>
                    <span 
                      className={styles.smallBadge}
                      style={{ backgroundColor: getCategoryColor(med.category) }}
                    >
                      {MEDICATION_CATEGORIES.find(c => c.value === med.category)?.label}
                    </span>
                  </td>
                  <td>{med.dose} {med.unit}</td>
                  <td>{ROUTES.find(r => r.value === med.route)?.label}</td>
                  <td>{med.frequency}</td>
                  <td>{med.instructions || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Past Medications */}
      {pastMeds.length > 0 && (
        <div className={styles.section}>
          <h2>Completed/Discontinued Medications ({pastMeds.length})</h2>
          <div className={styles.pastMedicationsTable}>
            <table>
              <thead>
                <tr>
                  <th>Medication</th>
                  <th>Category</th>
                  <th>Dose</th>
                  <th>Duration</th>
                  <th>Prescribed By</th>
                </tr>
              </thead>
              <tbody>
                {pastMeds.map((med) => (
                  <tr key={med.id}>
                    <td>{med.medication_name}</td>
                    <td>
                      <span 
                        className={styles.smallBadge}
                        style={{ backgroundColor: getCategoryColor(med.category) }}
                      >
                        {MEDICATION_CATEGORIES.find(c => c.value === med.category)?.label}
                      </span>
                    </td>
                    <td>{med.dose} {med.unit}</td>
                    <td>{med.start_date} - {med.end_date || 'N/A'}</td>
                    <td>{med.prescribed_by_name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Important Notes */}
      <div className={styles.notesSection}>
        <h3>Nursing Notes</h3>
        <ul>
          <li>Always verify patient identity before medication administration</li>
          <li>Check for allergies before administering any new medication</li>
          <li>Document injection site and any patient reactions</li>
          <li>Ensure proper storage of medications (refrigeration as required)</li>
          <li>Report any adverse reactions to the IVF Specialist immediately</li>
        </ul>
      </div>

      {/* New Medication Form Modal */}
      {showNewForm && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <div className={styles.modalHeader}>
              <h2>Add Medication</h2>
              <button className={styles.closeButton} onClick={() => setShowNewForm(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit} className={styles.form}>
              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Medication Name *</label>
                  <input
                    type="text"
                    value={formData.medication_name}
                    onChange={(e) => setFormData({ ...formData, medication_name: e.target.value })}
                    placeholder="e.g., Gonal-F"
                    required
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Category *</label>
                  <select
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                    required
                  >
                    {MEDICATION_CATEGORIES.map(cat => (
                      <option key={cat.value} value={cat.value}>{cat.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Dose *</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.dose}
                    onChange={(e) => setFormData({ ...formData, dose: e.target.value })}
                    placeholder="e.g., 150"
                    required
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>Unit *</label>
                  <select
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                    required
                  >
                    <option value="IU">IU</option>
                    <option value="mg">mg</option>
                    <option value="mcg">mcg</option>
                    <option value="mL">mL</option>
                    <option value="units">units</option>
                  </select>
                </div>
                <div className={styles.formGroup}>
                  <label>Route *</label>
                  <select
                    value={formData.route}
                    onChange={(e) => setFormData({ ...formData, route: e.target.value })}
                    required
                  >
                    {ROUTES.map(route => (
                      <option key={route.value} value={route.value}>{route.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Frequency *</label>
                  <input
                    type="text"
                    value={formData.frequency}
                    onChange={(e) => setFormData({ ...formData, frequency: e.target.value })}
                    placeholder="e.g., Once daily at 9 PM"
                    required
                  />
                </div>
              </div>

              <div className={styles.formRow}>
                <div className={styles.formGroup}>
                  <label>Start Date *</label>
                  <input
                    type="date"
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    required
                  />
                </div>
                <div className={styles.formGroup}>
                  <label>End Date</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  />
                </div>
              </div>

              <div className={styles.formGroup}>
                <label>Instructions</label>
                <textarea
                  value={formData.instructions}
                  onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
                  rows={3}
                  placeholder="Special instructions for administration..."
                />
              </div>

              <div className={styles.formActions}>
                <button type="button" onClick={() => setShowNewForm(false)} disabled={submitting}>
                  Cancel
                </button>
                <button type="submit" className={styles.submitButton} disabled={submitting}>
                  {submitting ? 'Saving...' : 'Add Medication'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
