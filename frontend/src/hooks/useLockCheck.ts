/**
 * React hook for checking action locks.
 */
import { useState, useEffect } from 'react';
import { LockResult, evaluateLock } from '../api/locks';

interface UseLockCheckOptions {
  actionType: string;
  params: Record<string, any>;
  enabled?: boolean;
  onLockChange?: (isLocked: boolean) => void;
}

export const useLockCheck = ({
  actionType,
  params,
  enabled = true,
  onLockChange,
}: UseLockCheckOptions) => {
  const [lockResult, setLockResult] = useState<LockResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const checkLock = async () => {
      try {
        setLoading(true);
        setError(null);
        const result = await evaluateLock(actionType, params);
        setLockResult(result);
        if (onLockChange) {
          onLockChange(result.is_locked);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to check lock status');
        console.error('Error checking lock:', err);
      } finally {
        setLoading(false);
      }
    };

    checkLock();
  }, [actionType, JSON.stringify(params), enabled, onLockChange]);

  return {
    lockResult,
    loading,
    error,
    isLocked: lockResult?.is_locked ?? false,
    refresh: async () => {
      if (enabled) {
        try {
          setLoading(true);
          const result = await evaluateLock(actionType, params);
          setLockResult(result);
          if (onLockChange) {
            onLockChange(result.is_locked);
          }
        } catch (err: any) {
          setError(err.message || 'Failed to check lock status');
        } finally {
          setLoading(false);
        }
      }
    },
  };
};

