/**
 * Audit Log Viewer Page
 * 
 * Displays audit logs for compliance and security monitoring.
 * Read-only access to all system actions.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchAuditLogs, AuditLog, AuditLogFilters, PaginatedAuditLogs } from '../api/audit';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/AuditLog.module.css';

export default function AuditLogPage() {
  const navigate = useNavigate();
  const { showError } = useToast();

  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState<{
    count: number;
    currentPage: number;
    pageSize: number;
    totalPages: number;
  }>({
    count: 0,
    currentPage: 1,
    pageSize: 50,
    totalPages: 0,
  });
  const [filters, setFilters] = useState<AuditLogFilters>({});
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    loadAuditLogs();
  }, [filters, pagination.currentPage]);

  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      const response = await fetchAuditLogs({
        ...filters,
        page: pagination.currentPage,
        page_size: pagination.pageSize,
      });

      if (response && typeof response === 'object' && 'results' in response) {
        setAuditLogs(response.results);
        setPagination(prev => ({
          ...prev,
          count: response.count,
          totalPages: Math.ceil(response.count / pagination.pageSize),
        }));
      } else {
        setAuditLogs(response as AuditLog[]);
        setPagination(prev => ({
          ...prev,
          count: (response as AuditLog[]).length,
          totalPages: 1,
        }));
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load audit logs';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getActionColor = (action: string) => {
    if (action.includes('CREATE') || action.includes('create')) return styles.actionCreate;
    if (action.includes('UPDATE') || action.includes('update')) return styles.actionUpdate;
    if (action.includes('DELETE') || action.includes('delete')) return styles.actionDelete;
    if (action.includes('READ') || action.includes('read')) return styles.actionRead;
    return styles.actionDefault;
  };

  return (
    <div className={styles.auditLogPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Audit Logs</h1>
        <p>System activity log for compliance and security</p>
      </header>

      <div className={styles.filters}>
        <button
          className={styles.filterToggle}
          onClick={() => setShowFilters(!showFilters)}
        >
          {showFilters ? 'Hide' : 'Show'} Filters
        </button>

        {showFilters && (
          <div className={styles.filterPanel}>
            <div className={styles.filterRow}>
              <div className={styles.filterGroup}>
                <label>Visit ID:</label>
                <input
                  type="number"
                  value={filters.visit_id || ''}
                  onChange={(e) => {
                    setFilters({
                      ...filters,
                      visit_id: e.target.value ? parseInt(e.target.value) : undefined
                    });
                    setPagination(prev => ({ ...prev, currentPage: 1 }));
                  }}
                  placeholder="Filter by visit ID"
                />
              </div>

              <div className={styles.filterGroup}>
                <label>Action:</label>
                <input
                  type="text"
                  value={filters.action || ''}
                  onChange={(e) => {
                    setFilters({
                      ...filters,
                      action: e.target.value || undefined
                    });
                    setPagination(prev => ({ ...prev, currentPage: 1 }));
                  }}
                  placeholder="Filter by action"
                />
              </div>

              <div className={styles.filterGroup}>
                <label>Resource Type:</label>
                <select
                  value={filters.resource_type || ''}
                  onChange={(e) => {
                    setFilters({
                      ...filters,
                      resource_type: e.target.value || undefined
                    });
                    setPagination(prev => ({ ...prev, currentPage: 1 }));
                  }}
                >
                  <option value="">All</option>
                  <option value="consultation">Consultation</option>
                  <option value="lab_order">Lab Order</option>
                  <option value="radiology_order">Radiology Order</option>
                  <option value="prescription">Prescription</option>
                  <option value="payment">Payment</option>
                  <option value="visit">Visit</option>
                </select>
              </div>

              <div className={styles.filterGroup}>
                <label>Date From:</label>
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={(e) => {
                    setFilters({
                      ...filters,
                      date_from: e.target.value || undefined
                    });
                    setPagination(prev => ({ ...prev, currentPage: 1 }));
                  }}
                />
              </div>

              <div className={styles.filterGroup}>
                <label>Date To:</label>
                <input
                  type="date"
                  value={filters.date_to || ''}
                  onChange={(e) => {
                    setFilters({
                      ...filters,
                      date_to: e.target.value || undefined
                    });
                    setPagination(prev => ({ ...prev, currentPage: 1 }));
                  }}
                />
              </div>

              <button
                className={styles.clearFiltersButton}
                onClick={() => {
                  setFilters({});
                  setPagination(prev => ({ ...prev, currentPage: 1 }));
                }}
              >
                Clear
              </button>
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <LoadingSkeleton count={10} />
      ) : auditLogs.length === 0 ? (
        <div className={styles.emptyState}>
          <p>No audit logs found</p>
        </div>
      ) : (
        <>
          <div className={styles.auditLogsTable}>
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Role</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Visit ID</th>
                  <th>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{new Date(log.timestamp).toLocaleString()}</td>
                    <td>{log.user_name || `User #${log.user}`}</td>
                    <td><span className={styles.roleBadge}>{log.user_role}</span></td>
                    <td>
                      <span className={`${styles.actionBadge} ${getActionColor(log.action)}`}>
                        {log.action}
                      </span>
                    </td>
                    <td>
                      {log.resource_type}
                      {log.resource_id && ` #${log.resource_id}`}
                    </td>
                    <td>
                      {log.visit_id ? (
                        <button
                          className={styles.visitLink}
                          onClick={() => navigate(`/visits/${log.visit_id}`)}
                        >
                          Visit #{log.visit_id}
                        </button>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td>{log.ip_address || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {pagination.totalPages > 1 && (
            <div className={styles.pagination}>
              <button
                className={styles.paginationButton}
                onClick={() => setPagination(prev => ({ ...prev, currentPage: prev.currentPage - 1 }))}
                disabled={pagination.currentPage === 1}
              >
                Previous
              </button>
              <span className={styles.paginationInfo}>
                Page {pagination.currentPage} of {pagination.totalPages} ({pagination.count} total)
              </span>
              <button
                className={styles.paginationButton}
                onClick={() => setPagination(prev => ({ ...prev, currentPage: prev.currentPage + 1 }))}
                disabled={pagination.currentPage >= pagination.totalPages}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
