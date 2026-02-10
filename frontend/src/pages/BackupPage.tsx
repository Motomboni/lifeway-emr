/**
 * Backup & Restore Management Page
 * 
 * For Superusers to manage data backups and restores.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import {
  fetchBackups,
  fetchRestores,
  createBackup,
  deleteBackup,
  downloadBackup,
  createRestore,
  Backup,
  BackupCreateData,
  Restore,
  RestoreCreateData,
  PaginatedBackupResponse,
  PaginatedRestoreResponse,
} from '../api/backup';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/Backup.module.css';

export default function BackupPage() {
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();

  const [backups, setBackups] = useState<Backup[]>([]);
  const [restores, setRestores] = useState<Restore[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'backups' | 'restores'>('backups');
  const [showCreateBackup, setShowCreateBackup] = useState(false);
  const [showCreateRestore, setShowCreateRestore] = useState(false);
  
  // Backup form data
  const [backupData, setBackupData] = useState<BackupCreateData>({
    backup_type: 'FULL',
    includes_patients: true,
    includes_visits: true,
    includes_consultations: true,
    includes_lab_data: true,
    includes_radiology_data: true,
    includes_prescriptions: true,
    includes_audit_logs: true,
    description: '',
  });
  
  // Restore form data
  const [restoreData, setRestoreData] = useState<RestoreCreateData>({
    backup: 0,
    restore_patients: true,
    restore_visits: true,
    restore_consultations: true,
    restore_lab_data: true,
    restore_radiology_data: true,
    restore_prescriptions: true,
    restore_audit_logs: false,
    description: '',
  });

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    try {
      setLoading(true);
      if (activeTab === 'backups') {
        const response = await fetchBackups();
        const backupsArray = Array.isArray(response)
          ? response
          : (response as PaginatedBackupResponse)?.results || [];
        setBackups(backupsArray);
      } else {
        const response = await fetchRestores();
        const restoresArray = Array.isArray(response)
          ? response
          : (response as PaginatedRestoreResponse)?.results || [];
        setRestores(restoresArray);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load data';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBackup = async () => {
    try {
      setIsSaving(true);
      await createBackup(backupData);
      showSuccess('Backup created successfully');
      setShowCreateBackup(false);
      resetBackupForm();
      loadData();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create backup';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCreateRestore = async () => {
    if (!restoreData.backup) {
      showError('Please select a backup to restore from');
      return;
    }

    try {
      setIsSaving(true);
      await createRestore(restoreData);
      showSuccess('Restore operation started successfully');
      setShowCreateRestore(false);
      resetRestoreForm();
      loadData();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create restore';
      showError(errorMessage);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteBackup = async (backupId: number) => {
    if (!window.confirm('Are you sure you want to delete this backup? This action cannot be undone.')) {
      return;
    }

    try {
      await deleteBackup(backupId);
      showSuccess('Backup deleted successfully');
      loadData();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to delete backup';
      showError(errorMessage);
    }
  };

  const handleDownloadBackup = async (backupId: number) => {
    try {
      const blob = await downloadBackup(backupId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `backup_${backupId}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      showSuccess('Backup downloaded successfully');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to download backup';
      showError(errorMessage);
    }
  };

  const resetBackupForm = () => {
    setBackupData({
      backup_type: 'FULL',
      includes_patients: true,
      includes_visits: true,
      includes_consultations: true,
      includes_lab_data: true,
      includes_radiology_data: true,
      includes_prescriptions: true,
      includes_audit_logs: true,
      description: '',
    });
  };

  const resetRestoreForm = () => {
    setRestoreData({
      backup: 0,
      restore_patients: true,
      restore_visits: true,
      restore_consultations: true,
      restore_lab_data: true,
      restore_radiology_data: true,
      restore_prescriptions: true,
      restore_audit_logs: false,
      description: '',
    });
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return 'N/A';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const formatDuration = (seconds?: number | null) => {
    if (!seconds) return 'N/A';
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}m ${secs}s`;
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return styles.statusCompleted;
      case 'IN_PROGRESS':
        return styles.statusInProgress;
      case 'FAILED':
        return styles.statusFailed;
      case 'PENDING':
        return styles.statusPending;
      case 'CANCELLED':
        return styles.statusCancelled;
      default:
        return styles.statusPending;
    }
  };

  if (!user?.is_superuser) {
    return (
      <div className={styles.backupPage}>
        <BackToDashboard />
        <div className={styles.accessDenied}>
          <h2>Access Denied</h2>
          <p>Only superusers can manage backups and restores.</p>
        </div>
      </div>
    );
  }

  const completedBackups = backups.filter(b => b.status === 'COMPLETED');

  return (
    <div className={styles.backupPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Backup & Restore Management</h1>
        {activeTab === 'backups' && !showCreateBackup && (
          <button
            className={styles.createButton}
            onClick={() => setShowCreateBackup(true)}
          >
            + Create Backup
          </button>
        )}
        {activeTab === 'restores' && !showCreateRestore && completedBackups.length > 0 && (
          <button
            className={styles.createButton}
            onClick={() => setShowCreateRestore(true)}
          >
            + Create Restore
          </button>
        )}
      </header>

      {/* Tabs */}
      <div className={styles.tabs}>
        <button
          className={activeTab === 'backups' ? styles.activeTab : styles.inactiveTab}
          onClick={() => setActiveTab('backups')}
        >
          Backups
        </button>
        <button
          className={activeTab === 'restores' ? styles.activeTab : styles.inactiveTab}
          onClick={() => setActiveTab('restores')}
        >
          Restores
        </button>
      </div>

      {/* Create Backup Form */}
      {showCreateBackup && (
        <div className={styles.formContainer}>
          <h2>Create New Backup</h2>
          
          <div className={styles.formGroup}>
            <label>Backup Type *</label>
            <select
              value={backupData.backup_type}
              onChange={(e) => setBackupData({ ...backupData, backup_type: e.target.value as any })}
            >
              <option value="FULL">Full Backup</option>
              <option value="INCREMENTAL">Incremental Backup</option>
              <option value="DIFFERENTIAL">Differential Backup</option>
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Include Data</label>
            <div className={styles.checkboxGroup}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={backupData.includes_patients}
                  onChange={(e) => setBackupData({ ...backupData, includes_patients: e.target.checked })}
                />
                Patients
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={backupData.includes_visits}
                  onChange={(e) => setBackupData({ ...backupData, includes_visits: e.target.checked })}
                />
                Visits
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={backupData.includes_consultations}
                  onChange={(e) => setBackupData({ ...backupData, includes_consultations: e.target.checked })}
                />
                Consultations
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={backupData.includes_lab_data}
                  onChange={(e) => setBackupData({ ...backupData, includes_lab_data: e.target.checked })}
                />
                Lab Data
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={backupData.includes_radiology_data}
                  onChange={(e) => setBackupData({ ...backupData, includes_radiology_data: e.target.checked })}
                />
                Radiology Data
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={backupData.includes_prescriptions}
                  onChange={(e) => setBackupData({ ...backupData, includes_prescriptions: e.target.checked })}
                />
                Prescriptions
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={backupData.includes_audit_logs}
                  onChange={(e) => setBackupData({ ...backupData, includes_audit_logs: e.target.checked })}
                />
                Audit Logs
              </label>
            </div>
          </div>

          <div className={styles.formGroup}>
            <label>Description</label>
            <textarea
              value={backupData.description}
              onChange={(e) => setBackupData({ ...backupData, description: e.target.value })}
              rows={3}
              placeholder="Optional description for this backup"
            />
          </div>

          <div className={styles.formActions}>
            <button
              className={styles.cancelButton}
              onClick={() => {
                setShowCreateBackup(false);
                resetBackupForm();
              }}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              className={styles.saveButton}
              onClick={handleCreateBackup}
              disabled={isSaving}
            >
              {isSaving ? 'Creating...' : 'Create Backup'}
            </button>
          </div>
        </div>
      )}

      {/* Create Restore Form */}
      {showCreateRestore && (
        <div className={styles.formContainer}>
          <h2>Create Restore Operation</h2>
          
          <div className={styles.formGroup}>
            <label>Select Backup *</label>
            <select
              value={restoreData.backup}
              onChange={(e) => setRestoreData({ ...restoreData, backup: parseInt(e.target.value) })}
              required
            >
              <option value={0}>Select a backup...</option>
              {completedBackups.map((backup) => (
                <option key={backup.id} value={backup.id}>
                  Backup #{backup.id} - {backup.backup_type} ({formatDateTime(backup.created_at)})
                </option>
              ))}
            </select>
          </div>

          <div className={styles.formGroup}>
            <label>Restore Data</label>
            <div className={styles.checkboxGroup}>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={restoreData.restore_patients}
                  onChange={(e) => setRestoreData({ ...restoreData, restore_patients: e.target.checked })}
                />
                Patients
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={restoreData.restore_visits}
                  onChange={(e) => setRestoreData({ ...restoreData, restore_visits: e.target.checked })}
                />
                Visits
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={restoreData.restore_consultations}
                  onChange={(e) => setRestoreData({ ...restoreData, restore_consultations: e.target.checked })}
                />
                Consultations
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={restoreData.restore_lab_data}
                  onChange={(e) => setRestoreData({ ...restoreData, restore_lab_data: e.target.checked })}
                />
                Lab Data
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={restoreData.restore_radiology_data}
                  onChange={(e) => setRestoreData({ ...restoreData, restore_radiology_data: e.target.checked })}
                />
                Radiology Data
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={restoreData.restore_prescriptions}
                  onChange={(e) => setRestoreData({ ...restoreData, restore_prescriptions: e.target.checked })}
                />
                Prescriptions
              </label>
              <label className={styles.checkboxLabel}>
                <input
                  type="checkbox"
                  checked={restoreData.restore_audit_logs}
                  onChange={(e) => setRestoreData({ ...restoreData, restore_audit_logs: e.target.checked })}
                />
                Audit Logs (usually False)
              </label>
            </div>
          </div>

          <div className={styles.formGroup}>
            <label>Description</label>
            <textarea
              value={restoreData.description}
              onChange={(e) => setRestoreData({ ...restoreData, description: e.target.value })}
              rows={3}
              placeholder="Optional description for this restore operation"
            />
          </div>

          <div className={styles.warningBox}>
            <strong>⚠️ Warning:</strong> Restoring data will overwrite existing data. This operation cannot be undone.
          </div>

          <div className={styles.formActions}>
            <button
              className={styles.cancelButton}
              onClick={() => {
                setShowCreateRestore(false);
                resetRestoreForm();
              }}
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              className={styles.saveButton}
              onClick={handleCreateRestore}
              disabled={isSaving}
            >
              {isSaving ? 'Starting...' : 'Start Restore'}
            </button>
          </div>
        </div>
      )}

      {/* Backups List */}
      {activeTab === 'backups' && !showCreateBackup && (
        <div className={styles.listContainer}>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : backups.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No backups found</p>
            </div>
          ) : (
            backups.map((backup) => (
              <div key={backup.id} className={styles.card}>
                <div className={styles.cardHeader}>
                  <div>
                    <h3>Backup #{backup.id} - {backup.backup_type}</h3>
                    <p className={styles.cardMeta}>
                      Created: {formatDateTime(backup.created_at)}
                      {backup.created_by_name && ` by ${backup.created_by_name}`}
                    </p>
                  </div>
                  <div className={styles.cardBadges}>
                    <span className={`${styles.statusBadge} ${getStatusBadgeClass(backup.status)}`}>
                      {backup.status}
                    </span>
                    {backup.is_expired && (
                      <span className={styles.expiredBadge}>EXPIRED</span>
                    )}
                  </div>
                </div>

                <div className={styles.cardDetails}>
                  <div className={styles.detailRow}>
                    <span className={styles.detailLabel}>File Size:</span>
                    <span className={styles.detailValue}>{formatFileSize(backup.file_size)}</span>
                  </div>
                  {backup.duration_seconds && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Duration:</span>
                      <span className={styles.detailValue}>{formatDuration(backup.duration_seconds)}</span>
                    </div>
                  )}
                  {backup.started_at && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Started:</span>
                      <span className={styles.detailValue}>{formatDateTime(backup.started_at)}</span>
                    </div>
                  )}
                  {backup.completed_at && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Completed:</span>
                      <span className={styles.detailValue}>{formatDateTime(backup.completed_at)}</span>
                    </div>
                  )}
                  {backup.description && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Description:</span>
                      <span className={styles.detailValue}>{backup.description}</span>
                    </div>
                  )}
                  {backup.error_message && (
                    <div className={styles.errorMessage}>
                      <strong>Error:</strong> {backup.error_message}
                    </div>
                  )}
                </div>

                <div className={styles.cardActions}>
                  {backup.status === 'COMPLETED' && (
                    <button
                      className={styles.downloadButton}
                      onClick={() => handleDownloadBackup(backup.id)}
                    >
                      Download
                    </button>
                  )}
                  <button
                    className={styles.deleteButton}
                    onClick={() => handleDeleteBackup(backup.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Restores List */}
      {activeTab === 'restores' && !showCreateRestore && (
        <div className={styles.listContainer}>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : restores.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No restore operations found</p>
            </div>
          ) : (
            restores.map((restore) => (
              <div key={restore.id} className={styles.card}>
                <div className={styles.cardHeader}>
                  <div>
                    <h3>Restore #{restore.id}</h3>
                    <p className={styles.cardMeta}>
                      Created: {formatDateTime(restore.created_at)}
                      {restore.created_by_name && ` by ${restore.created_by_name}`}
                    </p>
                    {restore.backup_info && (
                      <p className={styles.cardMeta}>
                        From Backup #{restore.backup_info.id} ({restore.backup_info.backup_type})
                      </p>
                    )}
                  </div>
                  <div className={styles.cardBadges}>
                    <span className={`${styles.statusBadge} ${getStatusBadgeClass(restore.status)}`}>
                      {restore.status}
                    </span>
                  </div>
                </div>

                <div className={styles.cardDetails}>
                  {restore.duration_seconds && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Duration:</span>
                      <span className={styles.detailValue}>{formatDuration(restore.duration_seconds)}</span>
                    </div>
                  )}
                  {restore.started_at && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Started:</span>
                      <span className={styles.detailValue}>{formatDateTime(restore.started_at)}</span>
                    </div>
                  )}
                  {restore.completed_at && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Completed:</span>
                      <span className={styles.detailValue}>{formatDateTime(restore.completed_at)}</span>
                    </div>
                  )}
                  {restore.description && (
                    <div className={styles.detailRow}>
                      <span className={styles.detailLabel}>Description:</span>
                      <span className={styles.detailValue}>{restore.description}</span>
                    </div>
                  )}
                  {restore.error_message && (
                    <div className={styles.errorMessage}>
                      <strong>Error:</strong> {restore.error_message}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
