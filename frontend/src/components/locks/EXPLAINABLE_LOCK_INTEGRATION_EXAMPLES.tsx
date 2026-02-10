/**
 * Integration Examples for Explainable Lock UI Pattern
 * 
 * These examples show how to integrate the lock pattern into various components.
 */

import React from 'react';
import LockIndicator from './LockIndicator';
import LockedButton from './LockedButton';
import LockWrapper from './LockWrapper';
import { useActionLock } from '../../hooks/useActionLock';

// ============================================================================
// Example 1: Consultation Start Button
// ============================================================================

export function ConsultationStartExample({ visitId }: { visitId: number }) {
  const consultationLock = useActionLock({
    actionType: 'consultation',
    params: { visit_id: visitId },
  });

  const handleStartConsultation = () => {
    // Start consultation logic
    console.log('Starting consultation...');
  };

  return (
    <div>
      <LockedButton
        lockResult={consultationLock.lockResult}
        loading={consultationLock.loading}
        onClick={handleStartConsultation}
        variant="primary"
        showLockMessage={true}
      >
        Start Consultation
      </LockedButton>
    </div>
  );
}

// ============================================================================
// Example 2: Radiology Upload Section
// ============================================================================

export function RadiologyUploadExample({ radiologyOrderId }: { radiologyOrderId: number }) {
  const uploadLock = useActionLock({
    actionType: 'radiology_upload',
    params: { radiology_request_id: radiologyOrderId },
  });

  return (
    <div>
      <h3>Upload Radiology Images</h3>
      
      {uploadLock.isLocked && uploadLock.lockResult && (
        <LockIndicator
          lockResult={uploadLock.lockResult}
          loading={uploadLock.loading}
          variant="card"
        />
      )}
      
      {!uploadLock.isLocked && (
        <div>
          <input type="file" accept="image/*,.dcm" />
          <button onClick={() => console.log('Upload...')}>
            Upload Images
          </button>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Example 3: Drug Dispense Action
// ============================================================================

export function DrugDispenseExample({ prescriptionId }: { prescriptionId: number }) {
  const dispenseLock = useActionLock({
    actionType: 'drug_dispense',
    params: { prescription_id: prescriptionId },
  });

  return (
    <LockWrapper
      actionType="drug_dispense"
      params={{ prescription_id: prescriptionId }}
      lockMessageVariant="inline"
    >
      {({ isLocked, loading }) => (
        <div>
          {!isLocked && !loading && (
            <button onClick={() => console.log('Dispense...')}>
              Dispense Drug
            </button>
          )}
        </div>
      )}
    </LockWrapper>
  );
}

// ============================================================================
// Example 4: Lab Order Form
// ============================================================================

export function LabOrderExample({ visitId, consultationId }: { 
  visitId: number; 
  consultationId?: number;
}) {
  const labOrderLock = useActionLock({
    actionType: 'lab_order',
    params: { visit_id: visitId, consultation_id: consultationId },
  });

  if (labOrderLock.loading) {
    return <div>Checking access...</div>;
  }

  if (labOrderLock.isLocked) {
    return (
      <div>
        <h3>Lab Orders</h3>
        <LockIndicator
          lockResult={labOrderLock.lockResult}
          variant="card"
        />
      </div>
    );
  }

  return (
    <div>
      <h3>Lab Orders</h3>
      <LabOrderForm visitId={visitId} consultationId={consultationId} />
    </div>
  );
}

function LabOrderForm({ visitId, consultationId }: { 
  visitId: number; 
  consultationId?: number;
}) {
  return <div>Lab Order Form...</div>;
}

// ============================================================================
// Example 5: Inline Lock Message
// ============================================================================

export function InlineLockExample({ visitId }: { visitId: number }) {
  const consultationLock = useActionLock({
    actionType: 'consultation',
    params: { visit_id: visitId },
  });

  return (
    <div className="consultation-section">
      <h2>Consultation</h2>
      
      {/* Show lock message inline if locked */}
      {consultationLock.isLocked && consultationLock.lockResult && (
        <LockIndicator
          lockResult={consultationLock.lockResult}
          variant="inline"
        />
      )}
      
      {/* Show consultation content if not locked */}
      {!consultationLock.isLocked && (
        <div>
          <p>Consultation content here...</p>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Example 6: Multiple Actions with Locks
// ============================================================================

export function MultipleActionsExample({ visitId }: { visitId: number }) {
  const consultationLock = useActionLock({
    actionType: 'consultation',
    params: { visit_id: visitId },
  });

  const labOrderLock = useActionLock({
    actionType: 'lab_order',
    params: { visit_id: visitId },
  });

  const procedureLock = useActionLock({
    actionType: 'procedure',
    params: { visit_id: visitId },
  });

  return (
    <div>
      <h2>Clinical Actions</h2>
      
      <div>
        <h3>Consultation</h3>
        <LockedButton
          lockResult={consultationLock.lockResult}
          loading={consultationLock.loading}
          onClick={() => console.log('Start consultation')}
          variant="primary"
        >
          Start Consultation
        </LockedButton>
      </div>
      
      <div>
        <h3>Lab Orders</h3>
        {labOrderLock.isLocked && labOrderLock.lockResult && (
          <LockIndicator
            lockResult={labOrderLock.lockResult}
            variant="inline"
          />
        )}
        {!labOrderLock.isLocked && (
          <button onClick={() => console.log('Create lab order')}>
            Create Lab Order
          </button>
        )}
      </div>
      
      <div>
        <h3>Procedures</h3>
        {procedureLock.isLocked && procedureLock.lockResult && (
          <LockIndicator
            lockResult={procedureLock.lockResult}
            variant="inline"
          />
        )}
        {!procedureLock.isLocked && (
          <button onClick={() => console.log('Create procedure')}>
            Create Procedure
          </button>
        )}
      </div>
    </div>
  );
}

