/**
 * useRadiologyOrders Hook
 * 
 * Custom hook for radiology order state management and API interactions.
 */
import { useState, useEffect, useCallback } from 'react';
import { RadiologyOrder, RadiologyOrderCreateData } from '../types/radiology';
import {
  fetchRadiologyOrders,
  createRadiologyOrder as createRadiologyOrderAPI,
} from '../api/radiology';

/** Data source: GET /visits/{visitId}/radiology/ (RadiologyRequest only). Do NOT fetch RadiologyResult. */
interface UseRadiologyOrdersReturn {
  radiologyOrders: RadiologyOrder[];
  loading: boolean;
  error: string | null;
  isSaving: boolean;
  createRadiologyOrder: (visitId: string, data: RadiologyOrderCreateData) => Promise<RadiologyOrder>;
  refresh: () => Promise<void>;
}

export function useRadiologyOrders(visitId: string): UseRadiologyOrdersReturn {
  const [radiologyOrders, setRadiologyOrders] = useState<RadiologyOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const orders = await fetchRadiologyOrders(visitId).catch(err => {
        if (err instanceof Error && (err.message.includes('404') || err.message.includes('Not found'))) {
          return [];
        }
        throw err;
      });

      const ordersArray = Array.isArray(orders)
        ? orders
        : (orders && typeof orders === 'object' && 'results' in orders && Array.isArray((orders as any).results))
          ? (orders as any).results
          : [];

      setRadiologyOrders(ordersArray);
    } catch (err) {
      if (err instanceof Error && !err.message.includes('404') && !err.message.includes('Not found')) {
        setError(err.message);
      } else {
        setRadiologyOrders([]);
      }
    } finally {
      setLoading(false);
    }
  }, [visitId]);

  // Fetch radiology orders and results on mount
  useEffect(() => {
    loadData();
  }, [loadData]);

  const createRadiologyOrder = useCallback(async (visitId: string, data: RadiologyOrderCreateData) => {
    setIsSaving(true);
    setError(null);
    
    try {
      const created = await createRadiologyOrderAPI(parseInt(visitId), {
        ...data,
      });
      setRadiologyOrders(prev => [...prev, created]);
      return created;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create radiology order');
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  return {
    radiologyOrders,
    loading,
    error,
    isSaving,
    createRadiologyOrder,
    refresh: loadData
  };
}
