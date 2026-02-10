/**
 * Billing Section Component (Wrapper)
 * 
 * Wraps the new BillingDashboard component for backward compatibility.
 * Per EMR Rules: Visit-scoped, Receptionist-only access.
 */
import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/useToast';
import { 
  getBillingSummary, 
  getHMOProviders,
  BillingSummary,
} from '../../api/billing';
import { Visit } from '../../types/visit';
import { Patient } from '../../types/patient';
import BillingDashboard from './BillingDashboard';
import LoadingSpinner from '../common/LoadingSpinner';

interface BillingSectionProps {
  visitId: number;
  visit: Visit;
  patient: Patient | null;
  billingSummary: BillingSummary | null;
  hmoProviders: any[];
  onBillingUpdate: () => void;
}

export default function BillingSection({
  visitId,
  visit,
  patient,
  billingSummary: initialSummary,
  hmoProviders: initialProviders,
  onBillingUpdate
}: BillingSectionProps) {
  const { showError } = useToast();
  const [billingSummary, setBillingSummary] = useState<BillingSummary | null>(initialSummary);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Refresh billing summary when visit changes
    if (visitId) {
      loadBillingSummary();
    }
  }, [visitId]);

  const loadBillingSummary = async () => {
    try {
      setLoading(true);
      const summary = await getBillingSummary(visitId);
      setBillingSummary(summary);
    } catch (error) {
      console.error('Failed to load billing summary:', error);
      showError('Failed to load billing information');
    } finally {
      setLoading(false);
    }
  };

  const handleBillingUpdate = () => {
    loadBillingSummary();
    onBillingUpdate();
  };

  if (loading && !billingSummary) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-6">
        <LoadingSpinner message="Loading billing information..." />
      </div>
    );
  }

  return (
    <BillingDashboard
      visitId={visitId}
      visit={visit}
      patient={patient}
      billingSummary={billingSummary}
      onBillingUpdate={handleBillingUpdate}
    />
  );
}
