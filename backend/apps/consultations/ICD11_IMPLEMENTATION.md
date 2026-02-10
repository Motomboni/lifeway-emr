# ICD-11 Code Implementation Guide

## Overview

This document outlines how to implement ICD-11 (International Classification of Diseases, 11th Revision) code support in the EMR system.

## Current State

- ✅ AI can generate ICD-11 code suggestions via Automated Coding feature
- ❌ ICD-11 codes are not stored in the database
- ❌ No structured diagnosis code field in Consultation model
- ❌ Codes cannot be used for billing, reporting, or analytics

## Proposed Implementation

### 1. Database Model Changes

#### Option A: Add ICD-11 fields to Consultation model

```python
# In backend/apps/consultations/models.py

class Consultation(models.Model):
    # ... existing fields ...
    
    # ICD-11 Diagnosis Codes
    primary_icd11_code = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Primary ICD-11 diagnosis code (e.g., 'CA40.Z')"
    )
    
    primary_icd11_description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Description of primary ICD-11 code"
    )
    
    secondary_icd11_codes = models.JSONField(
        default=list,
        blank=True,
        help_text="List of secondary ICD-11 codes: [{'code': 'CA40.Z', 'description': '...'}]"
    )
    
    # ... rest of model ...
```

#### Option B: Create separate DiagnosisCode model (Recommended)

```python
# New file: backend/apps/consultations/diagnosis_models.py

class DiagnosisCode(models.Model):
    """
    Diagnosis code model - links ICD-11 codes to consultations.
    
    Supports multiple codes per consultation (primary + secondary).
    """
    
    CODE_TYPE_CHOICES = [
        ('ICD11', 'ICD-11'),
        ('ICD10', 'ICD-10'),  # For backward compatibility
    ]
    
    consultation = models.ForeignKey(
        'consultations.Consultation',
        on_delete=models.CASCADE,
        related_name='diagnosis_codes',
        help_text="Consultation this code belongs to"
    )
    
    code_type = models.CharField(
        max_length=10,
        choices=CODE_TYPE_CHOICES,
        default='ICD11',
        help_text="Type of diagnosis code"
    )
    
    code = models.CharField(
        max_length=20,
        help_text="Diagnosis code (e.g., 'CA40.Z' for ICD-11)"
    )
    
    description = models.CharField(
        max_length=500,
        help_text="Description of the diagnosis code"
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text="True if this is the primary diagnosis"
    )
    
    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="AI confidence score (0-100) if code was AI-generated"
    )
    
    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.PROTECT,
        related_name='diagnosis_codes_created',
        help_text="User who assigned this code"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'diagnosis_codes'
        ordering = ['-is_primary', 'created_at']
        indexes = [
            models.Index(fields=['consultation']),
            models.Index(fields=['code']),
            models.Index(fields=['is_primary']),
        ]
        # Ensure only one primary code per consultation
        constraints = [
            models.UniqueConstraint(
                fields=['consultation', 'is_primary'],
                condition=models.Q(is_primary=True),
                name='unique_primary_diagnosis'
            )
        ]
    
    def __str__(self):
        return f"{self.code} - {self.description[:50]}"
```

### 2. Serializer Updates

```python
# In backend/apps/consultations/serializers.py

class DiagnosisCodeSerializer(serializers.ModelSerializer):
    """Serializer for diagnosis codes."""
    
    class Meta:
        model = DiagnosisCode
        fields = [
            'id',
            'code_type',
            'code',
            'description',
            'is_primary',
            'confidence',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


class ConsultationSerializer(serializers.ModelSerializer):
    """Updated serializer with diagnosis codes."""
    
    diagnosis_codes = DiagnosisCodeSerializer(many=True, read_only=True)
    
    class Meta:
        model = Consultation
        fields = [
            # ... existing fields ...
            'diagnosis_codes',  # Add this
        ]
```

### 3. API Endpoints

