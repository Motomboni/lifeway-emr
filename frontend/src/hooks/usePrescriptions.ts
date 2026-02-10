/**
 * usePrescriptions Hook
 * 
 * Custom hook for prescription state management and API interactions.
 */
import { useState, useEffect, useCallback } from 'react';
import { Prescription, PrescriptionCreateData } from '../types/prescription';
import {
  fetchPrescriptions,
  createPrescription as createPrescriptionAPI,
  dispensePrescription as dispensePrescriptionAPI
} from '../api/prescription';

interface UsePrescriptionsReturn {
  prescriptions: Prescription[];
  loading: boolean;
  error: string | null;
  isSaving: boolean;
  createPrescription: (visitId: string, consultationId: number, data: PrescriptionCreateData) => Promise<Prescription>;
  dispensePrescription: (visitId: string, prescriptionId: number, dispensingNotes?: string) => Promise<Prescription>;
  refresh: () => Promise<void>;
}

export function usePrescriptions(visitId: string): UsePrescriptionsReturn {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await fetchPrescriptions(visitId);
      setPrescriptions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load prescriptions');
    } finally {
      setLoading(false);
    }
  }, [visitId]);

  // Fetch prescriptions on mount
  useEffect(() => {
    loadData();
  }, [loadData]);

  const createPrescription = useCallback(async (
    visitId: string,
    consultationId: number,
    data: PrescriptionCreateData
  ) => {
    setIsSaving(true);
    setError(null);
    
    try {
      // Consultation is set from context by backend, not from request body
      const created = await createPrescriptionAPI(visitId, data);
      setPrescriptions(prev => [...prev, created]);
      return created;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create prescription');
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  const dispensePrescription = useCallback(async (
    visitId: string,
    prescriptionId: number,
    dispensingNotes?: string
  ) => {
    setIsSaving(true);
    setError(null);
    
    try {
      const dispensed = await dispensePrescriptionAPI(visitId, prescriptionId, dispensingNotes);
      setPrescriptions(prev => prev.map(p => p.id === prescriptionId ? dispensed : p));
      return dispensed;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to dispense prescription');
      throw err;
    } finally {
      setIsSaving(false);
    }
  }, []);

  return {
    prescriptions,
    loading,
    error,
    isSaving,
    createPrescription,
    dispensePrescription,
    refresh: loadData
  };
}
