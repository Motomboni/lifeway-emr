# Payment Event System - Event-Driven Architecture

## Overview

This document describes the event-driven mechanism for handling payment confirmations in the EMR system. When a `BillingLineItem` transitions to `PAID` status, a `PAYMENT_CONFIRMED` event is fired, which triggers handlers to unlock consultations, update visit status, and enable doctor dashboard access.

## Architecture

### Event-Driven Design

The system uses Django signals to detect state transitions and fire domain events. Event handlers are idempotent and ensure clean separation of concerns.

### Components

1. **Domain Events** (`domain_events.py`)
   - `PaymentConfirmedEvent`: Fired when BillingLineItem transitions to PAID

2. **Signal Handlers** (`billing_line_item_signals.py`)
   - `track_billing_line_item_status_change`: Tracks status before save
   - `handle_billing_line_item_payment_confirmed`: Fires event on transition to PAID

3. **Event Handlers** (`payment_event_handlers.py`)
   - `handle_payment_confirmed`: Main event handler
   - `handle_payment_confirmed_idempotent`: Idempotent wrapper
   - `_unlock_consultation`: Unlocks PENDING consultations
   - `_update_visit_status`: Updates visit payment status

## Event Flow

```
BillingLineItem.save() 
  → Status changes to PAID
  → Signal fires PAYMENT_CONFIRMED event
  → Event handlers process:
     1. Unlock consultation (PENDING → ACTIVE)
     2. Update visit payment status
     3. Enable doctor dashboard access
```

## Event Definition

### PaymentConfirmedEvent

```python
@dataclass
class PaymentConfirmedEvent:
    billing_line_item_id: int
    visit_id: int
    service_code: str
    amount: Decimal
    payment_method: str
    consultation_id: Optional[int] = None
    timestamp: Optional[datetime] = None
```

## Event Handlers

### 1. Unlock Consultation

**Trigger**: Consultation is in PENDING status  
**Action**: 
- Updates consultation status to ACTIVE
- Assigns doctor if not already assigned
- Updates visit payment_status if needed

**Idempotency**: 
- If consultation is already ACTIVE, handler does nothing
- Can be called multiple times safely

### 2. Update Visit Status

**Trigger**: Visit payment is not cleared  
**Action**:
- Updates visit payment_status to reflect payment confirmation
- Ensures visit is in "ACTIVE" state (OPEN with payment cleared)

**Idempotency**:
- If visit payment_status is already cleared, handler does nothing
- Can be called multiple times safely

## Idempotency Guarantees

### Signal-Level Protection

The signal handler tracks previous status to detect actual transitions:
- Only fires event when status changes from non-PAID to PAID
- Prevents double-triggering on save operations

### Handler-Level Protection

The idempotent wrapper checks consultation status:
- If consultation is already ACTIVE, skips processing
- Allows safe re-processing if consultation is still PENDING

### Handler Internal Protection

Each handler checks current state before processing:
- `_unlock_consultation`: Only processes if status is PENDING
- `_update_visit_status`: Only processes if visit is OPEN and payment not cleared

## Usage Examples

### Manual Event Handling

```python
from apps.billing.domain_events import PaymentConfirmedEvent
from apps.billing.payment_event_handlers import handle_payment_confirmed_idempotent

# Create event
event = PaymentConfirmedEvent(
    billing_line_item_id=line_item.id,
    visit_id=visit.id,
    service_code=line_item.source_service_code,
    amount=line_item.amount,
    payment_method='CASH',
    consultation_id=consultation.id if consultation else None,
)

# Handle event (idempotent)
handle_payment_confirmed_idempotent(event)
```

### Automatic Event Firing

Events are automatically fired when BillingLineItem transitions to PAID:

```python
# Apply payment (automatically fires event)
billing_line_item.apply_payment(
    payment_amount=Decimal('5000.00'),
    payment_method='CASH'
)
# Event is automatically fired and handled
```

## Testing

### Test Coverage

The test suite (`tests_payment_events.py`) covers:
- Event creation and serialization
- Consultation unlocking
- Visit status updates
- Idempotency (no double-triggering)
- Signal firing on status transitions
- Partial payments (no event)
- Already paid items (no event)

### Key Test Cases

1. **test_billing_line_item_transition_to_paid_fires_event**: Verifies event fires on transition
2. **test_billing_line_item_no_double_triggering**: Ensures event fires only once
3. **test_handle_payment_confirmed_idempotent**: Verifies handler is idempotent
4. **test_billing_line_item_partial_payment_no_event**: Verifies partial payment doesn't fire event

## Integration

### Signal Registration

Signals are automatically registered when the billing app is ready:

```python
# apps/billing/apps.py
def ready(self):
    import apps.billing.billing_line_item_signals  # noqa
```

### Transaction Safety

All event handlers use `transaction.atomic()` to ensure:
- All-or-nothing processing
- Database consistency
- Rollback on errors

## Error Handling

### Graceful Degradation

Event handlers use try-except blocks to:
- Log errors without failing the save operation
- Allow other handlers to proceed
- Prevent event processing from blocking billing operations

### Logging

All event processing is logged:
- Info level: Successful processing
- Debug level: Idempotency skips
- Warning level: Missing related objects
- Error level: Processing failures

## Future Enhancements

- Event queue for async processing
- Event replay for recovery
- Event sourcing for audit trail
- Multiple event types (PAYMENT_PARTIAL, PAYMENT_FAILED, etc.)
- Event subscriptions for external systems

