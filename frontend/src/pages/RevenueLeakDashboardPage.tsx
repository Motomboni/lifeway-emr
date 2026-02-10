/**
 * Revenue Leak Detection Dashboard
 * 
 * Displays detected revenue leaks with filtering and summary statistics.
 * Accessible only to Admin and Management roles.
 */
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  getRevenueLeaks, 
  getLeakSummary,
  LeakRecord,
  LeakSummary 
} from '../api/revenueLeaks';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import { 
  FaExclamationTriangle, 
  FaCheckCircle, 
  FaFlask, 
  FaXRay, 
  FaPills, 
  FaProcedures,
  FaFilter,
  FaEye
} from 'react-icons/fa';
import styles from '../styles/RevenueLeakDashboard.module.css';

const LEAK_TYPE_ICONS: Record<string, JSX.Element> = {
  LAB_RESULT: <FaFlask />,
  RADIOLOGY_REPORT: <FaXRay />,
  DRUG_DISPENSE: <FaPills />,
  PROCEDURE: <FaProcedures />,
};

const LEAK_TYPE_LABELS: Record<string, string> = {
  LAB_RESULT: 'Lab',
  RADIOLOGY_REPORT: 'Radiology',
  DRUG_DISPENSE: 'Drug',
  PROCEDURE: 'Procedure',
};

const HIGH_VALUE_THRESHOLD = 10000; // ₦10,000

