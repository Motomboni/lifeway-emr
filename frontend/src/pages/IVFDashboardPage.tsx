/**
 * IVF Dashboard Page
 * 
 * Main dashboard for IVF specialists and embryologists.
 * Shows statistics, recent cycles, and quick actions.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  fetchIVFCycles, 
  fetchIVFStatistics,
  IVFCycleListItem,
  IVFStatistics,
  CYCLE_STATUS_LABELS,
  CYCLE_TYPE_LABELS
} from '../api/ivf';
import { logger } from '../utils/logger';
import styles from '../styles/Dashboard.module.css';

export default function IVFDashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };
  
  const [cycles, setCycles] = useState<IVFCycleListItem[]>([]);
  const [statistics, setStatistics] = useState<IVFStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      logger.debug('IVF Dashboard: Starting data load...');

      const [cyclesData, statsData] = await Promise.all([
        fetchIVFCycles(statusFilter ? { status: statusFilter as any } : undefined),
        fetchIVFStatistics()
      ]);

      logger.debug('IVF Dashboard: Cycles loaded:', cyclesData, 'Statistics:', statsData);

      setCycles(cyclesData);
      setStatistics(statsData);
    } catch (err: any) {
      console.error('🔬 IVF Dashboard: Error loading data:', err);
      setError(err.message || 'Failed to load IVF data');
    } finally {
      setLoading(false);
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
        <div className={styles.loading}>Loading IVF Dashboard...</div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1>IVF Treatment Center</h1>
          <p>Welcome, {user?.first_name || user?.username} ({user?.role})</p>
        </div>
        <div className={styles.headerActions}>
          <button 
            className={styles.primaryButton}
            onClick={() => navigate('/ivf/cycles/new')}
          >
            + New IVF Cycle
          </button>
          <button 
            className={styles.secondaryButton}
            onClick={() => navigate('/dashboard')}
          >
            Main Dashboard
          </button>
          <button 
            className={styles.logoutButton}
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </header>

      {error && (
        <div className={styles.errorBanner}>
          {error}
          <button onClick={loadData}>Retry</button>
        </div>
      )}

      {/* Statistics Cards */}
      {statistics && (
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{statistics.total_cycles}</div>
            <div className={styles.statLabel}>Total Cycles</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{statistics.completed_cycles}</div>
            <div className={styles.statLabel}>Completed Cycles</div>
          </div>
          <div className={styles.statCard} style={{ borderColor: '#28a745' }}>
            <div className={styles.statValue} style={{ color: '#28a745' }}>
              {statistics.pregnancy_rate.toFixed(1)}%
            </div>
            <div className={styles.statLabel}>Pregnancy Rate</div>
          </div>
          <div className={styles.statCard} style={{ borderColor: '#007bff' }}>
            <div className={styles.statValue} style={{ color: '#007bff' }}>
              {statistics.clinical_pregnancy_rate.toFixed(1)}%
            </div>
            <div className={styles.statLabel}>Clinical Pregnancy Rate</div>
          </div>
          <div className={styles.statCard} style={{ borderColor: '#6f42c1' }}>
            <div className={styles.statValue} style={{ color: '#6f42c1' }}>
              {statistics.live_birth_rate.toFixed(1)}%
            </div>
            <div className={styles.statLabel}>Live Birth Rate</div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className={styles.quickActions}>
        <h2 className={styles.quickActionsHeading}>Quick Actions</h2>
        <div className={styles.actionGrid}>
          <button 
            className={styles.actionCard}
            onClick={() => navigate('/ivf/cycles')}
          >
            <span className={styles.actionIcon}>📋</span>
            <span>View All Cycles</span>
          </button>
          {(user?.role === 'IVF_SPECIALIST' || user?.role === 'ADMIN') && (
            <button 
              className={styles.actionCard}
              onClick={() => navigate('/ivf/cycles/new')}
            >
              <span className={styles.actionIcon}>➕</span>
              <span>New IVF Cycle</span>
            </button>
          )}
          {(user?.role === 'IVF_SPECIALIST' || user?.role === 'EMBRYOLOGIST' || user?.role === 'ADMIN' || user?.role === 'DOCTOR') && (
            <button 
              className={styles.actionCard}
              onClick={() => navigate('/ivf/sperm-analyses')}
            >
              <span className={styles.actionIcon}>🔬</span>
              <span>Sperm Analyses</span>
            </button>
          )}
          {(user?.role === 'IVF_SPECIALIST' || user?.role === 'EMBRYOLOGIST' || user?.role === 'ADMIN') && (
            <button 
              className={styles.actionCard}
              onClick={() => navigate('/ivf/embryo-inventory')}
            >
              <span className={styles.actionIcon}>🧬</span>
              <span>Embryo Inventory</span>
            </button>
          )}
          {(user?.role === 'IVF_SPECIALIST' || user?.role === 'ADMIN') && (
            <button 
              className={styles.actionCard}
              onClick={() => navigate('/ivf/reports')}
            >
              <span className={styles.actionIcon}>📊</span>
              <span>Reports</span>
            </button>
          )}
          <button 
            className={styles.actionCard}
            onClick={() => navigate('/ivf/patients')}
          >
            <span className={styles.actionIcon}>👥</span>
            <span>IVF Patients</span>
          </button>
          <button 
            className={styles.actionCard}
            onClick={() => navigate('/ivf/visits')}
          >
            <span className={styles.actionIcon}>📅</span>
            <span>IVF Patient Visits</span>
          </button>
        </div>
      </div>

      {/* Nurse-Specific Actions */}
      {(user?.role === 'NURSE' || user?.role === 'IVF_SPECIALIST' || user?.role === 'ADMIN') && (
        <div className={styles.nurseActionsSection}>
          <h2>Nursing Tasks</h2>
          <p className={styles.nurseDescription}>
            Select a cycle from the table below to record stimulation monitoring or medication administration.
          </p>
          <div className={styles.nurseTaskGrid}>
            <div className={styles.nurseTaskCard}>
              <span className={styles.nurseTaskIcon}>📊</span>
              <div className={styles.nurseTaskContent}>
                <h3>Stimulation Monitoring</h3>
                <p>Record daily hormone levels (E2, LH, P4), follicle measurements, and endometrial assessment</p>
              </div>
            </div>
            <div className={styles.nurseTaskCard}>
              <span className={styles.nurseTaskIcon}>💊</span>
              <div className={styles.nurseTaskContent}>
                <h3>Medication Administration</h3>
                <p>View prescribed medications and record administration times and notes</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Active Cycles */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <h2>Recent IVF Cycles</h2>
          <select 
            value={statusFilter} 
            onChange={(e) => setStatusFilter(e.target.value)}
            className={styles.filterSelect}
          >
            <option value="">All Statuses</option>
            <option value="PLANNED">Planned</option>
            <option value="STIMULATION">Stimulation</option>
            <option value="RETRIEVAL">Retrieval</option>
            <option value="TRANSFER">Transfer</option>
            <option value="LUTEAL">Luteal Phase</option>
            <option value="PREGNANCY_TEST">Pregnancy Test</option>
            <option value="PREGNANT">Pregnant</option>
            <option value="COMPLETED">Completed</option>
          </select>
        </div>

        {cycles.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No IVF cycles found</p>
            <button 
              className={styles.primaryButton}
              onClick={() => navigate('/ivf/cycles/new')}
            >
              Start New Cycle
            </button>
          </div>
        ) : (
          <div className={styles.tableContainer}>
            <table className={styles.dataTable}>
              <thead>
                <tr>
                  <th>Cycle #</th>
                  <th>Patient</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Start Date</th>
                  <th>Consent</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {cycles.map((cycle) => (
                  <tr key={cycle.id}>
                    <td>
                      <strong>#{cycle.cycle_number}</strong>
                    </td>
                    <td>
                      <div>{cycle.patient_name}</div>
                      {cycle.partner_name && (
                        <small style={{ color: '#6c757d' }}>
                          Partner: {cycle.partner_name}
                        </small>
                      )}
                    </td>
                    <td>{CYCLE_TYPE_LABELS[cycle.cycle_type]}</td>
                    <td>
                      <span 
                        className={styles.statusBadge}
                        style={{ 
                          backgroundColor: getStatusColor(cycle.status),
                          color: '#fff'
                        }}
                      >
                        {CYCLE_STATUS_LABELS[cycle.status]}
                      </span>
                    </td>
                    <td>
                      {cycle.actual_start_date || cycle.planned_start_date || '-'}
                    </td>
                    <td>
                      {cycle.consent_signed ? (
                        <span style={{ color: '#28a745' }}>✓ Signed</span>
                      ) : (
                        <span style={{ color: '#dc3545' }}>⚠ Pending</span>
                      )}
                    </td>
                    <td>
                      <div className={styles.actionButtons}>
                        <button
                          className={styles.actionButton}
                          onClick={() => navigate(`/ivf/cycles/${cycle.id}`)}
                        >
                          View
                        </button>
                        {(user?.role === 'NURSE' || user?.role === 'IVF_SPECIALIST' || user?.role === 'ADMIN') && (
                          <>
                            <button
                              className={styles.actionButton}
                              onClick={() => navigate(`/ivf/cycles/${cycle.id}/stimulation`)}
                              title="Stimulation Monitoring"
                            >
                              📊
                            </button>
                            <button
                              className={styles.actionButton}
                              onClick={() => navigate(`/ivf/cycles/${cycle.id}/medications`)}
                              title="Medication Administration"
                            >
                              💊
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Status Distribution Chart */}
      {statistics && statistics.cycles_by_status.length > 0 && (
        <div className={styles.section}>
          <h2>Cycles by Status</h2>
          <div className={styles.chartContainer}>
            {statistics.cycles_by_status.map((item) => (
              <div key={item.status} className={styles.chartBar}>
                <div className={styles.chartLabel}>
                  {CYCLE_STATUS_LABELS[item.status] || item.status}
                </div>
                <div className={styles.chartBarContainer}>
                  <div 
                    className={styles.chartBarFill}
                    style={{ 
                      width: `${(item.count / statistics.total_cycles) * 100}%`,
                      backgroundColor: getStatusColor(item.status)
                    }}
                  />
                  <span className={styles.chartValue}>{item.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
