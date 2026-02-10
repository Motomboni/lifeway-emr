/**
 * Offline Indicator Component
 * 
 * Displays when the application is offline.
 */
import React from 'react';
import styles from '../../styles/ConsultationWorkspace.module.css';

export default function OfflineIndicator() {
  return (
    <div className={styles.offlineIndicator}>
      ⚠️ You are currently offline. Changes will be saved when connection is restored.
    </div>
  );
}
