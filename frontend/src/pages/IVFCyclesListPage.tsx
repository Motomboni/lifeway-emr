/**
 * IVF Cycles List Page
 * 
 * List all IVF cycles with filtering and search capabilities.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  fetchIVFCycles,
  IVFCycleListItem,
  CYCLE_STATUS_LABELS,
  CYCLE_TYPE_LABELS
} from '../api/ivf';
import styles from '../styles/CyclesList.module.css';

export default function IVFCyclesListPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const patientIdFromUrl = searchParams.get('patient');
  
  const [cycles, setCycles] = useState<IVFCycleListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters (patient from URL when coming from IVF Patients page)
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    loadCycles();
  }, [statusFilter, typeFilter, searchQuery, patientIdFromUrl]);

  const loadCycles = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const filters: any = {};
      if (statusFilter) filters.status = statusFilter;
      if (typeFilter) filters.cycle_type = typeFilter;
      if (searchQuery) filters.search = searchQuery;
      if (patientIdFromUrl) {
        const pid = parseInt(patientIdFromUrl, 10);
        if (!isNaN(pid)) filters.patient = pid;
      }
      
      const data = await fetchIVFCycles(filters);
      setCycles(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load cycles');
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

  return (
    <div className={styles.pageContainer}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <button 
            className={styles.backButton}
            onClick={() => navigate('/ivf')}
          >
            ← Dashboard
          </button>
          <h1>IVF Cycles</h1>
        </div>
        <button 
          className={styles.primaryButton}
          onClick={() => navigate('/ivf/cycles/new')}
        >
          + New Cycle
        </button>
      </header>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.searchContainer}>
          <input
            type="text"
            placeholder="Search by patient name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
        </div>
        
        <select 
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className={styles.filterSelect}
        >
          <option value="">All Statuses</option>
          {Object.entries(CYCLE_STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        
        <select 
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className={styles.filterSelect}
        >
          <option value="">All Types</option>
          {Object.entries(CYCLE_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        
        <button 
          className={styles.clearButton}
          onClick={() => {
            setStatusFilter('');
            setTypeFilter('');
            setSearchQuery('');
          }}
        >
          Clear Filters
        </button>
      </div>

      {error && (
        <div className={styles.errorBanner}>
          {error}
          <button onClick={loadCycles}>Retry</button>
        </div>
      )}

      {loading ? (
        <div className={styles.loading}>Loading cycles...</div>
      ) : cycles.length === 0 ? (
        <div className={styles.emptyState}>
          <h3>No IVF cycles found</h3>
          <p>Start by creating a new IVF cycle for a patient.</p>
          <button 
            className={styles.primaryButton}
            onClick={() => navigate('/ivf/cycles/new')}
          >
            Create New Cycle
          </button>
        </div>
      ) : (
        <div className={styles.tableContainer}>
          <table className={styles.dataTable}>
            <thead>
              <tr>
                <th>Cycle #</th>
                <th>Patient</th>
                <th>Partner</th>
                <th>Type</th>
                <th>Status</th>
                <th>Start Date</th>
                <th>Consent</th>
                <th>Outcome</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {cycles.map((cycle) => (
                <tr key={cycle.id}>
                  <td>
                    <strong>#{cycle.cycle_number}</strong>
                  </td>
                  <td>{cycle.patient_name}</td>
                  <td>{cycle.partner_name || '-'}</td>
                  <td>
                    <span className={styles.typeTag}>
                      {CYCLE_TYPE_LABELS[cycle.cycle_type]}
                    </span>
                  </td>
                  <td>
                    <span 
                      className={styles.statusBadge}
                      style={{ backgroundColor: getStatusColor(cycle.status) }}
                    >
                      {CYCLE_STATUS_LABELS[cycle.status]}
                    </span>
                  </td>
                  <td>
                    {cycle.actual_start_date || cycle.planned_start_date || '-'}
                  </td>
                  <td>
                    {cycle.consent_signed ? (
                      <span className={styles.consentSigned}>✓</span>
                    ) : (
                      <span className={styles.consentPending}>⚠</span>
                    )}
                  </td>
                  <td>
                    {cycle.pregnancy_outcome ? (
                      <span className={
                        cycle.pregnancy_outcome === 'LIVE_BIRTH' || 
                        cycle.pregnancy_outcome === 'POSITIVE' ||
                        cycle.pregnancy_outcome === 'ONGOING'
                          ? styles.outcomePositive
                          : cycle.pregnancy_outcome === 'NEGATIVE' ||
                            cycle.pregnancy_outcome === 'MISCARRIAGE'
                          ? styles.outcomeNegative
                          : styles.outcomeNeutral
                      }>
                        {cycle.pregnancy_outcome}
                      </span>
                    ) : '-'}
                  </td>
                  <td>
                    <button
                      className={styles.viewButton}
                      onClick={() => navigate(`/ivf/cycles/${cycle.id}`)}
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
  );
}
