/**
 * Health Status Page
 * 
 * Displays application health status and system information.
 * Useful for monitoring and debugging.
 */
import React, { useState, useEffect } from 'react';
import { checkHealth, checkHealthDetailed, getHealthInfo, HealthStatus, HealthInfo } from '../api/health';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { useToast } from '../hooks/useToast';
import BackToDashboard from '../components/common/BackToDashboard';
import styles from '../styles/HealthStatus.module.css';

export default function HealthStatusPage() {
  const { showError } = useToast();
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [healthInfo, setHealthInfo] = useState<HealthInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadHealthData = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      const [status, detailed, info] = await Promise.all([
        checkHealth(),
        checkHealthDetailed(),
        getHealthInfo(),
      ]);

      setHealthStatus(detailed);
      setHealthInfo(info);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load health status';
      showError(errorMessage);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadHealthData();
  }, []);

  const handleRefresh = () => {
    loadHealthData(true);
  };

  if (loading) {
    return <LoadingSpinner message="Loading health status..." size="large" />;
  }

  const isHealthy = healthStatus?.status === 'healthy';

  return (
    <div className={styles.container}>
      <BackToDashboard />
      <div className={styles.header}>
        <h1>System Health Status</h1>
        <button
          className={styles.refreshButton}
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : '🔄 Refresh'}
        </button>
      </div>

      <div className={styles.content}>
        {/* Overall Status */}
        <div className={`${styles.statusCard} ${isHealthy ? styles.healthy : styles.unhealthy}`}>
          <div className={styles.statusHeader}>
            <span className={styles.statusIcon}>{isHealthy ? '✅' : '❌'}</span>
            <h2>Overall Status: {healthStatus?.status.toUpperCase()}</h2>
          </div>
          <p className={styles.timestamp}>
            Last checked: {healthStatus?.timestamp ? new Date(healthStatus.timestamp).toLocaleString() : 'N/A'}
          </p>
        </div>

        {/* Detailed Checks */}
        {healthStatus?.checks && (
          <div className={styles.checksCard}>
            <h3>Component Checks</h3>
            <div className={styles.checksList}>
              <div className={styles.checkItem}>
                <span className={healthStatus.checks.database ? styles.checkPass : styles.checkFail}>
                  {healthStatus.checks.database ? '✅' : '❌'}
                </span>
                <span>Database</span>
              </div>
              <div className={styles.checkItem}>
                <span className={healthStatus.checks.cache ? styles.checkPass : styles.checkFail}>
                  {healthStatus.checks.cache ? '✅' : '❌'}
                </span>
                <span>Cache</span>
              </div>
              <div className={styles.checkItem}>
                <span className={healthStatus.checks.application ? styles.checkPass : styles.checkFail}>
                  {healthStatus.checks.application ? '✅' : '❌'}
                </span>
                <span>Application</span>
              </div>
            </div>
          </div>
        )}

        {/* Errors */}
        {healthStatus?.errors && healthStatus.errors.length > 0 && (
          <div className={styles.errorsCard}>
            <h3>Errors</h3>
            <ul className={styles.errorsList}>
              {healthStatus.errors.map((error, index) => (
                <li key={index}>{error}</li>
              ))}
            </ul>
          </div>
        )}

        {/* System Information */}
        {healthInfo && (
          <div className={styles.infoCard}>
            <h3>System Information</h3>
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Application:</span>
                <span className={styles.infoValue}>{healthInfo.application}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Version:</span>
                <span className={styles.infoValue}>{healthInfo.version}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Environment:</span>
                <span className={styles.infoValue}>{healthInfo.environment}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Database:</span>
                <span className={styles.infoValue}>{healthInfo.database}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Debug Mode:</span>
                <span className={styles.infoValue}>{healthInfo.debug ? 'Enabled' : 'Disabled'}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Last Updated:</span>
                <span className={styles.infoValue}>
                  {new Date(healthInfo.timestamp).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
