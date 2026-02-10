"""
Diagnosis Code ViewSet - visit-scoped API endpoint for ICD-11 codes.

Endpoint: /api/v1/visits/{visit_id}/consultation/diagnosis-codes/

Enforcement:
1. Doctor-only access for write operations
2. Visit must be OPEN for mutations
3. Payment must be CLEARED for mutations
4. One primary code per consultation
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    NotFound,
    ValidationError as DRFValidationError,
)
from django.shortcuts import get_object_or_404

from .diagnosis_models import DiagnosisCode
from .serializers import DiagnosisCodeSerializer
from .models import Consultation
from apps.visits.models import Visit
from core.permissions import IsDoctor, IsVisitOpen, IsPaymentCleared, IsVisitAccessible
from core.audit import log_consultation_action


class DiagnosisCodeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing diagnosis codes for a consultation.
    
    Endpoints:
    - GET /api/v1/visits/{visit_id}/consultation/diagnosis-codes/
    - POST /api/v1/visits/{visit_id}/consultation/diagnosis-codes/
    - PUT /api/v1/visits/{visit_id}/consultation/diagnosis-codes/{id}/
    - PATCH /api/v1/visits/{visit_id}/consultation/diagnosis-codes/{id}/
    - DELETE /api/v1/visits/{visit_id}/consultation/diagnosis-codes/{id}/
    """
    
    serializer_class = DiagnosisCodeSerializer
    permission_classes = [IsDoctor, IsVisitOpen, IsPaymentCleared]
    
    def get_queryset(self):
        """Get diagnosis codes for the consultation."""
        visit_id = self.kwargs.get('visit_id')
        consultation = get_object_or_404(
            Consultation,
            visit_id=visit_id
        )
        return DiagnosisCode.objects.filter(consultation=consultation).select_related('created_by')
    
    def get_consultation(self):
        """Get consultation for the visit."""
        visit_id = self.kwargs.get('visit_id')
        consultation = get_object_or_404(
            Consultation,
            visit_id=visit_id
        )
        return consultation
    
    def get_visit(self):
        """Get and validate visit."""
        visit_id = self.kwargs.get('visit_id')
        visit = get_object_or_404(Visit, pk=visit_id)
        self.request.visit = visit
        return visit
    
    def check_visit_status(self, visit):
        """Ensure visit is OPEN before allowing mutations."""
        if visit.status == 'CLOSED':
            raise PermissionDenied(
                detail="Cannot modify diagnosis codes for a CLOSED visit. "
                       "Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
    
    def check_payment_status(self, visit):
        """Ensure payment is cleared before allowing mutations."""
        if not visit.is_payment_cleared():
            raise PermissionDenied(
                detail="Payment must be cleared before modifying diagnosis codes. "
                       f"Current payment status: {visit.payment_status}",
                code='payment_not_cleared'
            )
    
    def perform_create(self, serializer):
        """Create diagnosis code."""
        visit = self.get_visit()
        consultation = self.get_consultation()
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # If setting as primary, unset other primary codes
        if serializer.validated_data.get('is_primary'):
            DiagnosisCode.objects.filter(
                consultation=consultation,
                is_primary=True
            ).update(is_primary=False)
        
        diagnosis_code = serializer.save(
            consultation=consultation,
            created_by=self.request.user
        )
        
        # Audit log
        try:
            log_consultation_action(
                user=self.request.user,
                action='add_diagnosis_code',
                visit_id=visit.id,
                consultation_id=consultation.id,
                request=self.request,
                extra_data={'code': diagnosis_code.code, 'is_primary': diagnosis_code.is_primary}
            )
        except Exception:
            pass  # Don't fail request if audit logging fails
        
        return diagnosis_code
    
    def perform_update(self, serializer):
        """Update diagnosis code."""
        diagnosis_code = self.get_object()
        visit = diagnosis_code.consultation.visit
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # If setting as primary, unset other primary codes
        if serializer.validated_data.get('is_primary', False):
            DiagnosisCode.objects.filter(
                consultation=diagnosis_code.consultation,
                is_primary=True
            ).exclude(pk=diagnosis_code.pk).update(is_primary=False)
        
        updated_code = serializer.save()
        
        # Audit log
        try:
            log_consultation_action(
                user=self.request.user,
                action='update_diagnosis_code',
                visit_id=visit.id,
                consultation_id=diagnosis_code.consultation.id,
                request=self.request,
                extra_data={'code': updated_code.code, 'is_primary': updated_code.is_primary}
            )
        except Exception:
            pass  # Don't fail request if audit logging fails
        
        return updated_code
    
    def perform_destroy(self, instance):
        """Delete diagnosis code."""
        visit = instance.consultation.visit
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        code = instance.code
        consultation_id = instance.consultation.id
        
        instance.delete()
        
        # Audit log
        try:
            log_consultation_action(
                user=self.request.user,
                action='delete_diagnosis_code',
                visit_id=visit.id,
                consultation_id=consultation_id,
                request=self.request,
                extra_data={'code': code}
            )
        except Exception:
            pass  # Don't fail request if audit logging fails
    
    def get_permissions(self):
        """Override to allow read access for authenticated users."""
        if self.action in ['retrieve', 'list']:
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated(), IsVisitAccessible()]
        else:
            return [IsDoctor(), IsVisitOpen(), IsPaymentCleared()]
    
    @action(detail=False, methods=['post'], url_path='from-ai-suggestion')
    def from_ai_suggestion(self, request, visit_id=None):
        """
        Create diagnosis codes from AI suggestions.
        
        POST /api/v1/visits/{visit_id}/consultation/diagnosis-codes/from-ai-suggestion/
        
        Body:
        {
            "icd11_codes": [
                {"code": "CA40.Z", "description": "Acute upper respiratory infection", "confidence": 0.92},
                ...
            ],
            "set_primary": true
        }
        """
        visit = self.get_visit()
        consultation = self.get_consultation()
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        icd11_codes = request.data.get('icd11_codes', [])
        set_primary = request.data.get('set_primary', False)
        
        if not icd11_codes:
            raise DRFValidationError("icd11_codes is required and cannot be empty")
        
        # If setting primary, unset existing primary
        if set_primary:
            DiagnosisCode.objects.filter(
                consultation=consultation,
                is_primary=True
            ).update(is_primary=False)
        
        created_codes = []
        for idx, code_data in enumerate(icd11_codes):
            is_primary = set_primary and idx == 0
            
            code = DiagnosisCode.objects.create(
                consultation=consultation,
                code_type='ICD11',
                code=code_data.get('code', '').strip().upper(),
                description=code_data.get('description', '').strip(),
                is_primary=is_primary,
                confidence=code_data.get('confidence'),
                created_by=request.user
            )
            created_codes.append(code)
        
        # Audit log
        try:
            log_consultation_action(
                user=request.user,
                action='add_diagnosis_codes_from_ai',
                visit_id=visit.id,
                consultation_id=consultation.id,
                request=request,
                extra_data={'count': len(created_codes), 'set_primary': set_primary}
            )
        except Exception:
            pass  # Don't fail request if audit logging fails
        
        serializer = self.get_serializer(created_codes, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

