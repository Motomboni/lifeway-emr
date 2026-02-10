/**
 * Embryo Inventory Page
 * 
 * Shows all frozen embryos with management actions.
 * Supports filtering, thawing, and disposal workflows.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  fetchEmbryoInventory, 
  thawEmbryoFromInventory,
  disposeEmbryoFromInventory,
  EmbryoInventoryItem 
} from '../api/ivf';
import styles from '../styles/EmbryoInventory.module.css';

const GRADE_OPTIONS = [
  { value: '', label: 'All Grades' },
  { value: 'AA', label: 'Grade AA (Excellent)' },
  { value: 'AB', label: 'Grade AB (Good)' },
  { value: 'BA', label: 'Grade BA (Good)' },
  { value: 'BB', label: 'Grade BB (Fair)' },
  { value: 'BC', label: 'Grade BC (Fair)' },
  { value: 'CB', label: 'Grade CB (Poor)' },
  { value: 'CC', label: 'Grade CC (Poor)' },
];

const STAGE_LABELS: Record<string, string> = {
  ZYGOTE: 'Zygote (Day 0)',
  CLEAVAGE: 'Cleavage (Day 2-3)',
  MORULA: 'Morula (Day 4)',
  BLASTOCYST: 'Blastocyst (Day 5-6)',
  HATCHING_BLASTOCYST: 'Hatching Blastocyst',
};

export default function EmbryoInventoryPage() {
  const navigate = useNavigate();
  
  const [embryos, setEmbryos] = useState<EmbryoInventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [gradeFilter, setGradeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('FROZEN');
  const [selectedEmbryo, setSelectedEmbryo] = useState<EmbryoInventoryItem | null>(null);
  const [actionModal, setActionModal] = useState<'thaw' | 'dispose' | null>(null);

  useEffect(() => {
    loadEmbryos();
  }, [gradeFilter, statusFilter]);

  const loadEmbryos = async () => {
    try {
      setLoading(true);
      setError(null);
      const filters: any = {};
      if (gradeFilter) filters.grade = gradeFilter;
      if (statusFilter) filters.status = statusFilter;
      const data = await fetchEmbryoInventory(filters);
      setEmbryos(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load embryo inventory');
    } finally {
      setLoading(false);
    }
  };

  const handleThaw = async (embryoId: number, thawDate: string, thawedBy: string) => {
    try {
      await thawEmbryoFromInventory(embryoId, { thaw_date: thawDate, notes: thawedBy });
      setActionModal(null);
      setSelectedEmbryo(null);
      loadEmbryos();
    } catch (err: any) {
      alert(err.message || 'Failed to thaw embryo');
    }
  };

  const handleDispose = async (embryoId: number, reason: string, disposedBy: string) => {
    try {
      await disposeEmbryoFromInventory(embryoId, { reason, notes: disposedBy });
      setActionModal(null);
      setSelectedEmbryo(null);
      loadEmbryos();
    } catch (err: any) {
      alert(err.message || 'Failed to dispose embryo');
    }
  };

  const getGradeColor = (grade: string): string => {
    if (grade.startsWith('A')) return '#28a745';
    if (grade.startsWith('B') || grade.endsWith('A')) return '#17a2b8';
    if (grade.includes('B')) return '#ffc107';
    return '#dc3545';
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      FROZEN: '#007bff',
      THAWED: '#ffc107',
      TRANSFERRED: '#28a745',
      DISPOSED: '#6c757d',
      DISCARDED: '#dc3545',
    };
    return colors[status] || '#6c757d';
  };

  // Calculate statistics
  const stats = {
    total: embryos.length,
    frozen: embryos.filter(e => e.status === 'FROZEN').length,
    gradeA: embryos.filter(e => e.grade?.startsWith('A')).length,
    avgAge: embryos.length > 0 
      ? Math.round(embryos.reduce((sum, e) => sum + (e.storage_days || 0), 0) / embryos.length)
      : 0,
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
          <h1>Embryo Inventory</h1>
        </div>
      </header>

      {error && (
        <div className={styles.errorBanner}>
          {error}
          <button onClick={loadEmbryos}>Retry</button>
        </div>
      )}

      {/* Statistics Cards */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{stats.total}</div>
          <div className={styles.statLabel}>Total Embryos</div>
        </div>
        <div className={styles.statCard} style={{ borderColor: '#007bff' }}>
          <div className={styles.statValue} style={{ color: '#007bff' }}>{stats.frozen}</div>
          <div className={styles.statLabel}>Frozen</div>
        </div>
        <div className={styles.statCard} style={{ borderColor: '#28a745' }}>
          <div className={styles.statValue} style={{ color: '#28a745' }}>{stats.gradeA}</div>
          <div className={styles.statLabel}>Grade A</div>
        </div>
        <div className={styles.statCard} style={{ borderColor: '#6c757d' }}>
          <div className={styles.statValue} style={{ color: '#6c757d' }}>{stats.avgAge}</div>
          <div className={styles.statLabel}>Avg Storage Days</div>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <select 
          value={statusFilter} 
          onChange={(e) => setStatusFilter(e.target.value)}
          className={styles.filterSelect}
        >
          <option value="">All Statuses</option>
          <option value="FROZEN">Frozen</option>
          <option value="THAWED">Thawed</option>
          <option value="TRANSFERRED">Transferred</option>
          <option value="DISPOSED">Disposed</option>
        </select>
        <select 
          value={gradeFilter} 
          onChange={(e) => setGradeFilter(e.target.value)}
          className={styles.filterSelect}
        >
          {GRADE_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* Embryo Grid */}
      {loading ? (
        <div className={styles.loading}>Loading inventory...</div>
      ) : embryos.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No embryos found matching the selected filters</p>
        </div>
      ) : (
        <div className={styles.embryoGrid}>
          {embryos.map((embryo) => (
            <div key={embryo.id} className={styles.embryoCard}>
              <div className={styles.cardHeader}>
                <span 
                  className={styles.statusBadge}
                  style={{ backgroundColor: getStatusColor(embryo.status) }}
                >
                  {embryo.status}
                </span>
                {embryo.grade && (
                  <span 
                    className={styles.gradeBadge}
                    style={{ borderColor: getGradeColor(embryo.grade), color: getGradeColor(embryo.grade) }}
                  >
                    {embryo.grade}
                  </span>
                )}
              </div>
              
              <div className={styles.cardBody}>
                <div className={styles.embryoId}>
                  Embryo #{embryo.embryo_number}
                </div>
                <div className={styles.patientName}>
                  {embryo.patient_name}
                </div>
                <div className={styles.embryoDetails}>
                  <div className={styles.detailRow}>
                    <span>Stage:</span>
                    <span>{STAGE_LABELS[embryo.stage] || embryo.stage}</span>
                  </div>
                  <div className={styles.detailRow}>
                    <span>Cycle:</span>
                    <span>#{embryo.cycle_number}</span>
                  </div>
                  {embryo.freeze_date && (
                    <div className={styles.detailRow}>
                      <span>Frozen:</span>
                      <span>{embryo.freeze_date}</span>
                    </div>
                  )}
                  {embryo.storage_days !== undefined && embryo.storage_days > 0 && (
                    <div className={styles.detailRow}>
                      <span>Storage:</span>
                      <span>{embryo.storage_days} days</span>
                    </div>
                  )}
                  {embryo.tank_location && (
                    <div className={styles.detailRow}>
                      <span>Tank:</span>
                      <span>{embryo.tank_location}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className={styles.cardActions}>
                <button
                  className={styles.viewButton}
                  onClick={() => navigate(`/ivf/cycles/${embryo.cycle_id}`)}
                >
                  View Cycle
                </button>
                {embryo.status === 'FROZEN' && (
                  <>
                    <button
                      className={styles.thawButton}
                      onClick={() => {
                        setSelectedEmbryo(embryo);
                        setActionModal('thaw');
                      }}
                    >
                      Thaw
                    </button>
                    <button
                      className={styles.disposeButton}
                      onClick={() => {
                        setSelectedEmbryo(embryo);
                        setActionModal('dispose');
                      }}
                    >
                      Dispose
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Storage Information */}
      <div className={styles.storageInfo}>
        <h3>Storage Guidelines</h3>
        <div className={styles.guidelineGrid}>
          <div className={styles.guideline}>
            <strong>Vitrification Method</strong>
            <p>All embryos are cryopreserved using vitrification technique</p>
          </div>
          <div className={styles.guideline}>
            <strong>Storage Temperature</strong>
            <p>Maintained at -196°C in liquid nitrogen</p>
          </div>
          <div className={styles.guideline}>
            <strong>Consent Required</strong>
            <p>Patient consent must be valid for any embryo handling</p>
          </div>
          <div className={styles.guideline}>
            <strong>Storage Limit</strong>
            <p>Per Nigerian regulations, review storage annually</p>
          </div>
        </div>
      </div>

      {/* Thaw Modal */}
      {actionModal === 'thaw' && selectedEmbryo && (
        <ThawModal
          embryo={selectedEmbryo}
          onClose={() => {
            setActionModal(null);
            setSelectedEmbryo(null);
          }}
          onConfirm={handleThaw}
        />
      )}

      {/* Dispose Modal */}
      {actionModal === 'dispose' && selectedEmbryo && (
        <DisposeModal
          embryo={selectedEmbryo}
          onClose={() => {
            setActionModal(null);
            setSelectedEmbryo(null);
          }}
          onConfirm={handleDispose}
        />
      )}
    </div>
  );
}

// Thaw Modal Component
interface ThawModalProps {
  embryo: EmbryoInventoryItem;
  onClose: () => void;
  onConfirm: (embryoId: number, thawDate: string, notes: string) => void;
}

function ThawModal({ embryo, onClose, onConfirm }: ThawModalProps) {
  const [thawDate, setThawDate] = useState(new Date().toISOString().split('T')[0]);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await onConfirm(embryo.id, thawDate, notes);
    setLoading(false);
  };

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h2>Thaw Embryo</h2>
          <button className={styles.closeButton} onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className={styles.modalForm}>
          <div className={styles.embryoInfo}>
            <p><strong>Embryo:</strong> #{embryo.embryo_number}</p>
            <p><strong>Patient:</strong> {embryo.patient_name}</p>
            <p><strong>Grade:</strong> {embryo.grade}</p>
            <p><strong>Frozen since:</strong> {embryo.freeze_date}</p>
          </div>

          <div className={styles.formGroup}>
            <label>Thaw Date *</label>
            <input
              type="date"
              value={thawDate}
              onChange={(e) => setThawDate(e.target.value)}
              required
            />
          </div>

          <div className={styles.formGroup}>
            <label>Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Thaw observations, viability assessment..."
            />
          </div>

          <div className={styles.modalWarning}>
            ⚠️ This action will mark the embryo as THAWED and cannot be undone.
          </div>

          <div className={styles.modalActions}>
            <button type="button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className={styles.thawConfirmBtn} disabled={loading}>
              {loading ? 'Processing...' : 'Confirm Thaw'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Dispose Modal Component
interface DisposeModalProps {
  embryo: EmbryoInventoryItem;
  onClose: () => void;
  onConfirm: (embryoId: number, reason: string, notes: string) => void;
}

function DisposeModal({ embryo, onClose, onConfirm }: DisposeModalProps) {
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const DISPOSAL_REASONS = [
    'Patient request',
    'Storage period expired',
    'Failed viability assessment',
    'Consent withdrawn',
    'Embryo damage',
    'Research donation',
    'Other',
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason) {
      alert('Please select a disposal reason');
      return;
    }
    setLoading(true);
    await onConfirm(embryo.id, reason, notes);
    setLoading(false);
  };

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modal}>
        <div className={styles.modalHeader}>
          <h2>Dispose Embryo</h2>
          <button className={styles.closeButton} onClick={onClose}>×</button>
        </div>
        <form onSubmit={handleSubmit} className={styles.modalForm}>
          <div className={styles.embryoInfo}>
            <p><strong>Embryo:</strong> #{embryo.embryo_number}</p>
            <p><strong>Patient:</strong> {embryo.patient_name}</p>
            <p><strong>Grade:</strong> {embryo.grade}</p>
            <p><strong>Frozen since:</strong> {embryo.freeze_date}</p>
          </div>

          <div className={styles.formGroup}>
            <label>Disposal Reason *</label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
            >
              <option value="">Select reason...</option>
              {DISPOSAL_REASONS.map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Additional details about disposal..."
            />
          </div>

          <div className={styles.modalDanger}>
            ⚠️ WARNING: This action is IRREVERSIBLE. The embryo will be permanently marked as disposed.
          </div>

          <div className={styles.modalActions}>
            <button type="button" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className={styles.disposeConfirmBtn} disabled={loading}>
              {loading ? 'Processing...' : 'Confirm Disposal'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
