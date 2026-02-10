/**
 * Lock Message Component
 * 
 * Displays explainable lock messages inline when actions are blocked.
 */
import React from 'react';
import { LockResult } from '../../api/locks';
import styles from './LockMessage.module.css';

interface LockMessageProps {
  lockResult: LockResult;
  variant?: 'inline' | 'banner' | 'alert';
  showUnlockActions?: boolean;
}

const LockMessage: React.FC<LockMessageProps> = ({
  lockResult,
  variant = 'inline',
  showUnlockActions = true,
}) => {
  if (!lockResult.is_locked) {
    return null;
  }

  const getIcon = (reasonCode: string): string => {
    if (reasonCode.includes('PAYMENT')) {
      return '💰';
    } else if (reasonCode.includes('CONSULTATION')) {
      return '👨‍⚕️';
    } else if (reasonCode.includes('VISIT')) {
      return '🏥';
    } else if (reasonCode.includes('ORDER')) {
      return '📋';
    } else if (reasonCode.includes('PERMISSION')) {
      return '🔒';
    }
    return '⚠️';
  };

  const getVariantClass = (): string => {
    switch (variant) {
      case 'banner':
        return styles.banner;
      case 'alert':
        return styles.alert;
      default:
        return styles.inline;
    }
  };

  return (
    <div className={`${styles.lockMessage} ${getVariantClass()}`}>
      <div className={styles.lockHeader}>
        <span className={styles.icon}>{getIcon(lockResult.reason_code)}</span>
        <span className={styles.message}>{lockResult.human_readable_message}</span>
      </div>
      
      {lockResult.details && Object.keys(lockResult.details).length > 0 && (
        <div className={styles.details}>
          {Object.entries(lockResult.details).map(([key, value]) => (
            <div key={key} className={styles.detailItem}>
              <span className={styles.detailKey}>{key.replace(/_/g, ' ')}:</span>
              <span className={styles.detailValue}>{String(value)}</span>
            </div>
          ))}
        </div>
      )}
      
      {showUnlockActions && lockResult.unlock_actions && lockResult.unlock_actions.length > 0 && (
        <div className={styles.unlockActions}>
          <div className={styles.unlockActionsTitle}>To unlock:</div>
          <ul className={styles.unlockActionsList}>
            {lockResult.unlock_actions.map((action, index) => (
              <li key={index}>{action}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default LockMessage;

