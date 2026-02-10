/**
 * Prescriptions Page
 * 
 * For Pharmacists to view and dispense prescriptions.
 * Per EMR Rules: Visit-scoped, shows visits with pending prescriptions.
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { fetchVisits, PaginatedResponse } from '../api/visits';
import { fetchPrescriptions, dispensePrescription } from '../api/prescription';
import { Visit } from '../types/visit';
import { Prescription } from '../types/prescription';
import { useToast } from '../hooks/useToast';
import LoadingSkeleton from '../components/common/LoadingSkeleton';
import BackToDashboard from '../components/common/BackToDashboard';
import LockIndicator from '../components/locks/LockIndicator';
import { useActionLock } from '../hooks/useActionLock';
import styles from '../styles/Prescriptions.module.css';

// Component for dispense button with lock check
function DispenseButtonWithLock({
  prescriptionId,
  visitId,
  onDispense,
  isDispensing,
}: {
  prescriptionId: number;
  visitId: number | null;
  onDispense: (id: number) => void;
  isDispensing: boolean;
}) {
  const dispenseLock = useActionLock({
    actionType: 'drug_dispense',
    params: { prescription_id: prescriptionId },
    enabled: !!prescriptionId,
  });

  if (dispenseLock.isLocked && dispenseLock.lockResult) {
    return (
      <div>
        <LockIndicator
          lockResult={dispenseLock.lockResult}
          loading={dispenseLock.loading}
          variant="inline"
        />
      </div>
    );
  }

  // Simple styled button for dispense action
  return (
    <button
      onClick={() => onDispense(prescriptionId)}
      disabled={dispenseLock.loading || isDispensing || dispenseLock.isLocked}
      style={{
        padding: '10px 20px',
        backgroundColor: dispenseLock.loading ? '#95a5a6' : dispenseLock.isLocked ? '#ccc' : '#27ae60',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: dispenseLock.loading || dispenseLock.isLocked ? 'not-allowed' : 'pointer',
        fontSize: '14px',
        fontWeight: 500,
        transition: 'background-color 0.2s',
      }}
    >
      {dispenseLock.loading ? 'Checking...' : isDispensing ? 'Dispensing...' : 'Dispense'}
    </button>
  );
}

export default function PrescriptionsPage() {
  const { user } = useAuth();
  const { showError, showSuccess } = useToast();
  
  const [visits, setVisits] = useState<Visit[]>([]);
  const [selectedVisit, setSelectedVisit] = useState<number | null>(null);
  const [selectedVisitData, setSelectedVisitData] = useState<Visit | null>(null);
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingPrescriptions, setLoadingPrescriptions] = useState(false);
  const [dispensing, setDispensing] = useState<number | null>(null);

  useEffect(() => {
    loadVisitsWithPendingPrescriptions();
  }, []);

  useEffect(() => {
    if (selectedVisit) {
      loadPrescriptions(selectedVisit.toString());
    }
  }, [selectedVisit]);

  const loadVisitsWithPendingPrescriptions = async () => {
    try {
      setLoading(true);
      // Load all visits (both OPEN and CLOSED) - pharmacists need to see all visits with prescriptions
      // Payment status doesn't matter for viewing prescriptions (only for dispensing)
      const response = await fetchVisits({});
      const allVisits = Array.isArray(response) ? response : (response as PaginatedResponse<Visit>).results;
      
      // Filter visits to only show those with prescriptions
      const visitsWithPrescriptions: Visit[] = [];
      for (const visit of allVisits) {
        try {
          const prescriptions = await fetchPrescriptions(visit.id.toString());
          // Only include visits that have at least one prescription
          if (prescriptions.length > 0) {
            visitsWithPrescriptions.push(visit);
          }
        } catch (err) {
          // Skip visits where we can't load prescriptions (might be permission issue or no prescriptions)
        }
      }
      setVisits(visitsWithPrescriptions);
    } catch (error) {
      console.error('Error loading visits:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load visits';
      showError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadPrescriptions = async (visitId: string) => {
    try {
      setLoadingPrescriptions(true);
      const prescs = await fetchPrescriptions(visitId);
      // Show all prescriptions (PENDING, DISPENSED, and CANCELLED for visibility)
      // Pharmacist needs to see all to know what's available
      setPrescriptions(prescs);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load prescriptions';
      showError(errorMessage);
      setPrescriptions([]);
    } finally {
      setLoadingPrescriptions(false);
    }
  };

  const handleDispense = async (prescriptionId: number) => {
    if (!selectedVisit) return;

    try {
      setDispensing(prescriptionId);
      await dispensePrescription(selectedVisit.toString(), prescriptionId);
      showSuccess('Prescription dispensed successfully');
      await loadPrescriptions(selectedVisit.toString());
    } catch (error: any) {
      // Parse error message from API response
      let errorMessage = 'Failed to dispense prescription';
      if (error?.responseData?.detail) {
        errorMessage = error.responseData.detail;
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      // Check for specific error cases
      if (errorMessage.includes('CLOSED') || errorMessage.includes('closed')) {
        errorMessage = 'Cannot dispense medication for a CLOSED visit. Closed visits are immutable.';
      } else if (errorMessage.includes('permission') || errorMessage.includes('Forbidden')) {
        errorMessage = 'You do not have permission to dispense this prescription. Only Pharmacists can dispense medication.';
      } else if (errorMessage.includes('payment') || errorMessage.includes('Payment')) {
        errorMessage = 'Payment must be cleared before dispensing medication.';
      }
      
      showError(errorMessage);
    } finally {
      setDispensing(null);
    }
  };

  if (user?.role !== 'PHARMACIST') {
    return (
      <div className={styles.errorContainer}>
        <p>Access denied. This page is for Pharmacists only.</p>
      </div>
    );
  }

  return (
    <div className={styles.prescriptionsPage}>
      <BackToDashboard />
      <header className={styles.header}>
        <h1>Prescriptions</h1>
        <p>Select a visit to view and dispense prescriptions</p>
      </header>

      <div className={styles.content}>
        <div className={styles.visitsPanel}>
          <h2>Visits with Prescriptions</h2>
          {loading ? (
            <LoadingSkeleton count={5} />
          ) : visits.length === 0 ? (
            <div className={styles.emptyState}>
              <p>No visits with prescriptions found</p>
            </div>
          ) : (
            <div className={styles.visitsList}>
              {visits.map((visit) => (
                <div
                  key={visit.id}
                  className={`${styles.visitItem} ${selectedVisit === visit.id ? styles.selected : ''}`}
                  onClick={() => {
                    setSelectedVisit(visit.id);
                    setSelectedVisitData(visit);
                  }}
                >
                  <div className={styles.visitInfo}>
                    <h3>Visit #{visit.id}</h3>
                    <p>{visit.patient_name || 'Unknown Patient'}</p>
                    <p className={styles.visitDate}>
                      {new Date(visit.created_at).toLocaleDateString()}
                    </p>
                    <p className={styles.visitStatus}>Status: {visit.status}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className={styles.prescriptionsPanel}>
          {selectedVisit ? (
            <>
              <h2>Prescriptions for Visit #{selectedVisit}</h2>
              {loadingPrescriptions ? (
                <LoadingSkeleton count={3} />
              ) : prescriptions.length === 0 ? (
                <div className={styles.emptyState}>
                  <p>No prescriptions for this visit</p>
                </div>
              ) : (
                <div className={styles.prescriptionsList}>
                  {prescriptions.map((prescription) => (
                    <div key={prescription.id} className={styles.prescriptionCard}>
                      <div className={styles.prescriptionHeader}>
                        <h3>{prescription.drug}</h3>
                        <span className={styles.prescriptionStatus}>{prescription.status}</span>
                      </div>
                      <div className={styles.prescriptionDetails}>
                        <p><strong>Dosage:</strong> {prescription.dosage}</p>
                        {prescription.frequency && (
                          <p><strong>Frequency:</strong> {prescription.frequency}</p>
                        )}
                        {prescription.duration && (
                          <p><strong>Duration:</strong> {prescription.duration}</p>
                        )}
                        {prescription.quantity && (
                          <p><strong>Quantity:</strong> {prescription.quantity}</p>
                        )}
                        {prescription.instructions && (
                          <p><strong>Instructions:</strong> {prescription.instructions}</p>
                        )}
                        {prescription.dispensing_notes && (
                          <div className={styles.notesSection}>
                            <p><strong>Dispensing Notes:</strong></p>
                            <p className={styles.notesText}>{prescription.dispensing_notes}</p>
                          </div>
                        )}
                      </div>
                      <div className={styles.prescriptionActions}>
                        {prescription.status === 'PENDING' && 
                         selectedVisitData?.status === 'OPEN' && (
                          <DispenseButtonWithLock
                            prescriptionId={prescription.id}
                            visitId={selectedVisit}
                            onDispense={handleDispense}
                            isDispensing={dispensing === prescription.id}
                          />
                        )}
                        {prescription.status === 'PENDING' && 
                         selectedVisitData?.status === 'CLOSED' && (
                          <span className={styles.disabledNote}>
                            Cannot dispense: Visit is CLOSED
                          </span>
                        )}
                        {prescription.status === 'DISPENSED' && (
                          <span className={styles.disabledNote}>
                            Already dispensed
                          </span>
                        )}
                        {prescription.status === 'CANCELLED' && (
                          <span className={styles.disabledNote}>
                            Prescription cancelled
                          </span>
                        )}
                        {prescription.status === 'PENDING' && !selectedVisitData && (
                          <span className={styles.disabledNote}>
                            Loading visit data...
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div className={styles.emptyState}>
              <p>Select a visit to view prescriptions</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
