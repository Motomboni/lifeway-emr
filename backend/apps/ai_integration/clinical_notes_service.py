"""
Clinical AI Scribe — structured note generation from transcripts.

Supports auto-detected SOAP vs antenatal templates, NHIA/ICD-11 coding guidance,
Nigerian English/Pidgin normalization, and obstetric date calculations.
"""

import logging
from typing import Any, Dict, Optional

from django.utils import timezone

from .clinical_scribe_prompts import (
    CLINICAL_SCRIBE_SYSTEM,
    DISCHARGE_SYSTEM,
    SUMMARY_SYSTEM,
)
from .models import AIConfiguration, AIFeatureType, AIProvider, AIRequest
from .nhia_validation import validate_scribe_codes
from .note_parser import build_icd11_apply_payload, parse_scribe_sections
from .obstetric_calculations import (
    build_obstetric_context_block,
    resolve_template,
)
from .services import AIServiceError, AIServiceFactory

logger = logging.getLogger(__name__)

TEMPLATE_LABELS = {
    "soap": "SOAP",
    "antenatal": "Antenatal",
    "summary": "Summary",
    "discharge": "Discharge",
}


def _get_note_prompt(
    transcript: str,
    template: str,
    reference_date=None,
) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the resolved template."""
    transcript = (transcript or "").strip() or "No transcript provided."
    ref = reference_date or timezone.now().date()
    obstetric_block = ""

    if template == "antenatal":
        obstetric_block = build_obstetric_context_block(transcript, reference=ref)
        system = CLINICAL_SCRIBE_SYSTEM
        user = (
            "The following is an antenatal/maternity encounter. "
            "Apply TEMPLATE B (Antenatal Booking & Summary Card).\n\n"
            f"{transcript}{obstetric_block}"
        )
        return system, user

    if template == "soap":
        obstetric_block = build_obstetric_context_block(transcript, reference=ref)
        system = CLINICAL_SCRIBE_SYSTEM
        user = (
            "Apply TEMPLATE A (General Consultation Note / SOAP structure).\n\n"
            f"{transcript}{obstetric_block}"
        )
        return system, user

    if template == "summary":
        return SUMMARY_SYSTEM, f"Summarize the following clinical encounter:\n\n{transcript}"

    if template == "discharge":
        return DISCHARGE_SYSTEM, f"Generate a discharge summary from:\n\n{transcript}"

    system = CLINICAL_SCRIBE_SYSTEM
    user = f"Structure the following clinical encounter appropriately:\n\n{transcript}"
    return system, user


def generate_clinical_note(
    transcript: str,
    note_type: str = "auto",
    user=None,
    visit=None,
    reference_date=None,
) -> Dict[str, Any]:
    """
    Generate a structured clinical note from transcript/bullet notes.

    Args:
        transcript: Raw transcript, dialogue, or shorthand dictate.
        note_type: auto | SOAP | antenatal | summary | discharge
        user: Doctor requesting generation (audit).
        visit: Optional visit for audit logging.
        reference_date: Date for EGA calculation (defaults to today).

    Returns:
        {
            "note_type": str,
            "template_used": str,
            "structured_note": str,
            "raw_transcript": str,
            "request_id": int | None,
        }
    """
    template = resolve_template(note_type, transcript)
    note_type_display = TEMPLATE_LABELS.get(template, template.capitalize())

    config, _ = AIConfiguration.objects.get_or_create(
        feature_type=AIFeatureType.CLINICAL_NOTE_GENERATION,
        defaults={
            "default_provider": AIProvider.OPENAI,
            "default_model": "gpt-4o-mini",
            "enabled": True,
        },
    )
    if not config.enabled:
        raise AIServiceError("Clinical note generation is disabled.")

    system_prompt, user_prompt = _get_note_prompt(
        transcript, template, reference_date=reference_date
    )

    try:
        service = AIServiceFactory.create_service(
            provider=AIProvider(config.default_provider),
            model=config.default_model,
        )
        response = service.generate(
            user_prompt,
            system_prompt=system_prompt,
            max_tokens=config.max_tokens,
            temperature=float(config.temperature),
        )
        content = (response.get("content") or "").strip()
        prompt_tokens = response.get("prompt_tokens", 0)
        completion_tokens = response.get("completion_tokens", 0)
        cost = service.calculate_cost(prompt_tokens, completion_tokens)

        request_id = None
        if visit and user:
            request_id = AIRequest.objects.create(
                visit=visit,
                user=user,
                user_role=getattr(user, "role", "UNKNOWN"),
                feature_type=AIFeatureType.CLINICAL_NOTE_GENERATION,
                provider=config.default_provider,
                model_name=config.default_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
                cost_usd=cost,
                request_payload={
                    "note_type": note_type_display,
                    "template": template,
                    "prompt_length": len(user_prompt),
                },
                response_payload={"response_length": len(content)},
                success=True,
            ).id

        code_validation = validate_scribe_codes(content)
        parsed_sections = parse_scribe_sections(content, template=template)

        return {
            "note_type": note_type_display,
            "template_used": template,
            "structured_note": content,
            "raw_transcript": transcript,
            "request_id": request_id,
            "code_validation": code_validation,
            "parsed_sections": parsed_sections,
            "icd11_apply_payload": build_icd11_apply_payload(
                code_validation.get("validated_codes", [])
            ),
        }
    except Exception as e:
        if visit and user:
            AIRequest.objects.create(
                visit=visit,
                user=user,
                user_role=getattr(user, "role", "UNKNOWN"),
                feature_type=AIFeatureType.CLINICAL_NOTE_GENERATION,
                provider=config.default_provider,
                model_name=config.default_model,
                success=False,
                error_message=str(e),
            )
        logger.exception("Clinical note generation failed: %s", e)
        raise AIServiceError(f"Note generation failed: {str(e)}")
