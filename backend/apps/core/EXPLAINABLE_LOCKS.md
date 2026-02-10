# Explainable Lock System

## Overview

The Explainable Lock System provides a centralized mechanism for evaluating whether actions are locked and explaining why they are blocked. This ensures **no silent failures** - every blocked action has a clear, human-readable explanation.

## Key Principles

- **No Silent Failures**: Every lock must have an explanation
- **Deterministic**: Same inputs always produce same lock status
- **Auditable**: All lock evaluations are logged
- **Human-Readable**: Lock messages explain the issue clearly
- **Consistent**: Same logic used in backend and frontend

## Architecture

### LockEvaluator Service

The central `LockEvaluator` service provides static methods to evaluate locks for various actions:

- `evaluate_consultation_lock()` - Consultation access
- `evaluate_radiology_upload_lock()` - Radiology image upload
- `evaluate_drug_dispense_lock()` - Drug dispensing
- `evaluate_lab_order_lock()` - Lab order creation
- `evaluate_lab_result_post_lock()` - Lab result posting
- `evaluate_radiology_report_lock()` - Radiology report posting
- `evaluate_procedure_lock()` - Procedure creation
- `evaluate_action_lock()` - Generic action evaluation

### LockResult

Each evaluation returns a `LockResult` with:

- `is_locked` (boolean): Whether the action is locked
- `reason_code` (LockReasonCode): Standard reason code
- `human_readable_message` (string): Human-readable explanation
- `details` (dict, optional): Additional context
- `unlock_actions` (list, optional): Suggested actions to unlock

### LockReasonCode Enum

Standard reason codes:

- `PAYMENT_NOT_CLEARED` - Payment not cleared
- `PAYMENT_PARTIAL` - Partial payment
- `PAYMENT_PENDING` - Payment pending
- `CONSULTATION_NOT_STARTED` - Consultation not started
- `CONSULTATION_NOT_ACTIVE` - Consultation not active
- `CONSULTATION_CLOSED` - Consultation closed
- `VISIT_NOT_OPEN` - Visit not open
- `VISIT_CLOSED` - Visit closed
- `VISIT_NOT_FOUND` - Visit not found
- `ORDER_NOT_PAID` - Order not paid
- `ORDER_NOT_FOUND` - Order not found
- `ORDER_NOT_ACTIVE` - Order not active
- `INSUFFICIENT_PERMISSIONS` - Insufficient permissions
- `ROLE_NOT_ALLOWED` - Role not allowed
- `WORKFLOW_STEP_INCOMPLETE` - Workflow step incomplete
- `PREREQUISITE_MISSING` - Prerequisite missing
- `SYSTEM_MAINTENANCE` - System maintenance
- `RATE_LIMIT_EXCEEDED` - Rate limit exceeded
- `CUSTOM` - Custom reason

## API Endpoints

### Generic Lock Evaluation
```
POST /api/v1/locks/evaluate/
```

Request:
```json
{
  "action_type": "consultation",
  "visit_id": 123
}
```

Response:
```json
{
  "is_locked": true,
  "reason_code": "PAYMENT_NOT_CLEARED",
  "human_readable_message": "Consultation is locked because payment is not cleared...",
  "details": {
    "payment_status": "UNPAID"
  },
  "unlock_actions": [
    "Process payment for this visit",
    "Update payment status to PAID or SETTLED"
  ]
}
```

### Specific Action Endpoints

- `GET /api/v1/locks/consultation/?visit_id=123`
- `GET /api/v1/locks/radiology_upload/?radiology_order_id=456`
- `GET /api/v1/locks/drug_dispense/?prescription_id=789`
- `GET /api/v1/locks/lab_order/?visit_id=123&consultation_id=456`
- `GET /api/v1/locks/lab_result_post/?lab_order_id=789`
- `GET /api/v1/locks/radiology_report/?radiology_order_id=456`
- `GET /api/v1/locks/procedure/?visit_id=123&consultation_id=456`

## Frontend Integration

### API Client

```typescript
import { checkConsultationLock } from '../api/locks';

const lockResult = await checkConsultationLock(visitId);
if (lockResult.is_locked) {
  // Display lock message
}
```

### React Hook

```typescript
import { useLockCheck } from '../hooks/useLockCheck';

const consultationLock = useLockCheck({
  actionType: 'consultation',
  params: { visit_id: visitId },
  enabled: true,
});

if (consultationLock.lockResult?.is_locked) {
  // Display lock message
}
```

### LockMessage Component

```tsx
import LockMessage from '../components/locks/LockMessage';

<LockMessage 
  lockResult={lockResult} 
  variant="alert" 
  showUnlockActions={true} 
/>
```

