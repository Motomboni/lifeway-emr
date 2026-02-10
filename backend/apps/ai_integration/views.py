"""
AI Integration API views.

Per EMR Rules:
- All endpoints are visit-scoped
- Doctor-only access for clinical features
- Audit logging for all requests
- Payment must be cleared
- Visit must be OPEN
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from core.permissions import IsDoctor, IsVisitOpen, IsPaymentCleared
from core.audit import AuditLog
from .models import AIRequest, AIConfiguration, AIFeatureType
from .serializers import (
    AIRequestSerializer,
    ClinicalDecisionSupportRequestSerializer,
    ClinicalDecisionSupportResponseSerializer,
    NLPSummarizationRequestSerializer,
    NLPSummarizationResponseSerializer,
    AutomatedCodingRequestSerializer,
    AutomatedCodingResponseSerializer,
    DrugInteractionCheckRequestSerializer,
    DrugInteractionCheckResponseSerializer,
    AIConfigurationSerializer,
)
from .services import AIServiceManager, AIServiceError, RateLimitExceeded
from apps.consultations.models import Consultation


class AIRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing AI request history.
    
    Per EMR Rules:
    - Visit-scoped
    - Read-only (immutable audit trail)
    - Role-based access
    """
    serializer_class = AIRequestSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get AI requests for the current visit."""
        visit_id = self.kwargs.get('visit_id')
        from apps.visits.models import Visit
        visit = get_object_or_404(Visit, pk=visit_id)
        
        # Check visit access
        if hasattr(visit.patient, 'user') and visit.patient.user != self.request.user and self.request.user.role != 'DOCTOR':
            raise PermissionDenied("You do not have access to this visit's AI requests.")
        
        return AIRequest.objects.filter(visit=visit).order_by('-timestamp')
    
    def get_visit(self):
        """Get visit from URL parameter."""
        visit_id = self.kwargs.get('visit_id')
        from apps.visits.models import Visit
        return get_object_or_404(Visit, pk=visit_id)


class AIClinicalViewSet(viewsets.ViewSet):
    """
    ViewSet for AI clinical features.
    
    Per EMR Rules:
    - Visit-scoped
    - Doctor-only
    - Payment must be cleared
    - Visit must be OPEN
    """
    permission_classes = [IsAuthenticated, IsDoctor, IsVisitOpen, IsPaymentCleared]
    
    def get_visit(self):
        """Get visit from middleware or URL parameter."""
        # First try to get from request.visit set by middleware
        if hasattr(self.request, 'visit') and self.request.visit:
            return self.request.visit
        
        # Fallback to kwargs (from URL pattern)
        visit_id = self.kwargs.get('visit_id')
        if visit_id:
            from apps.visits.models import Visit
            return get_object_or_404(Visit, pk=visit_id)
        
        raise ValidationError("visit_id is required in URL")
    
    def _get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=False, methods=['post'], url_path='clinical-decision-support/')
    def clinical_decision_support(self, request, **kwargs):
        """
        Get clinical decision support (diagnosis suggestions, treatment recommendations).
        
        POST /api/v1/visits/{visit_id}/ai/clinical-decision-support/
        """
        visit = self.get_visit()
        
        serializer = ClinicalDecisionSupportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Build prompt from consultation or provided data
        prompt_parts = []
        
        if serializer.validated_data.get('consultation_id'):
            consultation = get_object_or_404(
                Consultation,
                pk=serializer.validated_data['consultation_id'],
                visit=visit
            )
            prompt_parts.append(f"Patient History: {consultation.history or 'Not provided'}")
            prompt_parts.append(f"Examination: {consultation.examination or 'Not provided'}")
            prompt_parts.append(f"Current Diagnosis: {consultation.diagnosis or 'Not provided'}")
        
        if serializer.validated_data.get('patient_symptoms'):
            prompt_parts.append(f"Symptoms: {serializer.validated_data['patient_symptoms']}")
        
        if serializer.validated_data.get('patient_history'):
            prompt_parts.append(f"Medical History: {serializer.validated_data['patient_history']}")
        
        if serializer.validated_data.get('current_medications'):
            prompt_parts.append(f"Current Medications: {', '.join(serializer.validated_data['current_medications'])}")
        
        prompt = "\n\n".join(prompt_parts)
        prompt += "\n\nProvide clinical decision support including:"
        
        if serializer.validated_data.get('include_differential_diagnosis', True):
            prompt += "\n- Differential diagnosis with confidence scores"
        
        if serializer.validated_data.get('include_treatment_suggestions', True):
            prompt += "\n- Treatment recommendations"
        
        prompt += "\n- Any clinical warnings or alerts"
        
        try:
            ai_manager = AIServiceManager(visit, request.user, AIFeatureType.CLINICAL_DECISION_SUPPORT)
            result = ai_manager.generate(prompt)
            
            # Update IP address in the request
            if result.get('request_id'):
                ai_request = AIRequest.objects.get(pk=result['request_id'])
                ai_request.ip_address = self._get_client_ip(request)
                ai_request.save(update_fields=['ip_address'])
            
            # Parse AI response (in production, use structured output)
            # For now, return raw response
            response_data = {
                'suggested_diagnoses': [],  # Parse from result['content']
                'differential_diagnosis': [],
                'treatment_suggestions': [],
                'warnings': [],
                'request_id': result.get('request_id'),
                'raw_response': result.get('content'),  # Temporary, for development
            }
            
            # Audit log
            user_role = getattr(request.user, 'role', None) or 'UNKNOWN'
            AuditLog.log(
                user=request.user,
                role=user_role,
                action='ai.clinical_decision_support',
                visit_id=visit.id,
                resource_type='ai_request',
                resource_id=result.get('request_id'),
                request=request
            )
            
            response_serializer = ClinicalDecisionSupportResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
            
        except RateLimitExceeded as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        except AIServiceError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='nlp-summarize/')
    def nlp_summarize(self, request, **kwargs):
        """
        Summarize clinical notes using NLP.
        
        POST /api/v1/visits/{visit_id}/ai/nlp-summarize/
        """
        visit = self.get_visit()
        
        serializer = NLPSummarizationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get text to summarize
        text = serializer.validated_data.get('text')
        if not text and serializer.validated_data.get('consultation_id'):
            consultation = get_object_or_404(
                Consultation,
                pk=serializer.validated_data['consultation_id'],
                visit=visit
            )
            text = f"{consultation.history or ''}\n{consultation.examination or ''}\n{consultation.diagnosis or ''}\n{consultation.clinical_notes or ''}"
        
        if not text:
            raise ValidationError("No text to summarize")
        
        summary_type = serializer.validated_data.get('summary_type', 'brief')
        prompt = f"Summarize the following clinical notes in a {summary_type} format:\n\n{text}"
        
        try:
            ai_manager = AIServiceManager(visit, request.user, AIFeatureType.NLP_SUMMARIZATION)
            result = ai_manager.generate(prompt)
            
            # Update IP address
            if result.get('request_id'):
                ai_request = AIRequest.objects.get(pk=result['request_id'])
                ai_request.ip_address = self._get_client_ip(request)
                ai_request.save(update_fields=['ip_address'])
            
            response_data = {
                'summary': result.get('content', ''),
                'key_points': [],  # Parse from result if needed
                'request_id': result.get('request_id'),
            }
            
            # Audit log
            user_role = getattr(request.user, 'role', None) or 'UNKNOWN'
            AuditLog.log(
                user=request.user,
                role=user_role,
                action='ai.nlp_summarize',
                visit_id=visit.id,
                resource_type='ai_request',
                resource_id=result.get('request_id'),
                request=request
            )
            
            response_serializer = NLPSummarizationResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
            
        except (RateLimitExceeded, AIServiceError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='automated-coding/')
    def automated_coding(self, request, **kwargs):
        """
        Generate ICD-11 and CPT codes from clinical notes.
        
        POST /api/v1/visits/{visit_id}/ai/automated-coding/
        """
        visit = self.get_visit()
        
        serializer = AutomatedCodingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        consultation = get_object_or_404(
            Consultation,
            pk=serializer.validated_data['consultation_id'],
            visit=visit
        )
        
        code_types = serializer.validated_data.get('code_types', ['icd11'])
        
        prompt = f"Based on the following clinical notes, suggest appropriate medical codes:\n\n"
        prompt += f"History: {consultation.history or 'Not provided'}\n"
        prompt += f"Examination: {consultation.examination or 'Not provided'}\n"
        prompt += f"Diagnosis: {consultation.diagnosis or 'Not provided'}\n"
        prompt += f"Clinical Notes: {consultation.clinical_notes or 'Not provided'}\n\n"
        
        if 'icd11' in code_types:
            prompt += "Suggest ICD-11 diagnosis codes with descriptions.\n"
        if 'cpt' in code_types:
            prompt += "Suggest CPT procedure codes with descriptions.\n"
        
        try:
            ai_manager = AIServiceManager(visit, request.user, AIFeatureType.AUTOMATED_CODING)
            result = ai_manager.generate(prompt)
            
            # Update IP address
            if result.get('request_id'):
                ai_request = AIRequest.objects.get(pk=result['request_id'])
                ai_request.ip_address = self._get_client_ip(request)
                ai_request.save(update_fields=['ip_address'])
            
            response_data = {
                'icd11_codes': [],  # Parse from result
                'cpt_codes': [],  # Parse from result
                'request_id': result.get('request_id'),
                'raw_response': result.get('content'),  # Temporary
            }
            
            # Audit log
            user_role = getattr(request.user, 'role', None) or 'UNKNOWN'
            AuditLog.log(
                user=request.user,
                role=user_role,
                action='ai.automated_coding',
                visit_id=visit.id,
                resource_type='ai_request',
                resource_id=result.get('request_id'),
                request=request
            )
            
            response_serializer = AutomatedCodingResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
            
        except (RateLimitExceeded, AIServiceError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='drug-interaction-check/')
    def drug_interaction_check(self, request, **kwargs):
        """
        Check for drug interactions.
        
        POST /api/v1/visits/{visit_id}/ai/drug-interaction-check/
        """
        visit = self.get_visit()
        
        serializer = DrugInteractionCheckRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        current_meds = serializer.validated_data['current_medications']
        new_med = serializer.validated_data['new_medication']
        
        prompt = f"Check for drug interactions between the following medications:\n\n"
        prompt += f"Current Medications: {', '.join(current_meds)}\n"
        prompt += f"New Medication: {new_med}\n\n"
        prompt += "Provide:\n- Whether an interaction exists\n- Severity (mild/moderate/severe/contraindicated)\n- Description of the interaction\n- Recommendations"
        
        try:
            ai_manager = AIServiceManager(visit, request.user, AIFeatureType.DRUG_INTERACTION_CHECK)
            result = ai_manager.generate(prompt)
            
            # Update IP address
            if result.get('request_id'):
                ai_request = AIRequest.objects.get(pk=result['request_id'])
                ai_request.ip_address = self._get_client_ip(request)
                ai_request.save(update_fields=['ip_address'])
            
            response_data = {
                'has_interaction': False,  # Parse from result
                'severity': None,
                'description': '',
                'recommendations': [],
                'request_id': result.get('request_id'),
                'raw_response': result.get('content'),  # Temporary
            }
            
            # Audit log
            user_role = getattr(request.user, 'role', None) or 'UNKNOWN'
            AuditLog.log(
                user=request.user,
                role=user_role,
                action='ai.drug_interaction_check',
                visit_id=visit.id,
                resource_type='ai_request',
                resource_id=result.get('request_id'),
                request=request
            )
            
            response_serializer = DrugInteractionCheckResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)
            return Response(response_serializer.validated_data, status=status.HTTP_200_OK)
            
        except (RateLimitExceeded, AIServiceError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AIConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AI configuration (admin only).
    """
    queryset = AIConfiguration.objects.all()
    serializer_class = AIConfigurationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Only superusers can manage AI configuration."""
        if self.request.user.is_superuser:
            return super().get_permissions()
        return [PermissionDenied("Only administrators can manage AI configuration.")]
