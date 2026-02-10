/**
 * Sperm Analyses List Page
 * 
 * Shows all sperm analysis records with filtering and search.
 * Allows creating new analyses and viewing details.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  fetchSpermAnalyses, 
  SpermAnalysisListItem,
  createSpermAnalysis,
  SpermAnalysisCreateData,
  SpermAssessment
} from '../api/ivf';
import { fetchPatients } from '../api/patient';
import { Patient } from '../types/patient';
import styles from '../styles/SpermAnalyses.module.css';

const ASSESSMENT_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Assessments' },
  { value: 'NORMOZOOSPERMIA', label: 'Normozoospermia' },
  { value: 'OLIGOZOOSPERMIA', label: 'Oligozoospermia' },
  { value: 'ASTHENOZOOSPERMIA', label: 'Asthenozoospermia' },
  { value: 'TERATOZOOSPERMIA', label: 'Teratozoospermia' },
  { value: 'OLIGOASTHENOTERATOZOOSPERMIA', label: 'OAT Syndrome' },
  { value: 'AZOOSPERMIA', label: 'Azoospermia' },
  { value: 'CRYPTOZOOSPERMIA', label: 'Cryptozoospermia' },
];

const ASSESSMENT_LABELS: Record<string, string> = {
  NORMOZOOSPERMIA: 'Normozoospermia',
  OLIGOZOOSPERMIA: 'Oligozoospermia',
  ASTHENOZOOSPERMIA: 'Asthenozoospermia',
  TERATOZOOSPERMIA: 'Teratozoospermia',
  OLIGOASTHENOTERATOZOOSPERMIA: 'OAT Syndrome',
  AZOOSPERMIA: 'Azoospermia',
  CRYPTOZOOSPERMIA: 'Cryptozoospermia',
  OLIGOASTHENOZOOSPERMIA: 'Oligoasthenozoospermia',
  NECROZOOSPERMIA: 'Necrozoospermia',
};

export default function SpermAnalysesPage() {
  const navigate = useNavigate();
  
  const [analyses, setAnalyses] = useState<SpermAnalysisListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assessmentFilter, setAssessmentFilter] = useState('');
  const [showNewModal, setShowNewModal] = useState(false);

  useEffect(() => {
    loadAnalyses();
  }, [assessmentFilter]);

  const loadAnalyses = async () => {
    try {
      setLoading(true);
      setError(null);
      const filters = assessmentFilter ? { assessment: assessmentFilter } : undefined;
      const data = await fetchSpermAnalyses(filters);
      setAnalyses(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load sperm analyses');
    } finally {
      setLoading(false);
    }
  };

  const getAssessmentColor = (assessment: string | undefined): string => {
    if (!assessment) return '#6c757d';
    const colors: Record<string, string> = {
      NORMOZOOSPERMIA: '#28a745',
      OLIGOZOOSPERMIA: '#ffc107',
      ASTHENOZOOSPERMIA: '#fd7e14',
      TERATOZOOSPERMIA: '#dc3545',
      OLIGOASTHENOTERATOZOOSPERMIA: '#dc3545',
      AZOOSPERMIA: '#6c757d',
      CRYPTOZOOSPERMIA: '#6c757d',
      OLIGOASTHENOZOOSPERMIA: '#fd7e14',
      NECROZOOSPERMIA: '#dc3545',
    };
    return colors[assessment] || '#6c757d';
  };

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <button 
            className={styles.backButton}
            onClick={() => navigate('/ivf')}
          >
            ← IVF Dashboard
          </button>
          <h1>Sperm Analyses</h1>
        </div>
        <div className={styles.headerActions}>
          <button 
            className={styles.primaryButton}
            onClick={() => setShowNewModal(true)}
          >
            + New Analysis
          </button>
        </div>
      </header>

      {error && (
        <div className={styles.errorBanner}>
          {error}
          <button onClick={loadAnalyses}>Retry</button>
        </div>
      )}

      {/* Filters */}
      <div className={styles.filters}>
        <select 
          value={assessmentFilter} 
          onChange={(e) => setAssessmentFilter(e.target.value)}
          className={styles.filterSelect}
        >
          {ASSESSMENT_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Results Table */}
      {loading ? (
        <div className={styles.loading}>Loading analyses...</div>
      ) : analyses.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No sperm analyses found</p>
          <button 
            className={styles.primaryButton}
            onClick={() => setShowNewModal(true)}
          >
            Create First Analysis
          </button>
        </div>
      ) : (
        <div className={styles.tableContainer}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Patient</th>
                <th>Collection Date</th>
                <th>Concentration</th>
                <th>Motility</th>
                <th>Morphology</th>
                <th>Assessment</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {analyses.map((analysis) => (
                <tr key={analysis.id}>
                  <td>
                    <strong>{analysis.patient_name}</strong>
                  </td>
                  <td>{analysis.collection_date}</td>
                  <td>
                    {analysis.concentration ? (
                      <span>
                        {Number(analysis.concentration).toFixed(1)} M/mL
                        {Number(analysis.concentration) < 16 && (
                          <span className={styles.lowIndicator}> ↓</span>
                        )}
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    {analysis.total_motility ? (
                      <span>
                        {Number(analysis.total_motility).toFixed(0)}%
                        {Number(analysis.total_motility) < 42 && (
                          <span className={styles.lowIndicator}> ↓</span>
                        )}
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    {analysis.normal_forms ? (
                      <span>
                        {Number(analysis.normal_forms).toFixed(0)}%
                        {Number(analysis.normal_forms) < 4 && (
                          <span className={styles.lowIndicator}> ↓</span>
                        )}
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    {analysis.assessment ? (
                      <span 
                        className={styles.assessmentBadge}
                        style={{ 
                          backgroundColor: getAssessmentColor(analysis.assessment),
                          color: '#fff'
                        }}
                      >
                        {ASSESSMENT_LABELS[analysis.assessment] || analysis.assessment}
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    <button
                      className={styles.actionButton}
                      onClick={() => navigate(`/ivf/sperm-analyses/${analysis.id}`)}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reference Values */}
      <div className={styles.referenceValues}>
        <h3>WHO 2021 Reference Values</h3>
        <div className={styles.referenceGrid}>
          <div className={styles.referenceItem}>
            <span className={styles.refLabel}>Concentration:</span>
            <span className={styles.refValue}>≥ 16 million/mL</span>
          </div>
          <div className={styles.referenceItem}>
            <span className={styles.refLabel}>Total Motility:</span>
            <span className={styles.refValue}>≥ 42%</span>
          </div>
          <div className={styles.referenceItem}>
            <span className={styles.refLabel}>Progressive Motility:</span>
            <span className={styles.refValue}>≥ 30%</span>
          </div>
          <div className={styles.referenceItem}>
            <span className={styles.refLabel}>Normal Morphology:</span>
            <span className={styles.refValue}>≥ 4%</span>
          </div>
          <div className={styles.referenceItem}>
            <span className={styles.refLabel}>Volume:</span>
            <span className={styles.refValue}>≥ 1.4 mL</span>
          </div>
          <div className={styles.referenceItem}>
            <span className={styles.refLabel}>Total Sperm Count:</span>
            <span className={styles.refValue}>≥ 39 million</span>
          </div>
        </div>
      </div>

      {/* New Analysis Modal */}
      {showNewModal && (
        <NewAnalysisModal 
          onClose={() => setShowNewModal(false)} 
          onCreated={() => {
            setShowNewModal(false);
            loadAnalyses();
          }}
        />
      )}
    </div>
  );
}

// New Analysis Modal Component
interface NewAnalysisModalProps {
  onClose: () => void;
  onCreated: () => void;
}

function NewAnalysisModal({ onClose, onCreated }: NewAnalysisModalProps) {
  const [patients, setPatients] = useState<Patient[]>([]);
  const [patientSearch, setPatientSearch] = useState('');
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [formData, setFormData] = useState({
    collection_date: new Date().toISOString().split('T')[0],
    abstinence_days: '',
    volume: '',
    concentration: '',
    total_motility: '',
    progressive_motility: '',
    normal_forms: '',
    assessment: '',
    notes: '',
  });

  useEffect(() => {
    const searchPatientsAsync = async () => {
      if (patientSearch.length < 2) return;
      try {
        const data = await fetchPatients(patientSearch);
        setPatients(data);
      } catch (err) {
        console.error('Failed to search patients:', err);
      }
    };
    const debounce = setTimeout(searchPatientsAsync, 300);
    return () => clearTimeout(debounce);
  }, [patientSearch]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPatient) {
      setError('Please select a patient');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const data: SpermAnalysisCreateData = {
        patient: selectedPatient.id,
        collection_date: formData.collection_date,
        abstinence_days: formData.abstinence_days ? parseInt(formData.abstinence_days) : undefined,
        volume: formData.volume ? parseFloat(formData.volume) : undefined,
        concentration: formData.concentration ? parseFloat(formData.concentration) : undefined,
        total_motility: formData.total_motility ? parseFloat(formData.total_motility) : undefined,
        progressive_motility: formData.progressive_motility ? parseFloat(formData.progressive_motility) : undefined,
        normal_forms: formData.normal_forms ? parseFloat(formData.normal_forms) : undefined,
        assessment: formData.assessment ? formData.assessment as SpermAssessment : undefined,
        notes: formData.notes || undefined,
      };

      await createSpermAnalysis(data);
      onCreated();
    } catch (err: any) {
      setError(err.message || 'Failed to create analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h2>New Sperm Analysis</h2>
          <button className={styles.closeButton} onClick={onClose}>×</button>
        </div>

        {error && <div className={styles.modalError}>{error}</div>}

        <form onSubmit={handleSubmit} className={styles.modalForm}>
          <div className={styles.formGroup}>
            <label>Patient *</label>
            <input
              type="text"
              placeholder="Search patient..."
              value={patientSearch}
              onChange={(e) => {
                setPatientSearch(e.target.value);
                setSelectedPatient(null);
              }}
            />
            {patientSearch.length >= 2 && patients.length > 0 && !selectedPatient && (
              <ul className={styles.patientList}>
                {patients.filter(p => p.gender === 'MALE').map(p => (
                  <li key={p.id} onClick={() => {
                    setSelectedPatient(p);
                    setPatientSearch(`${p.first_name} ${p.last_name}`);
                  }}>
                    {p.first_name} {p.last_name} ({p.patient_id})
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Collection Date *</label>
              <input
                type="date"
                value={formData.collection_date}
                onChange={(e) => setFormData({ ...formData, collection_date: e.target.value })}
                required
              />
            </div>
            <div className={styles.formGroup}>
              <label>Abstinence Days</label>
              <input
                type="number"
                value={formData.abstinence_days}
                onChange={(e) => setFormData({ ...formData, abstinence_days: e.target.value })}
                placeholder="2-5 days"
                min="0"
              />
            </div>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Volume (mL)</label>
              <input
                type="number"
                step="0.1"
                value={formData.volume}
                onChange={(e) => setFormData({ ...formData, volume: e.target.value })}
                placeholder="≥1.4"
              />
            </div>
            <div className={styles.formGroup}>
              <label>Concentration (M/mL)</label>
              <input
                type="number"
                step="0.1"
                value={formData.concentration}
                onChange={(e) => setFormData({ ...formData, concentration: e.target.value })}
                placeholder="≥16"
              />
            </div>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Total Motility (%)</label>
              <input
                type="number"
                step="0.1"
                value={formData.total_motility}
                onChange={(e) => setFormData({ ...formData, total_motility: e.target.value })}
                placeholder="≥42"
              />
            </div>
            <div className={styles.formGroup}>
              <label>Progressive Motility (%)</label>
              <input
                type="number"
                step="0.1"
                value={formData.progressive_motility}
                onChange={(e) => setFormData({ ...formData, progressive_motility: e.target.value })}
                placeholder="≥30"
              />
            </div>
          </div>

          <div className={styles.formRow}>
            <div className={styles.formGroup}>
              <label>Normal Morphology (%)</label>
              <input
                type="number"
                step="0.1"
                value={formData.normal_forms}
                onChange={(e) => setFormData({ ...formData, normal_forms: e.target.value })}
                placeholder="≥4"
              />
            </div>
            <div className={styles.formGroup}>
              <label>Assessment</label>
              <select
                value={formData.assessment}
                onChange={(e) => setFormData({ ...formData, assessment: e.target.value })}
              >
                <option value="">Select assessment...</option>
                {ASSESSMENT_OPTIONS.slice(1).map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className={styles.formGroup}>
            <label>Notes</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              rows={3}
              placeholder="Additional observations..."
            />
          </div>

          <div className={styles.modalActions}>
            <button type="button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className={styles.submitBtn} disabled={loading || !selectedPatient}>
              {loading ? 'Creating...' : 'Create Analysis'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
