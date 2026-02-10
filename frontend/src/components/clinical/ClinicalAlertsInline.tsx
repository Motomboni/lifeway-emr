/**
 * Clinical Alerts Inline Component
 * 
 * Displays clinical alerts for a visit with acknowledge/resolve functionality.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../hooks/useToast';
import { fetchClinicalAlerts, acknowledgeAlert, resolveAlert } from '../../api/clinical';
import { ClinicalAlert } from '../../types/clinical';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface ClinicalAlertsInlineProps {
  visitId: string;
}

export default function ClinicalAlertsInline({ visitId }: ClinicalAlertsInlineProps) {
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  const [alerts, setAlerts] = useState<ClinicalAlert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    loadAlerts();
    const interval = setInterval(loadAlerts, 30000);
    return () => clearInterval(interval);
  }, [visitId, user]);

  const loadAlerts = async () => {
    if (!user) return;
    try {
      setLoading(true);
      const data = await fetchClinicalAlerts(parseInt(visitId), false);
      setAlerts(Array.isArray(data) ? data : []);
    } catch (error: any) {
      if (error?.status !== 401 && error?.status !== 504) {
        console.warn('Failed to load clinical alerts:', error?.message || error);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledge = async (alertId: number) => {
    try {
      await acknowledgeAlert(parseInt(visitId), alertId);
      showSuccess('Alert acknowledged');
      await loadAlerts();
    } catch (error: any) {
      showError(error.message || 'Failed to acknowledge alert');
    }
  };

  const handleResolve = async (alertId: number) => {
    try {
      await resolveAlert(parseInt(visitId), alertId);
      showSuccess('Alert resolved');
      await loadAlerts();
    } catch (error: any) {
      showError(error.message || 'Failed to resolve alert');
    }
  };

  const getSeverityClass = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return styles.alertCritical;
      case 'HIGH':
        return styles.alertHigh;
      case 'MEDIUM':
        return styles.alertMedium;
      default:
        return styles.alertLow;
    }
  };

  if (loading) {
    return (
      <div className={styles.inlineComponent}>
        <h3>Clinical Alerts</h3>
        <p>Loading...</p>
      </div>
    );
  }

  if (alerts.length === 0) {
    return null; // Don't show if no alerts
  }

  return (
    <div className={styles.inlineComponent}>
      <div className={styles.inlineHeader}>
        <h3>Clinical Alerts ({alerts.length})</h3>
      </div>

      {alerts.map((alert) => (
        <div key={alert.id} className={`${styles.alertCard} ${getSeverityClass(alert.severity)}`}>
          <div className={styles.alertHeader}>
            <div>
              <strong>{alert.title}</strong>
              <span className={styles.severityBadge}>{alert.severity}</span>
            </div>
            <span className={styles.alertType}>{alert.alert_type.replace('_', ' ')}</span>
          </div>
          
          <div className={styles.alertMessage}>{alert.message}</div>
          
          {user?.role === 'DOCTOR' && !alert.is_resolved && (
            <div className={styles.alertActions}>
              {!alert.acknowledged_by && (
                <button
                  className={styles.acknowledgeButton}
                  onClick={() => handleAcknowledge(alert.id)}
                >
                  Acknowledge
                </button>
              )}
              <button
                className={styles.resolveButton}
                onClick={() => handleResolve(alert.id)}
              >
                Resolve
              </button>
            </div>
          )}
          
          {alert.acknowledged_by && (
            <div className={styles.alertMeta}>
              Acknowledged by {alert.acknowledged_by_name} at{' '}
              {new Date(alert.acknowledged_at!).toLocaleString()}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
