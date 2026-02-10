/**
 * IVF Cycle Detail Page
 * 
 * Comprehensive view of a single IVF cycle with all related data.
 * Includes tabs for stimulation, embryos, transfers, medications, etc.
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  fetchIVFCycleFull,
  advanceCycleStatus,
  cancelIVFCycle,
  IVFCycleFull,
  CycleStatus,
  CYCLE_STATUS_LABELS,
  CYCLE_TYPE_LABELS,
  EMBRYO_STATUS_LABELS
} from '../api/ivf';
import { logger } from '../utils/logger';
import styles from '../styles/CycleDetail.module.css';

type TabType = 'overview' | 'stimulation' | 'embryos' | 'transfers' | 'medications' | 'consents';

export default function IVFCycleDetailPage() {
  const { cycleId } = useParams<{ cycleId: string }>();
  const navigate = useNavigate();
  
  const [cycle, setCycle] = useState<IVFCycleFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    logger.debug('IVFCycleDetailPage: cycleId from URL params:', cycleId);
    
    if (!cycleId) {
      logger.debug('IVFCycleDetailPage: No cycle ID in URL');
      setError('No cycle ID provided');
      setLoading(false);
      return;
    }
    
    const numericId = parseInt(cycleId, 10);
    logger.debug('IVFCycleDetailPage: Parsed numeric ID:', numericId);
    
    if (isNaN(numericId) || numericId <= 0) {
      logger.debug('IVFCycleDetailPage: Invalid ID');
      setError('Invalid cycle ID');
      setLoading(false);
      return;
    }
    
    loadCycle(numericId);
  }, [cycleId]);

  const loadCycle = async (id: number) => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchIVFCycleFull(id);
      setCycle(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load cycle details');
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus: CycleStatus) => {
    if (!cycle) return;
    
    try {
      setActionLoading(true);
      await advanceCycleStatus(cycle.id, newStatus);
      await loadCycle(cycle.id);
    } catch (err: any) {
      alert(err.message || 'Failed to update status');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelCycle = async () => {
    if (!cycle) return;
    
    const reason = prompt('Enter cancellation reason:');
    if (!reason) return;
    
    try {
      setActionLoading(true);
      await cancelIVFCycle(cycle.id, reason as any, '');
      await loadCycle(cycle.id);
    } catch (err: any) {
      alert(err.message || 'Failed to cancel cycle');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      PLANNED: '#6c757d',
      STIMULATION: '#17a2b8',
      RETRIEVAL: '#ffc107',
      FERTILIZATION: '#fd7e14',
      CULTURE: '#e83e8c',
      TRANSFER: '#6f42c1',
      LUTEAL: '#20c997',
      PREGNANCY_TEST: '#007bff',
      PREGNANT: '#28a745',
      NOT_PREGNANT: '#dc3545',
      CANCELLED: '#6c757d',
      COMPLETED: '#28a745',
    };
    return colors[status] || '#6c757d';
  };

  if (loading) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.loading}>Loading cycle details...</div>
      </div>
    );
  }

  if (error || !cycle) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.error}>
          {error || 'Cycle not found'}
          <button onClick={() => navigate('/ivf/cycles')}>Back to Cycles</button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      {/* Header */}
      <header className={styles.header}>
        <button 
          className={styles.backButton}
          onClick={() => navigate('/ivf/cycles')}
        >
          ← Back to Cycles
        </button>
        <div className={styles.headerContent}>
          <h1>IVF Cycle #{cycle.cycle_number}</h1>
          <span 
            className={styles.statusBadge}
            style={{ backgroundColor: getStatusColor(cycle.status) }}
          >
            {CYCLE_STATUS_LABELS[cycle.status]}
          </span>
        </div>
        <div className={styles.headerActions}>
          {cycle.status !== 'COMPLETED' && cycle.status !== 'CANCELLED' && (
            <>
              <select 
                onChange={(e) => e.target.value && handleStatusChange(e.target.value as CycleStatus)}
                disabled={actionLoading}
                className={styles.statusSelect}
                value=""
              >
                <option value="">Change Status...</option>
                <option value="STIMULATION">Start Stimulation</option>
                <option value="RETRIEVAL">Proceed to Retrieval</option>
                <option value="FERTILIZATION">Fertilization</option>
                <option value="CULTURE">Embryo Culture</option>
                <option value="TRANSFER">Embryo Transfer</option>
                <option value="LUTEAL">Luteal Phase</option>
                <option value="PREGNANCY_TEST">Pregnancy Test</option>
                <option value="PREGNANT">Pregnant</option>
                <option value="NOT_PREGNANT">Not Pregnant</option>
                <option value="COMPLETED">Complete Cycle</option>
              </select>
              <button 
                className={styles.dangerButton}
                onClick={handleCancelCycle}
                disabled={actionLoading}
              >
                Cancel Cycle
              </button>
            </>
          )}
        </div>
      </header>

      {/* Patient Info Card */}
      <div className={styles.infoCard}>
        <div className={styles.infoGrid}>
          <div className={styles.infoItem}>
            <label>Patient</label>
            <span>{cycle.patient_name}</span>
          </div>
          {cycle.partner_name && (
            <div className={styles.infoItem}>
              <label>Partner</label>
              <span>{cycle.partner_name}</span>
            </div>
          )}
          <div className={styles.infoItem}>
            <label>Cycle Type</label>
            <span>{CYCLE_TYPE_LABELS[cycle.cycle_type]}</span>
          </div>
          <div className={styles.infoItem}>
            <label>Protocol</label>
            <span>{cycle.protocol || 'Not specified'}</span>
          </div>
          <div className={styles.infoItem}>
            <label>Start Date</label>
            <span>{cycle.actual_start_date || cycle.planned_start_date || '-'}</span>
          </div>
          <div className={styles.infoItem}>
            <label>Consent Status</label>
            <span style={{ color: cycle.consent_signed ? '#28a745' : '#dc3545' }}>
              {cycle.consent_signed ? '✓ Signed' : '⚠ Pending'}
            </span>
          </div>
        </div>
      </div>

      {/* Consent Warning */}
      {!cycle.consent_signed && (
        <div className={styles.warningBanner}>
          <strong>⚠ Consent Required:</strong> Patient consent must be signed before proceeding with treatment.
          This is a legal requirement under Nigerian healthcare regulations.
          <button onClick={() => setActiveTab('consents')}>
            Manage Consents
          </button>
        </div>
      )}

      {/* Nurse Quick Actions */}
      <div className={styles.nurseActions}>
        <h3>Nursing Actions</h3>
        <div className={styles.actionButtons}>
          <button 
            className={styles.nurseActionButton}
            onClick={() => navigate(`/ivf/cycles/${cycleId}/stimulation`)}
          >
            <span className={styles.actionIcon}>📊</span>
            <span>Stimulation Monitoring</span>
            <small>Record daily hormone levels & follicle measurements</small>
          </button>
          <button 
            className={styles.nurseActionButton}
            onClick={() => navigate(`/ivf/cycles/${cycleId}/medications`)}
          >
            <span className={styles.actionIcon}>💊</span>
            <span>Medication Administration</span>
            <small>View prescriptions & record administration</small>
          </button>
        </div>
      </div>

      {/* Cycle Summary Cards */}
      <div className={styles.summaryGrid}>
        <div className={styles.summaryCard}>
          <div className={styles.summaryIcon}>🥚</div>
          <div className={styles.summaryContent}>
            <div className={styles.summaryValue}>
              {cycle.oocyte_retrieval?.total_oocytes_retrieved || '-'}
            </div>
            <div className={styles.summaryLabel}>Oocytes Retrieved</div>
          </div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryIcon}>🧬</div>
          <div className={styles.summaryContent}>
            <div className={styles.summaryValue}>{cycle.total_embryos}</div>
            <div className={styles.summaryLabel}>Total Embryos</div>
          </div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryIcon}>❄️</div>
          <div className={styles.summaryContent}>
            <div className={styles.summaryValue}>{cycle.frozen_embryos}</div>
            <div className={styles.summaryLabel}>Frozen Embryos</div>
          </div>
        </div>
        <div className={styles.summaryCard}>
          <div className={styles.summaryIcon}>🎯</div>
          <div className={styles.summaryContent}>
            <div className={styles.summaryValue}>{cycle.transferred_embryos}</div>
            <div className={styles.summaryLabel}>Transferred</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        <button 
          className={`${styles.tab} ${activeTab === 'overview' ? styles.active : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button 
          className={`${styles.tab} ${activeTab === 'stimulation' ? styles.active : ''}`}
          onClick={() => setActiveTab('stimulation')}
        >
          Stimulation ({cycle.stimulation_records.length})
        </button>
        <button 
          className={`${styles.tab} ${activeTab === 'embryos' ? styles.active : ''}`}
          onClick={() => setActiveTab('embryos')}
        >
          Embryos ({cycle.embryos.length})
        </button>
        <button 
          className={`${styles.tab} ${activeTab === 'transfers' ? styles.active : ''}`}
          onClick={() => setActiveTab('transfers')}
        >
          Transfers ({cycle.embryo_transfers.length})
        </button>
        <button 
          className={`${styles.tab} ${activeTab === 'medications' ? styles.active : ''}`}
          onClick={() => setActiveTab('medications')}
        >
          Medications ({cycle.medications.length})
        </button>
        <button 
          className={`${styles.tab} ${activeTab === 'consents' ? styles.active : ''}`}
          onClick={() => setActiveTab('consents')}
        >
          Consents ({cycle.consents.length})
        </button>
      </div>

      {/* Tab Content */}
      <div className={styles.tabContent}>
        {activeTab === 'overview' && (
          <div className={styles.overviewTab}>
            <div className={styles.section}>
              <h3>Diagnosis</h3>
              <p>{cycle.diagnosis || 'No diagnosis recorded'}</p>
            </div>
            
            <div className={styles.section}>
              <h3>Clinical Notes</h3>
              <p>{cycle.clinical_notes || 'No notes recorded'}</p>
            </div>

            {cycle.outcome && (
              <div className={styles.section}>
                <h3>Outcome</h3>
                <div className={styles.outcomeGrid}>
                  <div>
                    <label>Clinical Pregnancy</label>
                    <span>{cycle.outcome.clinical_pregnancy ? 'Yes' : 'No'}</span>
                  </div>
                  <div>
                    <label>Fetal Heartbeat</label>
                    <span>{cycle.outcome.fetal_heartbeat ? 'Yes' : 'No'}</span>
                  </div>
                  <div>
                    <label>Live Births</label>
                    <span>{cycle.outcome.live_births}</span>
                  </div>
                </div>
              </div>
            )}

            {cycle.pregnancy_outcome && (
              <div className={styles.section}>
                <h3>Pregnancy Result</h3>
                <p>
                  <strong>Outcome:</strong> {cycle.pregnancy_outcome}
                  {cycle.beta_hcg_result && (
                    <span> | <strong>Beta-hCG:</strong> {cycle.beta_hcg_result} mIU/mL</span>
                  )}
                </p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'stimulation' && (
          <div className={styles.stimulationTab}>
            <div className={styles.sectionHeader}>
              <h3>Ovarian Stimulation Monitoring</h3>
              <button 
                className={styles.addButton}
                onClick={() => navigate(`/ivf/cycles/${cycle.id}/stimulation/new`)}
              >
                + Add Record
              </button>
            </div>
            
            {cycle.stimulation_records.length === 0 ? (
              <p className={styles.emptyState}>No stimulation records yet</p>
            ) : (
              <div className={styles.tableContainer}>
                <table className={styles.dataTable}>
                  <thead>
                    <tr>
                      <th>Day</th>
                      <th>Date</th>
                      <th>E2 (pg/mL)</th>
                      <th>LH</th>
                      <th>Endometrium (mm)</th>
                      <th>Follicles</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cycle.stimulation_records.map((record) => (
                      <tr key={record.id}>
                        <td>Day {record.day}</td>
                        <td>{record.date}</td>
                        <td>{record.estradiol || '-'}</td>
                        <td>{record.lh || '-'}</td>
                        <td>{record.endometrial_thickness || '-'}</td>
                        <td>
                          {record.total_follicle_count} total 
                          ({record.leading_follicles} ≥14mm)
                        </td>
                        <td>
                          <button 
                            className={styles.actionButton}
                            onClick={() => navigate(`/ivf/cycles/${cycle.id}/stimulation/${record.id}`)}
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
          </div>
        )}

        {activeTab === 'embryos' && (
          <div className={styles.embryosTab}>
            <div className={styles.sectionHeader}>
              <h3>Embryo Records</h3>
              <button 
                className={styles.addButton}
                onClick={() => navigate(`/ivf/cycles/${cycle.id}/embryos/new`)}
              >
                + Add Embryo
              </button>
            </div>
            
            {cycle.embryos.length === 0 ? (
              <p className={styles.emptyState}>No embryos recorded yet</p>
            ) : (
              <div className={styles.embryoGrid}>
                {cycle.embryos.map((embryo) => (
                  <div 
                    key={embryo.id} 
                    className={styles.embryoCard}
                    onClick={() => navigate(`/ivf/cycles/${cycle.id}/embryos/${embryo.id}`)}
                  >
                    <div className={styles.embryoHeader}>
                      <span className={styles.embryoNumber}>#{embryo.embryo_number}</span>
                      <span 
                        className={styles.embryoStatus}
                        style={{ backgroundColor: getStatusColor(embryo.status) }}
                      >
                        {EMBRYO_STATUS_LABELS[embryo.status]}
                      </span>
                    </div>
                    <div className={styles.embryoDetails}>
                      <div><strong>Lab ID:</strong> {embryo.lab_id}</div>
                      <div><strong>Method:</strong> {embryo.fertilization_method}</div>
                      {embryo.day3_grade && <div><strong>Day 3:</strong> {embryo.day3_grade}</div>}
                      {embryo.blastocyst_grade && <div><strong>Blast:</strong> {embryo.blastocyst_grade}</div>}
                      {embryo.pgt_performed && (
                        <div>
                          <strong>PGT:</strong> {embryo.pgt_result || 'Pending'}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'transfers' && (
          <div className={styles.transfersTab}>
            <div className={styles.sectionHeader}>
              <h3>Embryo Transfers</h3>
              <button 
                className={styles.addButton}
                onClick={() => navigate(`/ivf/cycles/${cycle.id}/transfers/new`)}
              >
                + Record Transfer
              </button>
            </div>
            
            {cycle.embryo_transfers.length === 0 ? (
              <p className={styles.emptyState}>No transfers recorded yet</p>
            ) : (
              <div className={styles.tableContainer}>
                <table className={styles.dataTable}>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Type</th>
                      <th>Embryos</th>
                      <th>Stage</th>
                      <th>Difficulty</th>
                      <th>Doctor</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cycle.embryo_transfers.map((transfer) => (
                      <tr key={transfer.id}>
                        <td>{transfer.transfer_date}</td>
                        <td>{transfer.transfer_type}</td>
                        <td>{transfer.embryos_transferred_count}</td>
                        <td>{transfer.embryo_stage || '-'}</td>
                        <td>{transfer.difficulty}</td>
                        <td>{transfer.performed_by_name}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'medications' && (
          <div className={styles.medicationsTab}>
            <div className={styles.sectionHeader}>
              <h3>Medications</h3>
              <button 
                className={styles.addButton}
                onClick={() => navigate(`/ivf/cycles/${cycle.id}/medications/new`)}
              >
                + Add Medication
              </button>
            </div>
            
            {cycle.medications.length === 0 ? (
              <p className={styles.emptyState}>No medications recorded yet</p>
            ) : (
              <div className={styles.tableContainer}>
                <table className={styles.dataTable}>
                  <thead>
                    <tr>
                      <th>Medication</th>
                      <th>Category</th>
                      <th>Dose</th>
                      <th>Route</th>
                      <th>Frequency</th>
                      <th>Start</th>
                      <th>End</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cycle.medications.map((med) => (
                      <tr key={med.id}>
                        <td><strong>{med.medication_name}</strong></td>
                        <td>{med.category}</td>
                        <td>{med.dose} {med.unit}</td>
                        <td>{med.route}</td>
                        <td>{med.frequency}</td>
                        <td>{med.start_date}</td>
                        <td>{med.end_date || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'consents' && (
          <div className={styles.consentsTab}>
            <div className={styles.sectionHeader}>
              <h3>Consent Forms</h3>
              <button 
                className={styles.addButton}
                onClick={() => navigate(`/ivf/cycles/${cycle.id}/consents/new`)}
              >
                + Add Consent
              </button>
            </div>
            
            {cycle.consents.length === 0 ? (
              <p className={styles.emptyState}>No consents recorded yet</p>
            ) : (
              <div className={styles.tableContainer}>
                <table className={styles.dataTable}>
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Patient</th>
                      <th>Status</th>
                      <th>Signed Date</th>
                      <th>Witness</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cycle.consents.map((consent) => (
                      <tr key={consent.id}>
                        <td>{consent.consent_type}</td>
                        <td>{consent.patient_name}</td>
                        <td>
                          {consent.revoked ? (
                            <span style={{ color: '#dc3545' }}>Revoked</span>
                          ) : consent.signed ? (
                            <span style={{ color: '#28a745' }}>✓ Signed</span>
                          ) : (
                            <span style={{ color: '#ffc107' }}>Pending</span>
                          )}
                        </td>
                        <td>{consent.signed_date || '-'}</td>
                        <td>{consent.witness_name || '-'}</td>
                        <td>
                          {!consent.signed && !consent.revoked && (
                            <button className={styles.actionButton}>
                              Sign
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
