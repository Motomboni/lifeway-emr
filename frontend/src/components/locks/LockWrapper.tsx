/**
 * Lock Wrapper Component
 * 
 * Wraps any component/action with lock checking and explanation.
 * Provides a consistent pattern for gated actions.
 */
import React from 'react';
import { LockResult } from '../../api/locks';
import LockIndicator from './LockIndicator';
import { useActionLock } from '../../hooks/useActionLock';

interface LockWrapperProps {
  actionType: string;
  params: Record<string, any>;
  children: (props: {
    isLocked: boolean;
    lockResult: LockResult | null;
    loading: boolean;
  }) => React.ReactNode;
  showLockMessage?: boolean;
  lockMessageVariant?: 'inline' | 'button' | 'card';
  className?: string;
}

const LockWrapper: React.FC<LockWrapperProps> = ({
  actionType,
  params,
  children,
  showLockMessage = true,
  lockMessageVariant = 'inline',
  className = '',
}) => {
  const lock = useActionLock({
    actionType,
    params,
    enabled: true,
    autoCheck: true,
  });

  return (
    <div className={className}>
      {showLockMessage && lock.isLocked && lock.lockResult && (
        <LockIndicator
          lockResult={lock.lockResult}
          loading={lock.loading}
          variant={lockMessageVariant}
        />
      )}
      {children({
        isLocked: lock.isLocked,
        lockResult: lock.lockResult,
        loading: lock.loading,
      })}
    </div>
  );
};

export default LockWrapper;