Variants:
- `inline` - Inline message (default)
- `banner` - Banner-style message
- `alert` - Alert-style message

## Lock Evaluation Examples

### Consultation Lock

**Locked when:**
- Visit payment not cleared
- Visit is closed
- Visit not found

**Example message:**
> "Consultation is locked because payment is not cleared. Current payment status: UNPAID. Please process payment before starting consultation."

**Unlock actions:**
- Process payment for this visit
- Update payment status to PAID or SETTLED

### Radiology Upload Lock

**Locked when:**
- Radiology order not found
- Order not paid
- Visit payment not cleared

**Example message:**
> "Radiology image upload is locked because visit payment is not cleared. Current payment status: UNPAID. Please process payment before uploading images."

### Drug Dispense Lock

**Locked when:**
- Prescription not found
- Visit payment not cleared (unless emergency)
- Consultation not active

**Example message:**
> "Drug dispense is locked because visit payment is not cleared. Current payment status: UNPAID. Please process payment before dispensing drugs. For emergency cases, set is_emergency=True with proper authorization."

## Integration Points

### Backend Validation

Use lock evaluation in views/serializers:

```python
from apps.core.lock_system import LockEvaluator

def create_consultation(request, visit_id):
    lock_result = LockEvaluator.evaluate_consultation_lock(visit_id)
    if lock_result.is_locked:
        return Response(
            lock_result.to_dict(),
            status=status.HTTP_403_FORBIDDEN
        )
    # Proceed with consultation creation
```

### Frontend Pre-Check

Check locks before allowing actions:

```typescript
const handleStartConsultation = async () => {
  const lockResult = await checkConsultationLock(visitId);
  if (lockResult.is_locked) {
    // Show lock message, disable button
    return;
  }
  // Proceed with consultation
};
```

### Inline Display

Display lock messages inline in forms:

```tsx
{consultationLock.lockResult?.is_locked && (
  <LockMessage 
    lockResult={consultationLock.lockResult} 
    variant="alert" 
  />
)}
```

## Audit Trail

All lock evaluations are logged:

```
INFO: Lock evaluation: action=consultation, locked=True, reason=PAYMENT_NOT_CLEARED, kwargs={'visit_id': 123}
```

This provides a complete audit trail of why actions were blocked.

## Extending the System

### Adding New Lock Evaluators

1. Add method to `LockEvaluator`:

```python
@staticmethod
def evaluate_custom_action_lock(param1: int, param2: str) -> LockResult:
    # Evaluation logic
    if condition:
        return LockResult(
            is_locked=True,
            reason_code=LockReasonCode.CUSTOM,
            human_readable_message="Action is locked because...",
            unlock_actions=["Action 1", "Action 2"]
        )
    return LockResult(
        is_locked=False,
        reason_code=LockReasonCode.CUSTOM,
        human_readable_message="Action is available."
    )
```

2. Add to `evaluate_action_lock`:

```python
action_evaluators = {
    # ... existing evaluators
    'custom_action': LockEvaluator.evaluate_custom_action_lock,
}
```

3. Add API endpoint (optional):

```python
@action(detail=False, methods=['get'])
def custom_action(self, request):
    param1 = request.query_params.get('param1')
    result = LockEvaluator.evaluate_custom_action_lock(
        param1=int(param1),
        param2=request.query_params.get('param2')
    )
    return Response(result.to_dict())
```

4. Add frontend API function:

```typescript
export const checkCustomActionLock = async (
  param1: number,
  param2: string
): Promise<LockResult> => {
  return apiRequest<LockResult>(
    `/locks/custom_action/?param1=${param1}&param2=${param2}`
  );
};
```

## Best Practices

1. **Always Check Locks**: Check locks before allowing actions
2. **Display Messages**: Always display lock messages to users
3. **Provide Actions**: Include unlock actions in messages
4. **Log Evaluations**: All evaluations are automatically logged
5. **Consistent Logic**: Use same logic in backend and frontend
6. **Clear Messages**: Write clear, actionable lock messages
7. **Standard Codes**: Use standard reason codes when possible

## Testing

Test lock evaluations:

```python
def test_consultation_lock_payment_not_cleared():
    visit = create_visit(payment_status='UNPAID')
    result = LockEvaluator.evaluate_consultation_lock(visit.id)
    assert result.is_locked
    assert result.reason_code == LockReasonCode.PAYMENT_NOT_CLEARED
    assert 'payment' in result.human_readable_message.lower()
```

## Future Enhancements

Potential enhancements:
- Lock expiration times
- Temporary lock overrides
- Lock history tracking
- Lock analytics
- Custom lock rules per organization
- Lock notifications

