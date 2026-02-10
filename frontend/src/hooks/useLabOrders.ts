/**
 * useLabOrders Hook
 * 
 * Custom hook for lab order state management and API interactions.
 */
import { useState, useEffect, useCallback } from 'react';
import { LabOrder, LabOrderCreateData, LabResult } from '../types/lab';
import {
  fetchLabOrders,
  createLabOrder as createLabOrderAPI,
  fetchLabResults,
  createLabResult as createLabResultAPI
} from '../api/lab';

interface UseLabOrdersReturn {
  labOrders: LabOrder[];
  labResults: LabResult[];
  loading: boolean;
  error: string | null;
  isSaving: boolean;
  createLabOrder: (visitId: string, data: LabOrderCreateData) => Promise<LabOrder>;
  createLabResult: (visitId: string, labOrderId: number, resultData: string, abnormalFlag?: 'NORMAL' | 'ABNORMAL' | 'CRITICAL') => Promise<LabResult>;
  refresh: () => Promise<void>;
}

export function useLabOrders(visitId: string): UseLabOrdersReturn {
  const [labOrders, setLabOrders] = useState<LabOrder[]>([]);
  const [labResults, setLabResults] = useState<LabResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [orders, results] = await Promise.all([
        fetchLabOrders(visitId).catch(err => {
          // If 404 or empty, return empty array
          if (err instanceof Error && (err.message.includes('404') || err.message.includes('Not found'))) {
            return [];
          }
          throw err;
        }),
        fetchLabResults(visitId).catch(err => {
          // If 404 or empty, return empty array (expected when no results exist)
          if (err instanceof Error && (err.message.includes('404') || err.message.includes('Not found'))) {
            return [];
          }
          throw err;
        })
      ]);
      setLabOrders(Array.isArray(orders) ? orders : []);
      setLabResults(Array.isArray(results) ? results : []);
    } catch (err) {
      // Only set error for non-404 errors
      if (err instanceof Error && !err.message.includes('404') && !err.message.includes('Not found')) {
        setError(err.message);
      } else {
        // 404 is expected for empty results, just set empty arrays
        setLabOrders([]);
        setLabResults([]);
      }
    } finally {
      setLoading(false);
    }
  }, [visitId]);

  // Fetch lab orders and results on mount
  useEffect(() => {
    loadData();
  }, [loadData]);

  const createLabOrder = useCallback(async (visitId: string, data: LabOrderCreateData) => {
    setIsSaving(true);
    setError(null);
    
    try {
      const created = await createLabOrderAPI(visitId, data);
      setLabOrders(prev => [...prev, created]);
      return created;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create lab order');
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  const createLabResult = useCallback(async (
    visitId: string,
    labOrderId: number,
    resultData: string,
    abnormalFlag: 'NORMAL' | 'ABNORMAL' | 'CRITICAL' = 'NORMAL'
  ) => {
    setIsSaving(true);
    setError(null);
    
    try {
      const created = await createLabResultAPI(visitId, {
        lab_order: labOrderId,
        result_data: resultData,
        abnormal_flag: abnormalFlag
      });
      setLabResults(prev => [...prev, created]);
      return created;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create lab result');
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  return {
    labOrders,
    labResults,
    loading,
    error,
    isSaving,
    createLabOrder,
    createLabResult,
    refresh: loadData
  };
}
