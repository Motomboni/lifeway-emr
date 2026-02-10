"""
Drug interaction check engine for e-prescription.

check_drug_interactions(medication_list) -> list of {severity, message, drug_a, drug_b}.
Severity: Mild, Moderate, Severe.
"""
from typing import List, Dict, Any
from .models import Medication, MedicationInteraction


def check_drug_interactions(medication_list: List[int]) -> List[Dict[str, Any]]:
    """
    Compare selected medication IDs and detect known interactions.

    Args:
        medication_list: List of Medication PKs.

    Returns:
        List of dicts: severity, message, drug_a_id, drug_a_name, drug_b_id, drug_b_name.
    """
    if not medication_list or len(medication_list) < 2:
        return []
    seen = set()
    warnings = []
    qs = MedicationInteraction.objects.filter(
        medication_a_id__in=medication_list,
        medication_b_id__in=medication_list,
    ).select_related('medication_a', 'medication_b')
    for ia in qs:
        key = (min(ia.medication_a_id, ia.medication_b_id), max(ia.medication_a_id, ia.medication_b_id))
        if key in seen:
            continue
        seen.add(key)
        warnings.append({
            'severity': ia.severity,
            'message': ia.description or f"Known {ia.severity} interaction between {ia.medication_a.name} and {ia.medication_b.name}.",
            'drug_a_id': ia.medication_a_id,
            'drug_a_name': ia.medication_a.name,
            'drug_b_id': ia.medication_b_id,
            'drug_b_name': ia.medication_b.name,
        })
    return warnings
