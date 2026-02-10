/**
 * Radiology Upload & Sync Status Page
 * 
 * Displays upload sessions with status, progress, and retry functionality.
 * Designed for Radiographers and Admin.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  getUploadSessions,
  getPendingUploads,
  getFailedUploads,
  retryUpload,
  ImageUploadSession,
} from '../api/radiologyUpload';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import {
  FaCloudUploadAlt,
  FaCheckCircle,
  FaExclamationTriangle,
  FaSync,
  FaRedo,
  FaWifi,
  // FaWifiSlash, // Not available in react-icons/fa, use FaWifi with conditional rendering
  FaClock,
  FaSpinner,
  FaFileImage,
} from 'react-icons/fa';
import styles from '../styles/RadiologyUploadStatus.module.css';

const STATUS_CONFIG: Record<string, {
  label: string;
  color: string;
  icon: JSX.Element;
  bgColor: string;
}> = {
  QUEUED: {
    label: 'Queued',
    color: '#ff9800',
    icon: <FaClock />,
    bgColor: '#fff3e0',
  },
  METADATA_UPLOADING: {
    label: 'Uploading Metadata',
    color: '#2196f3',
    icon: <FaSpinner className={styles.spinning} size={16} />,
    bgColor: '#e3f2fd',
  },
  METADATA_UPLOADED: {
    label: 'Metadata Uploaded',
    color: '#2196f3',
    icon: <FaCheckCircle size={16} />,
    bgColor: '#e3f2fd',
  },
  BINARY_UPLOADING: {
    label: 'Uploading',
    color: '#2196f3',
    icon: <FaSpinner className={styles.spinning} size={16} />,
    bgColor: '#e3f2fd',
  },
  SYNCED: {
    label: 'Synced',
    color: '#4caf50',
    icon: <FaCheckCircle size={16} />,
    bgColor: '#e8f5e9',
  },
  ACK_RECEIVED: {
    label: 'Completed',
    color: '#4caf50',
    icon: <FaCheckCircle size={16} />,
    bgColor: '#e8f5e9',
  },
  FAILED: {
    label: 'Failed',
    color: '#f44336',
    icon: <FaExclamationTriangle size={16} />,
    bgColor: '#ffebee',
  },
  CANCELLED: {
    label: 'Cancelled',
    color: '#757575',
    icon: <FaExclamationTriangle size={16} />,
    bgColor: '#f5f5f5',
  },
};

export default function RadiologyUploadStatusPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showError, showSuccess } = useToast();
  
  const [sessions, setSessions] = useState<ImageUploadSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [filter, setFilter] = useState<string>('all'); // all, pending, failed, completed
  
  // Check access
  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    
    if (user.role !== 'RADIOLOGY_TECH' && user.role !== 'ADMIN') {
      showError('Access denied. This page is only available to Radiographers and Admin.');
      navigate('/dashboard');
      return;
    }
  }, [user, navigate, showError]);
  
  // Network status monitoring
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);
  
  // Load data
  const loadSessions = useCallback(async () => {
    if (!user || (user.role !== 'RADIOLOGY_TECH' && user.role !== 'ADMIN')) {
      return;
    }
    
    try {
      let data: ImageUploadSession[] = [];
      
      switch (filter) {
        case 'pending':
          data = await getPendingUploads();
          break;
        case 'failed':
          data = await getFailedUploads();
          break;
        case 'completed':
          data = await getUploadSessions({ status: 'ACK_RECEIVED' });
          break;
        default:
          data = await getUploadSessions();
      }
      
      setSessions(data);
    } catch (error: any) {
      // Handle network errors gracefully
      if (!isOnline || error.message?.includes('network') || error.message?.includes('fetch')) {
        // Network error - don't show error toast, just keep existing data
        console.warn('Network error loading sessions:', error);
      } else {
        showError('Failed to load upload sessions.');
        console.error('Error loading sessions:', error);
      }
    } finally {
      setLoading(false);
    }
  }, [filter, user, isOnline, showError]);
  
  useEffect(() => {
    loadSessions();
  }, [loadSessions]);
  
  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh || !isOnline) {
      return;
    }
    
    const interval = setInterval(() => {
      loadSessions();
    }, 5000); // Refresh every 5 seconds
    
    return () => clearInterval(interval);
  }, [autoRefresh, isOnline, loadSessions]);
  
  const handleRetry = async (sessionId: string) => {
    try {
      await retryUpload(sessionId);
      showSuccess('Upload retry initiated.');
      loadSessions();
    } catch (error: any) {
      if (!isOnline) {
        showError('Cannot retry upload while offline. Please check your connection.');
      } else {
        showError('Failed to retry upload.');
        console.error('Error retrying upload:', error);
      }
    }
  };
  
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };
  
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('en-NG', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };
  
  const getStatusConfig = (status: string) => {
    return STATUS_CONFIG[status] || {
      label: status,
      color: '#757575',
      icon: <FaFileImage size={16} />,
      bgColor: '#f5f5f5',
    };
  };
  
  const isActiveStatus = (status: string): boolean => {
    return ['QUEUED', 'METADATA_UPLOADING', 'METADATA_UPLOADED', 'BINARY_UPLOADING'].includes(status);
  };
  
  const canRetry = (session: ImageUploadSession): boolean => {
    return session.status === 'FAILED' && session.retry_count < session.max_retries;
  };
  
  if (!user || (user.role !== 'RADIOLOGY_TECH' && user.role !== 'ADMIN')) {
    return null;
  }
  
  const pendingCount = sessions.filter(s => isActiveStatus(s.status)).length;
  const failedCount = sessions.filter(s => s.status === 'FAILED').length;
  const completedCount = sessions.filter(s => s.status === 'ACK_RECEIVED').length;
  
  return (
    <div className={styles.page}>
      <BackToDashboard />
      
      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <h1>Radiology Upload & Sync Status</h1>
          <p className={styles.subtitle}>
            Monitor and manage offline image uploads
          </p>
        </div>
        <div className={styles.headerRight}>
          <button
            onClick={() => {
              setAutoRefresh(!autoRefresh);
              if (!autoRefresh) {
                loadSessions();
              }
            }}
            className={`${styles.refreshButton} ${autoRefresh ? styles.active : ''}`}
            title={autoRefresh ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
          >
            <FaSync className={autoRefresh ? styles.spinning : ''} size={16} />
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </button>
          <button
            onClick={loadSessions}
            className={styles.manualRefreshButton}
            disabled={!isOnline}
            title="Refresh now"
          >
            <FaSync /> Refresh
          </button>
        </div>
      </div>
      
      {/* Offline Indicator */}
            {!isOnline && (
              <div className={styles.offlineBanner}>
                <FaWifi />
          <div>
            <strong>You are currently offline</strong>
            <p>Uploads will resume automatically when connection is restored.</p>
          </div>
        </div>
      )}
      
      {/* Summary Cards */}
      <div className={styles.summaryCards}>
        <div className={styles.summaryCard}>
          <div className={styles.summaryCardIcon} style={{ backgroundColor: '#ff9800' }}>
            <FaClock />
          </div>
          <div className={styles.summaryCardContent}>
            <div className={styles.summaryCardLabel}>Pending/Uploading</div>
            <div className={styles.summaryCardValue}>{pendingCount}</div>
          </div>
        </div>
        
        <div className={styles.summaryCard}>
          <div className={styles.summaryCardIcon} style={{ backgroundColor: '#f44336' }}>
            <FaExclamationTriangle />
          </div>
          <div className={styles.summaryCardContent}>
            <div className={styles.summaryCardLabel}>Failed</div>
            <div className={styles.summaryCardValue}>{failedCount}</div>
          </div>
        </div>
        
        <div className={styles.summaryCard}>
          <div className={styles.summaryCardIcon} style={{ backgroundColor: '#4caf50' }}>
            <FaCheckCircle />
          </div>
          <div className={styles.summaryCardContent}>
            <div className={styles.summaryCardLabel}>Completed</div>
            <div className={styles.summaryCardValue}>{completedCount}</div>
          </div>
        </div>
        
        <div className={styles.summaryCard}>
          <div className={styles.summaryCardIcon} style={{ backgroundColor: '#2196f3' }}>
            <FaCloudUploadAlt />
          </div>
          <div className={styles.summaryCardContent}>
            <div className={styles.summaryCardLabel}>Total Sessions</div>
            <div className={styles.summaryCardValue}>{sessions.length}</div>
          </div>
        </div>
      </div>
      
      {/* Filters */}
      <div className={styles.filters}>
        <button
          onClick={() => setFilter('all')}
          className={`${styles.filterButton} ${filter === 'all' ? styles.active : ''}`}
        >
          All ({sessions.length})
        </button>
        <button
          onClick={() => setFilter('pending')}
          className={`${styles.filterButton} ${filter === 'pending' ? styles.active : ''}`}
        >
          Pending ({pendingCount})
        </button>
        <button
          onClick={() => setFilter('failed')}
          className={`${styles.filterButton} ${filter === 'failed' ? styles.active : ''}`}
        >
          Failed ({failedCount})
        </button>
        <button
          onClick={() => setFilter('completed')}
          className={`${styles.filterButton} ${filter === 'completed' ? styles.active : ''}`}
        >
          Completed ({completedCount})
        </button>
      </div>
      
      {/* Sessions List */}
      {loading ? (
        <LoadingSkeleton />
      ) : sessions.length === 0 ? (
        <div className={styles.emptyState}>
          <FaCloudUploadAlt />
          <p>No upload sessions found</p>
          {filter !== 'all' && (
            <button
              onClick={() => setFilter('all')}
              className={styles.clearFilterButton}
            >
              Show all sessions
            </button>
          )}
        </div>
      ) : (
        <div className={styles.sessionsList}>
          {sessions.map((session) => {
            const statusConfig = getStatusConfig(session.status);
            const isActive = isActiveStatus(session.status);
            
            return (
              <div
                key={session.session_id}
                className={`${styles.sessionCard} ${isActive ? styles.active : ''}`}
              >
                <div className={styles.sessionHeader}>
                  <div className={styles.sessionLeft}>
                    <div
                      className={styles.statusBadge}
                      style={{
                        backgroundColor: statusConfig.bgColor,
                        color: statusConfig.color,
                      }}
                    >
                      {statusConfig.icon}
                      <span>{statusConfig.label}</span>
                    </div>
                    <div className={styles.fileInfo}>
                      <div className={styles.fileName}>
                        <FaFileImage />
                        {session.file_name}
                      </div>
                      <div className={styles.fileSize}>
                        {formatFileSize(session.file_size)}
                      </div>
                    </div>
                  </div>
                  <div className={styles.sessionRight}>
                    {session.metadata?.patient_name && (
                      <div className={styles.patientName}>
                        {session.metadata.patient_name}
                      </div>
                    )}
                    {session.metadata?.study_type && (
                      <div className={styles.studyType}>
                        {session.metadata.study_type}
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Progress Bar */}
                {isActive && (
                  <div className={styles.progressSection}>
                    <div className={styles.progressBar}>
                      <div
                        className={styles.progressFill}
                        style={{
                          width: `${session.upload_progress_percent}%`,
                          backgroundColor: statusConfig.color,
                        }}
                      />
                    </div>
                    <div className={styles.progressText}>
                      {session.upload_progress_percent.toFixed(1)}% • {formatFileSize(session.bytes_uploaded)} / {formatFileSize(session.file_size)}
                    </div>
                  </div>
                )}
                
                {/* Error Message */}
                {session.status === 'FAILED' && session.error_message && (
                  <div className={styles.errorMessage}>
                    <FaExclamationTriangle />
                    <div>
                      <strong>Error:</strong> {session.error_message}
                      {session.error_code && (
                        <span className={styles.errorCode}> ({session.error_code})</span>
                      )}
                    </div>
                  </div>
                )}
                
                {/* Session Details */}
                <div className={styles.sessionDetails}>
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>Created:</span>
                    <span className={styles.detailValue}>{formatDate(session.created_at)}</span>
                  </div>
                  {session.metadata_uploaded_at && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Metadata Uploaded:</span>
                      <span className={styles.detailValue}>{formatDate(session.metadata_uploaded_at)}</span>
                    </div>
                  )}
                  {session.binary_uploaded_at && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Binary Uploaded:</span>
                      <span className={styles.detailValue}>{formatDate(session.binary_uploaded_at)}</span>
                    </div>
                  )}
                  {session.server_ack_at && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Acknowledged:</span>
                      <span className={styles.detailValue}>{formatDate(session.server_ack_at)}</span>
                    </div>
                  )}
                  {session.retry_count > 0 && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Retry Attempts:</span>
                      <span className={styles.detailValue}>
                        {session.retry_count} / {session.max_retries}
                      </span>
                    </div>
                  )}
                </div>
                
                {/* Actions */}
                <div className={styles.sessionActions}>
                  {canRetry(session) && (
                    <button
                      onClick={() => handleRetry(session.session_id)}
                      className={styles.retryButton}
                      disabled={!isOnline}
                      title={!isOnline ? 'Cannot retry while offline' : 'Retry upload'}
                    >
                      <FaRedo /> Retry Upload
                    </button>
                  )}
                  {session.status === 'ACK_RECEIVED' && (
                    <div className={styles.successMessage}>
                      <FaCheckCircle />
                      <span>Upload completed successfully</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

