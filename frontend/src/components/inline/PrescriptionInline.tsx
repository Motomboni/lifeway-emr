/**
 * PrescriptionInline Component
 * 
 * Inline component for prescriptions within consultation workspace.
 * 
 * Per EMR Rules:
 * - Visit-scoped: Requires visitId
 * - Consultation-dependent: Requires consultationId
 * - Doctor: Can create prescriptions, view all
 * - Pharmacist: Can dispense prescriptions (separate workflow)
 * - No sidebar navigation - inline only
 */
import React, { useState } from 'react';
import { usePrescriptions } from '../../hooks/usePrescriptions';
import { useToast } from '../../hooks/useToast';
import { useAuth } from '../../contexts/AuthContext';
import { Prescription } from '../../types/prescription';
import DrugSearchInput from '../common/DrugSearchInput';
import { Drug } from '../../types/drug';
import LockedButton from '../locks/LockedButton';
import { useActionLock } from '../../hooks/useActionLock';
import styles from '../../styles/ConsultationWorkspace.module.css';

interface PrescriptionInlineProps {
  visitId: string;
  consultationId?: number;
}

// Component for dispense button with lock check
function DispenseButtonWithLock({
  prescriptionId,
  visitId,
  onDispense,
  isDispensing,
}: {
  prescriptionId: number;
  visitId: string;
  onDispense: (id: number) => void;
  isDispensing: boolean;
}) {
  const dispenseLock = useActionLock({
    actionType: 'drug_dispense',
    params: { prescription_id: prescriptionId },
    enabled: !!prescriptionId,
  });

  return (
    <LockedButton
      lockResult={dispenseLock.lockResult}
      loading={dispenseLock.loading || isDispensing}
      onClick={() => onDispense(prescriptionId)}
      variant="primary"
      showLockMessage={true}
      className={styles.addButton}
    >
      {isDispensing ? 'Dispensing...' : 'Dispense'}
    </LockedButton>
  );
}

