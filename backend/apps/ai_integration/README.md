# AI Integration - EMR Compliant Implementation

## Overview

The AI Integration app provides AI-powered features for the EMR system, including:
- Clinical decision support (diagnosis suggestions, treatment recommendations)
- NLP for clinical notes (summarization, extraction)
- Automated coding (ICD-11, CPT codes)
- Drug interaction checking
- Documentation assistance

## EMR Rule Compliance

✅ **Visit-Scoped Architecture**: All AI endpoints are nested under `/api/v1/visits/{visit_id}/ai/`  
✅ **Doctor-Only Access**: Clinical AI features require Doctor role  
✅ **Payment Enforcement**: Payment must be CLEARED before using AI features  
✅ **Visit Status Check**: Visit must be OPEN  
✅ **Audit Logging**: All AI interactions are logged for compliance  
✅ **PHI Sanitization**: Protected Health Information is sanitized before sending to AI  
✅ **Rate Limiting**: Per-user rate limiting to prevent abuse  
✅ **Cost Tracking**: All AI requests are tracked for cost analysis  

## Endpoints

### AI Clinical Features

All endpoints are visit-scoped and require:
- Authentication
- Doctor role
- Payment cleared
- Visit OPEN

#### Clinical Decision Support

```
POST /api/v1/visits/{visit_id}/ai/clinical-decision-support/
```

Get diagnosis suggestions and treatment recommendations based on consultation data.

**Request:**
```json
{
  "consultation_id": 123,
  "patient_symptoms": "Fever, cough, fatigue",
  "patient_history": "Hypertension, diabetes",
  "current_medications": ["Metformin", "Lisinopril"],
  "include_differential_diagnosis": true,
  "include_treatment_suggestions": true
}
```

**Response:**
```json
{
  "suggested_diagnoses": [
    {
      "diagnosis": "Upper respiratory infection",
      "confidence": 0.85,
      "icd11_code": "CA40.Z"
    }
  ],
  "differential_diagnosis": [...],
  "treatment_suggestions": [...],
  "warnings": [...],
  "request_id": 456
}
```

#### NLP Summarization

```
POST /api/v1/visits/{visit_id}/ai/nlp-summarize/
```

Summarize clinical notes using NLP.

**Request:**
```json
{
  "consultation_id": 123,
  "text": "Long clinical notes...",
  "summary_type": "brief"
}
```

**Response:**
```json
{
  "summary": "Brief summary of clinical notes",
  "key_points": ["Point 1", "Point 2"],
  "request_id": 456
}
```

#### Automated Coding

```
POST /api/v1/visits/{visit_id}/ai/automated-coding/
```

Generate ICD-11 and CPT codes from clinical notes.

**Request:**
```json
{
  "consultation_id": 123,
  "code_types": ["icd11", "cpt"]
}
```

**Response:**
```json
{
  "icd11_codes": [
    {
      "code": "CA40.Z",
      "description": "Acute upper respiratory infection, unspecified",
      "confidence": 0.92
    }
  ],
  "cpt_codes": [...],
  "request_id": 456
}
```

#### Drug Interaction Check

```
POST /api/v1/visits/{visit_id}/ai/drug-interaction-check/
```

Check for drug interactions.

**Request:**
```json
{
  "current_medications": ["Metformin", "Lisinopril"],
  "new_medication": "Warfarin"
}
```

**Response:**
```json
{
  "has_interaction": true,
  "severity": "moderate",
  "description": "Interaction description",
  "recommendations": ["Recommendation 1"],
  "request_id": 456
}
```

### AI Request History

```
GET /api/v1/visits/{visit_id}/ai/ai-requests/
```

View history of AI requests for a visit (read-only, for audit trail).

## AI Providers

The system supports multiple AI providers:
- **OpenAI** (GPT-4, GPT-3.5-turbo)
- **Anthropic** (Claude 3 Opus, Sonnet, Haiku)
- **Azure OpenAI**
- **Local Models** (for on-premise deployment)

## Configuration

AI features can be configured via Django admin:
- Enable/disable features
- Set default provider and model
- Configure rate limits
- Set temperature and max tokens
- Track costs

## Security & Privacy

1. **PHI Sanitization**: All prompts are sanitized to remove PHI before sending to AI
2. **Audit Logging**: Every AI request is logged with:
   - User ID and role
   - Visit ID
   - Feature type
   - Provider and model
   - Token usage
   - Cost
   - Timestamp
   - IP address
3. **Rate Limiting**: Per-user rate limiting prevents abuse
4. **Cost Tracking**: All costs are tracked for budget management
5. **Caching**: Responses are cached to reduce API calls and costs

## Models

### AIRequest

Tracks all AI API requests for audit and cost tracking.

### AIConfiguration

Configuration for AI providers and features (per-feature settings).

### AICache

Cache for AI responses to reduce API calls and costs.

## Installation

1. Install required packages:
```bash
pip install openai anthropic
```

2. Set environment variables:
```bash
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

3. Run migrations:
```bash
python manage.py migrate ai_integration
```

4. Configure AI features in Django admin

## Usage Example

```python
from apps.ai_integration.services import AIServiceManager
from apps.ai_integration.models import AIFeatureType

# In a view
visit = get_visit()
ai_manager = AIServiceManager(visit, request.user, AIFeatureType.CLINICAL_DECISION_SUPPORT)
result = ai_manager.generate(prompt)
```

## Future Enhancements

- Image analysis for radiology
- Predictive analytics (readmission risk, disease progression)
- Real-time clinical alerts
- Patient-facing AI chatbot
- Structured output parsing
- Multi-provider fallback