export default function RevenueLeakDashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();
  
  const [leaks, setLeaks] = useState<LeakRecord[]>([]);
  const [summary, setSummary] = useState<LeakSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedLeak, setSelectedLeak] = useState<LeakRecord | null>(null);
  
  // Filters
  const [departmentFilter, setDepartmentFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [startDate, setStartDate] = useState<string>(
    new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  );
  const [endDate, setEndDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  );
  
  // Check access
  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    
    if (user.role !== 'ADMIN' && user.role !== 'MANAGEMENT') {
      showError('Access denied. This page is only available to Admin and Management roles.');
      navigate('/dashboard');
      return;
    }
  }, [user, navigate, showError]);
  
  // Load data
  useEffect(() => {
    if (!user || (user.role !== 'ADMIN' && user.role !== 'MANAGEMENT')) {
      return;
    }
    
    loadData();
  }, [startDate, endDate, departmentFilter, statusFilter, user]);
  
  const loadData = async () => {
    try {
      setLoading(true);
      
      const params: any = {
        start_date: startDate,
        end_date: endDate,
      };
      
      if (statusFilter) {
        params.is_resolved = statusFilter === 'resolved';
      }
      
      if (departmentFilter) {
        // Map department to entity_type
        const entityTypeMap: Record<string, string> = {
          'LAB': 'LAB_RESULT',
          'RADIOLOGY': 'RADIOLOGY_REPORT',
          'PHARMACY': 'DRUG_DISPENSE',
          'CLINICAL': 'PROCEDURE',
        };
        params.entity_type = entityTypeMap[departmentFilter] || departmentFilter;
      }
      
      const [leaksData, summaryData] = await Promise.all([
        getRevenueLeaks(params),
        getLeakSummary({ start_date: startDate, end_date: endDate }),
      ]);
      
      setLeaks(leaksData);
      setSummary(summaryData);
    } catch (error: any) {
      showError('Failed to load revenue leak data.');
      console.error('Error loading revenue leaks:', error);
    } finally {
      setLoading(false);
    }
  };
  
  const formatCurrency = (amount: string | number): string => {
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    return new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 2,
    }).format(numAmount);
  };
  
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-NG', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };
  
  const getLeakTypeLabel = (entityType: string): string => {
    return LEAK_TYPE_LABELS[entityType] || entityType;
  };
  
  const getLeakTypeIcon = (entityType: string): JSX.Element => {
    return LEAK_TYPE_ICONS[entityType] || <FaExclamationTriangle />;
  };
  
  const isHighValue = (amount: string | number): boolean => {
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    return numAmount >= HIGH_VALUE_THRESHOLD;
  };
  
  const handleRowClick = (leak: LeakRecord) => {
    setSelectedLeak(leak);
  };
  
  const handleViewVisit = (visitId: number) => {
    navigate(`/visits/${visitId}`);
  };
  
  const handleCloseDetail = () => {
    setSelectedLeak(null);
  };
  
  if (!user || (user.role !== 'ADMIN' && user.role !== 'MANAGEMENT')) {
    return null;
  }
  
  if (loading) {
    return (
      <div className={styles.page}>
        <BackToDashboard />
        <LoadingSkeleton />
      </div>
    );
  }
  
  const departmentEntityMap: Record<string, string> = {
    LAB: 'LAB_RESULT',
    RADIOLOGY: 'RADIOLOGY_REPORT',
    PHARMACY: 'DRUG_DISPENSE',
    CLINICAL: 'PROCEDURE',
  };

  const filteredLeaks = leaks.filter((leak) => {
    if (departmentFilter) {
      const expectedType = departmentEntityMap[departmentFilter] || departmentFilter;
      return leak.entity_type === expectedType;
    }
    return true;
  });
  
  return (
    <div className={styles.page}>
      <BackToDashboard />
      
      <div className={styles.header}>
        <h1>Revenue Leak Detection Dashboard</h1>
        <p className={styles.subtitle}>
          Monitor and track potential revenue leaks across all departments
        </p>
      </div>
      
      {/* Summary Cards */}
      {summary && (
        <div className={styles.summaryCards}>
          <div className={styles.summaryCard}>
            <div className={styles.summaryCardIcon} style={{ backgroundColor: '#f44336' }}>
              <FaExclamationTriangle />
            </div>
            <div className={styles.summaryCardContent}>
              <div className={styles.summaryCardLabel}>Total Potential Leaked Revenue</div>
              <div className={styles.summaryCardValue}>
                {formatCurrency(summary.total_amount)}
              </div>
            </div>
          </div>
          
          <div className={styles.summaryCard}>
            <div className={styles.summaryCardIcon} style={{ backgroundColor: '#ff9800' }}>
              <FaExclamationTriangle />
            </div>
            <div className={styles.summaryCardContent}>
              <div className={styles.summaryCardLabel}>Total Leak Incidents</div>
              <div className={styles.summaryCardValue}>{summary.total_leaks}</div>
            </div>
          </div>
          
          <div className={styles.summaryCard}>
            <div className={styles.summaryCardIcon} style={{ backgroundColor: '#4caf50' }}>
              <FaCheckCircle />
            </div>
            <div className={styles.summaryCardContent}>
              <div className={styles.summaryCardLabel}>Resolved</div>
              <div className={styles.summaryCardValue}>{summary.resolved_count}</div>
            </div>
          </div>
          
          <div className={styles.summaryCard}>
            <div className={styles.summaryCardIcon} style={{ backgroundColor: '#f44336' }}>
              <FaExclamationTriangle />
            </div>
            <div className={styles.summaryCardContent}>
              <div className={styles.summaryCardLabel}>Unresolved</div>
              <div className={styles.summaryCardValue}>{summary.unresolved_count}</div>
            </div>
          </div>
        </div>
      )}
      
      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.filterGroup}>
          <label htmlFor="startDate">Start Date</label>
          <input
            id="startDate"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className={styles.filterInput}
          />
        </div>
        
        <div className={styles.filterGroup}>
          <label htmlFor="endDate">End Date</label>
          <input
            id="endDate"
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className={styles.filterInput}
          />
        </div>
        
        <div className={styles.filterGroup}>
          <label htmlFor="department">Department</label>
          <select
            id="department"
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className={styles.filterInput}
          >
            <option value="">All Departments</option>
            <option value="LAB">Laboratory</option>
            <option value="RADIOLOGY">Radiology</option>
            <option value="PHARMACY">Pharmacy</option>
            <option value="CLINICAL">Clinical</option>
          </select>
        </div>
        
        <div className={styles.filterGroup}>
          <label htmlFor="status">Status</label>
          <select
            id="status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className={styles.filterInput}
          >
            <option value="">All Status</option>
            <option value="unresolved">Unresolved</option>
            <option value="resolved">Resolved</option>
          </select>
        </div>
        
        <button 
          onClick={loadData}
          className={styles.refreshButton}
          title="Refresh data"
        >
          <FaFilter /> Apply Filters
        </button>
      </div>
      
      {/* Table */}
      <div className={styles.tableContainer}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Service Name</th>
              <th>Department</th>
              <th>Leak Type</th>
              <th>Estimated Amount</th>
              <th>Status</th>
              <th>Detected Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredLeaks.length === 0 ? (
              <tr>
                <td colSpan={7} className={styles.emptyState}>
                  No revenue leaks found for the selected filters.
                </td>
              </tr>
            ) : (
              filteredLeaks.map((leak) => (
                <tr
                  key={leak.id}
                  className={`${styles.tableRow} ${
                    isHighValue(leak.estimated_amount) ? styles.highValue : ''
                  } ${!leak.is_resolved ? styles.unresolved : ''}`}
                  onClick={() => handleRowClick(leak)}
                >
                  <td>
                    <div className={styles.serviceName}>
                      {leak.service_name}
                      {isHighValue(leak.estimated_amount) && (
                        <span className={styles.highValueBadge}>High Value</span>
                      )}
                    </div>
                    <div className={styles.serviceCode}>{leak.service_code}</div>
                  </td>
                  <td>
                    <div className={styles.department}>
                      {getLeakTypeLabel(leak.entity_type)}
                    </div>
                  </td>
                  <td>
                    <div className={styles.leakType}>
                      <span className={styles.leakTypeIcon}>
                        {getLeakTypeIcon(leak.entity_type)}
                      </span>
                      {getLeakTypeLabel(leak.entity_type)}
                    </div>
                  </td>
                  <td>
                    <div className={`${styles.amount} ${
                      isHighValue(leak.estimated_amount) ? styles.highValueAmount : ''
                    }`}>
                      {formatCurrency(leak.estimated_amount)}
                    </div>
                  </td>
                  <td>
                    <div className={styles.status}>
                      {leak.is_resolved ? (
                        <span className={styles.statusBadgeResolved}>
                          <FaCheckCircle /> Resolved
                        </span>
                      ) : (
                        <span className={styles.statusBadgeUnresolved}>
                          <FaExclamationTriangle /> Open
                        </span>
                      )}
                    </div>
                  </td>
                  <td>{formatDate(leak.detected_at)}</td>
                  <td>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleViewVisit(leak.visit_id || leak.visit);
                      }}
                      className={styles.viewButton}
                      title="View Visit"
                    >
                      <FaEye /> View
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      
      {/* Detail Modal */}
      {selectedLeak && (
        <div className={styles.modalOverlay} onClick={handleCloseDetail}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2>Leak Details</h2>
              <button onClick={handleCloseDetail} className={styles.modalClose}>×</button>
            </div>
            <div className={styles.modalContent}>
              <div className={styles.detailSection}>
                <h3>Service Information</h3>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Service Name:</span>
                  <span className={styles.detailValue}>{selectedLeak.service_name}</span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Service Code:</span>
                  <span className={styles.detailValue}>{selectedLeak.service_code}</span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Leak Type:</span>
                  <span className={styles.detailValue}>
                    {getLeakTypeLabel(selectedLeak.entity_type)}
                  </span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Estimated Amount:</span>
                  <span className={`${styles.detailValue} ${
                    isHighValue(selectedLeak.estimated_amount) ? styles.highValueAmount : ''
                  }`}>
                    {formatCurrency(selectedLeak.estimated_amount)}
                  </span>
                </div>
              </div>
              
              <div className={styles.detailSection}>
                <h3>Visit Information</h3>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Visit ID:</span>
                  <span className={styles.detailValue}>{selectedLeak.visit_id || selectedLeak.visit}</span>
                </div>
                {selectedLeak.visit_patient_name && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Patient:</span>
                    <span className={styles.detailValue}>{selectedLeak.visit_patient_name}</span>
                  </div>
                )}
                <button
                  onClick={() => handleViewVisit(selectedLeak.visit_id || selectedLeak.visit)}
                  className={styles.viewVisitButton}
                >
                  <FaEye /> View Visit Details
                </button>
              </div>
              
              <div className={styles.detailSection}>
                <h3>Detection Information</h3>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Detected At:</span>
                  <span className={styles.detailValue}>
                    {formatDate(selectedLeak.detected_at)}
                  </span>
                </div>
                <div className={styles.detailRow}>
                  <span className={styles.detailLabel}>Status:</span>
                  <span className={styles.detailValue}>
                    {selectedLeak.is_resolved ? 'Resolved' : 'Open'}
                  </span>
                </div>
                {selectedLeak.resolved_at && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Resolved At:</span>
                    <span className={styles.detailValue}>
                      {formatDate(selectedLeak.resolved_at)}
                    </span>
                  </div>
                )}
                {selectedLeak.resolved_by_name && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Resolved By:</span>
                    <span className={styles.detailValue}>{selectedLeak.resolved_by_name}</span>
                  </div>
                )}
                {selectedLeak.resolution_notes && (
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Resolution Notes:</span>
                    <span className={styles.detailValue}>{selectedLeak.resolution_notes}</span>
                  </div>
                )}
              </div>
              
              {selectedLeak.detection_context && Object.keys(selectedLeak.detection_context).length > 0 && (
                <div className={styles.detailSection}>
                  <h3>Detection Context</h3>
                  <pre className={styles.contextJson}>
                    {JSON.stringify(selectedLeak.detection_context, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