export default function PrescriptionInline({ visitId, consultationId }: PrescriptionInlineProps) {
  const {
    prescriptions,
    loading,
    error,
    isSaving,
    createPrescription,
    dispensePrescription,
    refresh
  } = usePrescriptions(visitId);
  
  const { user } = useAuth();
  const { showSuccess, showError } = useToast();
  
  // Only pharmacists can dispense
  const canDispense = user?.role === 'PHARMACIST';
  
  const [showCreatePrescription, setShowCreatePrescription] = useState(false);
  const [newPrescriptionDrug, setNewPrescriptionDrug] = useState('');
  const [newPrescriptionDrugCode, setNewPrescriptionDrugCode] = useState('');
  const [newPrescriptionDosage, setNewPrescriptionDosage] = useState('');
  const [newPrescriptionFrequency, setNewPrescriptionFrequency] = useState('');
  const [newPrescriptionDuration, setNewPrescriptionDuration] = useState('');
  const [newPrescriptionQuantity, setNewPrescriptionQuantity] = useState('');
  const [newPrescriptionInstructions, setNewPrescriptionInstructions] = useState('');

  const handleCreatePrescription = async () => {
    if (!consultationId) {
      showError('Consultation is required to create prescriptions');
      return;
    }

    if (!newPrescriptionDrug.trim()) {
      showError('Drug name is required');
      return;
    }

    if (!newPrescriptionDosage.trim()) {
      showError('Dosage is required');
      return;
    }

    try {
      await createPrescription(visitId, consultationId, {
        drug: newPrescriptionDrug,
        drug_code: newPrescriptionDrugCode || undefined,
        dosage: newPrescriptionDosage,
        frequency: newPrescriptionFrequency || undefined,
        duration: newPrescriptionDuration || undefined,
        quantity: newPrescriptionQuantity || undefined,
        instructions: newPrescriptionInstructions || undefined
      });
      showSuccess('Prescription created successfully');
      setShowCreatePrescription(false);
      resetForm();
      await refresh();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to create prescription');
    }
  };

  const handleDispense = async (prescriptionId: number) => {
    try {
      await dispensePrescription(visitId, prescriptionId);
      showSuccess('Prescription dispensed successfully');
      await refresh();
    } catch (err) {
      showError(err instanceof Error ? err.message : 'Failed to dispense prescription');
    }
  };

  const resetForm = () => {
    setNewPrescriptionDrug('');
    setNewPrescriptionDrugCode('');
    setNewPrescriptionDosage('');
    setNewPrescriptionFrequency('');
    setNewPrescriptionDuration('');
    setNewPrescriptionQuantity('');
    setNewPrescriptionInstructions('');
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'DISPENSED':
        return styles.statusBadge;
      case 'CANCELLED':
        return styles.statusBadge;
      default:
        return styles.statusBadge;
    }
  };

  if (loading) {
    return (
      <div className={styles.inlineComponent}>
        <h3>Prescriptions</h3>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className={styles.inlineComponent}>
      <div className={styles.inlineHeader}>
        <h3>Prescriptions</h3>
        {consultationId && !showCreatePrescription && user?.role === 'DOCTOR' && (
          <button
            className={styles.addButton}
            onClick={() => setShowCreatePrescription(true)}
            type="button"
          >
            + New Prescription
          </button>
        )}
      </div>

      {error && (
        <div className={styles.errorMessage}>{error}</div>
      )}

      {/* Create new prescription form */}
      {showCreatePrescription && consultationId && (
        <div className={styles.createForm}>
          <h4>Create Prescription</h4>
          <div className={styles.formGroup}>
            <label>Drug Name *</label>
            <DrugSearchInput
              value={newPrescriptionDrug}
              onChange={(drugName, drugCode) => {
                setNewPrescriptionDrug(drugName);
                if (drugCode) {
                  setNewPrescriptionDrugCode(drugCode);
                }
              }}
              onDrugSelect={(drug: Drug) => {
                // Auto-fill drug code if available
                if (drug.drug_code) {
                  setNewPrescriptionDrugCode(drug.drug_code);
                }
                // Optionally suggest common dosages if available
                if (drug.common_dosages && !newPrescriptionDosage) {
                  // Could pre-fill or show as hint
                }
              }}
              placeholder="Search for a drug (e.g., Paracetamol, Amoxicillin)..."
              required
            />
          </div>
          <div className={styles.formGroup}>
            <label>Drug Code (optional)</label>
            <input
              type="text"
              value={newPrescriptionDrugCode}
              onChange={(e) => setNewPrescriptionDrugCode(e.target.value)}
              placeholder="e.g., NDC code (auto-filled if drug selected)"
            />
          </div>
          <div className={styles.formGroup}>
            <label>Dosage *</label>
            <input
              type="text"
              value={newPrescriptionDosage}
              onChange={(e) => setNewPrescriptionDosage(e.target.value)}
              placeholder="e.g., 500mg twice daily"
              required
            />
          </div>
          <div className={styles.formGroup}>
            <label>Frequency (optional)</label>
            <input
              type="text"
              value={newPrescriptionFrequency}
              onChange={(e) => setNewPrescriptionFrequency(e.target.value)}
              placeholder="e.g., BID, TID, QID"
            />
          </div>
          <div className={styles.formGroup}>
            <label>Duration (optional)</label>
            <input
              type="text"
              value={newPrescriptionDuration}
              onChange={(e) => setNewPrescriptionDuration(e.target.value)}
              placeholder="e.g., 7 days, 2 weeks"
            />
          </div>
          <div className={styles.formGroup}>
            <label>Quantity (optional)</label>
            <input
              type="text"
              value={newPrescriptionQuantity}
              onChange={(e) => setNewPrescriptionQuantity(e.target.value)}
              placeholder="e.g., 30 tablets, 1 bottle"
            />
          </div>
          <div className={styles.formGroup}>
            <label>Instructions (optional)</label>
            <textarea
              value={newPrescriptionInstructions}
              onChange={(e) => setNewPrescriptionInstructions(e.target.value)}
              placeholder="Additional instructions for the patient"
              rows={3}
            />
          </div>
          <div className={styles.formActions}>
            <button
              className={styles.saveButton}
              onClick={handleCreatePrescription}
              disabled={isSaving || !newPrescriptionDrug.trim() || !newPrescriptionDosage.trim()}
            >
              {isSaving ? 'Creating...' : 'Create Prescription'}
            </button>
            <button
              className={styles.cancelButton}
              onClick={() => {
                setShowCreatePrescription(false);
                resetForm();
              }}
              disabled={isSaving}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Prescriptions list */}
      {prescriptions.length === 0 && !showCreatePrescription && (
        <p className={styles.emptyState}>No prescriptions for this visit.</p>
      )}

      {prescriptions.map(prescription => (
        <div key={prescription.id} className={styles.labOrderCard}>
          <div className={styles.orderHeader}>
            <div>
              <strong>Prescription #{prescription.id}</strong>
              <span
                className={getStatusBadgeClass(prescription.status)}
                style={prescription.status === 'DISPENSED' ? { backgroundColor: '#4caf50', color: 'white' } : undefined}
              >
                {prescription.status}
              </span>
            </div>
            {prescription.status === 'PENDING' && !prescription.dispensed && canDispense && (
              <DispenseButtonWithLock
                prescriptionId={prescription.id}
                visitId={visitId}
                onDispense={handleDispense}
                isDispensing={isSaving}
              />
            )}
          </div>

          <div className={styles.orderDetails}>
            <div><strong>Drug:</strong> {prescription.drug}</div>
            {prescription.drug_code && (
              <div><strong>Code:</strong> {prescription.drug_code}</div>
            )}
            <div><strong>Dosage:</strong> {prescription.dosage}</div>
            {prescription.frequency && (
              <div><strong>Frequency:</strong> {prescription.frequency}</div>
            )}
            {prescription.duration && (
              <div><strong>Duration:</strong> {prescription.duration}</div>
            )}
            {prescription.quantity && (
              <div><strong>Quantity:</strong> {prescription.quantity}</div>
            )}
            {prescription.instructions && (
              <div><strong>Instructions:</strong> {prescription.instructions}</div>
            )}
          </div>

          {prescription.dispensed && prescription.dispensed_date && (
            <div className={styles.resultCard}>
              <div className={styles.resultHeader}>
                <strong>Dispensing Information</strong>
              </div>
              {prescription.dispensing_notes && (
                <div className={styles.resultData}>{prescription.dispensing_notes}</div>
              )}
              <div className={styles.resultMeta}>
                Dispensed: {new Date(prescription.dispensed_date).toLocaleString()}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