```python
# New file: backend/apps/consultations/diagnosis_views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .diagnosis_models import DiagnosisCode
from .serializers import DiagnosisCodeSerializer

class DiagnosisCodeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing diagnosis codes for a consultation.
    
    Endpoints:
    - GET /api/v1/visits/{visit_id}/consultation/diagnosis-codes/
    - POST /api/v1/visits/{visit_id}/consultation/diagnosis-codes/
    - PUT /api/v1/visits/{visit_id}/consultation/diagnosis-codes/{id}/
    - DELETE /api/v1/visits/{visit_id}/consultation/diagnosis-codes/{id}/
    """
    
    serializer_class = DiagnosisCodeSerializer
    permission_classes = [IsAuthenticated, IsDoctor]
    
    def get_queryset(self):
        """Get diagnosis codes for the consultation."""
        visit_id = self.kwargs['visit_id']
        consultation = get_object_or_404(
            Consultation,
            visit_id=visit_id
        )
        return DiagnosisCode.objects.filter(consultation=consultation)
    
    def perform_create(self, serializer):
        """Create diagnosis code."""
        visit_id = self.kwargs['visit_id']
        consultation = get_object_or_404(
            Consultation,
            visit_id=visit_id
        )
        
        # If setting as primary, unset other primary codes
        if serializer.validated_data.get('is_primary'):
            DiagnosisCode.objects.filter(
                consultation=consultation,
                is_primary=True
            ).update(is_primary=False)
        
        serializer.save(
            consultation=consultation,
            created_by=self.request.user
        )
    
    @action(detail=False, methods=['post'], url_path='from-ai-suggestion')
    def from_ai_suggestion(self, request, visit_id):
        """
        Create diagnosis codes from AI suggestions.
        
        POST /api/v1/visits/{visit_id}/consultation/diagnosis-codes/from-ai-suggestion/
        
        Body:
        {
            "icd11_codes": [
                {"code": "CA40.Z", "description": "...", "confidence": 0.92},
                ...
            ],
            "set_primary": true
        }
        """
        consultation = get_object_or_404(Consultation, visit_id=visit_id)
        icd11_codes = request.data.get('icd11_codes', [])
        set_primary = request.data.get('set_primary', False)
        
        created_codes = []
        for idx, code_data in enumerate(icd11_codes):
            is_primary = set_primary and idx == 0
            
            if is_primary:
                # Unset existing primary
                DiagnosisCode.objects.filter(
                    consultation=consultation,
                    is_primary=True
                ).update(is_primary=False)
            
            code = DiagnosisCode.objects.create(
                consultation=consultation,
                code_type='ICD11',
                code=code_data['code'],
                description=code_data['description'],
                is_primary=is_primary,
                confidence=code_data.get('confidence'),
                created_by=request.user
            )
            created_codes.append(code)
        
        serializer = self.get_serializer(created_codes, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

### 4. Frontend Integration

#### Update AutomatedCoding Component

```typescript
// In frontend/src/components/ai/AutomatedCoding.tsx

// Add after code generation:
const handleApplyCodes = async (codes: ICD11Code[]) => {
  try {
    await applyDiagnosisCodes(visitId, {
      icd11_codes: codes,
      set_primary: true
    });
    showSuccess('Diagnosis codes applied to consultation');
    // Reload consultation to show codes
    onConsultationUpdate?.();
  } catch (error) {
    showError('Failed to apply codes');
  }
};
```

#### Add Diagnosis Code Display Component

```typescript
// New file: frontend/src/components/consultation/DiagnosisCodes.tsx

interface DiagnosisCode {
  id: number;
  code: string;
  description: string;
  is_primary: boolean;
  confidence?: number;
}

interface DiagnosisCodesProps {
  visitId: string;
  consultationId: number;
  codes: DiagnosisCode[];
  onUpdate: () => void;
}

export default function DiagnosisCodes({
  visitId,
  consultationId,
  codes,
  onUpdate
}: DiagnosisCodesProps) {
  // Display and manage diagnosis codes
  // Allow adding, editing, removing codes
  // Show primary vs secondary
  // Link to AI suggestions
}
```

### 5. Use Cases

#### A. Billing Integration

```python
# In backend/apps/billing/bill_models.py

class Bill(models.Model):
    # ... existing fields ...
    
    def get_diagnosis_codes(self):
        """Get ICD-11 codes for this bill's visit."""
        if not self.visit.consultation:
            return []
        
        return DiagnosisCode.objects.filter(
            consultation=self.visit.consultation
        ).values_list('code', flat=True)
    
    def generate_insurance_claim(self):
        """Generate insurance claim with ICD-11 codes."""
        codes = self.get_diagnosis_codes()
        # Include codes in claim submission
        ...
```

#### B. Reporting and Analytics

```python
# New file: backend/apps/reporting/diagnosis_analytics.py

def get_diagnosis_statistics(start_date, end_date):
    """Get statistics on diagnosis codes."""
    codes = DiagnosisCode.objects.filter(
        consultation__visit__created_at__range=[start_date, end_date]
    )
    
    # Group by code
    code_counts = codes.values('code', 'description').annotate(
        count=Count('id')
    ).order_by('-count')
    
    return code_counts
```

#### C. Clinical Decision Support

```python
# Use ICD-11 codes to:
# - Suggest appropriate treatments
# - Check for drug contraindications
# - Recommend follow-up care
# - Identify at-risk patients
```

## Migration Steps

1. **Create DiagnosisCode model** (Option B recommended)
2. **Run migrations**: `python manage.py makemigrations consultations`
3. **Update serializers** to include diagnosis codes
4. **Create API endpoints** for managing codes
5. **Update frontend** to display and manage codes
6. **Integrate with AI** to auto-apply suggested codes
7. **Update billing** to use codes in claims
8. **Add reporting** features using codes

## Benefits

✅ **Structured Data**: Diagnosis codes stored in structured format  
✅ **Billing Integration**: Codes can be included in insurance claims  
✅ **Analytics**: Enable disease tracking and epidemiology  
✅ **Compliance**: Meet medical coding standards  
✅ **AI Integration**: Seamlessly apply AI-suggested codes  
✅ **Reporting**: Generate diagnosis-based reports  

## Next Steps

1. Choose implementation approach (Option A or B)
2. Create database migration
3. Update API endpoints
4. Build frontend components
5. Integrate with existing AI features
6. Add billing integration
7. Create reporting dashboards

