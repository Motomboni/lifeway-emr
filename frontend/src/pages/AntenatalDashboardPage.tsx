/**
 * Antenatal Clinic Dashboard Page
 * 
 * Main dashboard for antenatal clinic management.
 * Shows antenatal records, statistics, and quick actions.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  fetchAntenatalRecords,
  AntenatalRecordListItem,
  PregnancyOutcome,
} from '../api/antenatal';
import { useToast } from '../hooks/useToast';
import styles from '../styles/AntenatalDashboard.module.css';

const OUTCOME_LABELS: Record<PregnancyOutcome, string> = {
  ONGOING: 'Ongoing',
  DELIVERED: 'Delivered',
  MISCARRIAGE: 'Miscarriage',
  STILLBIRTH: 'Stillbirth',
  TERMINATION: 'Termination',
  ECTOPIC: 'Ectopic',
  MOLAR: 'Molar',
};

export default function AntenatalDashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { showError } = useToast();

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };
  
  const [records, setRecords] = useState<AntenatalRecordListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [outcomeFilter, setOutcomeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadData();
  }, [outcomeFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const filters: any = {};
      if (outcomeFilter) {
        filters.outcome = outcomeFilter;
      }
      if (searchQuery) {
        filters.search = searchQuery;
      }

      const recordsData = await fetchAntenatalRecords(filters);
      setRecords(recordsData);
    } catch (err: any) {
      console.error('Error loading antenatal records:', err);
      setError(err.message || 'Failed to load antenatal records');
      showError(err.message || 'Failed to load antenatal records');
    } finally {
      setLoading(false);
    }
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

  const formatGestationalAge = (weeks?: number, days?: number): string => {
    if (weeks === undefined || weeks === null) return 'N/A';
    if (days && days > 0) {
      return `${weeks}w ${days}d`;
    }
    return `${weeks}w`;
  };

  const statistics = {
    total: records.length,
    ongoing: records.filter(r => r.outcome === 'ONGOING').length,
    delivered: records.filter(r => r.outcome === 'DELIVERED').length,
    high_risk: records.filter(r => r.high_risk).length,
  };

  if (loading) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.loading}>Loading Antenatal Dashboard...</div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1>Antenatal Clinic Management</h1>
          <p>Welcome, {user?.first_name || user?.username} ({user?.role})</p>
        </div>
        <div className={styles.headerActions}>
          <button 
            className={styles.primaryButton}
            onClick={() => navigate('/antenatal/records/new')}
          >
            + New Antenatal Record
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
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statValue}>{statistics.total}</div>
          <div className={styles.statLabel}>Total Records</div>
        </div>
        <div className={styles.statCard} style={{ borderColor: '#007bff' }}>
          <div className={styles.statValue} style={{ color: '#007bff' }}>
            {statistics.ongoing}
          </div>
          <div className={styles.statLabel}>Ongoing Pregnancies</div>
        </div>
        <div className={styles.statCard} style={{ borderColor: '#28a745' }}>
          <div className={styles.statValue} style={{ color: '#28a745' }}>
            {statistics.delivered}
          </div>
          <div className={styles.statLabel}>Delivered</div>
        </div>
        <div className={styles.statCard} style={{ borderColor: '#ffc107' }}>
          <div className={styles.statValue} style={{ color: '#ffc107' }}>
            {statistics.high_risk}
          </div>
          <div className={styles.statLabel}>High Risk</div>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filtersSection}>
        <div className={styles.searchBox}>
          <input
            type="text"
            placeholder="Search by patient name or MRN..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                loadData();
              }
            }}
          />
          <button onClick={loadData}>Search</button>
        </div>
        <div className={styles.filterButtons}>
          <button
            className={outcomeFilter === '' ? styles.activeFilter : ''}
            onClick={() => {
              setOutcomeFilter('');
              loadData();
            }}
          >
            All
          </button>
          <button
            className={outcomeFilter === 'ONGOING' ? styles.activeFilter : ''}
            onClick={() => {
              setOutcomeFilter('ONGOING');
              loadData();
            }}
          >
            Ongoing
          </button>
          <button
            className={outcomeFilter === 'DELIVERED' ? styles.activeFilter : ''}
            onClick={() => {
              setOutcomeFilter('DELIVERED');
              loadData();
            }}
          >
            Delivered
          </button>
        </div>
      </div>

      {/* Records Table */}
      <div className={styles.recordsSection}>
        <h2>Antenatal Records</h2>
        {records.length === 0 ? (
          <div className={styles.emptyState}>
            <p>No antenatal records found.</p>
            <button 
              className={styles.primaryButton}
              onClick={() => navigate('/antenatal/records/new')}
            >
              Create First Record
            </button>
          </div>
        ) : (
          <table className={styles.recordsTable}>
            <thead>
              <tr>
                <th>Patient</th>
                <th>Pregnancy #</th>
                <th>Booking Date</th>
                <th>LMP</th>
                <th>EDD</th>
                <th>Gestational Age</th>
                <th>Outcome</th>
                <th>Risk</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id}>
                  <td>{record.patient_name}</td>
                  <td>{record.pregnancy_number}</td>
                  <td>{new Date(record.booking_date).toLocaleDateString()}</td>
                  <td>{new Date(record.lmp).toLocaleDateString()}</td>
                  <td>{new Date(record.edd).toLocaleDateString()}</td>
                  <td>
                    {formatGestationalAge(
                      record.current_gestational_age_weeks,
                      record.current_gestational_age_days
                    )}
                  </td>
                  <td>
                    <span
                      className={styles.outcomeBadge}
                      style={{ backgroundColor: getOutcomeColor(record.outcome) }}
                    >
                      {OUTCOME_LABELS[record.outcome]}
                    </span>
                  </td>
                  <td>
                    {record.high_risk && (
                      <span className={styles.riskBadge}>High Risk</span>
                    )}
                  </td>
                  <td>
                    <button
                      className={styles.viewButton}
                      onClick={() => navigate(`/antenatal/records/${record.id}`)}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
