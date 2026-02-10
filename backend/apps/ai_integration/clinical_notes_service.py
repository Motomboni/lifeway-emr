"""
AI clinical notes generation service.

generate_clinical_note(transcript, note_type) -> structured note (SOAP/summary/discharge).
Doctor must approve/edit before final save. Audit logged when visit is provided.
"""
import logging
from typing import Dict, Any, Optional
from django.conf import settings

from .models import AIFeatureType, AIRequest, AIConfiguration, AIProvider
from .services import AIServiceFactory, AIServiceError

logger = logging.getLogger(__name__)

SOAP_SYSTEM = """You are a clinical documentation assistant. Given a transcript or bullet notes from a consultation, produce a structured SOAP note.
Output ONLY the following sections with clear headers. Use neutral, professional language. Do not invent findings not implied by the transcript.

S — Subjective: Chief complaint and history in patient's words or summarized.
O — Objective: Vital signs, physical exam, lab/imaging findings if mentioned.
A — Assessment: Working diagnosis or problem list.
P — Plan: Treatment plan, medications, follow-up."""

SUMMARY_SYSTEM = """You are a clinical documentation assistant. Given a transcript or bullet notes, produce a concise clinical summary paragraph suitable for the medical record. Do not invent information. Use professional language."""

DISCHARGE_SYSTEM = """You are a clinical documentation assistant. Given a transcript or bullet notes from a discharge discussion, produce a structured discharge summary: Diagnosis, Hospital Course (brief), Discharge Medications, Follow-up instructions, and Patient Education. Use professional language. Do not invent information."""


def _get_note_prompt(transcript: str, note_type: str) -> tuple:
    """Return (system_prompt, user_prompt) for the given note type."""
    transcript = (transcript or "").strip() or "No transcript provided."
    if note_type == "SOAP":
        return SOAP_SYSTEM, f"Generate a SOAP note from the following:\n\n{transcript}"
    if note_type == "summary":
        return SUMMARY_SYSTEM, f"Summarize the following clinical encounter:\n\n{transcript}"
    if note_type == "discharge":
        return DISCHARGE_SYSTEM, f"Generate a discharge summary from:\n\n{transcript}"
    return SUMMARY_SYSTEM, f"Summarize:\n\n{transcript}"


def generate_clinical_note(
    transcript: str,
    note_type: str,
    user=None,
    visit=None,
) -> Dict[str, Any]:
    """
    Generate a structured clinical note from transcript/bullet notes.

    Args:
        transcript: Raw transcript or bullet points.
        note_type: One of 'SOAP', 'summary', 'discharge'.
        user: User (doctor) requesting generation (for audit).
        visit: Optional visit for audit logging.

    Returns:
        {
            "note_type": str,
            "structured_note": str,  # AI output (editable by doctor)
            "raw_transcript": str,
            "request_id": int | None,
        }
    """
    note_type = (note_type or "summary").strip().lower()
    if note_type not in ("soap", "summary", "discharge"):
        note_type = "summary"
    note_type_display = "SOAP" if note_type == "soap" else note_type.capitalize()

    config, _ = AIConfiguration.objects.get_or_create(
        feature_type=AIFeatureType.CLINICAL_NOTE_GENERATION,
        defaults={
            "default_provider": AIProvider.OPENAI,
            "default_model": "gpt-3.5-turbo",
            "enabled": True,
        },
    )
    if not config.enabled:
        raise AIServiceError("Clinical note generation is disabled.")

    system_prompt, user_prompt = _get_note_prompt(transcript, note_type_display)
    full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"

    try:
        service = AIServiceFactory.create_service(
            provider=AIProvider(config.default_provider),
            model=config.default_model,
        )
        response = service.generate(
            full_prompt,
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
                request_payload={"note_type": note_type_display, "prompt_length": len(full_prompt)},
                response_payload={"response_length": len(content)},
                success=True,
            ).id

        return {
            "note_type": note_type_display,
            "structured_note": content,
            "raw_transcript": transcript,
            "request_id": request_id,
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
