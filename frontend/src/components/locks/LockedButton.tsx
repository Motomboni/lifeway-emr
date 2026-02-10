/**
 * Locked Button Component
 * 
 * A button that shows lock status and explanation when disabled.
 */
import React from 'react';
import { LockResult } from '../../api/locks';
import LockIndicator from './LockIndicator';
import { FaLock } from 'react-icons/fa';
import styles from './LockedButton.module.css';

interface LockedButtonProps {
  lockResult: LockResult | null;
  loading?: boolean;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'small' | 'medium' | 'large';
  children: React.ReactNode;
  showLockMessage?: boolean;
}

const LockedButton: React.FC<LockedButtonProps> = ({
  lockResult,
  loading = false,
  onClick,
  disabled = false,
  className = '',
  variant = 'primary',
  size = 'medium',
  children,
  showLockMessage = true,
}) => {
  const isLocked = lockResult?.is_locked ?? false;
  const isDisabled = disabled || isLocked || loading;

  const buttonClasses = [
    styles.button,
    styles[variant],
    styles[size],
    isLocked && styles.locked,
    isDisabled && styles.disabled,
    className,
  ].filter(Boolean).join(' ');

  const handleClick = () => {
    if (!isDisabled && onClick) {
      onClick();
    }
  };

  return (
    <div className={styles.buttonContainer}>
      <button
        className={buttonClasses}
        onClick={handleClick}
        disabled={isDisabled}
        title={isLocked ? lockResult?.human_readable_message : undefined}
      >
        {isLocked && <FaLock className={styles.lockIcon} size={16} />}
        {loading && <span className={styles.loadingSpinner} />}
        {children}
      </button>
      {isLocked && showLockMessage && lockResult && (
        <LockIndicator
          lockResult={lockResult}
          variant="inline"
          className={styles.lockMessage}
        />
      )}
    </div>
  );
};

export default LockedButton;

