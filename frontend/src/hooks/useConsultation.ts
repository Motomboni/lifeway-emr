/**
 * useConsultation Hook
 * 
 * Custom hook for consultation state management and API interactions.
 * 
 * State Management Approach:
 * - Local state for form data (optimistic updates)
 * - Server state for consultation data (fetch on mount)
 * - Dirty state tracking for unsaved changes
 * - Loading and error states
 * 
 * API Interaction:
 * - GET /api/v1/visits/{visitId}/consultation/ - Fetch consultation
 * - POST /api/v1/visits/{visitId}/consultation/ - Create consultation
 * - PATCH /api/v1/visits/{visitId}/consultation/ - Update consultation
 */
import { useState, useEffect, useCallback } from 'react';
import { ConsultationData, Consultation } from '../types/consultation';
import {
  fetchConsultation,
  createConsultation,
  updateConsultation as updateConsultationAPI
} from '../api/consultation';

interface UseConsultationReturn {
  consultation: Consultation | null;
  loading: boolean;
  error: string | null;
  isSaving: boolean;
  saveConsultation: (visitId: string, data: ConsultationData) => Promise<void>;
  updateConsultation: (visitId: string, data: ConsultationData) => Promise<void>;
}

export interface UseConsultationOptions {
  /** When false, the consultation API is not called (avoids 403 when registration not paid). Default true. */
  enabled?: boolean;
}

export function useConsultation(visitId: string, options?: UseConsultationOptions): UseConsultationReturn {
  const enabled = options?.enabled !== false;
  const [consultation, setConsultation] = useState<Consultation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Fetch consultation on mount only when enabled (skip when payment gate not cleared)
  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      setError(null);
      setConsultation(null);
      return;
    }
    const loadConsultation = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const data = await fetchConsultation(visitId);
        setConsultation(data);
      } catch (err) {
        // 404 is expected if consultation doesn't exist yet
        if (err instanceof Error && err.message.includes('404')) {
          setConsultation(null);
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load consultation');
        }
      } finally {
        setLoading(false);
      }
    };

    loadConsultation();
  }, [visitId, enabled]);

  const saveConsultation = useCallback(async (visitId: string, data: ConsultationData) => {
    setIsSaving(true);
    setError(null);
    
    try {
      const saved = await createConsultation(visitId, data);
      setConsultation(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save consultation');
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  const updateConsultation = useCallback(async (visitId: string, data: ConsultationData) => {
    setIsSaving(true);
    setError(null);
    
    try {
      const updated = await updateConsultationAPI(visitId, data);
      setConsultation(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update consultation');
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  return {
    consultation,
    loading,
    error,
    isSaving,
    saveConsultation,
    updateConsultation
  };
}
