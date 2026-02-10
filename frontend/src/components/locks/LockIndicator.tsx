/**
 * Lock Indicator Component
 * 
 * Reusable component for showing explainable locks inline.
 * Displays lock icon and explanation message when an action is disabled.
 */
import React from 'react';
import { LockResult } from '../../api/locks';
import { FaLock, FaUnlock } from 'react-icons/fa';
import styles from './LockIndicator.module.css';

interface LockIndicatorProps {
  lockResult: LockResult | null;
  loading?: boolean;
  variant?: 'inline' | 'button' | 'card';
  showIcon?: boolean;
  className?: string;
  children?: React.ReactNode;
}

const LockIndicator: React.FC<LockIndicatorProps> = ({
  lockResult,
  loading = false,
  variant = 'inline',
  showIcon = true,
  className = '',
  children,
}) => {
  if (loading) {
    return (
      <div className={`${styles.lockIndicator} ${styles.loading} ${className}`}>
        <span className={styles.loadingText}>Checking access...</span>
      </div>
    );
  }

  if (!lockResult || !lockResult.is_locked) {
    // Not locked - show unlock icon if requested, or just render children
    if (variant === 'button' && showIcon) {
      return (
        <div className={`${styles.lockIndicator} ${styles.unlocked} ${className}`}>
          {showIcon && <FaUnlock className={styles.unlockIcon} size={16} />}
          {children}
        </div>
      );
    }
    return <>{children}</>;
  }

  // Locked - show explanation
  const lockClasses = [
    styles.lockIndicator,
    styles.locked,
    styles[variant],
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={lockClasses}>
      {showIcon && (
        <div className={styles.lockIconContainer}>
          <FaLock className={styles.lockIcon} size={16} />
        </div>
      )}
      <div className={styles.lockContent}>
        <div className={styles.lockMessage}>
          {lockResult.human_readable_message}
        </div>
        {lockResult.unlock_actions && lockResult.unlock_actions.length > 0 && (
          <div className={styles.unlockActions}>
            <span className={styles.unlockLabel}>To unlock:</span>
            <ul className={styles.unlockActionsList}>
              {lockResult.unlock_actions.map((action, index) => (
                <li key={index}>{action}</li>
              ))}
            </ul>
          </div>
        )}
        {lockResult.details && Object.keys(lockResult.details).length > 0 && (
          <div className={styles.lockDetails}>
            {Object.entries(lockResult.details).map(([key, value]) => (
              <span key={key} className={styles.detailItem}>
                <span className={styles.detailKey}>
                  {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                </span>
                <span className={styles.detailValue}>{String(value)}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default LockIndicator;

