"""
Insurance claim generator and submission stub.

generate_claim(patient, services) -> Claim (draft)
submit_claim(claim_id) -> stub: approved/rejected/pending
"""
import logging
from decimal import Decimal
from django.utils import timezone

from .insurance_models import ClaimPolicy, Claim

logger = logging.getLogger(__name__)


def generate_claim(patient, services=None, policy=None):
    """
    Create a draft claim for patient. Auto-pull consultations, labs, medications, procedures
    if services not provided (from recent visits).
    """
    if not policy and patient:
        policy = ClaimPolicy.objects.filter(patient=patient, is_active=True).first()
    if not policy:
        raise ValueError("No active insurance policy for patient.")
    if services is None:
        services = _gather_services_for_patient(patient)
    total = sum(Decimal(str(s.get('amount', 0))) for s in services)
    claim = Claim.objects.create(
        patient=policy.patient,
        policy=policy,
        services=services,
        total_amount=total,
        status='draft',
    )
    return claim


def _gather_services_for_patient(patient):
    """Stub: gather consultations, labs, medications, procedures from recent visits."""
    from apps.visits.models import Visit
    from apps.consultations.models import Consultation
    from apps.pharmacy.models import Prescription
    from apps.laboratory.models import LabOrder
    services = []
    visits = Visit.objects.filter(patient=patient).order_by('-created_at')[:10]
    for v in visits:
        for c in Consultation.objects.filter(visit=v):
            services.append({
                'type': 'consultation',
                'visit_id': v.id,
                'consultation_id': c.id,
                'description': f"Consultation {c.id}",
                'amount': '0',
            })
        for p in Prescription.objects.filter(visit=v):
            services.append({
                'type': 'prescription',
                'visit_id': v.id,
                'prescription_id': p.id,
                'description': p.drug or 'Prescription',
                'amount': '0',
            })
        for lab in LabOrder.objects.filter(visit=v):
            services.append({
                'type': 'lab',
                'visit_id': v.id,
                'lab_order_id': lab.id,
                'description': lab.test_name or 'Lab',
                'amount': '0',
            })
    return services


def submit_claim(claim_id):
    """
    Stub: submit claim to external insurer API. Simulate approved/rejected/pending.
    Returns (success: bool, new_status: str, response_payload: dict).
    """
    claim = Claim.objects.get(id=claim_id)
    if claim.status != 'draft':
        raise ValueError(f"Claim {claim_id} is not in draft status.")
    # Stub: simulate response
    import random
    outcomes = ['approved', 'rejected', 'pending']
    weights = [0.5, 0.2, 0.3]
    new_status = random.choices(outcomes, weights=weights)[0]
    claim.status = new_status
    claim.submitted_at = timezone.now()
    claim.response_payload = {
        'stub': True,
        'status': new_status,
        'reference': f"REF-{claim_id}-{timezone.now().strftime('%Y%m%d%H%M')}",
    }
    claim.save(update_fields=['status', 'submitted_at', 'response_payload', 'updated_at'])
    return True, new_status, claim.response_payload
