"""
Explainable Lock System for EMR.

This module provides a centralized system for evaluating whether actions
are locked and explaining why they are blocked.

Key Principles:
- No silent failures: Every lock must have an explanation
- Deterministic: Same inputs always produce same lock status
- Auditable: All lock evaluations are logged
- Human-readable: Lock messages explain the issue clearly
"""
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from django.utils import timezone

logger = logging.getLogger(__name__)


class LockReasonCode(Enum):
    """Standard lock reason codes across the EMR."""
    
    # Payment-related locks
    PAYMENT_NOT_CLEARED = "PAYMENT_NOT_CLEARED"
    PAYMENT_PARTIAL = "PAYMENT_PARTIAL"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    
    # Consultation-related locks
    CONSULTATION_NOT_STARTED = "CONSULTATION_NOT_STARTED"
    CONSULTATION_NOT_ACTIVE = "CONSULTATION_NOT_ACTIVE"
    CONSULTATION_CLOSED = "CONSULTATION_CLOSED"
    
    # Visit-related locks
    VISIT_NOT_OPEN = "VISIT_NOT_OPEN"
    VISIT_CLOSED = "VISIT_CLOSED"
    VISIT_NOT_FOUND = "VISIT_NOT_FOUND"
    
    # Order-related locks
    ORDER_NOT_PAID = "ORDER_NOT_PAID"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_NOT_ACTIVE = "ORDER_NOT_ACTIVE"
    
    # Permission-related locks
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    ROLE_NOT_ALLOWED = "ROLE_NOT_ALLOWED"
    
    # Workflow-related locks
    WORKFLOW_STEP_INCOMPLETE = "WORKFLOW_STEP_INCOMPLETE"
    PREREQUISITE_MISSING = "PREREQUISITE_MISSING"
    
    # System locks
    SYSTEM_MAINTENANCE = "SYSTEM_MAINTENANCE"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    
    # Custom locks (for specific use cases)
    CUSTOM = "CUSTOM"


@dataclass
class LockResult:
    """
    Result of a lock evaluation.
    
    Attributes:
        is_locked: Whether the action is locked
        reason_code: Standard reason code for the lock
        human_readable_message: Human-readable explanation
        details: Additional context (optional)
        unlock_actions: Suggested actions to unlock (optional)
    """
    is_locked: bool
    reason_code: LockReasonCode
    human_readable_message: str
    details: Optional[Dict[str, Any]] = None
    unlock_actions: Optional[list] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'is_locked': self.is_locked,
            'reason_code': self.reason_code.value,
            'human_readable_message': self.human_readable_message,
            'details': self.details or {},
            'unlock_actions': self.unlock_actions or []
        }


class LockEvaluator:
    """
    Central lock evaluator service.
    
    This service evaluates locks for various actions across the EMR
    and provides explainable lock results.
    """
    
    @staticmethod
    def evaluate_consultation_lock(visit_id: int, user_role: str = None) -> LockResult:
        """
        Evaluate if consultation is locked.
        
        Locks consultation if:
        - Visit payment not cleared
        - Visit is closed
        - Visit not found
        """
        from apps.visits.models import Visit
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.VISIT_NOT_FOUND,
                human_readable_message=f"Visit {visit_id} not found.",
                unlock_actions=["Create a new visit for this patient"]
            )
        
        # Check if visit is closed
        if visit.status == 'CLOSED':
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.VISIT_CLOSED,
                human_readable_message="This visit is closed. Consultations cannot be started for closed visits.",
                details={'visit_status': visit.status},
                unlock_actions=["Create a new visit for this patient"]
            )
        
        # Check payment status
        if not visit.is_payment_cleared():
            payment_status = visit.payment_status
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.PAYMENT_NOT_CLEARED,
                human_readable_message=(
                    f"Consultation is locked because payment is not cleared. "
                    f"Current payment status: {payment_status}. "
                    f"Please process payment before starting consultation."
                ),
                details={
                    'payment_status': payment_status,
                    'payment_type': getattr(visit, 'payment_type', None)
                },
                unlock_actions=[
                    "Process payment for this visit",
                    "Update payment status to PAID or SETTLED"
                ]
            )
        
        # Consultation is not locked
        return LockResult(
            is_locked=False,
            reason_code=LockReasonCode.CUSTOM,
            human_readable_message="Consultation is available."
        )
    
    @staticmethod
    def evaluate_radiology_upload_lock(
        radiology_order_id: int,
        visit_id: int = None
    ) -> LockResult:
        """
        Evaluate if radiology image upload is locked.
        
        Locks upload if:
        - Radiology order not found
        - Order not paid
        - Visit payment not cleared
        """
        from apps.radiology.models import RadiologyRequest
        
        try:
            radiology_order = RadiologyRequest.objects.get(pk=radiology_order_id)
        except RadiologyRequest.DoesNotExist:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.ORDER_NOT_FOUND,
                human_readable_message=f"Radiology order {radiology_order_id} not found.",
                unlock_actions=["Create a radiology order first"]
            )
        
        visit = radiology_order.visit
        
        # Check visit payment
        if not visit.is_payment_cleared():
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.PAYMENT_NOT_CLEARED,
                human_readable_message=(
                    f"Radiology image upload is locked because visit payment is not cleared. "
                    f"Current payment status: {visit.payment_status}. "
                    f"Please process payment before uploading images."
                ),
                details={
                    'payment_status': visit.payment_status,
                    'visit_id': visit.id
                },
                unlock_actions=[
                    "Process payment for this visit",
                    "Update payment status to PAID or SETTLED"
                ]
            )
        
        # Check if order is active
        if radiology_order.status not in ['PENDING', 'ORDERED', 'IN_PROGRESS']:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.ORDER_NOT_ACTIVE,
                human_readable_message=(
                    f"Radiology image upload is locked because the order status is '{radiology_order.status}'. "
                    f"Only active orders can receive image uploads."
                ),
                details={'order_status': radiology_order.status},
                unlock_actions=["Update radiology order status to active"]
            )
        
        # Upload is not locked
        return LockResult(
            is_locked=False,
            reason_code=LockReasonCode.CUSTOM,
            human_readable_message="Radiology image upload is available."
        )
    
    @staticmethod
    def evaluate_drug_dispense_lock(
        prescription_id: int,
        visit_id: int = None
    ) -> LockResult:
        """
        Evaluate if drug dispense is locked.
        
        Locks dispense if:
        - Prescription not found
        - Visit payment not cleared (unless emergency)
        - Consultation not active
        """
        from apps.pharmacy.models import Prescription
        
        try:
            prescription = Prescription.objects.get(pk=prescription_id)
        except Prescription.DoesNotExist:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.ORDER_NOT_FOUND,
                human_readable_message=f"Prescription {prescription_id} not found.",
                unlock_actions=["Create a prescription first"]
            )
        
        visit = prescription.visit
        
        # Emergency prescriptions bypass payment check
        if not prescription.is_emergency:
            # Check visit payment
            if not visit.is_payment_cleared():
                return LockResult(
                    is_locked=True,
                    reason_code=LockReasonCode.PAYMENT_NOT_CLEARED,
                    human_readable_message=(
                        f"Drug dispense is locked because visit payment is not cleared. "
                        f"Current payment status: {visit.payment_status}. "
                        f"Please process payment before dispensing drugs. "
                        f"For emergency cases, set is_emergency=True with proper authorization."
                    ),
                    details={
                        'payment_status': visit.payment_status,
                        'is_emergency': False
                    },
                    unlock_actions=[
                        "Process payment for this visit",
                        "Or mark prescription as emergency (requires authorization)"
                    ]
                )
        
        # Check consultation if required
        if prescription.consultation:
            if prescription.consultation.status != 'ACTIVE':
                return LockResult(
                    is_locked=True,
                    reason_code=LockReasonCode.CONSULTATION_NOT_ACTIVE,
                    human_readable_message=(
                        f"Drug dispense is locked because the consultation is not active. "
                        f"Current consultation status: {prescription.consultation.status}. "
                        f"Only active consultations can have drugs dispensed."
                    ),
                    details={'consultation_status': prescription.consultation.status},
                    unlock_actions=["Activate the consultation"]
                )
        
        # Dispense is not locked
        return LockResult(
            is_locked=False,
            reason_code=LockReasonCode.CUSTOM,
            human_readable_message="Drug dispense is available."
        )
    
    @staticmethod
    def evaluate_lab_order_lock(visit_id: int, consultation_id: int = None) -> LockResult:
        """
        Evaluate if lab order creation is locked.
        
        Locks lab order if:
        - Visit payment not cleared
        - Consultation not active (if consultation_id provided)
        """
        from apps.visits.models import Visit
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.VISIT_NOT_FOUND,
                human_readable_message=f"Visit {visit_id} not found.",
                unlock_actions=["Create a new visit for this patient"]
            )
        
        # Check visit payment
        if not visit.is_payment_cleared():
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.PAYMENT_NOT_CLEARED,
                human_readable_message=(
                    f"Lab order is locked because visit payment is not cleared. "
                    f"Current payment status: {visit.payment_status}. "
                    f"Please process payment before placing lab orders."
                ),
                details={'payment_status': visit.payment_status},
                unlock_actions=["Process payment for this visit"]
            )
        
        # Check consultation if provided
        if consultation_id:
            from apps.consultations.models import Consultation
            try:
                consultation = Consultation.objects.get(pk=consultation_id)
                if consultation.status != 'ACTIVE':
                    return LockResult(
                        is_locked=True,
                        reason_code=LockReasonCode.CONSULTATION_NOT_ACTIVE,
                        human_readable_message=(
                            f"Lab order is locked because the consultation is not active. "
                            f"Current consultation status: {consultation.status}. "
                            f"Only active consultations can have lab orders."
                        ),
                        details={'consultation_status': consultation.status},
                        unlock_actions=["Activate the consultation"]
                    )
            except Consultation.DoesNotExist:
                return LockResult(
                    is_locked=True,
                    reason_code=LockReasonCode.CONSULTATION_NOT_STARTED,
                    human_readable_message=f"Consultation {consultation_id} not found.",
                    unlock_actions=["Create a consultation first"]
                )
        
        # Lab order is not locked
        return LockResult(
            is_locked=False,
            reason_code=LockReasonCode.CUSTOM,
            human_readable_message="Lab order is available."
        )
    
    @staticmethod
    def evaluate_lab_result_post_lock(lab_order_id: int) -> LockResult:
        """
        Evaluate if lab result posting is locked.
        
        Locks result posting if:
        - Lab order not found
        - Visit payment not cleared
        - Order not active
        """
        from apps.laboratory.models import LabOrder
        
        try:
            lab_order = LabOrder.objects.get(pk=lab_order_id)
        except LabOrder.DoesNotExist:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.ORDER_NOT_FOUND,
                human_readable_message=f"Lab order {lab_order_id} not found.",
                unlock_actions=["Create a lab order first"]
            )
        
        visit = lab_order.visit
        
        # Check visit payment
        if not visit.is_payment_cleared():
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.PAYMENT_NOT_CLEARED,
                human_readable_message=(
                    f"Lab result posting is locked because visit payment is not cleared. "
                    f"Current payment status: {visit.payment_status}. "
                    f"Please process payment before posting lab results."
                ),
                details={'payment_status': visit.payment_status},
                unlock_actions=["Process payment for this visit"]
            )
        
        # Check order status - allow posting results for ORDERED or SAMPLE_COLLECTED orders
        if lab_order.status not in [LabOrder.Status.ORDERED, LabOrder.Status.SAMPLE_COLLECTED]:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.ORDER_NOT_ACTIVE,
                human_readable_message=(
                    f"Lab result posting is locked because the order status is '{lab_order.status}'. "
                    f"Only active orders (Ordered or Sample Collected) can have results posted."
                ),
                details={'order_status': lab_order.status},
                unlock_actions=["Ensure lab order is in Ordered or Sample Collected status"]
            )
        
        # Result posting is not locked
        return LockResult(
            is_locked=False,
            reason_code=LockReasonCode.CUSTOM,
            human_readable_message="Lab result posting is available."
        )
    
    @staticmethod
    def evaluate_radiology_report_lock(radiology_order_id: int) -> LockResult:
        """
        Evaluate if radiology report posting is locked.
        
        Locks report posting if:
        - Radiology order not found
        - Visit payment not cleared
        - Order not active
        """
        from apps.radiology.models import RadiologyRequest
        
        try:
            radiology_order = RadiologyRequest.objects.get(pk=radiology_order_id)
        except RadiologyRequest.DoesNotExist:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.ORDER_NOT_FOUND,
                human_readable_message=f"Radiology order {radiology_order_id} not found.",
                unlock_actions=["Create a radiology order first"]
            )
        
        visit = radiology_order.visit
        
        # Check visit payment
        if not visit.is_payment_cleared():
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.PAYMENT_NOT_CLEARED,
                human_readable_message=(
                    f"Radiology report posting is locked because visit payment is not cleared. "
                    f"Current payment status: {visit.payment_status}. "
                    f"Please process payment before posting radiology reports."
                ),
                details={'payment_status': visit.payment_status},
                unlock_actions=["Process payment for this visit"]
            )
        
        # Check order status
        if radiology_order.status not in ['PENDING', 'ORDERED', 'IN_PROGRESS']:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.ORDER_NOT_ACTIVE,
                human_readable_message=(
                    f"Radiology report posting is locked because the order status is '{radiology_order.status}'. "
                    f"Only active orders can have reports posted."
                ),
                details={'order_status': radiology_order.status},
                unlock_actions=["Update radiology order status to active"]
            )
        
        # Report posting is not locked
        return LockResult(
            is_locked=False,
            reason_code=LockReasonCode.CUSTOM,
            human_readable_message="Radiology report posting is available."
        )

    @staticmethod
    def evaluate_radiology_view_lock(radiology_order_id: int) -> LockResult:
        """
        Evaluate if viewing a radiology order/result is locked.

        Locks view if:
        - Radiology order not found
        - Visit payment not cleared (policy: pay before viewing results)
        """
        from apps.radiology.models import RadiologyRequest

        try:
            radiology_order = RadiologyRequest.objects.get(pk=radiology_order_id)
        except RadiologyRequest.DoesNotExist:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.ORDER_NOT_FOUND,
                human_readable_message=f"Radiology order {radiology_order_id} not found.",
                unlock_actions=["Create a radiology order first"]
            )

        visit = radiology_order.visit

        if not visit.is_payment_cleared():
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.PAYMENT_NOT_CLEARED,
                human_readable_message=(
                    f"Radiology view is locked because visit payment is not cleared. "
                    f"Current payment status: {visit.payment_status}. "
                    f"Please process payment to view radiology results."
                ),
                details={'payment_status': visit.payment_status},
                unlock_actions=["Process payment for this visit"]
            )

        return LockResult(
            is_locked=False,
            reason_code=LockReasonCode.CUSTOM,
            human_readable_message="Radiology view is available."
        )

    @staticmethod
    def evaluate_procedure_lock(visit_id: int, consultation_id: int = None) -> LockResult:
        """
        Evaluate if procedure creation is locked.
        
        Locks procedure if:
        - Visit payment not cleared
        - Consultation not active (if consultation_id provided)
        """
        from apps.visits.models import Visit
        
        try:
            visit = Visit.objects.get(pk=visit_id)
        except Visit.DoesNotExist:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.VISIT_NOT_FOUND,
                human_readable_message=f"Visit {visit_id} not found.",
                unlock_actions=["Create a new visit for this patient"]
            )
        
        # Check visit payment
        if not visit.is_payment_cleared():
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.PAYMENT_NOT_CLEARED,
                human_readable_message=(
                    f"Procedure is locked because visit payment is not cleared. "
                    f"Current payment status: {visit.payment_status}. "
                    f"Please process payment before creating procedures."
                ),
                details={'payment_status': visit.payment_status},
                unlock_actions=["Process payment for this visit"]
            )
        
        # Check consultation if provided
        if consultation_id:
            from apps.consultations.models import Consultation
            try:
                consultation = Consultation.objects.get(pk=consultation_id)
                if consultation.status != 'ACTIVE':
                    return LockResult(
                        is_locked=True,
                        reason_code=LockReasonCode.CONSULTATION_NOT_ACTIVE,
                        human_readable_message=(
                            f"Procedure is locked because the consultation is not active. "
                            f"Current consultation status: {consultation.status}. "
                            f"Only active consultations can have procedures."
                        ),
                        details={'consultation_status': consultation.status},
                        unlock_actions=["Activate the consultation"]
                    )
            except Consultation.DoesNotExist:
                return LockResult(
                    is_locked=True,
                    reason_code=LockReasonCode.CONSULTATION_NOT_STARTED,
                    human_readable_message=f"Consultation {consultation_id} not found.",
                    unlock_actions=["Create a consultation first"]
                )
        
        # Procedure is not locked
        return LockResult(
            is_locked=False,
            reason_code=LockReasonCode.CUSTOM,
            human_readable_message="Procedure is available."
        )
    
    @staticmethod
    def evaluate_action_lock(
        action_type: str,
        **kwargs
    ) -> LockResult:
        """
        Generic method to evaluate locks for any action.
        
        Args:
            action_type: Type of action (e.g., 'consultation', 'radiology_upload', 'drug_dispense')
            **kwargs: Action-specific parameters
        
        Returns:
            LockResult
        """
        action_evaluators = {
            'consultation': LockEvaluator.evaluate_consultation_lock,
            'radiology_upload': LockEvaluator.evaluate_radiology_upload_lock,
            'radiology_view': LockEvaluator.evaluate_radiology_view_lock,
            'drug_dispense': LockEvaluator.evaluate_drug_dispense_lock,
            'lab_order': LockEvaluator.evaluate_lab_order_lock,
            'lab_result_post': LockEvaluator.evaluate_lab_result_post_lock,
            'radiology_report': LockEvaluator.evaluate_radiology_report_lock,
            'procedure': LockEvaluator.evaluate_procedure_lock,
        }
        
        evaluator = action_evaluators.get(action_type)
        if not evaluator:
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.CUSTOM,
                human_readable_message=f"Unknown action type: {action_type}",
                details={'action_type': action_type}
            )
        
        try:
            result = evaluator(**kwargs)
            # Log lock evaluation for audit trail
            logger.info(
                f"Lock evaluation: action={action_type}, "
                f"locked={result.is_locked}, reason={result.reason_code.value}, "
                f"kwargs={kwargs}"
            )
            return result
        except Exception as e:
            logger.error(f"Error evaluating lock for action {action_type}: {e}")
            return LockResult(
                is_locked=True,
                reason_code=LockReasonCode.CUSTOM,
                human_readable_message=f"Error evaluating lock: {str(e)}",
                details={'error': str(e)}
            )

