# Explainable Lock UI Pattern

## Overview

The Explainable Lock UI pattern provides a consistent, reusable way to show why actions are disabled across the EMR. Instead of silent failures or confusing disabled buttons, users see clear explanations of what needs to happen to unlock an action.

## Components

### LockIndicator

A reusable component that displays lock status and explanation inline.

```tsx
import LockIndicator from '../components/locks/LockIndicator';
import { useActionLock } from '../hooks/useActionLock';

const consultationLock = useActionLock({
  actionType: 'consultation',
  params: { visit_id: visitId },
});

<LockIndicator 
  lockResult={consultationLock.lockResult}
  loading={consultationLock.loading}
  variant="inline"
/>
```

**Props:**
- `lockResult`: LockResult from API (null if not locked)
- `loading`: Boolean indicating if lock check is in progress
- `variant`: 'inline' | 'button' | 'card'
- `showIcon`: Boolean (default: true)
- `className`: Additional CSS classes
- `children`: Content to show when unlocked

### LockedButton

A button component that automatically shows lock status and explanation.

```tsx
import LockedButton from '../components/locks/LockedButton';
import { useActionLock } from '../hooks/useActionLock';

const consultationLock = useActionLock({
  actionType: 'consultation',
  params: { visit_id: visitId },
});

<LockedButton
  lockResult={consultationLock.lockResult}
  loading={consultationLock.loading}
  onClick={handleStartConsultation}
  variant="primary"
  showLockMessage={true}
>
  Start Consultation
</LockedButton>
```

**Props:**
- `lockResult`: LockResult from API
- `loading`: Boolean
- `onClick`: Handler function
- `disabled`: Additional disabled state
- `variant`: 'primary' | 'secondary' | 'danger'
- `size`: 'small' | 'medium' | 'large'
- `showLockMessage`: Show explanation below button (default: true)
- `children`: Button label

### useActionLock Hook

React hook for checking action locks with auto-refresh.

```tsx
const consultationLock = useActionLock({
  actionType: 'consultation',
  params: { visit_id: visitId },
  enabled: true,
  autoCheck: true,
  checkInterval: 30000, // 30 seconds
});
```

**Returns:**
- `lockResult`: LockResult | null
- `loading`: Boolean
- `error`: string | null
- `isLocked`: Boolean
- `checkLock`: Function to manually check
- `refresh`: Alias for checkLock

## Usage Examples

### Example 1: Consultation Lock

```tsx
import LockedButton from '../components/locks/LockedButton';
import { useActionLock } from '../hooks/useActionLock';

function ConsultationSection({ visitId }) {
  const consultationLock = useActionLock({
    actionType: 'consultation',
    params: { visit_id: visitId },
  });

  return (
    <div>
      <LockedButton
        lockResult={consultationLock.lockResult}
        loading={consultationLock.loading}
        onClick={handleStartConsultation}
        variant="primary"
      >
        Start Consultation
      </LockedButton>
    </div>
  );
}
```

### Example 2: Radiology Upload Lock

```tsx
import LockIndicator from '../components/locks/LockIndicator';
import { useActionLock } from '../hooks/useActionLock';

function RadiologyUploadSection({ radiologyOrderId }) {
  const uploadLock = useActionLock({
    actionType: 'radiology_upload',
    params: { radiology_request_id: radiologyOrderId },
  });

  return (
    <div>
      <LockIndicator 
        lockResult={uploadLock.lockResult}
        loading={uploadLock.loading}
        variant="card"
      />
      {!uploadLock.isLocked && (
        <UploadButton onClick={handleUpload} />
      )}
    </div>
  );
}
```

### Example 3: Inline Lock Message

```tsx
import LockIndicator from '../components/locks/LockIndicator';
import { useActionLock } from '../hooks/useActionLock';

function LabOrderSection({ visitId, consultationId }) {
  const labOrderLock = useActionLock({
    actionType: 'lab_order',
    params: { visit_id: visitId, consultation_id: consultationId },
  });

  return (
    <div>
      <h3>Lab Orders</h3>
      {labOrderLock.isLocked && (
        <LockIndicator 
          lockResult={labOrderLock.lockResult}
          variant="inline"
        />
      )}
      {!labOrderLock.isLocked && (
        <LabOrderForm />
      )}
    </div>
  );
}
```

### Example 4: Conditional Rendering

```tsx
import LockIndicator from '../components/locks/LockIndicator';
import { useActionLock } from '../hooks/useActionLock';

function DrugDispenseSection({ prescriptionId }) {
  const dispenseLock = useActionLock({
    actionType: 'drug_dispense',
    params: { prescription_id: prescriptionId },
  });

  if (dispenseLock.loading) {
    return <LoadingSpinner />;
  }

  if (dispenseLock.isLocked) {
    return (
      <LockIndicator 
        lockResult={dispenseLock.lockResult}
        variant="card"
      />
    );
  }

  return <DispenseForm prescriptionId={prescriptionId} />;
}
```

## Message Format

Lock messages follow this format:

**Pattern:**
```
[Action] locked: [Reason]. [Context]. [Unlock actions].
```

**Examples:**
- "Consultation locked: Payment not cleared. Current payment status: UNPAID. Please process payment before starting consultation."
- "Radiology image upload is locked because visit payment is not cleared. Current payment status: UNPAID. Please process payment before uploading images."
- "Drug dispense is locked because visit payment is not cleared. Current payment status: UNPAID. Please process payment before dispensing drugs. For emergency cases, set is_emergency=True with proper authorization."

## Styling

The lock indicator uses consistent styling:
- **Background**: Light yellow (#fff3cd)
- **Border**: Yellow (#ffc107) with left accent
- **Icon**: Lock icon in yellow
- **Text**: Dark yellow (#856404)
- **Unlock actions**: Bulleted list

## Best Practices

1. **Always Check Locks**: Check locks before showing action buttons
2. **Show Immediately**: Display lock message as soon as lock is detected
3. **Auto-Refresh**: Use auto-refresh for dynamic lock status
4. **Clear Messages**: Ensure messages explain both why and how to fix
5. **Consistent Placement**: Place lock indicators near the action they affect
6. **No Modals**: Keep explanations inline, not in popups
7. **Contextual**: Show locks in context of the action

## Integration Points

Apply this pattern to:
- ✅ Consultation start button
- ✅ Radiology upload buttons
- ✅ Drug dispense actions
- ✅ Lab order creation
- ✅ Lab result posting
- ✅ Radiology report posting
- ✅ Procedure creation
- ✅ Any other gated actions

## Accessibility

- Lock indicators are keyboard accessible
- Screen reader friendly
- High contrast colors
- Clear visual hierarchy
- Descriptive text for screen readers

