"""
Domain Events for Billing System.

Per EMR Rules:
- Events are fired when significant state changes occur
- Event handlers are idempotent
- Clean separation of concerns
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal


@dataclass
class PaymentConfirmedEvent:
    """
    Event fired when a BillingLineItem transitions to PAID status.
    
    This event triggers:
    - Consultation unlocking (if waiting)
    - Doctor dashboard access
    - Visit status update to ACTIVE
    """
    billing_line_item_id: int
    visit_id: int
    service_code: str
    amount: Decimal
    payment_method: str
    consultation_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            from django.utils import timezone
            self.timestamp = timezone.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for logging/serialization."""
        return {
            'event_type': 'PAYMENT_CONFIRMED',
            'billing_line_item_id': self.billing_line_item_id,
            'visit_id': self.visit_id,
            'service_code': self.service_code,
            'amount': str(self.amount),
            'payment_method': self.payment_method,
            'consultation_id': self.consultation_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }

