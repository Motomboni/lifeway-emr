"""
Consultation ViewSet - strictly visit-scoped API endpoint.

Endpoint: /api/v1/visits/{visit_id}/consultation/

Enforcement:
1. Doctor-only access (IsDoctor permission)
2. Visit must be OPEN (IsVisitOpen permission)
3. Payment must be CLEARED (IsPaymentCleared permission)
4. Visit ownership validation
5. Audit logging for all actions
6. CLOSED visit rejection
7. No standalone endpoints (visit-scoped only)
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import (
    PermissionDenied,
    NotFound,
    ValidationError as DRFValidationError,
    status as drf_status
)
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from .models import Consultation
from .serializers import ConsultationSerializer, ConsultationWithCodesSerializer
from apps.visits.models import Visit
from core.permissions import (
    IsDoctor,
    IsVisitOpen,
    IsPaymentCleared,
    IsVisitAccessible,
    IsRegistrationPaymentCleared,
    IsConsultationPaymentCleared,
)
from core.audit import log_consultation_action


class ConsultationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Consultation - visit-scoped clinical documentation.
    
    Rules enforced:
    - Doctor-only access
    - Visit must be OPEN
    - Payment must be CLEARED
    - Visit ownership validation
    - Audit logging
    - CLOSED visit rejection
    """
    serializer_class = ConsultationSerializer
    # Default permissions - will be overridden by get_permissions() based on action
    permission_classes = [IsDoctor, IsVisitOpen]
    
    def get_queryset(self):
        """
        Get consultation for the specific visit.
        OneToOneField ensures only one consultation per visit.
        """
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            return Consultation.objects.none()
        
        return Consultation.objects.filter(visit_id=visit_id)
    
    def get_object(self):
        """
        Get consultation for the visit.
        Since it's OneToOneField, there's only one consultation per visit.
        """
        visit_id = self.kwargs.get('visit_id')
        consultation = Consultation.objects.filter(visit_id=visit_id).first()
        
        if not consultation:
            raise NotFound(
                detail="Consultation not found for this visit. "
                       "Create a consultation first."
            )
        
        return consultation
    
    def get_visit(self):
        """
        Get and validate visit from URL parameter.
        This ensures visit-scoped architecture is maintained.
        """
        visit_id = self.kwargs.get('visit_id')
        if not visit_id:
            raise DRFValidationError("visit_id is required in URL")
        
        visit = get_object_or_404(Visit, pk=visit_id)
        
        # Store visit in request for middleware/permissions
        self.request.visit = visit
        
        return visit
    
    def check_visit_status(self, visit):
        """
        Ensure visit is OPEN before allowing mutations.
        CLOSED visits are immutable per EMR rules.
        """
        if visit.status == 'CLOSED':
            raise PermissionDenied(
                detail="Cannot create or modify consultation for a CLOSED visit. "
                       "Closed visits are immutable per EMR rules.",
                code='visit_closed'
            )
    
    def check_payment_status(self, visit):
        """
        Ensure payment is cleared before allowing consultation.
        Payment checks MUST occur in backend (not frontend).
        """
        if not visit.is_payment_cleared():
            raise PermissionDenied(
                detail="Payment must be cleared before consultation. "
                       "Current payment status: {status}".format(
                           status=visit.payment_status
                       ),
                code='payment_not_cleared'
            )
    
    def merge_with_patient_history(self, consultation, visit):
        """
        Merge consultation data into patient's medical history.
        
        This appends the current consultation to the patient's ongoing
        medical history record, creating a cumulative patient record.
        """
        from django.utils import timezone
        
        patient = visit.patient
        if not patient:
            return
        
        # Use consultation's created_at timestamp, or current time if not set
        timestamp = consultation.created_at if consultation.created_at else timezone.now()
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M')
        
        # Build consultation entry with visit context
        consultation_entry = []
        consultation_entry.append(f"\n{'='*60}")
        consultation_entry.append(f"Visit #{visit.id} - {timestamp_str}")
        consultation_entry.append(f"{'='*60}")
        
        if consultation.history:
            consultation_entry.append(f"\nHISTORY:")
            consultation_entry.append(consultation.history)
        
        if consultation.examination:
            consultation_entry.append(f"\nEXAMINATION:")
            consultation_entry.append(consultation.examination)
        
        if consultation.diagnosis:
            consultation_entry.append(f"\nDIAGNOSIS:")
            consultation_entry.append(consultation.diagnosis)
        
        if consultation.clinical_notes:
            consultation_entry.append(f"\nCLINICAL NOTES:")
            consultation_entry.append(consultation.clinical_notes)
        
        consultation_entry.append(f"\n{'='*60}\n")
        
        # Append to patient's medical history
        new_entry = "\n".join(consultation_entry)
        if patient.medical_history:
            patient.medical_history += new_entry
        else:
            patient.medical_history = new_entry
        
        # Save patient (this updates the medical_history field)
        patient.save(update_fields=['medical_history'])
    
    def perform_create(self, serializer):
        """
        Create consultation with visit-scoped enforcement.
        
        Rules:
        1. Visit must exist and be OPEN
        2. Payment must be CLEARED
        3. created_by set to authenticated user (doctor)
        4. Visit set from URL parameter
        5. Audit log created
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            visit = self.get_visit()
            
            # Enforce visit status
            self.check_visit_status(visit)
            
            # Enforce payment status
            self.check_payment_status(visit)
            
            # Check if consultation already exists (OneToOneField constraint)
            if Consultation.objects.filter(visit=visit).exists():
                raise DRFValidationError(
                    "Consultation already exists for this visit. "
                    "Use PUT/PATCH to update instead."
                )
            
            # Set visit and created_by (cannot be set by user)
            try:
                # Extract merge flag before saving (it's write_only, won't be saved to model)
                merge_with_patient = serializer.validated_data.pop('merge_with_patient_record', False)
                
                consultation = serializer.save(
                    visit=visit,
                    created_by=self.request.user
                )
                
                # Merge with patient medical history if requested
                if merge_with_patient:
                    self.merge_with_patient_history(consultation, visit)
                    
            except Exception as e:
                logger.error(f"Error saving consultation: {str(e)}", exc_info=True)
                raise DRFValidationError(f"Error creating consultation: {str(e)}")
            
            # Audit log (don't fail request if audit logging fails)
            try:
                log_consultation_action(
                    user=self.request.user,
                    action='create',
                    visit_id=visit.id,
                    consultation_id=consultation.id,
                    request=self.request
                )
            except Exception as e:
                logger.error(f"Failed to log consultation create action: {str(e)}", exc_info=True)
                # Don't fail the request if audit logging fails
            
            return consultation
        except (DRFValidationError, PermissionDenied, NotFound):
            # Re-raise DRF exceptions as-is
            raise
        except Exception as e:
            # Catch any other exceptions and return proper error
            logger.error(f"Unexpected error creating consultation: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error creating consultation: {str(e)}")
    
    def update(self, request, *args, **kwargs):
        """
        Update consultation - handles both PUT and PATCH.
        Since consultation is OneToOneField, update can be called on list endpoint.
        """
        try:
            visit = self.get_visit()
            
            # Get or create consultation
            consultation = Consultation.objects.filter(visit=visit).first()
            
            if not consultation:
                from rest_framework.exceptions import NotFound
                raise NotFound(
                    detail="Consultation not found for this visit. "
                           "Create a consultation first."
                )
            
            # Enforce visit status
            self.check_visit_status(visit)
            
            # Enforce payment status
            self.check_payment_status(visit)
            
            # Partial update (PATCH) or full update (PUT)
            partial = kwargs.pop('partial', False)
            serializer = self.get_serializer(consultation, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            # Extract merge flag before saving (it's write_only, won't be saved to model)
            merge_with_patient = serializer.validated_data.pop('merge_with_patient_record', False)
            
            # Update consultation
            updated_consultation = serializer.save()
            
            # Merge with patient medical history if requested
            if merge_with_patient:
                self.merge_with_patient_history(updated_consultation, visit)
            
            # Audit log
            log_consultation_action(
                user=request.user,
                action='update',
                visit_id=visit.id,
                consultation_id=updated_consultation.id,
                request=request
            )
            
            return Response(serializer.data)
        except (DRFValidationError, PermissionDenied, NotFound):
            raise
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating consultation: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error updating consultation: {str(e)}")
    
    def partial_update(self, request, *args, **kwargs):
        """Handle PATCH requests on detail endpoint."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def get_allowed_methods(self):
        """
        Override to allow PATCH on list endpoint.
        Since consultation is OneToOneField, updates happen on list endpoint.
        """
        methods = super().get_allowed_methods()
        # Add PATCH to allowed methods for list endpoint
        if 'PATCH' not in methods:
            methods.append('PATCH')
        return methods
    
    def update_consultation(self, request, *args, **kwargs):
        """
        Custom method to handle PATCH on list endpoint.
        Since consultation is OneToOneField, updates happen on list endpoint.
        This method is called via as_view({'patch': 'update_consultation'})
        """
        # Route to update method with partial=True
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    
    def perform_update(self, serializer):
        """
        Update consultation with visit-scoped enforcement.
        
        Rules:
        1. Visit must be OPEN
        2. Payment must be CLEARED
        3. Audit log created
        """
        consultation = self.get_object()
        visit = consultation.visit
        
        # Enforce visit status
        self.check_visit_status(visit)
        
        # Enforce payment status
        self.check_payment_status(visit)
        
        # Extract merge flag before saving (it's write_only, won't be saved to model)
        merge_with_patient = serializer.validated_data.pop('merge_with_patient_record', False)
        
        # Update consultation
        updated_consultation = serializer.save()
        
        # Merge with patient medical history if requested
        if merge_with_patient:
            self.merge_with_patient_history(updated_consultation, visit)
        
        # Audit log
        log_consultation_action(
            user=self.request.user,
            action='update',
            visit_id=visit.id,
            consultation_id=updated_consultation.id,
            request=self.request
        )
        
        return updated_consultation
    
    def get_permissions(self):
        """
        Strict payment rules:
        - Read (retrieve/list): Registration must be paid before access to consultation.
        - Write (create/update/partial_update): Consultation must be paid before doctor starts encounter.
        """
        if self.action in ['retrieve', 'list']:
            # Block access to consultation until registration is paid
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated(), IsRegistrationPaymentCleared()]
        else:
            # Block doctor from starting encounter until consultation is paid
            return [IsDoctor(), IsVisitOpen(), IsConsultationPaymentCleared()]
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve consultation for visit.
        Read access is allowed for doctors even if visit is CLOSED.
        Returns 404 if consultation doesn't exist.
        """
        try:
            visit = self.get_visit()
            
            # Try to get consultation
            consultation = Consultation.objects.filter(visit_id=visit.id).prefetch_related('diagnosis_codes').first()
            
            if not consultation:
                raise NotFound(
                    detail="Consultation not found for this visit. "
                           "Create a consultation first."
                )
            
            # Audit log for read access
            try:
                log_consultation_action(
                    user=request.user,
                    action='read',
                    visit_id=visit.id,
                    consultation_id=consultation.id,
                    request=request
                )
            except Exception as e:
                # Log audit error but don't fail the request
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to log consultation read action: {str(e)}", exc_info=True)
            
            # Use extended serializer that includes diagnosis codes
            serializer = ConsultationWithCodesSerializer(consultation)
            return Response(serializer.data)
        except NotFound:
            # Re-raise NotFound as-is (DRF will handle it as 404)
            raise
        except Exception as e:
            # Catch any other exceptions and return proper error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving consultation: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error retrieving consultation: {str(e)}")
    
    def list(self, request, *args, **kwargs):
        """
        List consultation for visit (GET) or handle update on list endpoint (PATCH).
        Since consultation is OneToOneField, PATCH on list endpoint should update.
        Read access is allowed for doctors even if visit is CLOSED.
        """
        # If PATCH request, route to update method with partial=True
        if request.method == 'PATCH':
            kwargs['partial'] = True
            return self.update(request, *args, **kwargs)
        
        # Otherwise, handle as normal list (GET)
        try:
            # Get visit_id directly from kwargs to avoid recursion in get_visit()
            visit_id = kwargs.get('visit_id')
            if not visit_id:
                raise DRFValidationError("visit_id is required in URL")
            
            # Get visit directly without setting request.visit to avoid recursion
            visit = get_object_or_404(Visit, pk=visit_id)
            
            # Get consultation with minimal queries to avoid recursion
            consultation = Consultation.objects.filter(visit_id=visit_id).select_related('created_by').prefetch_related('diagnosis_codes').first()
            
            if consultation:
                # Audit log for read access (skip if it causes issues)
                try:
                    log_consultation_action(
                        user=request.user,
                        action='read',
                        visit_id=visit.id,
                        consultation_id=consultation.id,
                        request=request
                    )
                except Exception as e:
                    # Log audit error but don't fail the request
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to log consultation read action: {str(e)}", exc_info=True)
                
                # Use extended serializer that includes diagnosis codes
                serializer = ConsultationWithCodesSerializer(consultation)
                return Response([serializer.data])
            
            return Response([])
        except (DRFValidationError, NotFound):
            raise
        except Exception as e:
            # Catch any exceptions and return proper error
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error listing consultation: {str(e)}", exc_info=True, stack_info=True)
            raise DRFValidationError(f"Error listing consultation: {str(e)}")
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete consultation.
        Per EMR rules, consultations should not be deleted (soft-delete only).
        This endpoint is disabled for compliance.
        """
        raise PermissionDenied(
            detail="Consultations cannot be deleted. "
                   "Use soft-delete or update instead for compliance.",
            code='delete_forbidden'
        )
    
    @action(detail=False, methods=['get'], url_path='patient-consultations')
    def patient_consultations(self, request, *args, **kwargs):
        """
        Get all consultations for the patient in the current visit.
        
        GET /api/v1/visits/{visit_id}/consultation/patient-consultations/
        
        Returns all previous consultations for the same patient, excluding the current visit.
        Useful for viewing and copying data from previous consultations.
        
        Permission: Doctor-only (inherited from ViewSet permissions)
        """
        try:
            visit = self.get_visit()
            
            # Check if patient exists
            if not visit.patient:
                raise DRFValidationError("Visit does not have an associated patient.")
            
            patient = visit.patient
            
            # Get all consultations for this patient, excluding current visit
            consultations = Consultation.objects.filter(
                visit__patient=patient
            ).exclude(
                visit=visit
            ).select_related(
                'visit', 'created_by'
            ).prefetch_related(
                'diagnosis_codes'
            ).order_by('-created_at')
            
            # Serialize consultations
            serializer = ConsultationWithCodesSerializer(consultations, many=True)
            
            return Response({
                'count': consultations.count(),
                'results': serializer.data
            })
        except (DRFValidationError, NotFound, PermissionDenied):
            # Re-raise DRF exceptions as-is
            raise
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching patient consultations: {str(e)}", exc_info=True)
            raise DRFValidationError(f"Error fetching patient consultations: {str(e)}")
