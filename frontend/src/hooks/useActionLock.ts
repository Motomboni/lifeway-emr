/**
 * React hook for checking action locks.
 * 
 * Provides a simple interface for checking if an action is locked
 * and getting the explanation.
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { isAccessTokenExpired } from '../api/auth';
import {
  evaluateLock,
  checkConsultationLock,
  checkRadiologyUploadLock,
  checkDrugDispenseLock,
  checkLabOrderLock,
  checkLabResultPostLock,
  checkRadiologyReportLock,
  checkRadiologyViewLock,
  checkProcedureLock,
  LockResult
} from '../api/locks';

interface UseActionLockOptions {
  actionType: string;
  params: Record<string, any>;
  enabled?: boolean;
  autoCheck?: boolean;
  checkInterval?: number;
}

export const useActionLock = ({
  actionType,
  params,
  enabled = true,
  autoCheck = true,
  checkInterval = 30000, // 30 seconds default
}: UseActionLockOptions) => {
  const { user } = useAuth();
  const [lockResult, setLockResult] = useState<LockResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const actuallyEnabled = enabled && !!user;

  const checkLock = async () => {
    if (!actuallyEnabled) {
      return;
    }

    // Skip lock check if access token is expired to avoid 401 errors
    try {
      const storedTokens = localStorage.getItem('auth_tokens');
      if (storedTokens) {
        const parsed = JSON.parse(storedTokens);
        if (parsed?.access && isAccessTokenExpired(parsed.access)) {
          return;
        }
      } else {
        return;
      }
    } catch {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Use specific check functions for known action types
      let result: LockResult;
      
      switch (actionType) {
        case 'consultation':
          result = await checkConsultationLock(params.visit_id);
          break;
        case 'radiology_upload':
          result = await checkRadiologyUploadLock(params.radiology_order_id);
          break;
        case 'drug_dispense':
          result = await checkDrugDispenseLock(params.prescription_id);
          break;
        case 'lab_order':
          result = await checkLabOrderLock(params.visit_id, params.consultation_id);
          break;
        case 'lab_result_post':
          result = await checkLabResultPostLock(params.lab_order_id);
          break;
        case 'radiology_report':
          result = await checkRadiologyReportLock(params.radiology_order_id);
          break;
        case 'procedure':
          result = await checkProcedureLock(params.visit_id, params.consultation_id);
          break;
        case 'radiology_view':
          result = await checkRadiologyViewLock(params.radiology_order_id);
          break;
        default:
          result = await evaluateLock(actionType, params);
      }
      
      setLockResult(result);
    } catch (err: any) {
      setError(err.message || 'Failed to check lock status');
      // Don't log 401 (auth) or 504 (gateway timeout - transient) to reduce console noise
      if (err?.status !== 401 && err?.status !== 504) {
        console.warn('Lock check failed:', err?.message || err);
      }
      // On error, set a default unlocked result so the button still shows
      // This prevents the button from disappearing when lock check fails
      setLockResult({
        is_locked: false,
        reason_code: 'ERROR',
        human_readable_message: 'Unable to verify lock status. Action may be available.',
        details: { error: err.message },
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!actuallyEnabled || !autoCheck) {
      return;
    }

    checkLock();

    if (autoCheck && checkInterval > 0) {
      const interval = setInterval(checkLock, checkInterval);
      return () => clearInterval(interval);
    }
  }, [actionType, JSON.stringify(params), actuallyEnabled, autoCheck, checkInterval]);

  return {
    lockResult,
    loading,
    error,
    isLocked: lockResult?.is_locked ?? false,
    checkLock,
    refresh: checkLock,
  };
};

